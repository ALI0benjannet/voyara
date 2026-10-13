"""Prévisions météo Open-Meteo (sans clé) avec cache en base (`meteo_cache`).

Le cache est servi tant que toutes les dates demandées y sont et datent de moins
de METEO_CACHE_HEURES (6 h). Sinon, un seul appel Open-Meteo rafraîchit la plage
entière. Si Open-Meteo est injoignable, le cache périmé est renvoyé (marqué
`perime=True`) plutôt que rien : un itinéraire reste constructible hors-ligne.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import MeteoCache
from app.villes import trouver_ville

logger = logging.getLogger(__name__)

HORIZON_MAX_JOURS = 16  # limite des prévisions Open-Meteo
VARIABLES = "temperature_2m_min,temperature_2m_max,precipitation_sum,weather_code"
PAUSE_AVANT_NOUVELLE_TENTATIVE_S = 2


class MeteoIndisponible(Exception):
    """Ni Open-Meteo ni le cache ne peuvent fournir la météo demandée."""


@dataclass(frozen=True)
class MeteoJour:
    ville: str
    date: date
    temp_min: float | None
    temp_max: float | None
    precipitations: float | None
    code_meteo: int | None
    perime: bool = False


def _depuis_cache(lignes: list[MeteoCache], perime: bool) -> list[MeteoJour]:
    return [
        MeteoJour(m.ville, m.date, m.temp_min, m.temp_max, m.precipitations, m.code_meteo, perime)
        for m in sorted(lignes, key=lambda m: m.date)
    ]


def _appeler_open_meteo(client: httpx.Client, ville, debut: date, fin: date, dormir) -> list[dict]:
    params = {
        "latitude": ville.latitude,
        "longitude": ville.longitude,
        "daily": VARIABLES,
        "timezone": "Africa/Tunis",
        "start_date": debut.isoformat(),
        "end_date": fin.isoformat(),
    }
    # Open-Meteo renvoie parfois un 503 passager (constaté le 13/10/2026) : une nouvelle tentative
    for tentative in range(2):
        if tentative:
            dormir(PAUSE_AVANT_NOUVELLE_TENTATIVE_S)
        try:
            reponse = client.get(settings.OPEN_METEO_URL, params=params, timeout=15)
        except httpx.TransportError:
            if tentative:
                raise
            continue
        if reponse.status_code < 500 or tentative:
            break
    reponse.raise_for_status()
    jours = reponse.json()["daily"]
    return [
        {
            "date": date.fromisoformat(jours["time"][i]),
            "temp_min": jours["temperature_2m_min"][i],
            "temp_max": jours["temperature_2m_max"][i],
            "precipitations": jours["precipitation_sum"][i],
            "code_meteo": jours["weather_code"][i],
        }
        for i in range(len(jours["time"]))
    ]


def obtenir_meteo(
    db: Session,
    ville: str,
    date_debut: date,
    nb_jours: int = 1,
    client: httpx.Client | None = None,
    dormir: Callable[[float], None] = time.sleep,
) -> list[MeteoJour]:
    """Météo journalière de `ville` pour `nb_jours` à partir de `date_debut`."""
    if not 1 <= nb_jours <= HORIZON_MAX_JOURS:
        raise ValueError(f"nb_jours doit être entre 1 et {HORIZON_MAX_JOURS}")
    v = trouver_ville(ville)
    fin = date_debut + timedelta(days=nb_jours - 1)
    maintenant = datetime.now(UTC)
    limite = maintenant - timedelta(hours=settings.METEO_CACHE_HEURES)

    en_cache = (
        db.query(MeteoCache)
        .filter(MeteoCache.ville == v.nom, MeteoCache.date >= date_debut, MeteoCache.date <= fin)
        .all()
    )
    if len(en_cache) == nb_jours and all(m.maj_le > limite for m in en_cache):
        return _depuis_cache(en_cache, perime=False)

    proprietaire = client is None
    client = client or httpx.Client()
    try:
        jours = _appeler_open_meteo(client, v, date_debut, fin, dormir)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        logger.warning("Open-Meteo indisponible pour %s : %s", v.nom, exc)
        if en_cache:
            return _depuis_cache(en_cache, perime=True)
        raise MeteoIndisponible(f"Météo indisponible pour {v.nom} et aucun cache") from exc
    finally:
        if proprietaire:
            client.close()

    for jour in jours:
        requete = insert(MeteoCache).values(ville=v.nom, maj_le=maintenant, **jour)
        db.execute(
            requete.on_conflict_do_update(
                constraint="uq_meteo_ville_date",
                set_={c: requete.excluded[c] for c in (*jour, "maj_le") if c != "date"},
            )
        )
    db.commit()
    return [MeteoJour(v.nom, perime=False, **jour) for jour in jours]
