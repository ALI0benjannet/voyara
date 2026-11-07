"""Client interne vers catalog (routes /internal/* des étapes 2 et 2-bis).

Construit sur `voyara_common.internal.ServiceClient` (clé `X-Internal-Api-Key`, timeout).
Les erreurs httpx sont traduites en erreurs typées, pour que le moteur dégrade proprement
(liste vide + avertissement à l'étape 5) au lieu d'inventer une offre.
Paramètres et champs : voir CLAUDE.md §4 et services/catalog/app/internal_offres_routes.py.
"""

from datetime import date, datetime
from typing import Any

import httpx

from voyara_common.internal import ServiceClient


class ErreurCatalog(Exception):
    """Base des erreurs du client catalog."""


class CatalogIndisponible(ErreurCatalog):
    """Connexion impossible, délai dépassé ou erreur 5xx : réessayable, dégradation propre."""


class CatalogLieuInconnu(ErreurCatalog):
    """404 sur une recherche : origine ou destination inconnue (poser une question)."""


class CatalogRequeteInvalide(ErreurCatalog):
    """422 : paramètres refusés par catalog (bug d'appel)."""


class CatalogAccesRefuse(ErreurCatalog):
    """401 / 403 : INTERNAL_API_KEY absente ou différente entre les services."""


def _iso(valeur: date | datetime | None) -> str | None:
    return valeur.isoformat() if valeur is not None else None


def _sans_vides(params: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in params.items() if v is not None}


class ClientCatalog:
    def __init__(self, base_url: str, timeout_s: float = 5.0,
                 transport: httpx.AsyncBaseTransport | None = None):
        self._client = ServiceClient(base_url, timeout=timeout_s, transport=transport)

    async def _get(self, chemin: str, params: dict[str, Any]) -> Any:
        try:
            return await self._client.get(chemin, params=_sans_vides(params))
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            try:
                detail = exc.response.json().get("detail")
            except ValueError:
                detail = exc.response.text[:200]
            if code == 404:
                raise CatalogLieuInconnu(str(detail)) from exc
            if code == 422:
                raise CatalogRequeteInvalide(str(detail)) from exc
            if code in (401, 403):
                raise CatalogAccesRefuse(f"accès refusé ({code})") from exc
            raise CatalogIndisponible(f"catalog a répondu {code}") from exc
        except httpx.TimeoutException as exc:
            raise CatalogIndisponible("délai dépassé") from exc
        except httpx.HTTPError as exc:
            raise CatalogIndisponible(f"catalog injoignable ({type(exc).__name__})") from exc

    # --- Index sémantique (étape 5) -------------------------------------------

    async def exporter_activites(self, page: int = 1, size: int = 100,
                                 modifie_depuis: datetime | None = None,
                                 statut: str | None = None, tags_valides: bool | None = None) -> dict:
        return await self._get("/internal/activities/export", {
            "page": page, "size": size, "modifie_depuis": _iso(modifie_depuis),
            "statut": statut, "tags_valides": tags_valides,
        })

    async def exporter_sejours(self, page: int = 1, size: int = 100,
                               modifie_depuis: datetime | None = None, actif: bool | None = None) -> dict:
        return await self._get("/internal/stays/export", {
            "page": page, "size": size, "modifie_depuis": _iso(modifie_depuis), "actif": actif,
        })

    async def aeroports(self) -> dict:
        return await self._get("/internal/airports", {"size": 100})

    # --- Transport : recherche structurée en direct (jamais indexée) -----------

    async def rechercher_vols(self, origine: str, destination: str, jour: date,
                              tolerance_jours: int = 0, nb_passagers: int = 1,
                              classe: str | None = None, escales_max: int = 1,
                              tri: str = "pertinence", page: int = 1, size: int = 20) -> dict:
        return await self._get("/internal/flights/search", {
            "origine": origine, "destination": destination, "date": _iso(jour),
            "tolerance_jours": tolerance_jours, "nb_passagers": nb_passagers, "classe": classe,
            "escales_max": escales_max, "tri": tri, "page": page, "size": size,
        })

    async def rechercher_voitures(self, lieu_prise: str, prise_le: datetime, retour_le: datetime,
                                  lieu_retour: str | None = None, nb_places: int = 1,
                                  transmission: str | None = None, categorie: str | None = None,
                                  page: int = 1, size: int = 20) -> dict:
        return await self._get("/internal/car-rentals/search", {
            "lieu_prise": lieu_prise, "lieu_retour": lieu_retour, "prise_le": _iso(prise_le),
            "retour_le": _iso(retour_le), "nb_places": nb_places, "transmission": transmission,
            "categorie": categorie, "page": page, "size": size,
        })

    async def rechercher_transferts(self, depart: str, arrivee: str, date_heure: datetime,
                                    nb_passagers: int = 1, bagages: int = 0,
                                    page: int = 1, size: int = 20) -> dict:
        return await self._get("/internal/transfers/search", {
            "depart": depart, "arrivee": arrivee, "date_heure": _iso(date_heure),
            "nb_passagers": nb_passagers, "bagages": bagages, "page": page, "size": size,
        })
