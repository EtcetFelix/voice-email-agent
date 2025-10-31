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
    NYLAS_API_KEY: str = Field(description="Nylas API Key")
    ELEVENLABS_API_KEY: str = Field(description="ElevenLabs API Key")
    OPENAI_API_KEY: str = Field(description="OpenAI API Key")
    NYLAS_EMAIL_ACCOUNT_GRANT_ID: str = Field(description="Nylas Email Account Grant ID")

# Create settings instance - this will automatically load from env vars
settings = Settings()

def validate_settings():
    """Validate that all required settings are available"""
    required_settings = {
        "NYLAS_API_KEY": settings.NYLAS_API_KEY,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "ELEVENLABS_API_KEY": settings.ELEVENLABS_API_KEY,
        "NYLAS_EMAIL_ACCOUNT_GRANT_ID": settings.NYLAS_EMAIL_ACCOUNT_GRANT_ID,
    }

    missing_settings = [name for name, value in required_settings.items() if not value]

    if missing_settings:
        error_msg = (
            f"Missing required environment variables: {', '.join(missing_settings)}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    return True