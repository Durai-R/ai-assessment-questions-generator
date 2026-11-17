from types import SimpleNamespace

import httpx
import pytest
from bson import ObjectId

from app.auth import get_current_user
from app.config import Settings
from app.main import create_app


ORIGIN = "http://localhost:5173"


class FakeTransaction:
    def __init__(self) -> None:
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, error_type, _error, _traceback):
        self.committed = error_type is None


class FakeSession:
    def __init__(self) -> None:
        self.transaction = FakeTransaction()

    async def __aenter__(self):
        return self

    async def __aexit__(self, _error_type, _error, _traceback):
        return None

    async def start_transaction(self):
        return self.transaction


class FakeMongoClient:
    def __init__(self) -> None:
        self.session = FakeSession()

    def start_session(self):
        return self.session


class FakeQuestions:
    def __init__(self) -> None:
        self.rows = []
        self.insert_calls = 0

    async def insert_many(self, documents, *, ordered, session):
        self.insert_calls += 1
        assert ordered
        assert session is not None
        inserted_ids = []
        for document in documents:
            question_id = ObjectId()
            self.rows.append({**document, "_id": question_id})
            inserted_ids.append(question_id)
        return SimpleNamespace(inserted_ids=inserted_ids)


def payload(questions):
    return {
        "subject": "React.js",
        "topic": "Hooks",
        "difficulty": "Medium",
        "questions": questions,
    }


def question(text):
    return {
        "question_text": text,
        "options": ["useState", "useEffect", "useMemo", "useRef"],
        "correct_option_index": 0,
        "explanation": "A reviewed mock explanation.",
    }


@pytest.mark.asyncio
async def test_bulk_save_commits_only_valid_reviewed_rows():
    application = create_app(
        Settings(
            jwt_secret="test-only-secret-that-is-at-least-thirty-two-characters",
            frontend_origin=ORIGIN,
        )
    )
    user_id = ObjectId()
    application.dependency_overrides[get_current_user] = lambda: {"_id": user_id}
    mongo_client = FakeMongoClient()
    questions = FakeQuestions()
    application.state.mongo_client = mongo_client
    application.state.database = SimpleNamespace(questions=questions)
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Origin": ORIGIN},
    ) as client:
        invalid = await client.post(
            "/api/questions/bulk",
            json=payload([question("valid"), {**question("invalid"), "options": ["same"] * 4}]),
        )
        assert invalid.status_code == 422
        assert questions.insert_calls == 0

        saved = await client.post(
            "/api/questions/bulk",
            json=payload([question("edited draft"), question("second reviewed draft")]),
        )

    assert saved.status_code == 201
    assert [row["question_text"] for row in saved.json()["items"]] == [
        "edited draft",
        "second reviewed draft",
    ]
    assert len(questions.rows) == 2
    assert all(row["user_id"] == user_id for row in questions.rows)
    assert all(row["created_at"] == row["updated_at"] for row in questions.rows)
    assert mongo_client.session.transaction.committed
