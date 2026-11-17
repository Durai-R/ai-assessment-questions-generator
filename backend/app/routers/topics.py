from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import get_current_user
from app.mock_generation import GenerationError, suggest_topics
from app.schemas import SubjectRequest, TopicSuggestions


router = APIRouter(prefix="/api/topics", tags=["topics"])


@router.post("/suggest", response_model=TopicSuggestions)
async def topics_suggest(
    payload: SubjectRequest,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> TopicSuggestions:
    try:
        topics = await suggest_topics(payload.subject, request.app.state.settings)
    except GenerationError as exc:
        print(exc)
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return TopicSuggestions(topics=topics)
