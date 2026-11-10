"""Route publique du module 1 : `POST /api/ai/comprendre` (via le gateway)."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request

from voyara_common.auth import TokenIdentity, get_optional_identity
from voyara_common.limiter import limiter

from app.config import settings
from app.nlu.extraction import comprendre
from app.nlu.schemas import ReponseComprendre, RequeteComprendre

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Compréhension (NLU)"])

# La Tunisie est à UTC+1 toute l'année (pas d'heure d'été depuis 2009).
FUSEAU_TUNIS = timezone(timedelta(hours=1), "Africa/Tunis")


@router.post("/comprendre", response_model=ReponseComprendre)
@limiter.limit("20/minute")
async def comprendre_demande(
    request: Request,
    corps: RequeteComprendre,
    identite: TokenIdentity | None = Depends(get_optional_identity),
) -> ReponseComprendre:
    """Texte libre (fr / en / ar / darija) → demande de voyage structurée, champs manquants et
    question de clarification. Ouvert aux visiteurs anonymes ; un token invalide → 401.

    Méthode hybride (règles + LLM). Si le LLM ne répond pas en `NLU_DELAI_LLM_S` secondes (25 s,
    sous le délai de 30 s du gateway), la réponse vient des règles seules (`methode = "regles"`)."""
    reference = corps.date_reference or datetime.now(FUSEAU_TUNIS).date()
    client_llm = getattr(request.app.state, "llm", None)
    reponse = await comprendre(corps.texte, reference, client_llm=client_llm, methode="hybride",
                               delai_s=settings.NLU_DELAI_LLM_S)
    logger.info("NLU : methode=%s provider=%s latence=%d ms utilisateur=%s", reponse.methode, reponse.provider,
                reponse.latence_ms, identite.user_id if identite else "anonyme")
    return reponse
