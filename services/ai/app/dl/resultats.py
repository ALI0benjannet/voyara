"""Lecture des résultats chiffrés (CSV de docs/ia/resultats) pour l'interface DL test."""

import csv
import math
from pathlib import Path
from typing import Any

from app.dl import chemins


def _valeur(brute: str) -> Any:
    if brute is None or brute == "":
        return None
    try:
        nombre = float(brute)
    except ValueError:
        return brute
    return None if math.isnan(nombre) else nombre


def lire_csv(nom: str, dossier: Path | None = None) -> list[dict[str, Any]]:
    """Lignes d'un CSV de résultats (nombres convertis, cellules vides → None) ; [] si absent."""
    chemin = (dossier or chemins.RESULTATS) / nom
    if not chemin.exists():
        return []
    with chemin.open(encoding="utf-8", newline="") as f:
        return [{cle: _valeur(v) for cle, v in ligne.items()} for ligne in csv.DictReader(f)]


def tous_les_resultats(dossier: Path | None = None) -> dict[str, Any]:
    return {
        "recherche": {
            "global": lire_csv("dl_recherche.csv", dossier),
            "choix_modele": lire_csv("dl_recherche_choix_modele.csv", dossier),
            "pertes": lire_csv("dl_recherche_pertes.csv", dossier),
            "rangs": lire_csv("dl_recherche_rangs.csv", dossier),
        },
        "classification": {
            "global": lire_csv("dl_classif.csv", dossier),
            "regles": lire_csv("dl_classif_regles.csv", dossier),
        },
    }
