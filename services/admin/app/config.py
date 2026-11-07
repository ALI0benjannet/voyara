from functools import lru_cache

from voyara_common.config import CommonSettings


class Settings(CommonSettings):
    SERVICE_NAME: str = "admin-service"
    PROJECT_NAME: str = "Voyara Admin Service (BFF)"

    AUTH_SERVICE_URL: str = "http://127.0.0.1:8001"
    CATALOG_SERVICE_URL: str = "http://127.0.0.1:8002"
    BOOKING_SERVICE_URL: str = "http://127.0.0.1:8003"
    PAYMENT_SERVICE_URL: str = "http://127.0.0.1:8004"
    REVIEW_SERVICE_URL: str = "http://127.0.0.1:8005"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
