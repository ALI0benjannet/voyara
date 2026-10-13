from functools import lru_cache

from voyara_common.config import CommonSettings
from voyara_common.database import build_postgres_url


class Settings(CommonSettings):
    SERVICE_NAME: str = "ai-service"
    PROJECT_NAME: str = "Voyara AI Service"

    # Base dédiée `voyara_ai` dans le conteneur `postgres-ai` (pgvector, port hôte 5435)
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5435
    POSTGRES_DB: str = "voyara_ai"

    # Sources de données ouvertes (sans clé)
    OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"
    OPEN_METEO_URL: str = "https://api.open-meteo.com/v1/forecast"

    # Durée de validité du cache météo
    METEO_CACHE_HEURES: int = 6

    @property
    def DATABASE_URL(self) -> str:
        return build_postgres_url(
            self.POSTGRES_USER,
            self.POSTGRES_PASSWORD,
            self.POSTGRES_HOST,
            self.POSTGRES_PORT,
            self.POSTGRES_DB,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
