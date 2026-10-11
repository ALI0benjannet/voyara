from functools import lru_cache

from voyara_common.config import CommonSettings
from voyara_common.database import build_postgres_url


class Settings(CommonSettings):
    SERVICE_NAME: str = "booking-service"
    PROJECT_NAME: str = "Voyara Booking Service"

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "voyara_booking"

    CATALOG_SERVICE_URL: str = "http://localhost:8002"
    AUTH_SERVICE_URL: str = "http://localhost:8001"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8006"

    AUTO_CREATE_TABLES: bool = True

    # --- Expiration des réservations non payées -----------------------------
    # Une réservation `pending` garde ses places décrémentées : sans expiration,
    # un utilisateur qui abandonne avant de payer les bloque indéfiniment.
    # 180 min = 3 h : large pour finir un paiement, assez court pour libérer le
    # créneau le jour même.
    BOOKING_EXPIRY_MINUTES: int = 180
    # Fréquence du balayage. 5 min suffit : la précision de l'expiration n'a pas
    # besoin d'être à la seconde, et cela garde la charge base négligeable.
    BOOKING_EXPIRY_SWEEP_SECONDS: int = 300
    # Permet de couper la tâche (tests, environnement de démo figé).
    BOOKING_EXPIRY_ENABLED: bool = True

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
