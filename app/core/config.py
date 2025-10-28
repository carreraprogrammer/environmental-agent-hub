"""
Configuration management using Pydantic Settings.

Loads configuration from environment variables with sensible defaults.
"""

from __future__ import annotations

from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Priority order:
    1. Environment variables
    2. .env file
    3. Default values
    
    Attributes:
        API_TITLE: API title for documentation
        API_VERSION: Current version
        DEBUG: Enable debug mode
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
        LOG_FORMAT: Log format (json or text)
        CLASSIFIER_MODEL: Active classification model
        CORS_ORIGINS: Allowed CORS origins
        OPENAI_API_KEY: OpenAI API key
        OPENAI_TIMEOUT: OpenAI request timeout
        ANTHROPIC_API_KEY: Anthropic API key (optional)
        GOOGLE_API_KEY: Google API key (optional)
        ROBOFLOW_API_KEY: Roboflow API key (optional)
        AWS_ACCESS_KEY_ID: AWS access key (optional)
        AWS_SECRET_ACCESS_KEY: AWS secret key (optional)
        AWS_REGION: AWS region
        S3_BUCKET: S3 bucket name
        BACKEND_API_URL: Rails backend URL
        BACKEND_TIMEOUT: Backend request timeout
    """
    
    # API Settings
    API_TITLE: str = "Agent Hub"
    API_VERSION: str = "2.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Active Model (CRITICAL - cambiar sin redeploy)
    CLASSIFIER_MODEL: str = "openai-gpt4"
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = ""
    OPENAI_TIMEOUT: int = 10
    
    # Anthropic Configuration (Optional)
    ANTHROPIC_API_KEY: str | None = None
    
    # Google Configuration (Optional)
    GOOGLE_API_KEY: str | None = None
    
    # Roboflow Configuration (Optional)
    ROBOFLOW_API_KEY: str | None = None
    
    # AWS S3 Configuration (Optional)
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: str = "agent-hub-images"
    
    # Backend Rails API Configuration
    BACKEND_API_URL: str = "http://localhost:3000/api/v1"
    BACKEND_TIMEOUT: int = 3
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = True


# Singleton instance
settings = Settings()
