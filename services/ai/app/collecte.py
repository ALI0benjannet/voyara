"""Collecte des POI OpenStreetMap via l'API Overpass (licence ODbL).

Utilisé par scripts/collecter_pois.py. Le client HTTP et la fonction de pause
sont injectables : les tests simulent le réseau (httpx.MockTransport) et
n'attendent jamais réellement.
"""

import logging
import math
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
from sqlalchemy import literal_column
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Poi
from app.osm import coordonnees, element_vers_poi
from app.villes import VILLES, Ville

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


def construire_requete_aeroports() -> str:
    """Aérodromes à code IATA de Tunisie (étape 2-bis), quelle que soit leur distance
    au centre-ville : Enfidha est à ~35 km de Sousse, hors des rayons de collecte."""
    return (
        f"[out:json][timeout:{TIMEOUT_OVERPASS_S}];\n"
        'area["ISO3166-1"="TN"][admin_level=2]->.tunisie;\n'
        'nwr["aeroway"="aerodrome"]["iata"]["name"](area.tunisie);\n'
        "out center tags;"
    )


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance orthodromique (haversine), rayon terrestre moyen 6 371 km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))


DISTANCE_MAX_AEROPORT_KM = 60
# Exceptions à la règle de la ville la plus proche : l'aéroport de Tunis-Carthage est à
# 3,8 km du centre d'Ariana (7,9 km de Tunis), mais le catalogue le rattache à Tunis
# (`AEROPORTS_REFERENCE` de services/catalog/app/lieux.py) et les voyageurs aussi.
VILLE_IMPOSEE_PAR_IATA = {"TUN": "Tunis"}


def ville_la_plus_proche(latitude: float, longitude: float,
                         max_km: float = DISTANCE_MAX_AEROPORT_KM) -> Ville | None:
    """Ville couverte la plus proche d'un point, ou None au-delà de `max_km`."""
    distance, ville = min(
        ((distance_km(latitude, longitude, v.latitude, v.longitude), v) for v in VILLES),
        key=lambda paire: paire[0],
    )
    return ville if distance <= max_km else None


def ville_de_rattachement(latitude: float, longitude: float, ville: Ville) -> Ville:
    """Ville à laquelle rattacher un POI trouvé par la collecte de `ville`.

    Parmi `ville` et les villes dont le cercle de collecte contient le point, celle dont
    le centre est le plus proche. Un point qui n'est que dans le cercle de `ville` lui
    reste rattaché, même s'il est plus près du centre d'une ville voisine."""
    candidates = [ville] + [
        v for v in VILLES
        if v != ville and distance_km(latitude, longitude, v.latitude, v.longitude) * 1000 <= v.rayon_m
    ]
    return min(candidates, key=lambda v: distance_km(latitude, longitude, v.latitude, v.longitude))


def selectionner_aeroports(elements: list[dict], maintenant: datetime) -> list[dict]:
    """Un POI par code IATA, rattaché à la ville couverte la plus proche.

    Un aéroport peut sortir deux fois (nœud + contour) : on garde le contour
    (centre géométrique) plutôt que le nœud. Les aéroports à plus de 60 km de
    toute ville couverte (El Borma...) sont ignorés ; `VILLE_IMPOSEE_PAR_IATA`
    prime sur la distance (TUN → Tunis)."""
    par_iata: dict[str, dict] = {}
    for element in sorted(elements, key=lambda e: (e.get("type") == "node", e.get("id", 0))):
        position = coordonnees(element)
        if position is None:
            continue
        ville = ville_la_plus_proche(*position)
        poi = element_vers_poi(element, ville.nom, maintenant) if ville else None
        if poi and poi["type"] == "aeroport":
            code = poi["tags"]["iata"].upper()
            poi["ville"] = VILLE_IMPOSEE_PAR_IATA.get(code, poi["ville"])
            par_iata.setdefault(code, poi)
    return [par_iata[code] for code in sorted(par_iata)]


def collecter_aeroports(
    client: httpx.Client, url: str, dormir: Callable[[float], None] = time.sleep
) -> list[dict]:
    elements = interroger_overpass(client, url, construire_requete_aeroports(), dormir)
    return selectionner_aeroports(elements, datetime.now(UTC))


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
    """Convertit les éléments et plafonne chaque type de façon déterministe (ordre des id OSM).

    Rattachement unique : un élément situé aussi dans le cercle d'une autre ville, et plus
    proche de son centre, est écarté (il sera collecté avec elle). Sans ce filtre, un POI
    dans deux cercles (Grand Tunis) prendrait la ville de la dernière collecte lancée."""
    pois = {}
    for element in elements:
        position = coordonnees(element)
        if position and ville_de_rattachement(*position, ville) != ville:
            continue
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
