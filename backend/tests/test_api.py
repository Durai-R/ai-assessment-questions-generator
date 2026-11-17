import os
import uuid

import httpx
import pytest
import pytest_asyncio
from bson import ObjectId
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from app.config import Settings
from app.main import create_app


ORIGIN = "http://localhost:5173"
PASSWORD = "assessment-password-123"


def draft(index: int, text: str | None = None) -> dict:
    return {
        "question_text": text or f"Question {index}",
        "options": [f"Option {index} A", f"Option {index} B", f"Option {index} C", f"Option {index} D"],
        "correct_option_index": 1,
        "explanation": f"Explanation {index}",
    }


def bulk_payload(subject: str, topic: str, difficulty: str, questions: list[dict]) -> dict:
    return {
        "subject": subject,
        "topic": topic,
        "difficulty": difficulty,
        "questions": questions,
    }


@pytest_asyncio.fixture
async def api():
    uri = os.getenv("MONGO_TEST_URI", "mongodb://localhost:27017/?replicaSet=rs0")
    client = AsyncMongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=1200)
    try:
        await client.admin.command("ping")
    except PyMongoError:
        await client.close()
        pytest.skip("Set MONGO_TEST_URI to a reachable MongoDB replica set to run API integration tests.")

    database_name = "ai_assessment_test_" + uuid.uuid4().hex
    database = client[database_name]
    settings = Settings(
        mongodb_uri=uri,
        mongodb_db_name=database_name,
        jwt_secret="test-only-secret-that-is-at-least-thirty-two-characters",
        frontend_origin=ORIGIN,
    )
    application = create_app(settings, database=database, mongo_client=client)
    try:
        async with application.router.lifespan_context(application):
            transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={"Origin": ORIGIN},
            ) as http_client:
                yield http_client, database, application
    finally:
        await client.drop_database(database_name)
        await client.close()


async def register(client: httpx.AsyncClient, email: str) -> dict:
    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text

    login_response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login_response.status_code == 200, login_response.text
    assert login_response.json()["email"] == email
    return response.json()


@pytest.mark.asyncio
async def test_question_save_filters_pagination_and_user_ownership(api):
    client, database, application = api
    owner = await register(client, "owner@example.com")

    invalid_batch = await client.post(
        "/api/questions/bulk",
        json=bulk_payload(
            "React.js",
            "Hooks",
            "Medium",
            [draft(0), {**draft(1), "options": ["same", "same", "third", "fourth"]}],
        ),
    )
    assert invalid_batch.status_code == 422
    assert await database.questions.count_documents({}) == 0

    reviewed = [draft(1, "useEffect question one"), draft(2, "edited useEffect question")]
    saved = await client.post(
        "/api/questions/bulk",
        json=bulk_payload("React.js", "Hooks", "Medium", reviewed),
    )
    assert saved.status_code == 201
    assert [row["question_text"] for row in saved.json()["items"]] == [
        "useEffect question one",
        "edited useEffect question",
    ]
    assert await database.questions.count_documents({"user_id": ObjectId(owner["id"])}) == 2
    first_id = saved.json()["items"][0]["id"]

    await client.post(
        "/api/questions/bulk",
        json=bulk_payload("React.js", "Components", "Easy", [draft(20, "component question")]),
    )
    await client.post(
        "/api/questions/bulk",
        json=bulk_payload("Python", "Generators", "Medium", [draft(21, "generator question")]),
    )

    paged_ids = []
    for page, expected_count in ((1, 1), (2, 1)):
        listed = await client.get(
            "/api/questions",
            params={
                "search": "Effect",
                "subject": "React.js",
                "topic": "Hooks",
                "difficulty": "Medium",
                "page": page,
                "page_size": 1,
            },
        )
        assert listed.status_code == 200
        assert listed.json()["total"] == 2
        assert listed.json()["page"] == page
        assert len(listed.json()["items"]) == expected_count
        paged_ids.extend(row["id"] for row in listed.json()["items"])
    assert len(set(paged_ids)) == 2

    literal_search = await client.get(
        "/api/questions",
        params={"search": "use.", "subject": "React.js"},
    )
    assert literal_search.json()["total"] == 0
    options = (await client.get("/api/questions/filter-options")).json()
    assert options == {
        "subjects": ["Python", "React.js"],
        "topics": ["Components", "Generators", "Hooks"],
    }
    scoped_options = (
        await client.get("/api/questions/filter-options", params={"subject": "React.js"})
    ).json()
    assert scoped_options == {
        "subjects": ["Python", "React.js"],
        "topics": ["Components", "Hooks"],
    }

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application, raise_app_exceptions=False),
        base_url="http://test",
        headers={"Origin": ORIGIN},
    ) as other:
        await register(other, "other@example.com")
        assert (await other.get("/api/questions")).json()["total"] == 0
        assert (await other.get("/api/questions/filter-options")).json() == {
            "subjects": [],
            "topics": [],
        }
        assert (
            await other.patch(
                f"/api/questions/{first_id}",
                json={"question_text": "forbidden edit"},
            )
        ).status_code == 404
        assert (await other.delete(f"/api/questions/{first_id}")).status_code == 404

    before = await database.questions.find_one(
        {"_id": ObjectId(first_id), "user_id": ObjectId(owner["id"])}
    )
    updated = await client.patch(
        f"/api/questions/{first_id}",
        json={
            "question_text": "Updated saved question",
            "options": ["one", "two", "three", "four"],
            "correct_option_index": 2,
            "explanation": "Updated explanation",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["question_text"] == "Updated saved question"
    stored = await database.questions.find_one({"_id": before["_id"]})
    assert stored["updated_at"] >= before["updated_at"]
    assert (await client.delete(f"/api/questions/{first_id}")).status_code == 204
    assert (await client.delete("/api/questions/not-an-object-id")).status_code == 404
