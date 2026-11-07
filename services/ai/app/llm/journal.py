"""Journalisation des appels LLM dans `llm_appels` (étape 3).

L'écriture passe dans un thread (SQLAlchemy synchrone, appelé depuis du code async) et ne
casse jamais l'appel LLM : une base indisponible est seulement signalée dans les logs.
"""

import asyncio
import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.models import LlmAppel

logger = logging.getLogger(__name__)

LONGUEUR_MAX_ERREUR = 500


class JournalLLM:
    def __init__(self, fabrique_session: Callable[[], Session]):
        self.fabrique_session = fabrique_session

    def _ecrire(self, ligne: dict) -> int | None:
        try:
            with self.fabrique_session() as session:
                appel = LlmAppel(**ligne)
                session.add(appel)
                session.commit()
                return appel.id
        except Exception:  # noqa: BLE001 — le journal ne doit jamais faire échouer l'appel
            logger.exception("Écriture de llm_appels impossible")
            return None

    async def enregistrer(
        self,
        provider: str,
        modele: str,
        statut: str,
        usage: str = "inconnu",
        tokens_entree: int = 0,
        tokens_sortie: int = 0,
        latence_ms: int = 0,
        cout_estime: float | None = None,
        erreur: Exception | str | None = None,
        appel_parent_id: int | None = None,
    ) -> int | None:
        if isinstance(erreur, Exception):
            erreur = f"{type(erreur).__name__}: {erreur}"
        ligne = {
            "provider": provider,
            "modele": modele,
            "statut": statut,
            "usage": usage,
            "tokens_entree": tokens_entree,
            "tokens_sortie": tokens_sortie,
            "latence_ms": latence_ms,
            "cout_estime": cout_estime,
            "erreur": erreur[:LONGUEUR_MAX_ERREUR] if erreur else None,
            "appel_parent_id": appel_parent_id,
        }
        return await asyncio.to_thread(self._ecrire, ligne)


class JournalMemoire(JournalLLM):
    """Journal sans base (tests, scripts hors-ligne) : garde les lignes en mémoire."""

    def __init__(self):
        self.lignes: list[dict] = []

    def _ecrire(self, ligne: dict) -> int:
        self.lignes.append(ligne)
        return len(self.lignes)
