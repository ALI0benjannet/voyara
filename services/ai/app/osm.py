"""Conversion des éléments OpenStreetMap (réponse Overpass) en POI Voyara.

Fonctions pures, sans réseau ni base : testées par tests/test_osm.py.
"""

import re
from datetime import datetime

# Ordre de priorité quand un objet porte plusieurs tags reconnus
# (ex. un musée installé dans un fort : `tourism=museum` + `historic=fort` -> musee).
REGLES_TYPE: tuple[tuple[str, str, frozenset[str]], ...] = (
    ("musee", "tourism", frozenset({"museum"})),
    ("monument", "historic", frozenset({"monument", "memorial", "archaeological_site", "castle", "fort", "ruins"})),
    ("souk", "amenity", frozenset({"marketplace"})),
    ("souk", "shop", frozenset({"bazaar"})),
    ("plage", "natural", frozenset({"beach"})),
    ("plage", "leisure", frozenset({"beach_resort"})),
    ("parc", "leisure", frozenset({"park", "water_park"})),
    ("parc", "tourism", frozenset({"zoo", "theme_park"})),
    ("restaurant", "amenity", frozenset({"restaurant"})),
    ("cafe", "amenity", frozenset({"cafe"})),
)

JOURS_OSM = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
JOURS_FR = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")

_PLAGE_HORAIRE = re.compile(r"^([01]\d|2[0-4]):([0-5]\d)-([01]\d|2[0-4]):([0-5]\d)\+?$")
_PRIX = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:tnd|dt|dinars?)\b", re.IGNORECASE)


def determiner_type(tags: dict) -> str | None:
    """Type Voyara d'un objet OSM, ou None s'il n'entre dans aucune famille."""
    # Aéroport (étape 2-bis) : seulement avec un code IATA, ce qui écarte aéroclubs,
    # pistes agricoles et bases militaires sans vols commerciaux.
    if tags.get("aeroway") == "aerodrome" and tags.get("iata"):
        return "aeroport"
    for type_poi, cle, valeurs in REGLES_TYPE:
        if tags.get(cle) in valeurs:
            return type_poi
    return None


def _jours(expression: str) -> list[int] | None:
    """`Mo-Fr,Su` -> [0, 1, 2, 3, 4, 6] ; None si l'expression n'est pas reconnue."""
    resultat: list[int] = []
    for morceau in expression.split(","):
        bornes = morceau.split("-")
        if not all(b in JOURS_OSM for b in bornes) or len(bornes) > 2:
            return None
        debut = JOURS_OSM.index(bornes[0])
        fin = JOURS_OSM.index(bornes[-1])
        if fin < debut:  # plage qui passe par dimanche : Sa-Mo
            fin += 7
        resultat.extend(j % 7 for j in range(debut, fin + 1))
    return resultat


def _plages(expression: str) -> list[list[str]] | None:
    """`09:00-12:00,14:00-18:00` -> [["09:00", "12:00"], ["14:00", "18:00"]]."""
    if expression in ("off", "closed"):
        return []
    plages = []
    for morceau in expression.split(","):
        m = _PLAGE_HORAIRE.match(morceau.strip())
        if not m:
            return None
        plages.append([f"{m.group(1)}:{m.group(2)}", f"{m.group(3)}:{m.group(4)}"])
    return plages


def normaliser_horaires(brut: str | None) -> dict[str, list[list[str]]] | None:
    """Analyse le sous-ensemble courant de la syntaxe OSM `opening_hours`.

    Retourne {"lundi": [["09:00", "18:00"]], ..., "dimanche": []} (liste vide = fermé),
    ou None si une règle n'est pas reconnue : le texte brut reste alors la seule source.
    Les règles se lisent dans l'ordre, une règle plus loin remplace la précédente pour
    les mêmes jours (sémantique OSM). Les règles de jours fériés (`PH`, `SH`) sont ignorées.
    """
    if not brut or not brut.strip():
        return None
    texte = brut.strip()
    if texte == "24/7":
        return {jour: [["00:00", "24:00"]] for jour in JOURS_FR}

    semaine: dict[str, list[list[str]]] = {jour: [] for jour in JOURS_FR}
    for regle in (r.strip() for r in texte.split(";")):
        if not regle:
            continue
        if regle.startswith(("PH", "SH")):
            continue
        morceaux = regle.split(None, 1)
        if len(morceaux) == 2 and _jours(morceaux[0]) is not None:
            jours, plages = _jours(morceaux[0]), _plages(morceaux[1].strip())
        elif len(morceaux) == 1:
            # Plages seules (« 08:00-23:00 ») = tous les jours ; jours seuls = non géré
            jours, plages = list(range(7)), _plages(morceaux[0])
        else:
            return None
        if jours is None or plages is None:
            return None
        for j in jours:
            semaine[JOURS_FR[j]] = plages
    return semaine


def extraire_prix(tags: dict) -> float | None:
    """Prix en DT : `charge` lisible en dinars, ou 0 si l'accès est gratuit (`fee=no`)."""
    charge = tags.get("charge")
    if charge:
        m = _PRIX.search(charge)
        if m:
            return float(m.group(1).replace(",", "."))
    if tags.get("fee") == "no":
        return 0.0
    return None


def coordonnees(element: dict) -> tuple[float, float] | None:
    """Un nœud porte lat/lon ; une voie ou une relation, son `center` (out center)."""
    if "lat" in element and "lon" in element:
        return element["lat"], element["lon"]
    centre = element.get("center")
    if centre:
        return centre["lat"], centre["lon"]
    return None


def element_vers_poi(element: dict, ville: str, maintenant: datetime) -> dict | None:
    """Élément Overpass -> dictionnaire prêt pour l'upsert de `pois` ; None si inexploitable."""
    tags = element.get("tags") or {}
    type_poi = determiner_type(tags)
    nom = (tags.get("name:fr") or tags.get("name") or "").strip()
    position = coordonnees(element)
    if type_poi is None or not nom or position is None:
        return None
    horaires = tags.get("opening_hours")
    return {
        "type": type_poi,
        "nom": nom[:255],
        "nom_en": (tags.get("name:en") or "").strip()[:255] or None,
        "nom_ar": (tags.get("name:ar") or "").strip()[:255] or None,
        "ville": ville,
        "latitude": round(position[0], 7),
        "longitude": round(position[1], 7),
        "horaires_ouverture": horaires,
        "horaires_normalises": normaliser_horaires(horaires),
        "prix_moyen": extraire_prix(tags),
        "tags": tags,
        "source": "osm",
        "source_id": f"{element['type']}/{element['id']}",
        "maj_le": maintenant,
    }
