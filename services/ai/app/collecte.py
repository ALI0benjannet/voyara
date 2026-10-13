"""Collecte des POI OpenStreetMap via l'API Overpass (licence ODbL).

Utilisé par scripts/collecter_pois.py. Le client HTTP et la fonction de pause
sont injectables : les tests simulent le réseau (httpx.MockTransport) et
n'attendent jamais réellement.
"""

import logging
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
from sqlalchemy import literal_column
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Poi
from app.osm import element_vers_poi
from app.villes import Ville

logger = logging.getLogger(__name__)

USER_AGENT = "Voyara-PFE/1.0 (collecte pedagogique de POI, projet etudiant)"
TIMEOUT_OVERPASS_S = 90
# Attente avant chaque nouvelle tentative : 1 essai + 3 nouvelles tentatives au plus.
ATTENTES_S = (10, 30, 60)
STATUTS_A_REESSAYER = {429, 502, 503, 504}


class OverpassIndisponible(Exception):
    """Overpass n'a pas répondu correctement après toutes les tentatives."""


def construire_requete(ville: Ville) -> str:
    """Requête Overpass QL : objets nommés des familles reconnues autour du centre."""
    autour = f"(around:{ville.rayon_m},{ville.latitude},{ville.longitude})"
    filtres = (
        '["amenity"~"^(restaurant|cafe|marketplace)$"]',
        '["tourism"~"^(museum|zoo|theme_park|attraction)$"]',
        '["historic"~"^(monument|memorial|archaeological_site|castle|fort|ruins)$"]',
        '["natural"="beach"]',
        '["leisure"~"^(beach_resort|park|water_park)$"]',
        '["shop"="bazaar"]',
    )
    corps = "\n".join(f'  nwr["name"]{f}{autour};' for f in filtres)
    return f"[out:json][timeout:{TIMEOUT_OVERPASS_S}];\n(\n{corps}\n);\nout center tags;"


def interroger_overpass(
    client: httpx.Client,
    url: str,
    requete: str,
    dormir: Callable[[float], None] = time.sleep,
) -> list[dict]:
    """POST de la requête, avec nouvelles tentatives sur saturation ou délai dépassé."""
    derniere_erreur = ""
    for tentative in range(len(ATTENTES_S) + 1):
        if tentative:
            attente = ATTENTES_S[tentative - 1]
            logger.warning("Overpass : %s — nouvelle tentative dans %s s", derniere_erreur, attente)
            dormir(attente)
        try:
            reponse = client.post(url, data={"data": requete}, timeout=TIMEOUT_OVERPASS_S + 30)
        except httpx.TransportError as exc:  # délai dépassé, connexion refusée...
            derniere_erreur = f"erreur réseau ({type(exc).__name__})"
            continue
        if reponse.status_code in STATUTS_A_REESSAYER:
            derniere_erreur = f"HTTP {reponse.status_code}"
            continue
        if reponse.status_code != 200:
            raise OverpassIndisponible(f"HTTP {reponse.status_code} (non réessayable)")
        contenu = reponse.json()
        # Overpass répond 200 avec une remarque quand la requête a expiré côté serveur
        remarque = contenu.get("remark") or ""
        if "runtime error" in remarque:
            derniere_erreur = f"délai serveur ({remarque[:80]})"
            continue
        return contenu.get("elements", [])
    raise OverpassIndisponible(f"échec après {len(ATTENTES_S) + 1} essais : {derniere_erreur}")


def _cle_tri(poi: dict) -> tuple[str, int]:
    type_osm, identifiant = poi["source_id"].split("/")
    return type_osm, int(identifiant)


def selectionner(elements: list[dict], ville: Ville, max_par_type: int, maintenant: datetime) -> list[dict]:
    """Convertit les éléments et plafonne chaque type de façon déterministe (ordre des id OSM)."""
    pois = {}
    for element in elements:
        poi = element_vers_poi(element, ville.nom, maintenant)
        if poi:
            pois[poi["source_id"]] = poi  # un objet peut sortir de deux filtres
    retenus: list[dict] = []
    par_type: Counter[str] = Counter()
    for poi in sorted(pois.values(), key=_cle_tri):
        if par_type[poi["type"]] < max_par_type:
            par_type[poi["type"]] += 1
            retenus.append(poi)
    return retenus


def enregistrer(db: Session, pois: list[dict]) -> tuple[int, int]:
    """Upsert idempotent sur `source_id`. Retourne (insérés, mis à jour)."""
    inseres = mis_a_jour = 0
    for poi in pois:
        requete = insert(Poi).values(**poi)
        requete = requete.on_conflict_do_update(
            index_elements=[Poi.source_id],
            set_={c: requete.excluded[c] for c in poi if c != "source_id"},
        ).returning(literal_column("(xmax = 0)"))  # vrai si la ligne vient d'être insérée
        if db.execute(requete).scalar():
            inseres += 1
        else:
            mis_a_jour += 1
    db.commit()
    return inseres, mis_a_jour


def collecter_ville(
    client: httpx.Client,
    url: str,
    ville: Ville,
    max_par_type: int,
    dormir: Callable[[float], None] = time.sleep,
) -> list[dict]:
    elements = interroger_overpass(client, url, construire_requete(ville), dormir)
    return selectionner(elements, ville, max_par_type, datetime.now(UTC))


def nouveau_client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": USER_AGENT})
