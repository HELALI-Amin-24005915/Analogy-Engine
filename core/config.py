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

    AZURE_OPENAI_API_KEY: str | None = Field(
        default=None,
        description="Azure OpenAI API key (optional; can be provided via UI in Live mode).",
    )
    AZURE_OPENAI_ENDPOINT: str | None = Field(
        default=None,
        description="Azure OpenAI endpoint URL (optional; can be provided via UI in Live mode).",
    )
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

    Uses injected settings from get_config(). Requires AZURE_OPENAI_API_KEY
    and AZURE_OPENAI_ENDPOINT to be set in environment.
    """
    settings = get_config()
    if not settings.AZURE_OPENAI_API_KEY or not settings.AZURE_OPENAI_ENDPOINT:
        raise ValueError(
            "Azure OpenAI API key and endpoint are required. "
            "Set them in .env or provide them in the sidebar for Live mode."
        )
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


def build_llm_config_from_input(
    api_key: str,
    endpoint: str,
    deployment: str = "gpt-4o",
    api_version: str = "2024-02-15-preview",
) -> dict[str, Any]:
    """
    Build the LLM config dict from user-provided credentials (e.g. sidebar inputs).

    Used in Live mode when the user enters API key and endpoint in the UI.
    """
    key = (api_key or "").strip()
    url = (endpoint or "").strip()
    if not key or not url:
        raise ValueError("API key and endpoint are required for Live mode.")
    return {
        "config_list": [
            {
                "model": deployment,
                "api_type": "azure",
                "api_key": key,
                "base_url": url.rstrip("/") + "/",
                "api_version": api_version,
            }
        ]
    }
