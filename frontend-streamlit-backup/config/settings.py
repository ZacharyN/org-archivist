"""
Application configuration and settings.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API Configuration
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "30"))

    # Application Settings
    APP_NAME: str = "Org Archivist"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Session Settings
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))

    # UI Settings
    ITEMS_PER_PAGE: int = int(os.getenv("ITEMS_PER_PAGE", "25"))
    MAX_FILE_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_FILE_UPLOAD_SIZE_MB", "50"))

    # Feature Flags
    ENABLE_ANALYTICS: bool = os.getenv("ENABLE_ANALYTICS", "False").lower() == "true"
    ENABLE_COLLABORATION: bool = os.getenv("ENABLE_COLLABORATION", "False").lower() == "true"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
