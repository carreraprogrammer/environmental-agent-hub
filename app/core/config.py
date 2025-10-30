"""Application configuration loaded from environment variables."""

from __future__ import annotations

from typing import List

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        validate_assignment=True,
    )

    # API Settings
    API_TITLE: str = Field(default="Agent Hub")
    API_VERSION: str = Field(default="2.0.0")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")

    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])

    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(
        default="changeme-openai",
        description="OpenAI API key",
    )
    OPENAI_MODEL: str = Field(default="gpt-4-vision-preview")
    OPENAI_TIMEOUT: int = Field(default=30, ge=5, le=60)
    OPENAI_MAX_RETRIES: int = Field(default=3, ge=1, le=5)

    # Google Gemini Configuration
    GOOGLE_API_KEY: str = Field(
        default="changeme-google",
        description="Google Gemini API key",
    )
    GOOGLE_MODEL: str = Field(default="gemini-pro-vision")
    GOOGLE_RATE_LIMIT_PER_MIN: int = Field(default=50, ge=1, le=60)
    GOOGLE_DAILY_LIMIT: int = Field(default=1400, ge=1, le=1500)

    # Roboflow Configuration
    ROBOFLOW_API_KEY: str = Field(
        default="changeme-roboflow",
        description="Roboflow API key",
    )
    ROBOFLOW_MODEL_ID: str = Field(
        default="environmental-agent-hub/waste-classifier/1",
        description="Model ID format: workspace/project/version",
    )
    ROBOFLOW_WORKSPACE: str = Field(default="environmental-agent-hub")
    ROBOFLOW_CONFIDENCE_THRESHOLD: float = Field(default=0.4, ge=0.0, le=1.0)

    # Active classifier
    CLASSIFIER_MODEL: str = Field(
        default="openai-gpt4",
        description="Active model: openai-gpt4|gemini|roboflow",
    )

    # Anthropic Configuration (Optional)
    ANTHROPIC_API_KEY: str | None = Field(default=None)

    # AWS S3 Configuration (Optional)
    AWS_ACCESS_KEY_ID: str | None = Field(default=None)
    AWS_SECRET_ACCESS_KEY: str | None = Field(default=None)
    AWS_REGION: str = Field(default="us-east-1")
    S3_BUCKET: str = Field(default="agent-hub-images")

    # Backend Rails API Configuration
    BACKEND_API_URL: str = Field(default="http://localhost:3000/api/v1")
    BACKEND_TIMEOUT: int = Field(default=3)

    @field_validator("OPENAI_API_KEY", "GOOGLE_API_KEY", "ROBOFLOW_API_KEY")
    @classmethod
    def validate_api_keys_not_empty(cls, value: str, info: ValidationInfo) -> str:
        """Ensure API keys are non-empty strings."""

        if not value or value.strip() == "":
            raise ValueError(f"{info.field_name} cannot be empty")
        return value.strip()

    @field_validator("CLASSIFIER_MODEL")
    @classmethod
    def validate_classifier_model(cls, value: str) -> str:
        """Validate the selected classifier model."""

        allowed = ["openai-gpt4", "openai-gpt4o", "gemini", "roboflow"]
        if value not in allowed:
            raise ValueError(f"CLASSIFIER_MODEL must be one of {allowed}")
        return value


# Singleton instance
settings = Settings()
