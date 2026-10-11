from functools import lru_cache

from voyara_common.config import CommonSettings
from voyara_common.database import build_postgres_url


class Settings(CommonSettings):
    SERVICE_NAME: str = "auth-service"
    PROJECT_NAME: str = "Voyara Auth Service"

    # Base de données du service (par défaut : la base historique `voyara`,
    # ce qui préserve les comptes utilisateurs existants)
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "voyara"

    # URL du service de notification (envoi d'e-mails)
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8006"

    # Durées de vie des tokens envoyés par e-mail
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    # Compte administrateur initial (seed)
    FIRST_ADMIN_EMAIL: str = "admin@voyara.com"
    FIRST_ADMIN_PASSWORD: str = "ChangeMe@1234"

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
