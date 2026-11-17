"""Routes publiques de la démonstration DL (`/api/ai/dl/*`, via le gateway), sans LLM.

Servent la page temporaire « DL test » du site client. Les calculs (TF-IDF, encodage e5,
régression logistique) tournent dans un thread pour ne pas bloquer la boucle asyncio.
"""

import asyncio
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator

from voyara_common.limiter import limiter

from app.dl import classification as clf
from app.dl import recherche as rech
from app.dl.resultats import tous_les_resultats

router = APIRouter(prefix="/dl", tags=["Validation Deep Learning (démo)"])

_moteur = rech.MoteurRecherche()
_classifieur = clf.Classifieur()


def moteur(request: Request) -> rech.MoteurRecherche:
    return getattr(request.app.state, "dl_recherche", None) or _moteur


def classifieur(request: Request) -> clf.Classifieur:
    return getattr(request.app.state, "dl_classif", None) or _classifieur


class _Texte(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _sans_blancs(cls, v):
        return v.strip() if isinstance(v, str) else v


class RequeteRecherche(_Texte):
    requete: str = Field(..., min_length=1, max_length=300)
    methodes: list[Literal["tfidf", "e5_gele", "e5_fine_tune"]] = ["tfidf", "e5_gele", "e5_fine_tune"]
    k: int = Field(10, ge=1, le=20)


class RequeteClassif(_Texte):
    texte: str = Field(..., min_length=1, max_length=2000)
    methodes: list[Literal["regles", "ml_tfidf", "xlmr_fine_tune"]] = ["regles", "ml_tfidf", "xlmr_fine_tune"]


@router.get("/resultats")
def resultats():
    """Résultats chiffrés des deux validations (CSV de docs/ia/resultats)."""
    return tous_les_resultats()


@router.get("/etat")
def etat(request: Request):
    """Méthodes disponibles en direct sur ce poste (modèles présents ou non)."""
    return {"recherche": moteur(request).disponibilites(), "recherche_etats": moteur(request).etats(),
            "classification": classifieur(request).disponibilites()}


@router.post("/prechauffer")
def prechauffer(request: Request):
    """Lance en arrière-plan le chargement des modèles d'embeddings (appelé à l'ouverture de la
    page) et répond aussitôt : `pret`, `chargement`, `erreur` ou `indisponible` par méthode."""
    return moteur(request).prechauffer()


@router.get("/exemples")
def exemples(request: Request):
    """Requêtes du jeu de test (recherche) et demandes du jeu de test NLU (classification)."""
    return {"recherche": moteur(request).exemples(), "classification": classifieur(request).exemples()}


@router.post("/rechercher")
@limiter.limit("30/minute")
async def rechercher(request: Request, corps: RequeteRecherche):
    return await asyncio.to_thread(moteur(request).rechercher, corps.requete, corps.methodes, corps.k)


@router.post("/classifier")
@limiter.limit("30/minute")
async def classifier(request: Request, corps: RequeteClassif):
    return await classifieur(request).classifier(corps.texte, corps.methodes)
