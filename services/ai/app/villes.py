"""Référentiel des villes couvertes par le moteur IA.

Partagé par la collecte des POI (centre + rayon de la requête Overpass) et par
la météo (coordonnées envoyées à Open-Meteo). Coordonnées OpenStreetMap
(nœud `place` de la ville, vérifié avec Nominatim le 09/11/2026).

29 villes : les chefs-lieux des 24 gouvernorats, plus Sidi Bou Saïd, Hammamet,
Djerba, Tabarka et Douz. Les noms suivent les `localisation` du catalogue.
Un POI situé dans deux cercles (Grand Tunis) est rattaché au centre le plus
proche (`collecte.selectionner`).
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
    # Tabarka : le rayon couvre le port, le fort génois et l'aéroport Tabarka–Aïn Draham (TBJ)
    Ville("Tabarka", 36.9544, 8.7580, 6000),
    # --- Chefs-lieux ajoutés le 09/11/2026 (rapport etape-04-villes-tunisie) ---
    # Grand Tunis : rayons réduits, le recouvrement avec Tunis (5 km) reste < 7 % du petit cercle
    Ville("Ariana", 36.8587, 10.1882, 2500),
    Ville("Ben Arous", 36.7517, 10.2245, 2500),
    Ville("La Manouba", 36.8113, 10.0947, 2500),
    # Nabeul : 4 km pour ne pas toucher le cercle de Hammamet (12 km entre les centres)
    Ville("Nabeul", 36.4513, 10.7356, 4000),
    Ville("Zaghouan", 36.3995, 10.1446, 3000),
    Ville("Bizerte", 37.2721, 9.8709, 5000),
    Ville("Béja", 36.7237, 9.1854, 3000),
    # Jendouba : 8 km pour inclure le site de Bulla Regia (7 km au nord)
    Ville("Jendouba", 36.4967, 8.7757, 8000),
    # Le Kef et Siliana : pas de nœud `place` dans OSM, centre du polygone résidentiel
    Ville("Le Kef", 36.1784, 8.7073, 3000),
    Ville("Siliana", 36.0847, 9.3744, 3000),
    Ville("Mahdia", 35.5036, 11.0682, 5000),
    Ville("Sfax", 34.7394, 10.7604, 6000),
    Ville("Kasserine", 35.1688, 8.8366, 4000),
    Ville("Sidi Bouzid", 35.0382, 9.4865, 3000),
    # Gabès : 5 km pour inclure l'oasis littorale de Chenini de Gabès
    Ville("Gabès", 33.8878, 10.1004, 5000),
    Ville("Médenine", 33.3434, 10.4911, 3000),
    Ville("Tataouine", 32.9315, 10.4504, 4000),
    Ville("Gafsa", 34.4224, 8.7844, 4000),
    Ville("Kébili", 33.7061, 8.9698, 4000),
    # Douz : 5 km pour inclure la zone touristique et les premières dunes
    Ville("Douz", 33.4571, 9.0250, 5000),
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
