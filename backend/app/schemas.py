from datetime import datetime
from typing import Annotated, Literal, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)


Difficulty = Literal["Easy", "Medium", "Hard"]
AnswerIndex: TypeAlias = Annotated[StrictInt, Field(ge=0, le=3)]
AnswerOption: TypeAlias = Annotated[str, Field(min_length=1, max_length=500)]


def _trim_distinct_options(options: list[str]) -> list[str]:
    trimmed = [option.strip() for option in options]
    if any(not option for option in trimmed):
        raise ValueError("Options must not be empty.")
    if len({option.casefold() for option in trimmed}) != 4:
        raise ValueError("Options must be distinct.")
    return trimmed


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Credentials(StrictModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().casefold() if isinstance(value, str) else value


class UserResponse(StrictModel):
    id: str
    email: EmailStr


class SubjectRequest(StrictModel):
    subject: str = Field(min_length=1, max_length=160)

    @field_validator("subject")
    @classmethod
    def trim_subject(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Subject must not be empty.")
        return value


class TopicSuggestions(StrictModel):
    topics: list[Annotated[str, Field(min_length=1, max_length=160)]] = Field(min_length=5, max_length=5)

    @field_validator("topics")
    @classmethod
    def clean_topics(cls, topics: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for topic in topics:
            topic = topic.strip()
            normalized = topic.casefold()
            if not topic:
                raise ValueError("Topics must not be empty.")
            if normalized not in seen:
                cleaned.append(topic)
                seen.add(normalized)
        if not cleaned:
            raise ValueError("At least one distinct topic is required.")
        return cleaned


class DraftQuestion(StrictModel):
    question_text: str = Field(min_length=1, max_length=2000)
    options: list[AnswerOption] = Field(min_length=4, max_length=4)
    correct_option_index: AnswerIndex
    explanation: str = Field(min_length=1, max_length=4000)

    @field_validator("question_text", "explanation")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Text must not be empty.")
        return value

    @field_validator("options")
    @classmethod
    def trim_distinct_options(cls, options: list[str]) -> list[str]:
        return _trim_distinct_options(options)


class QuestionGenerationRequest(SubjectRequest):
    topic: str = Field(min_length=1, max_length=160)
    difficulty: Difficulty
    count: Annotated[StrictInt, Field(ge=1, le=30)]

    @field_validator("topic")
    @classmethod
    def trim_topic(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Topic must not be empty.")
        return value


class GeneratedQuestions(StrictModel):
    questions: list[DraftQuestion] = Field(min_length=1, max_length=30)


class QuestionBatch(StrictModel):
    subject: str = Field(min_length=1, max_length=160)
    topic: str = Field(min_length=1, max_length=160)
    difficulty: Difficulty
    questions: list[DraftQuestion] = Field(min_length=1, max_length=30)

    @field_validator("subject", "topic")
    @classmethod
    def trim_metadata(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Subject and topic must not be empty.")
        return value


class QuestionUpdate(StrictModel):
    subject: str | None = Field(default=None, min_length=1, max_length=160)
    topic: str | None = Field(default=None, min_length=1, max_length=160)
    difficulty: Difficulty | None = None
    question_text: str | None = Field(default=None, min_length=1, max_length=2000)
    options: list[AnswerOption] | None = Field(default=None, min_length=4, max_length=4)
    correct_option_index: AnswerIndex | None = None
    explanation: str | None = Field(default=None, min_length=1, max_length=4000)

    @field_validator("subject", "topic", "question_text", "explanation")
    @classmethod
    def trim_update_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Text must not be empty.")
        return value

    @field_validator("options")
    @classmethod
    def validate_update_options(cls, options: list[str] | None) -> list[str] | None:
        if options is None:
            return None
        return _trim_distinct_options(options)

    @model_validator(mode="after")
    def require_editable_fields(self) -> "QuestionUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one editable field is required.")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Editable fields must not be null.")
        return self


class QuestionResponse(StrictModel):
    id: str
    subject: str
    topic: str
    difficulty: Difficulty
    question_text: str
    options: list[str]
    correct_option_index: AnswerIndex
    explanation: str
    created_at: datetime
    updated_at: datetime


class BulkQuestionResponse(StrictModel):
    items: list[QuestionResponse]


class QuestionListResponse(StrictModel):
    items: list[QuestionResponse]
    total: int
    page: int
    page_size: int


class FilterOptions(StrictModel):
    subjects: list[str]
    topics: list[str]
