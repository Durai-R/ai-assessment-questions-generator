import json

import httpx
import pytest
from bson import ObjectId

from app.auth import get_current_user
from app.config import Settings
from app.main import create_app
from app.mock_generation import GenerationError
from app.schemas import GeneratedQuestions, TopicSuggestions


ORIGIN = "http://localhost:5173"


@pytest.mark.asyncio
async def test_generation_routes_keep_response_contract_and_do_not_save(monkeypatch):
    async def fake_gemini_response(_settings, prompt, response_schema):
        if response_schema is TopicSuggestions:
            return json.dumps(
                {
                    "topics": [
                        "Hooks",
                        "Components",
                        "Props",
                        "State Management",
                        "Routing",
                    ]
                }
            )
        assert response_schema is GeneratedQuestions
        count = int(prompt.rsplit("Question count: ", 1)[1])
        return json.dumps(
            {
                "questions": [
                    {
                        "question_text": f"Generated React Hooks question {number}",
                        "options": [
                            f"Option {number} A",
                            f"Option {number} B",
                            f"Option {number} C",
                            f"Option {number} D",
                        ],
                        "correct_option_index": (number - 1) % 4,
                        "explanation": f"Explanation for question {number}",
                    }
                    for number in range(1, count + 1)
                ]
            }
        )

    monkeypatch.setattr("app.mock_generation._request_json", fake_gemini_response)
    application = create_app(
        Settings(
            _env_file=None,
            jwt_secret="test-only-secret-that-is-at-least-thirty-two-characters",
            frontend_origin=ORIGIN,
        )
    )
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Origin": ORIGIN},
    ) as client:
        unauthorized = await client.post(
            "/api/topics/suggest",
            json={"subject": "React.js"},
        )
        assert unauthorized.status_code == 401

        application.dependency_overrides[get_current_user] = lambda: {"_id": ObjectId()}
        topics = await client.post(
            "/api/topics/suggest",
            json={"subject": " React.js "},
        )
        assert topics.status_code == 200
        assert topics.json() == {
            "topics": ["Hooks", "Components", "Props", "State Management", "Routing"]
        }

        for count in (1, 5, 30):
            generated = await client.post(
                "/api/questions/generate",
                json={
                    "subject": "React.js",
                    "topic": "Hooks",
                    "difficulty": "Medium",
                    "count": count,
                },
            )
            assert generated.status_code == 200
            assert len(generated.json()["questions"]) == count
            assert generated.json()["questions"][0]["question_text"] == (
                "Generated React Hooks question 1"
            )

        assert application.state.database is None


@pytest.mark.asyncio
async def test_missing_gemini_configuration_is_a_clear_generation_error():
    application = create_app(
        Settings(
            _env_file=None,
            jwt_secret="test-only-secret-that-is-at-least-thirty-two-characters",
            frontend_origin=ORIGIN,
        )
    )
    application.dependency_overrides[get_current_user] = lambda: {"_id": ObjectId()}
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Origin": ORIGIN},
    ) as client:
        response = await client.post(
            "/api/questions/generate",
            json={
                "subject": "React.js",
                "topic": "Hooks",
                "difficulty": "Medium",
                "count": 1,
            },
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "AI generation is not configured. Set GEMINI_API_KEY on the backend."
    }


@pytest.mark.asyncio
async def test_exhausted_gemini_503_is_returned_as_a_safe_service_error(monkeypatch):
    async def unavailable(*_args):
        raise GenerationError(
            503,
            "The AI service is temporarily busy. Please wait a moment and try again.",
        )

    monkeypatch.setattr("app.mock_generation._request_json", unavailable)
    application = create_app(
        Settings(
            _env_file=None,
            jwt_secret="test-only-secret-that-is-at-least-thirty-two-characters",
            frontend_origin=ORIGIN,
        )
    )
    application.dependency_overrides[get_current_user] = lambda: {"_id": ObjectId()}
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Origin": ORIGIN},
    ) as client:
        response = await client.post("/api/topics/suggest", json={"subject": "React.js"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "The AI service is temporarily busy. Please wait a moment and try again."
    }
