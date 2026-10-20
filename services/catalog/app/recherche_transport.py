"""Calculs de la recherche transport (étape 2-bis) : fonctions pures, sans base.

Les horaires de `flights` sont en heure locale de l'aéroport (sans fuseau en base) :
le fuseau vient du référentiel `aeroports`. Testé par tests/test_transport_interne.py.
"""

import math
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

# Correspondance : même aéroport, attente bornée (en dessous, la correspondance est
# irréaliste ; au-delà, mieux vaut proposer une nuit sur place).
ATTENTE_MIN = timedelta(minutes=60)
ATTENTE_MAX = timedelta(hours=8)
DEVISE = "DT"


def localiser(moment: datetime, fuseau: str | None) -> datetime:
    """Heure locale naïve + fuseau IANA -> datetime avec décalage ; inchangée si fuseau inconnu."""
    if moment.tzinfo or not fuseau:
        return moment
    return moment.replace(tzinfo=ZoneInfo(fuseau))


def en_utc(moment: datetime, fuseau: str | None) -> datetime | None:
    local = localiser(moment, fuseau)
    return local.astimezone(UTC) if local.tzinfo else None


def minutes_entre(debut: datetime | None, fin: datetime | None) -> int | None:
    if debut is None or fin is None:
        return None
    return round((fin - debut).total_seconds() / 60)


def fenetre_jours(jour: date, tolerance: int) -> tuple[datetime, datetime]:
    """[jour - tolérance 00:00 ; jour + tolérance + 1 00:00[ en heure locale de départ."""
    debut = datetime.combine(jour - timedelta(days=tolerance), datetime.min.time())
    return debut, debut + timedelta(days=2 * tolerance + 1)


def segment(vol, fuseaux: dict[str, str]) -> dict:
    """Un tronçon (ligne `flights`) au format de l'API, horaires ISO 8601 avec décalage."""
    f_dep, f_arr = fuseaux.get(vol.aeroport_depart), fuseaux.get(vol.aeroport_arrivee)
    return {
        "id": vol.id,
        "compagnie": vol.compagnie,
        "numero_vol": vol.numero_vol,
        "aeroport_depart": vol.aeroport_depart,
        "aeroport_arrivee": vol.aeroport_arrivee,
        "ville_depart": vol.ville_depart,
        "ville_arrivee": vol.ville_arrivee,
        "depart_le": localiser(vol.depart_le, f_dep).isoformat(),
        "arrivee_le": localiser(vol.arrivee_le, f_arr).isoformat(),
        "duree_min": minutes_entre(en_utc(vol.depart_le, f_dep), en_utc(vol.arrivee_le, f_arr)),
        "classe": vol.classe,
        "prix": float(vol.prix),
        "places_disponibles": vol.places_disponibles,
    }


def itineraire(vols: list, jour: date, nb_passagers: int, fuseaux: dict[str, str]) -> dict:
    """Vol direct (1 tronçon) ou avec correspondance (2 tronçons) -> offre comparable."""
    premier, dernier = vols[0], vols[-1]
    attente = (
        minutes_entre(vols[0].arrivee_le, vols[1].depart_le) if len(vols) == 2 else 0
    )  # même aéroport, donc même fuseau : différence d'heures locales exacte
    prix_par_passager = round(sum(float(v.prix) for v in vols), 2)
    return {
        "escales": len(vols) - 1,
        "aeroports_escale": [v.aeroport_arrivee for v in vols[:-1]],
        "segments": [segment(v, fuseaux) for v in vols],
        "aeroport_depart": premier.aeroport_depart,
        "aeroport_arrivee": dernier.aeroport_arrivee,
        "depart_le": localiser(premier.depart_le, fuseaux.get(premier.aeroport_depart)).isoformat(),
        "arrivee_le": localiser(dernier.arrivee_le, fuseaux.get(dernier.aeroport_arrivee)).isoformat(),
        "duree_totale_min": minutes_entre(
            en_utc(premier.depart_le, fuseaux.get(premier.aeroport_depart)),
            en_utc(dernier.arrivee_le, fuseaux.get(dernier.aeroport_arrivee)),
        ),
        "attente_min": attente,
        "classe": premier.classe,
        "places_restantes": min(v.places_disponibles for v in vols),
        "nb_passagers": nb_passagers,
        "prix_par_passager": prix_par_passager,
        "prix_total": round(prix_par_passager * nb_passagers, 2),
        "devise": DEVISE,
        "ecart_jours": (premier.depart_le.date() - jour).days,
    }


def composer_correspondances(premiers: list, seconds: list) -> list[tuple]:
    """Paires (vol 1, vol 2) : même aéroport de correspondance, même classe,
    attente dans [ATTENTE_MIN ; ATTENTE_MAX], et pas de retour au point de départ."""
    paires = []
    for v1 in premiers:
        for v2 in seconds:
            if (
                v2.aeroport_depart == v1.aeroport_arrivee
                and v2.classe == v1.classe
                and v2.aeroport_arrivee != v1.aeroport_depart
                and ATTENTE_MIN <= v2.depart_le - v1.arrivee_le <= ATTENTE_MAX
            ):
                paires.append((v1, v2))
    return paires


CLES_TRI = {
    # Par défaut : la date demandée d'abord, puis le direct, puis le prix.
    "pertinence": lambda i: (abs(i["ecart_jours"]), i["escales"], i["prix_total"], i["depart_le"]),
    "prix": lambda i: (i["prix_total"], i["depart_le"]),
    "depart": lambda i: (i["depart_le"], i["prix_total"]),
    "duree": lambda i: (
        i["duree_totale_min"] if i["duree_totale_min"] is not None else math.inf, i["prix_total"]
    ),
}


def nb_jours_location(prise_le: datetime, retour_le: datetime) -> int:
    """Jours facturés : toute période de 24 h entamée est due, minimum 1."""
    return max(1, math.ceil((retour_le - prise_le).total_seconds() / 86400))
