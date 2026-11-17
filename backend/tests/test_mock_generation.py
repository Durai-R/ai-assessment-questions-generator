import asyncio
import json
import logging
from types import SimpleNamespace

import httpx
import pytest
from google import genai
from google.genai import errors, types
from pydantic import SecretStr

from app.config import Settings
from app.mock_generation import (
    GEMINI_MAX_RETRIES,
    GEMINI_RETRY_INITIAL_DELAY_SECONDS,
    GEMINI_RETRY_JITTER_SECONDS,
    GEMINI_TIMEOUT_MILLISECONDS,
    GEMINI_TOTAL_TIMEOUT_SECONDS,
    GenerationError,
    _gemini_json_schema,
    generate_questions,
    suggest_topics,
)
from app.schemas import GeneratedQuestions, QuestionGenerationRequest


def settings(api_key: str | None = "test-key") -> Settings:
    return Settings(
        _env_file=None,
        gemini_api_key=SecretStr(api_key) if api_key is not None else None,
        gemini_model="gemini-test",
    )


def test_gemini_model_defaults_and_trims_environment_value():
    assert settings().gemini_model == "gemini-test"
    assert Settings(_env_file=None).gemini_model == "gemini-3.5-flash-lite"
    assert Settings(_env_file=None, gemini_model=" custom-model ").gemini_model == "custom-model"
    assert Settings(_env_file=None, gemini_model=" ").gemini_model == "gemini-3.5-flash-lite"


def test_gemini_retry_budget_respects_minimum_and_total_deadlines():
    assert GEMINI_TIMEOUT_MILLISECONDS >= 10_000
    maximum_backoff = sum(
        GEMINI_RETRY_INITIAL_DELAY_SECONDS * (2**attempt) + GEMINI_RETRY_JITTER_SECONDS
        for attempt in range(GEMINI_MAX_RETRIES)
    )
    maximum_attempts = GEMINI_MAX_RETRIES + 1
    maximum_duration = maximum_attempts * GEMINI_TIMEOUT_MILLISECONDS / 1000 + maximum_backoff

    assert maximum_duration < GEMINI_TOTAL_TIMEOUT_SECONDS


def make_question(index: int) -> dict:
    return {
        "question_text": f"Question {index}",
        "options": [
            f"Option {index} A",
            f"Option {index} B",
            f"Option {index} C",
            f"Option {index} D",
        ],
        "correct_option_index": index % 4,
        "explanation": f"Explanation {index}",
    }


def install_fake_client(monkeypatch, response_text: str | None = None, error=None) -> list[dict]:
    calls = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            if error is not None:
                raise error
            return SimpleNamespace(text=response_text)

    class FakeClient:
        def __init__(self, *, api_key, http_options):
            calls.append(
                {
                    "api_key": api_key,
                    "timeout": http_options.timeout,
                    "retry_attempts": http_options.retry_options.attempts,
                }
            )
            self.models = FakeModels()

        def close(self):
            pass

    monkeypatch.setattr("app.mock_generation.genai.Client", FakeClient)
    return calls


def install_sequenced_fake_client(monkeypatch, outcomes) -> list[dict]:
    calls = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return SimpleNamespace(text=outcome)

    class FakeClient:
        def __init__(self, *, api_key, http_options):
            assert api_key == "test-key"
            assert http_options.retry_options.attempts == 1
            self.models = FakeModels()

        def close(self):
            pass

    monkeypatch.setattr("app.mock_generation.genai.Client", FakeClient)
    return calls


@pytest.mark.asyncio
async def test_topics_use_gemini_json_and_return_five_distinct_topics(monkeypatch):
    calls = install_fake_client(
        monkeypatch,
        json.dumps(
            {
                "topics": [
                    " Hooks ",
                    "Components",
                    "Props",
                    "State Management",
                    "Routing",
                ]
            }
        ),
    )

    topics = await suggest_topics("React.js", settings())

    assert topics == ["Hooks", "Components", "Props", "State Management", "Routing"]
    assert calls[0] == {
        "api_key": "test-key",
        "timeout": GEMINI_TIMEOUT_MILLISECONDS,
        "retry_attempts": 1,
    }
    request = calls[1]
    assert request["model"] == "gemini-test"
    assert request["config"].response_mime_type == "application/json"
    schema = request["config"].response_json_schema
    assert request["config"].response_schema is None
    assert schema["additionalProperties"] is False
    assert schema["properties"]["topics"]["maxItems"] == 5
    assert "minLength" not in json.dumps(schema)
    assert "React.js" in request["contents"]


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [1, 5, 30])
async def test_questions_use_gemini_and_return_exact_requested_count(monkeypatch, count):
    calls = install_fake_client(
        monkeypatch,
        json.dumps({"questions": [make_question(index) for index in range(count)]}),
    )
    payload = QuestionGenerationRequest(
        subject="React.js",
        topic="Hooks",
        difficulty="Hard",
        count=count,
    )

    questions = await generate_questions(payload, settings())

    assert len(questions) == count
    assert calls[1]["config"].response_schema is None
    assert "$defs" in calls[1]["config"].response_json_schema
    assert calls[1]["config"].response_mime_type == "application/json"
    assert "maxLength" not in json.dumps(calls[1]["config"].response_json_schema)
    assert '"React.js"' in calls[1]["contents"]
    assert '"Hooks"' in calls[1]["contents"]
    assert "Difficulty: Hard" in calls[1]["contents"]
    assert f"Question count: {count}" in calls[1]["contents"]


@pytest.mark.asyncio
async def test_fewer_questions_are_rejected(monkeypatch):
    install_fake_client(monkeypatch, json.dumps({"questions": [make_question(1)]}))
    payload = QuestionGenerationRequest(
        subject="React.js",
        topic="Hooks",
        difficulty="Medium",
        count=5,
    )

    with pytest.raises(GenerationError, match="fewer questions than requested") as exc_info:
        await generate_questions(payload, settings())

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_invalid_options_are_rejected_without_exposing_validation_details(monkeypatch):
    invalid = make_question(1)
    invalid["options"] = ["same", " Same ", "third", "fourth"]
    install_fake_client(monkeypatch, json.dumps({"questions": [invalid]}))
    payload = QuestionGenerationRequest(
        subject="React.js",
        topic="Hooks",
        difficulty="Medium",
        count=1,
    )

    with pytest.raises(GenerationError, match="Gemini returned an invalid response") as exc_info:
        await generate_questions(payload, settings())

    assert exc_info.value.status_code == 502
    assert "same" not in exc_info.value.detail


@pytest.mark.asyncio
async def test_duplicate_topics_that_leave_fewer_than_five_are_rejected(monkeypatch):
    install_fake_client(
        monkeypatch,
        json.dumps({"topics": ["Hooks", "Components", "Props", "Hooks", "Routing"]}),
    )

    with pytest.raises(GenerationError, match="fewer than five distinct topics"):
        await suggest_topics("React.js", settings())


@pytest.mark.asyncio
async def test_missing_api_key_returns_configuration_error_without_calling_gemini():
    with pytest.raises(GenerationError, match="GEMINI_API_KEY") as exc_info:
        await suggest_topics("React.js", settings(api_key=None))

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_quota_failure_is_safe_and_maps_to_rate_limit(monkeypatch):
    calls = install_fake_client(
        monkeypatch,
        error=errors.APIError(429, {"error": {"message": "sensitive provider response"}}),
    )

    with pytest.raises(GenerationError, match="usage limit") as exc_info:
        await suggest_topics("React.js", settings())

    assert exc_info.value.status_code == 429
    assert "sensitive provider response" not in exc_info.value.detail
    assert sum("model" in call for call in calls) == 1


@pytest.mark.asyncio
async def test_timeout_is_safe_and_maps_to_gateway_timeout(monkeypatch):
    install_fake_client(monkeypatch, error=httpx.TimeoutException("sensitive provider response"))

    with pytest.raises(GenerationError, match="timed out") as exc_info:
        await suggest_topics("React.js", settings())

    assert exc_info.value.status_code == 504
    assert "sensitive provider response" not in exc_info.value.detail


@pytest.mark.asyncio
async def test_total_generation_timeout_is_bounded(monkeypatch):
    async def slow_provider_call(*_args):
        await asyncio.sleep(0.2)

    monkeypatch.setattr("app.mock_generation.asyncio.to_thread", slow_provider_call)
    monkeypatch.setattr("app.mock_generation.GEMINI_TOTAL_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(GenerationError, match="timed out") as exc_info:
        await suggest_topics("React.js", settings())

    assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_service_unavailable_retries_then_succeeds(monkeypatch):
    topics_response = json.dumps(
        {"topics": ["Hooks", "Components", "Props", "State", "Routing"]}
    )
    calls = install_sequenced_fake_client(
        monkeypatch,
        [
            errors.APIError(503, {"error": {"message": "temporary failure"}}),
            errors.APIError(503, {"error": {"message": "temporary failure"}}),
            topics_response,
        ],
    )
    delays = []
    jitter_bounds = []

    async def fake_sleep(delay):
        delays.append(delay)

    def fake_uniform(lower, upper):
        jitter_bounds.append((lower, upper))
        return upper / 2

    monkeypatch.setattr("app.mock_generation.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("app.mock_generation.random.uniform", fake_uniform)

    result = await suggest_topics("React.js", settings())

    assert result == ["Hooks", "Components", "Props", "State", "Routing"]
    assert len(calls) == 3
    assert delays == [0.35, 0.6]
    assert jitter_bounds == [(0, 0.2), (0, 0.2)]


@pytest.mark.asyncio
async def test_service_unavailable_returns_503_after_two_retries(monkeypatch, caplog, capsys):
    calls = install_sequenced_fake_client(
        monkeypatch,
        [
            errors.APIError(503, {"error": {"message": "temporary failure"}}),
            errors.APIError(503, {"error": {"message": "temporary failure"}}),
            errors.APIError(503, {"error": {"message": "temporary failure"}}),
        ],
    )

    async def fake_sleep(_delay):
        pass

    monkeypatch.setattr("app.mock_generation.asyncio.sleep", fake_sleep)

    with caplog.at_level(logging.WARNING, logger="app.mock_generation"):
        with pytest.raises(GenerationError) as exc_info:
            await suggest_topics("React.js", settings())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == (
        "The AI service is temporarily busy. Please wait a moment and try again."
    )
    assert len(calls) == 3
    assert sum("503" in record.message for record in caplog.records) == 3
    assert all("temporary failure" not in record.message for record in caplog.records)
    assert capsys.readouterr().out == ""


def test_sdk_serializes_schema_in_gemini_json_schema_field():
    captured = {}

    def respond(request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"questions":[]}'}]}}]},
        )

    transport = httpx.Client(transport=httpx.MockTransport(respond))
    client = genai.Client(
        api_key="local-test-only",
        http_options=types.HttpOptions(httpx_client=transport),
    )
    try:
        client.models.generate_content(
            model="gemini-test",
            contents="test",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=_gemini_json_schema(GeneratedQuestions),
            ),
        )
    finally:
        client.close()
        transport.close()

    config = captured["body"]["generationConfig"]
    schema_json = json.dumps(config["responseJsonSchema"])
    assert "responseSchema" not in config
    assert "additionalProperties" in schema_json
    assert "additional_properties" not in schema_json
    assert "minLength" not in schema_json
    assert "maxLength" not in schema_json
