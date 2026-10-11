from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class CommonSettings(BaseSettings):
    """Variables partagées par tous les services.

    Chaque service charge son propre fichier `.env` (répertoire courant) ;
    en Docker, les variables sont injectées par docker-compose.
    `extra="ignore"` permet à chaque service d'avoir ses variables en plus.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # JWT — secret partagé (HS256). Évolution possible : RS256 + JWKS exposé par auth-service.
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Clé partagée protégeant les endpoints /internal/* (communication inter-services)
    INTERNAL_API_KEY: str = "dev-internal-key-change-me"


@lru_cache
def get_common_settings() -> CommonSettings:
    return CommonSettings()
