import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pymongo import ReturnDocument
from pymongo.errors import OperationFailure

from app.auth import get_current_user
from app.mock_generation import GenerationError, generate_questions as generate_gemini_questions
from app.schemas import (
    BulkQuestionResponse,
    DraftQuestion,
    FilterOptions,
    GeneratedQuestions,
    QuestionBatch,
    QuestionGenerationRequest,
    QuestionListResponse,
    QuestionResponse,
    QuestionUpdate,
)


router = APIRouter(prefix="/api/questions", tags=["questions"])


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def serialize_question(document: dict) -> QuestionResponse:
    return QuestionResponse(
        id=str(document["_id"]),
        subject=document["subject"],
        topic=document["topic"],
        difficulty=document["difficulty"],
        question_text=document["question_text"],
        options=document["options"],
        correct_option_index=document["correct_option_index"],
        explanation=document["explanation"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def parse_question_id(question_id: str) -> ObjectId | None:
    try:
        return ObjectId(question_id)
    except (InvalidId, TypeError):
        return None


@router.post("/generate", response_model=GeneratedQuestions)
async def generate_questions(
    payload: QuestionGenerationRequest,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> GeneratedQuestions:
    try:
        questions = await generate_gemini_questions(payload, request.app.state.settings)
    except GenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return GeneratedQuestions(questions=questions)


@router.post("/bulk", response_model=BulkQuestionResponse, status_code=status.HTTP_201_CREATED)
async def save_questions(
    payload: QuestionBatch,
    request: Request,
    user: dict = Depends(get_current_user),
) -> BulkQuestionResponse:
    now = utc_now()
    documents = [
        {
            "user_id": user["_id"],
            "subject": payload.subject,
            "topic": payload.topic,
            "difficulty": payload.difficulty,
            **question.model_dump(),
            "created_at": now,
            "updated_at": now,
        }
        for question in payload.questions
    ]

    try:
        async with request.app.state.mongo_client.start_session() as session:
            async with await session.start_transaction():
                result = await request.app.state.database.questions.insert_many(
                    documents,
                    ordered=True,
                    session=session,
                )
    except OperationFailure as exc:
        if exc.code in (20, 303):
            raise HTTPException(
                status_code=503,
                detail="Bulk save requires a MongoDB replica set with transaction support.",
            ) from exc
        raise

    saved = [
        serialize_question({**document, "_id": inserted_id})
        for document, inserted_id in zip(documents, result.inserted_ids)
    ]
    return BulkQuestionResponse(items=saved)


@router.get("/filter-options", response_model=FilterOptions)
async def filter_options(
    request: Request,
    subject: str | None = Query(default=None, min_length=1, max_length=160),
    user: dict = Depends(get_current_user),
) -> FilterOptions:
    collection = request.app.state.database.questions
    user_filter = {"user_id": user["_id"]}
    subjects = await collection.distinct("subject", user_filter)

    topic_filter = dict(user_filter)
    if subject is not None:
        topic_filter["subject"] = subject
    topics = await collection.distinct("topic", topic_filter)
    return FilterOptions(
        subjects=sorted(subjects),
        topics=sorted(topics),
    )


@router.get("", response_model=QuestionListResponse)
async def list_questions(
    request: Request,
    search: str | None = Query(default=None, max_length=120),
    subject: str | None = Query(default=None, min_length=1, max_length=160),
    topic: str | None = Query(default=None, min_length=1, max_length=160),
    difficulty: str | None = Query(default=None, pattern="^(Easy|Medium|Hard)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    user: dict = Depends(get_current_user),
) -> QuestionListResponse:
    filters: dict = {"user_id": user["_id"]}
    if search and search.strip():
        filters["question_text"] = {"$regex": re.escape(search.strip()), "$options": "i"}
    if subject is not None:
        filters["subject"] = subject
    if topic is not None:
        filters["topic"] = topic
    if difficulty is not None:
        filters["difficulty"] = difficulty

    collection = request.app.state.database.questions
    total = await collection.count_documents(filters)
    skip = (page - 1) * page_size
    if skip > 2**63 - 1:
        return QuestionListResponse(items=[], total=total, page=page, page_size=page_size)
    cursor = (
        collection.find(filters)
        .sort([("created_at", -1), ("_id", -1)])
        .skip(skip)
        .limit(page_size)
    )
    items = [serialize_question(document) async for document in cursor]
    return QuestionListResponse(items=items, total=total, page=page, page_size=page_size)


@router.patch("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: str,
    payload: QuestionUpdate,
    request: Request,
    user: dict = Depends(get_current_user),
) -> QuestionResponse:
    object_id = parse_question_id(question_id)
    if object_id is None:
        raise HTTPException(status_code=404, detail="Question not found.")

    collection = request.app.state.database.questions
    scope = {"_id": object_id, "user_id": user["_id"]}
    existing = await collection.find_one(scope)
    if existing is None:
        raise HTTPException(status_code=404, detail="Question not found.")

    merged = {
        "subject": existing["subject"],
        "topic": existing["topic"],
        "difficulty": existing["difficulty"],
        "question_text": existing["question_text"],
        "options": existing["options"],
        "correct_option_index": existing["correct_option_index"],
        "explanation": existing["explanation"],
    }
    merged.update(payload.model_dump(exclude_unset=True))
    validated = QuestionBatch(
        subject=merged["subject"],
        topic=merged["topic"],
        difficulty=merged["difficulty"],
        questions=[
            DraftQuestion(
                question_text=merged["question_text"],
                options=merged["options"],
                correct_option_index=merged["correct_option_index"],
                explanation=merged["explanation"],
            )
        ],
    )
    question = validated.questions[0].model_dump()
    update_fields = {
        "subject": validated.subject,
        "topic": validated.topic,
        "difficulty": validated.difficulty,
        **question,
        "updated_at": utc_now(),
    }
    updated = await collection.find_one_and_update(
        scope,
        {"$set": update_fields},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Question not found.")
    return serialize_question(updated)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
) -> Response:
    object_id = parse_question_id(question_id)
    if object_id is None:
        raise HTTPException(status_code=404, detail="Question not found.")
    result = await request.app.state.database.questions.delete_one(
        {"_id": object_id, "user_id": user["_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Question not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
