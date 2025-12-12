"""
Trading-FAIT Configuration
Pydantic Settings for Azure OpenAI and application configuration
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =====================
    # Azure OpenAI Settings
    # =====================
    azure_openai_endpoint: str = Field(
        ...,
        description="Azure OpenAI endpoint URL",
        examples=["https://your-resource.openai.azure.com/"],
    )
    azure_openai_api_key: str = Field(
        ...,
        description="Azure OpenAI API key",
    )
    azure_openai_deployment: str = Field(
        default="gpt-4o",
        description="Azure OpenAI deployment name",
    )
    azure_openai_model: str = Field(
        default="gpt-4o",
        description="Azure OpenAI model name (for token counting, e.g. gpt-4o, gpt-4, gpt-35-turbo)",
    )
    azure_openai_api_version: str = Field(
        default="2024-02-01",
        description="Azure OpenAI API version",
    )

    # =====================
    # Application Settings
    # =====================
    app_name: str = Field(default="Trading-FAIT")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)

    # =====================
    # Logging Settings
    # =====================
    log_level: str = Field(
        default="INFO",
        description="Log level: DEBUG, INFO, WARNING, ERROR",
    )
    log_dir: str = Field(
        default="./logs/discussions",
        description="Directory for agent discussion logs",
    )

    # =====================
    # Redis Settings
    # =====================
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL",
    )

    # =====================
    # Agent Settings
    # =====================
    agent_max_turns: int = Field(
        default=20,
        description="Maximum turns for agent discussions",
    )
    agent_max_stalls: int = Field(
        default=3,
        description="Maximum stalls before re-planning",
    )

    # =====================
    # WebSocket Settings
    # =====================
    ws_heartbeat_interval: int = Field(
        default=30,
        description="WebSocket heartbeat interval in seconds",
    )

    @property
    def is_configured(self) -> bool:
        """Check if Azure OpenAI is properly configured"""
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key
            and "your-resource" not in self.azure_openai_endpoint
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Convenience function for dependency injection
def get_config() -> Settings:
    """Get settings for FastAPI dependency injection"""
    return get_settings()
