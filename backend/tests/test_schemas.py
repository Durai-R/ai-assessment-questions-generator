import pytest
from pydantic import ValidationError

from app.schemas import DraftQuestion, QuestionGenerationRequest, QuestionUpdate, TopicSuggestions


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
