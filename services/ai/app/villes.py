"""Référentiel des villes couvertes par le moteur IA.

Partagé par la collecte des POI (centre + rayon de la requête Overpass) et par
la météo (coordonnées envoyées à Open-Meteo). Coordonnées OpenStreetMap.
"""

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Ville:
    nom: str
    latitude: float
    longitude: float
    rayon_m: int  # rayon de collecte autour du centre


VILLES: tuple[Ville, ...] = (
    # Djerba : centre de l'île, le rayon couvre Houmt Souk, Midoun, Guellala et Ajim
    Ville("Djerba", 33.8100, 10.8800, 16000),
    Ville("Tunis", 36.7990, 10.1700, 5000),
    Ville("Sidi Bou Saïd", 36.8687, 10.3416, 2000),
    Ville("Sousse", 35.8256, 10.6411, 6000),
    Ville("Hammamet", 36.4000, 10.6167, 7000),
    Ville("Monastir", 35.7643, 10.8113, 5000),
    Ville("Tozeur", 33.9197, 8.1335, 6000),
    Ville("Kairouan", 35.6781, 10.0963, 4000),
)


def normaliser(texte: str) -> str:
    """Minuscules, sans accents ni séparateurs : « Sidi-Bou-Said » == « sidi bou saïd »."""
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return "".join(c for c in sans_accents.lower() if c.isalnum())


def trouver_ville(nom: str) -> Ville:
    cle = normaliser(nom)
    for ville in VILLES:
        if normaliser(ville.nom) == cle:
            return ville
    connues = ", ".join(v.nom for v in VILLES)
    raise ValueError(f"Ville inconnue : {nom!r} (villes connues : {connues})")
