from functools import lru_cache

from voyara_common.config import CommonSettings
from voyara_common.database import build_postgres_url


class Settings(CommonSettings):
    SERVICE_NAME: str = "ai-service"
    PROJECT_NAME: str = "Voyara AI Service"
    # Préfixe public routé par le gateway (ADR-007) — distinct de /api/v1 des autres services.
    API_AI_PREFIX: str = "/api/ai"

    # Base dédiée `voyara_ai` dans le conteneur `postgres-ai` (pgvector, port hôte 5435)
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5435
    POSTGRES_DB: str = "voyara_ai"

    # Crée l'extension `vector` et les tables au démarrage (dev). En production : migrations.
    AUTO_CREATE_TABLES: bool = True

    # Sources de données ouvertes (sans clé)
    OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"
    OPEN_METEO_URL: str = "https://api.open-meteo.com/v1/forecast"

    # Durée de validité du cache météo
    METEO_CACHE_HEURES: int = 6

    # Catalogue (routes /internal/* de l'étape 2-bis). 127.0.0.1 et non localhost :
    # sous Windows, localhost tente d'abord IPv6 (~2 s par appel, architecture.md §12 n° 13).
    CATALOG_SERVICE_URL: str = "http://127.0.0.1:8002"
    CATALOG_TIMEOUT_S: float = 5.0

    # --- Couche LLM hybride (étape 3) --------------------------------------
    # claude | ollama | auto (Claude, puis Ollama en cas de panne ou de clé absente)
    LLM_PROVIDER: str = "auto"
    # Secret : uniquement dans .env, jamais dans le code ni les rapports.
    ANTHROPIC_API_KEY: str | None = None
    CLAUDE_MODEL: str = "claude-sonnet-5-5"
    CLAUDE_EFFORT: str = "medium"  # low | medium | high | xhigh | max
    CLAUDE_TIMEOUT_S: float = 60.0
    # Peu de nouvelles tentatives : en mode auto, mieux vaut basculer vite sur Ollama.
    CLAUDE_MAX_RETRIES: int = 1
    # Repli côté serveur quand un classifieur de sécurité refuse (bêta, Claude API).
    CLAUDE_FALLBACKS: bool = True
    OLLAMA_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"  # 7b : ~4,4 Go de RAM, trop pour un poste 8 Go
    OLLAMA_TIMEOUT_S: float = 180.0  # un 7B sur CPU peut prendre plusieurs dizaines de secondes

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
