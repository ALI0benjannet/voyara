"""Jeu d'évaluation NLU (étape 4) : lecture, vocabulaire, règles dérivées, validation, écarts.

Source unique des règles de `data/eval/README.md` côté code : la génération des fichiers de
relecture, leur import et l'accord entre annotateurs passent tous par ce module.
Aucune dépendance au service (pas de base, pas de réseau) : utilisable seul depuis scripts/.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any

DOSSIER_EVAL = Path(__file__).resolve().parents[1] / "data" / "eval"
FICHIER_HUMAINES = "demandes_humaines_a_annoter.jsonl"
FICHIERS_JEU = (FICHIER_HUMAINES, "nlu_dev.jsonl", "nlu_test.jsonl")

# --- Vocabulaire (README §2) ---------------------------------------------------
VILLES_CATALOGUE = ("Djerba", "Tunis", "Sidi Bou Saïd", "Sousse", "Hammamet", "Monastir", "Tozeur", "Kairouan")
# Thèmes de l'étape 2 (services/catalog/app/tags_ia.py)
THEMES = ("plage", "culture", "histoire", "nature", "gastronomie",
          "aventure", "detente", "shopping", "nautique", "desert")
TYPES_VOYAGE = ("famille", "couple", "solo", "amis", "groupe")
LANGUES = ("fr", "en", "ar", "darija")
BESOINS = ("oui", "non", "indifferent")
PRIORITES = ("prix", "confort")
BASES_BUDGET = ("total", "par_personne", "par_nuit", "par_jour")
CHAMPS_MANQUANTS = ("destination", "duree", "budget", "voyageurs", "ville_depart", "date_debut")
STATUTS = ("a_relire", "valide", "corrige")
STATUTS_RELUS = ("valide", "corrige")
DUREE_MAX_JOURS = 60  # au-delà de 14 : avertissement « planning limité à 14 jours » (étape 7)


# --- Lecture / écriture ----------------------------------------------------------

def lire_jsonl(chemin: Path) -> list[dict]:
    return [json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines() if l.strip()]


def ecrire_jsonl(chemin: Path, lignes: list[dict]) -> None:
    chemin.write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in lignes), encoding="utf-8")


def charger_jeu(dossier: Path = DOSSIER_EVAL) -> dict[str, list[dict]]:
    """{nom de fichier: demandes}, dans l'ordre de FICHIERS_JEU."""
    return {nom: lire_jsonl(dossier / nom) for nom in FICHIERS_JEU if (dossier / nom).exists()}


# --- Règles dérivées -------------------------------------------------------------

def champs_manquants(a: dict) -> list[str]:
    """Règle des champs essentiels (README §3). Pas de question de budget s'il est illimité."""
    if a.get("hors_sujet"):
        return []
    manquants = []
    if a.get("destination") is None:
        manquants.append("destination")
    if a.get("duree_jours") is None:
        manquants.append("duree")
    if a.get("budget_montant") is None and not a.get("budget_illimite"):
        manquants.append("budget")
    if a.get("nb_voyageurs") is None:
        manquants.append("voyageurs")
    if (a.get("besoins_transport") or {}).get("vol") == "oui":
        if a.get("ville_depart") is None:
            manquants.append("ville_depart")
        if a.get("date_debut") is None:
            manquants.append("date_debut")
    return manquants


def deriver(a: dict) -> None:
    """Recalcule les champs qui découlent des autres (jamais saisis à la main)."""
    a["budget_total_dt"] = a.get("budget_montant") if a.get("budget_devise") == "TND" else None
    a["champs_manquants"] = champs_manquants(a)


# --- Validation ------------------------------------------------------------------

def _date_iso(valeur: Any) -> date | None:
    if valeur is None:
        return None
    return date.fromisoformat(str(valeur))


def valider(demande: dict) -> list[str]:
    """Liste des incohérences d'une demande annotée (vide = valide)."""
    erreurs: list[str] = []
    a = demande.get("attendu") or {}

    def err(message: str) -> None:
        erreurs.append(message)

    def dans(champ: str, valeur: Any, autorisees: tuple, nul_ok: bool = True) -> None:
        if valeur is None and nul_ok:
            return
        if valeur not in autorisees:
            err(f"{champ} = {valeur!r} interdit (attendu : {', '.join(map(str, autorisees))})")

    def entier(champ: str, valeur: Any, mini: int, maxi: int) -> None:
        if valeur is None:
            return
        if not isinstance(valeur, int) or isinstance(valeur, bool) or not mini <= valeur <= maxi:
            err(f"{champ} = {valeur!r} hors limites ({mini} à {maxi})")

    def booleen(champ: str, valeur: Any, nul_ok: bool = True) -> None:
        if valeur is None and nul_ok:
            return
        if not isinstance(valeur, bool):
            err(f"{champ} = {valeur!r} : vrai ou faux attendu")

    dans("source", demande.get("source"), ("humain", "genere"), nul_ok=False)
    dans("jeu", demande.get("jeu"), ("dev", "test"))
    dans("statut", demande.get("statut"), STATUTS, nul_ok=False)
    try:
        reference = _date_iso(demande.get("date_reference"))
        if reference is None:
            err("date_reference absente")
    except ValueError:
        reference = None
        err(f"date_reference = {demande.get('date_reference')!r} : format AAAA-MM-JJ attendu")

    dans("destination", a.get("destination"), VILLES_CATALOGUE)
    autres = a.get("autres_villes")
    if not isinstance(autres, list):
        err("autres_villes doit être une liste")
    else:
        for ville in autres:
            dans("autres_villes", ville, VILLES_CATALOGUE, nul_ok=False)
        if len(set(autres)) != len(autres):
            err("autres_villes contient un doublon")
        if a.get("destination") in autres:
            err("autres_villes répète la destination")
        if autres and a.get("destination") is None:
            err("autres_villes sans destination principale")

    try:
        debut = _date_iso(a.get("date_debut"))
        if debut and reference and debut < reference:
            err(f"date_debut {debut} antérieure à date_reference {reference}")
    except ValueError:
        err(f"date_debut = {a.get('date_debut')!r} : format AAAA-MM-JJ attendu")

    jours, nuits = a.get("duree_jours"), a.get("nb_nuits")
    entier("duree_jours", jours, 1, DUREE_MAX_JOURS)
    entier("nb_nuits", nuits, 0, DUREE_MAX_JOURS)
    if isinstance(jours, int) and isinstance(nuits, int) and nuits not in (jours - 1, jours):
        err(f"duree_jours {jours} et nb_nuits {nuits} incohérents (nuits = jours ou jours - 1)")
    if (jours is None) != (nuits is None):
        err("duree_jours et nb_nuits : renseigner les deux ou aucun (règle unique du README)")

    montant, devise, base = a.get("budget_montant"), a.get("budget_devise"), a.get("budget_base")
    if montant is not None and (not isinstance(montant, (int, float)) or isinstance(montant, bool) or montant <= 0):
        err(f"budget_montant = {montant!r} : nombre > 0 attendu")
    if (montant is None) != (devise is None):
        err("budget_montant et budget_devise : renseigner les deux ou aucun")
    if devise is not None and not (isinstance(devise, str) and len(devise) == 3 and devise.isalpha() and devise.isupper()):
        err(f"budget_devise = {devise!r} : code ISO en 3 majuscules attendu (TND, EUR…)")
    if (montant is None) != (base is None):
        err("budget_montant et budget_base : renseigner les deux ou aucun")
    dans("budget_base", base, BASES_BUDGET)
    booleen("budget_illimite", a.get("budget_illimite"), nul_ok=False)
    if a.get("budget_illimite") and montant is not None:
        err("budget_illimite = vrai mais budget_montant renseigné")

    voyageurs, adultes, enfants = a.get("nb_voyageurs"), a.get("nb_adultes"), a.get("nb_enfants")
    entier("nb_voyageurs", voyageurs, 1, 500)
    entier("nb_adultes", adultes, 1, 500)
    entier("nb_enfants", enfants, 0, 500)
    if (adultes is None) != (enfants is None):
        err("nb_adultes et nb_enfants : renseigner les deux ou aucun")
    if isinstance(adultes, int) and isinstance(enfants, int):
        if voyageurs != adultes + enfants:
            err(f"nb_voyageurs {voyageurs} ≠ adultes + enfants ({adultes} + {enfants})")
    dans("type_voyage", a.get("type_voyage"), TYPES_VOYAGE)
    if a.get("type_voyage") == "solo" and voyageurs not in (None, 1):
        err(f"type_voyage solo mais nb_voyageurs = {voyageurs}")
    if a.get("type_voyage") == "couple" and adultes not in (None, 2):
        err(f"type_voyage couple mais nb_adultes = {adultes}")

    prefs = a.get("preferences")
    if not isinstance(prefs, list):
        err("preferences doit être une liste")
    else:
        for theme in prefs:
            dans("preferences", theme, THEMES, nul_ok=False)
        if len(set(prefs)) != len(prefs):
            err("preferences contient un doublon")

    c = a.get("contraintes") or {}
    entier("niveau_marche_max", c.get("niveau_marche_max"), 1, 3)
    booleen("mobilite_reduite", c.get("mobilite_reduite"))
    if c.get("horaires") is not None and not isinstance(c.get("horaires"), str):
        err("horaires doit être un texte")

    dans("langue", a.get("langue"), LANGUES, nul_ok=False)
    depart = a.get("ville_depart")
    if depart is not None and (not isinstance(depart, str) or not depart.strip()):
        err("ville_depart doit être un texte non vide")
    if depart is not None and depart == a.get("destination"):
        err("ville_depart identique à la destination")

    b = a.get("besoins_transport") or {}
    for cle in ("vol", "voiture", "transfert"):
        dans(f"besoins_transport.{cle}", b.get(cle), BESOINS, nul_ok=False)
    p = a.get("preferences_transport") or {}
    booleen("vol_direct", p.get("vol_direct"))
    booleen("boite_auto", p.get("boite_auto"))
    dans("priorite", p.get("priorite"), PRIORITES)
    booleen("budget_inclut_transport", a.get("budget_inclut_transport"), nul_ok=False)
    booleen("hors_sujet", a.get("hors_sujet"), nul_ok=False)
    if a.get("hors_sujet") and any(a.get(k) is not None for k in ("destination", "duree_jours", "budget_montant")):
        err("hors_sujet = vrai mais destination, durée ou budget renseigné")

    if a.get("champs_manquants") != champs_manquants(a):
        err(f"champs_manquants {a.get('champs_manquants')} ≠ règle {champs_manquants(a)}")
    return erreurs


# --- Annotation d'origine de l'équipe (brut/demandes_equipe.json) ---------------

_LANGUES_EQUIPE = {"fr": "fr", "en": "en", "arabe": "ar", "darija_arabe": "ar", "darija_latin": "darija"}
_TYPES_EQUIPE = {"famille_enfants": "famille"}
_BASES_EQUIPE = {"total": "total", "par_personne": "par_personne", "par_jour": "par_jour", "par_nuit": "par_nuit"}


def attendu_equipe(e: dict) -> dict:
    """Annotation de l'équipe traduite dans le vocabulaire du jeu (champs comparables seulement)."""
    transport = set(e.get("transport") or [])
    villes = list(e.get("villes") or [])
    montant = e.get("budget_montant")
    manquants = {"personnes": "voyageurs"}
    return {
        "destination": villes[0] if villes else None,
        "autres_villes": villes[1:],
        "langue": _LANGUES_EQUIPE.get(e.get("langue"), e.get("langue")),
        "type_voyage": _TYPES_EQUIPE.get(e.get("type_groupe"), e.get("type_groupe")),
        "nb_voyageurs": e.get("nb_personnes"),
        "duree_jours": e.get("duree_jours"),
        "budget_montant": montant,
        "budget_devise": e.get("budget_devise"),
        "budget_base": _BASES_EQUIPE.get(e.get("budget_type"), "total" if montant is not None else None),
        "ville_depart": e.get("vol_depuis") or None,
        "vol": "oui" if "vol" in transport else "indifferent",
        "voiture": ("oui" if "location_voiture" in transport
                    else "non" if transport & {"sans_voiture", "voiture_perso"} else "indifferent"),
        "transfert": "oui" if transport & {"transfert_aeroport", "chauffeur_prive"} else "indifferent",
        "champs_manquants": sorted(manquants.get(m, m) for m in e.get("infos_manquantes") or []),
    }


def valeur_comparable(a: dict, champ: str) -> Any:
    """Valeur d'un champ de `attendu` sous la forme utilisée par attendu_equipe()."""
    if champ in ("vol", "voiture", "transfert"):
        return a["besoins_transport"][champ]
    if champ == "champs_manquants":
        return sorted(a["champs_manquants"])
    return a.get(champ)


CHAMPS_COMPARES = ("destination", "autres_villes", "langue", "type_voyage", "nb_voyageurs", "duree_jours",
                   "budget_montant", "budget_devise", "budget_base", "ville_depart", "vol", "voiture",
                   "transfert", "champs_manquants")


def ecarts_equipe(demande: dict) -> list[str]:
    """« champ : équipe → jeu » pour chaque champ où l'annotation diffère de celle de l'équipe."""
    e = demande.get("annotation_equipe")
    if not e:
        return []
    equipe, a = attendu_equipe(e), demande["attendu"]
    sortie = []
    for champ in CHAMPS_COMPARES:
        v_equipe, v_jeu = equipe[champ], valeur_comparable(a, champ)
        if v_equipe != v_jeu:
            sortie.append(f"{champ} : {v_equipe} → {v_jeu}")
    return sortie
