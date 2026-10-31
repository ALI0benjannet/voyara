"""Routes publiques du service ai, sous `/api/ai` (gateway). Étape 3 : santé détaillée."""

import asyncio

from fastapi import APIRouter, Request
from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal

router = APIRouter(tags=["Moteur IA"])


def _etat_base() -> dict:
    try:
        with SessionLocal() as session:
            version = session.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
        return {"base": "ok", "pgvector": version or "absente"}
    except Exception:  # noqa: BLE001 — la santé rapporte l'état, elle ne lève pas
        return {"base": "injoignable", "pgvector": None}


@router.get("/health")
async def health_detaillee(request: Request):
    """État du moteur : base, extension pgvector, fournisseur LLM, Ollama.

    N'expose aucun secret : seulement la présence (oui/non) de la clé Claude."""
    llm = request.app.state.llm
    base, ollama_ok = await asyncio.gather(asyncio.to_thread(_etat_base), llm.ollama.est_joignable())
    statut = "ok" if base["base"] == "ok" else "degrade"
    return {
        "service": settings.SERVICE_NAME,
        "status": statut,
        **base,
        "llm": {
            "provider": llm.mode,
            "claude": {"modele": llm.claude.modele, "cle_configuree": llm.claude.cle_presente},
            "ollama": {"modele": llm.ollama.modele, "joignable": ollama_ok},
        },
    }
