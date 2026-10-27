
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve the .env file relative to this config.py file.
# Location: backend/app/core/config.py
# Result:   backend/.env
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "RevPilot AI"
    app_version: str = "0.1.0"

    # Required database connection.
    database_url: str

    # NVIDIA AI configuration.
    nvidia_api_key: str | None = None
    nvidia_model: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

    # JWT authentication configuration.
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
