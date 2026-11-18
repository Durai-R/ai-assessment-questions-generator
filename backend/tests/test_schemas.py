import pytest
from pydantic import ValidationError

from app.schemas import (
    Credentials,
    DraftQuestion,
    QuestionGenerationRequest,
    QuestionUpdate,
    TopicSuggestions,
)


@pytest.mark.parametrize(
    "password",
    ["short", "p" * 129],
)
def test_credentials_password_length_must_be_between_eight_and_128_characters(password):
    with pytest.raises(ValidationError):
        Credentials(email="user@example.com", password=password)


def test_credentials_accept_passwords_at_both_length_boundaries():
    assert len(Credentials(email="user@example.com", password="p" * 8).password) == 8
    assert len(Credentials(email="user@example.com", password="p" * 128).password) == 128


def test_question_text_and_options_are_trimmed_and_unique_case_insensitively():
    question = DraftQuestion(
        question_text="  What is a hook?  ",
        options=[" A ", "b", "C", "d"],
        correct_option_index=2,
        explanation="  A short explanation.  ",
    )
    assert question.question_text == "What is a hook?"
    assert question.options == ["A", "b", "C", "d"]
    assert question.explanation == "A short explanation."

    with pytest.raises(ValidationError):
        DraftQuestion(
            question_text="Question",
            options=["same", " Same ", "third", "fourth"],
            correct_option_index=0,
            explanation="Explanation",
        )


@pytest.mark.parametrize("count", [0, 31, "2", True])
def test_generation_count_is_an_integer_between_one_and_thirty(count):
    with pytest.raises(ValidationError):
        QuestionGenerationRequest(
            subject="React",
            topic="Hooks",
            difficulty="Medium",
            count=count,
        )


def test_topic_suggestions_are_trimmed_and_deduplicated():
    assert TopicSuggestions(
        topics=[" Hooks ", "State", "hooks", "Components", "Routing"]
    ).topics == ["Hooks", "State", "Components", "Routing"]


def test_question_updates_use_the_same_option_validation():
    update = QuestionUpdate(options=[" A ", "b", "C", "d"])
    assert update.options == ["A", "b", "C", "d"]

    with pytest.raises(ValidationError):
        QuestionUpdate(options=["same", " Same ", "third", "fourth"])
