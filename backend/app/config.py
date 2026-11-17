from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    mongodb_uri: str = "mongodb://localhost:27017/?replicaSet=rs0"
    mongodb_db_name: str = "ai_assessment"
    jwt_secret: str = "development-only-change-this-jwt-secret"
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_expiry_minutes: int = Field(default=60, ge=1, le=10080)
    frontend_origin: str = "http://localhost:5173"
    trusted_origins: str = ""
    environment: str = "development"
    auth_cookie_name: str = "assessment_access_token"
    auth_cookie_secure: bool | None = None
    auth_cookie_domain: str | None = None
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.5-flash-lite"

    @field_validator("frontend_origin")
    @classmethod
    def normalize_frontend_origin(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @field_validator("trusted_origins", mode="before")
    @classmethod
    def normalize_trusted_origins(cls, value: object) -> str:
        if not isinstance(value, str):
            return ""
        return ",".join(origin.strip().rstrip("/") for origin in value.split(",") if origin.strip())

    @field_validator("auth_cookie_domain", mode="before")
    @classmethod
    def normalize_cookie_domain(cls, value: object) -> str | None:
        if not isinstance(value, str):
            return value
        value = value.strip()
        return value or None

    @field_validator("gemini_model", mode="before")
    @classmethod
    def default_gemini_model(cls, value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            return "gemini-3.5-flash-lite"
        return value.strip()

    @model_validator(mode="after")
    def check_jwt_secret(self) -> "Settings":
        if self.environment.lower() == "production":
            if len(self.jwt_secret) < 32 or self.jwt_secret.lower().startswith("replace-with-"):
                raise ValueError("JWT_SECRET must be a unique secret of at least 32 characters.")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        additional_origins = [origin for origin in self.trusted_origins.split(",") if origin]
        return list(dict.fromkeys([self.frontend_origin, *additional_origins]))

    @property
    def secure_auth_cookie(self) -> bool:
        return self.environment.lower() == "production" or self.auth_cookie_secure is True
