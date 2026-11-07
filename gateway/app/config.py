from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    SERVICE_NAME: str = "gateway"
    PROJECT_NAME: str = "Voyara API Gateway"
    ENVIRONMENT: str = "development"

    AUTH_SERVICE_URL: str = "http://127.0.0.1:8001"
    CATALOG_SERVICE_URL: str = "http://127.0.0.1:8002"
    BOOKING_SERVICE_URL: str = "http://127.0.0.1:8003"
    PAYMENT_SERVICE_URL: str = "http://127.0.0.1:8004"
    REVIEW_SERVICE_URL: str = "http://127.0.0.1:8005"
    NOTIFICATION_SERVICE_URL: str = "http://127.0.0.1:8006"
    ADMIN_SERVICE_URL: str = "http://127.0.0.1:8007"
    AI_SERVICE_URL: str = "http://127.0.0.1:8008"  # moteur IA (ADR-007)

    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    PROXY_TIMEOUT_SECONDS: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
