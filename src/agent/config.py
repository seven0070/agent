"""
Configuration Management Foundation for Layer 0.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

class Settings(BaseSettings):
    """
    Application Settings Model using Pydantic.
    Separates configuration, credentials, and runtime state.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    agent_env: str = Field(default="development", description="Execution environment (development, test, production)")
    log_level: str = Field(default="INFO", description="Structured log level")
    agent_version: str = Field(default="0.1.0", description="Current system version")

    # Provider key placeholders (Optional, default None, read from environment)
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API Key placeholder")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API Key placeholder")
    dashscope_api_key: Optional[str] = Field(default=None, description="DashScope API Key placeholder")

def get_settings() -> Settings:
    """Returns initialized application settings instance."""
    return Settings()
