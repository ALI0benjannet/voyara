from functools import lru_cache

from voyara_common.config import CommonSettings
from voyara_common.database import build_postgres_url


class Settings(CommonSettings):
    SERVICE_NAME: str = "payment-service"
    PROJECT_NAME: str = "Voyara Payment Service"

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "voyara_payment"

    BOOKING_SERVICE_URL: str = "http://localhost:8003"

    # Stripe — si STRIPE_SECRET_KEY est vide, le service passe en MODE SIMULATION
    # (bouton « Simuler le paiement » côté front, clairement étiqueté démo).
    # NB : Stripe ne supporte pas le TND — en mode réel, le montant est facturé
    # en EUR à valeur numérique égale (limitation documentée, projet de démo).
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY)

    AUTO_CREATE_TABLES: bool = True

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
