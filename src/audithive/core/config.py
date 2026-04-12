"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """AuditHive application settings loaded from environment / .env file."""

    DATABASE_URL: str = "postgresql+asyncpg://audithive:audithive_dev@localhost:5432/audithive"
    REDIS_URL: str = "redis://localhost:6379/0"
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "change-me-in-production"
    API_KEY_PREFIX: str = "ah-"

    # Examiner simulation
    ANTHROPIC_API_KEY: str = ""

    # Alerting - SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "alerts@audithive.io"
    WEBHOOK_TIMEOUT_SECONDS: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
