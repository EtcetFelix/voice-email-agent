import logging

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # This ignores extra environment variables
    )
    
    # API keys
    NYLAS_API_KEY: str = Field(..., env="NYLAS_API_KEY")
    ELEVENLABS_API_KEY: str = Field(..., env="ELEVENLABS_API_KEY")
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")

settings = Settings.model_validate({})

def validate_settings():
    """Validate that all required settings are available"""
    required_settings = {
        "NYLAS_API_KEY": settings.nylas_api_key,
        "OPENAI_API_KEY": settings.openai_api_key,
        "ELEVENLABS_API_KEY": settings.elevenlabs_api_key,
    }

    missing_settings = [name for name, value in required_settings.items() if not value]

    if missing_settings:
        error_msg = (
            f"Missing required environment variables: {', '.join(missing_settings)}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    return True