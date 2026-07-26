from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "Workbook Agent"
    environment: str = "development"
    frontend_origins: str = "http://localhost:5173"
    model_provider: str = "nvidia"
    model_name: str = "nvidia/nemotron-3-nano-30b-a3b"
    nvidia_api_key: SecretStr | None = Field(default=None, validation_alias="NVIDIA_API_KEY")
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    require_write_confirmation: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WORKBOOK_AGENT_",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
