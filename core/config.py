"""
Configuration loader with validation.

Uses pydantic-settings to load and validate environment variables.
Azure OpenAI settings are required for the pipeline.
"""

from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment (e.g. .env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    AZURE_OPENAI_API_KEY: str = Field(..., min_length=1, description="Azure OpenAI API key.")
    AZURE_OPENAI_ENDPOINT: str = Field(..., min_length=1, description="Azure OpenAI endpoint URL.")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = Field(
        default="gpt-4o",
        description="Deployment name for the model.",
    )
    AZURE_OPENAI_API_VERSION: str = Field(
        default="2024-02-15-preview",
        description="API version for Azure OpenAI.",
    )
    MONGODB_URI: str = Field(
        ...,
        min_length=1,
        description="MongoDB connection string (e.g. mongodb+srv://...).",
    )


@lru_cache(maxsize=1)
def get_config() -> Settings:
    """Load and return validated application settings (singleton)."""
    return Settings()  # type: ignore[call-arg]


def build_llm_config() -> dict[str, Any]:
    """
    Build the LLM config dict expected by AutoGen for Azure OpenAI.

    Uses injected settings from get_config(). Caller may pass a Settings
    instance for dependency injection in tests.
    """
    settings = get_config()
    return {
        "config_list": [
            {
                "model": settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                "api_type": "azure",
                "api_key": settings.AZURE_OPENAI_API_KEY,
                "base_url": settings.AZURE_OPENAI_ENDPOINT.rstrip("/") + "/",
                "api_version": settings.AZURE_OPENAI_API_VERSION,
            }
        ]
    }
