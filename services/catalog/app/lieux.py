"""Lieux du domaine transport : référentiel des aéroports, déduction et résolution de lieux.

Fonctions pures, sans base ni réseau (testées par tests/test_lieux.py). Utilisées par
la migration scripts/add_transport_ia.py, l'API admin (travel_routes), le seed des
offres et les recherches internes du moteur IA (internal_offres_routes).
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

# Référentiel initial : les 14 aéroports déjà utilisés par la table `flights`.
# Faits publics (code IATA, nom usuel, ville desservie, pays ISO-2, fuseau IANA).
# `ville` reprend exactement `flights.ville_depart / ville_arrivee` du seed.
AEROPORTS_REFERENCE: tuple[dict[str, str], ...] = (
    {"code_iata": "TUN", "nom": "Tunis-Carthage", "ville": "Tunis", "pays": "TN", "fuseau": "Africa/Tunis"},
    {"code_iata": "DJE", "nom": "Djerba-Zarzis", "ville": "Djerba", "pays": "TN", "fuseau": "Africa/Tunis"},
    {"code_iata": "MIR", "nom": "Monastir Habib-Bourguiba", "ville": "Monastir", "pays": "TN", "fuseau": "Africa/Tunis"},
    {"code_iata": "NBE", "nom": "Enfidha-Hammamet", "ville": "Enfidha", "pays": "TN", "fuseau": "Africa/Tunis"},
    {"code_iata": "TOE", "nom": "Tozeur-Nefta", "ville": "Tozeur", "pays": "TN", "fuseau": "Africa/Tunis"},
    {"code_iata": "ORY", "nom": "Paris-Orly", "ville": "Paris", "pays": "FR", "fuseau": "Europe/Paris"},
    {"code_iata": "CDG", "nom": "Paris-Charles-de-Gaulle", "ville": "Paris", "pays": "FR", "fuseau": "Europe/Paris"},
    {"code_iata": "LYS", "nom": "Lyon-Saint-Exupéry", "ville": "Lyon", "pays": "FR", "fuseau": "Europe/Paris"},
    {"code_iata": "MRS", "nom": "Marseille-Provence", "ville": "Marseille", "pays": "FR", "fuseau": "Europe/Paris"},
    {"code_iata": "NCE", "nom": "Nice-Côte d'Azur", "ville": "Nice", "pays": "FR", "fuseau": "Europe/Paris"},
    {"code_iata": "FCO", "nom": "Rome-Fiumicino", "ville": "Rome", "pays": "IT", "fuseau": "Europe/Rome"},
    {"code_iata": "FRA", "nom": "Francfort-sur-le-Main", "ville": "Francfort", "pays": "DE", "fuseau": "Europe/Berlin"},
    {"code_iata": "BRU", "nom": "Bruxelles-Zaventem", "ville": "Bruxelles", "pays": "BE", "fuseau": "Europe/Brussels"},
    {"code_iata": "GVA", "nom": "Genève-Cointrin", "ville": "Genève", "pays": "CH", "fuseau": "Europe/Zurich"},
)

_CODE_IATA = re.compile(r"^[A-Za-z]{3}$")


def normaliser(texte: str | None) -> str:
    """Minuscules, sans accents ni séparateurs : « Aéroport Tunis-Carthage » -> « aeroporttuniscarthage »."""
    sans_accents = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()
    return "".join(c for c in sans_accents.lower() if c.isalnum())


def _champ(aeroport: Any, nom: str) -> str:
    """Accepte un dict du référentiel ou une ligne ORM `Aeroport`."""
    return aeroport[nom] if isinstance(aeroport, dict) else getattr(aeroport, nom)


def _cles_aeroport(aeroport: Any) -> list[str]:
    """Formes reconnues du nom : « tuniscarthage », et sans la ville en tête : « carthage »."""
    nom, ville = normaliser(_champ(aeroport, "nom")), normaliser(_champ(aeroport, "ville"))
    cles = [nom]
    if ville and nom.startswith(ville) and len(nom) - len(ville) >= 5:
        cles.append(nom[len(ville):])
    return cles


def deduire_lieu(texte: str | None, aeroports: list) -> tuple[str | None, str | None]:
    """(ville, code IATA) d'un libellé libre de voiture ou de transfert.

    - « Tunis, aéroport Tunis-Carthage » -> ("Tunis", "TUN")
    - « Aéroport Monastir Habib-Bourguiba » -> ("Monastir", "MIR")
    - « Djerba, zone touristique de Midoun » -> ("Djerba", None)
    Un libellé sans aéroport reconnu ni virgule donne une ville None : on n'invente rien.
    """
    cle = normaliser(texte)
    if "aeroport" in cle or "airport" in cle:
        for aeroport in aeroports:
            if any(c in cle for c in _cles_aeroport(aeroport)):
                return _champ(aeroport, "ville"), _champ(aeroport, "code_iata")
    if texte and "," in texte:
        ville = texte.split(",", 1)[0].strip()
        return (ville or None), None
    return None, None


def ville_de_localisation(localisation: str | None) -> str | None:
    """Ville d'un séjour : préfixe de `localisation` (« Tunis, Sidi Bou Saïd » -> « Tunis »)."""
    if not localisation:
        return None
    return localisation.split(",", 1)[0].strip() or None


def completer_lieux(offre: Any, aeroports: list) -> None:
    """Remplit les colonnes de lieu restées vides d'une voiture ou d'un transfert.

    Une valeur déjà renseignée (saisie admin) n'est jamais écrasée."""
    if hasattr(offre, "localisation") and hasattr(offre, "aeroport"):  # CarRental
        ville, code = deduire_lieu(offre.localisation, aeroports)
        offre.ville = offre.ville or ville
        offre.aeroport = offre.aeroport or code
        return
    for sens in ("depart", "arrivee"):  # Transfer
        ville, code = deduire_lieu(getattr(offre, sens), aeroports)
        if not getattr(offre, f"ville_{sens}"):
            setattr(offre, f"ville_{sens}", ville)
        if not getattr(offre, f"aeroport_{sens}"):
            setattr(offre, f"aeroport_{sens}", code)


@dataclass(frozen=True)
class Lieu:
    """Lieu demandé par le moteur IA, résolu contre le référentiel.

    mode = « aeroport » (code IATA donné), « ville » (ville connue), « texte » (autre)."""

    saisie: str
    mode: str
    codes: frozenset[str]
    ville: str | None

    def correspond_au_texte(self, *textes: str | None) -> bool:
        cle = normaliser(self.saisie)
        return bool(cle) and any(cle in normaliser(t) for t in textes)


def resoudre_lieu(saisie: str, aeroports: list, villes_connues: set[str] | None = None,
                  codes_connus: set[str] | None = None) -> Lieu:
    """« DJE » -> aéroport ; « paris » -> ville Paris (ORY + CDG) ; « Midoun » -> texte."""
    saisie = saisie.strip()
    par_code = {_champ(a, "code_iata"): a for a in aeroports}
    if _CODE_IATA.match(saisie) and (saisie.upper() in par_code or saisie.upper() in (codes_connus or set())):
        code = saisie.upper()
        ville = _champ(par_code[code], "ville") if code in par_code else None
        return Lieu(saisie, "aeroport", frozenset({code}), ville)

    cle = normaliser(saisie)
    du_referentiel = [a for a in aeroports if normaliser(_champ(a, "ville")) == cle]
    if du_referentiel:
        ville = _champ(du_referentiel[0], "ville")
        return Lieu(saisie, "ville", frozenset(_champ(a, "code_iata") for a in du_referentiel), ville)
    for ville in villes_connues or set():
        if ville and normaliser(ville) == cle:
            return Lieu(saisie, "ville", frozenset(), ville)
    return Lieu(saisie, "texte", frozenset(), None)
