"""Fichiers Excel de relecture du jeu NLU, un par relecteur (docs/ia/relecture/).

Toutes les demandes (humaines et générées) sont réparties entre les relecteurs, stratifiées par
langue avec une graine fixe : chaque relecteur reçoit environ le même nombre de demandes de chaque
langue. Les champs dérivés (`budget_total_dt`, `champs_manquants`) ne sont pas proposés : ils sont
recalculés à l'import (scripts/importer_relecture.py).

    cd services\\ai ; ..\\..\\.venv\\Scripts\\python scripts\\generer_relecture.py
"""

import argparse
import random
import sys
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jeu_nlu as j  # noqa: E402

DOSSIER_RELECTURE = Path(__file__).resolve().parents[3] / "docs" / "ia" / "relecture"
RELECTEURS = ("ali", "boutheina", "ons", "ghayth")
GRAINE = 20261109
FEUILLE = "Relecture"
VRAI, FAUX = "vrai", "faux"

# (en-tête Excel, chemin dans `attendu`, type) — type : texte | entier | nombre | liste | bool | choix:<vocabulaire>
COLONNES_CHAMPS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("destination", ("destination",), "choix:villes"),
    ("autres_villes", ("autres_villes",), "liste"),
    ("date_debut", ("date_debut",), "texte"),
    ("duree_jours", ("duree_jours",), "entier"),
    ("nb_nuits", ("nb_nuits",), "entier"),
    ("budget_montant", ("budget_montant",), "nombre"),
    ("budget_devise", ("budget_devise",), "texte"),
    ("budget_base", ("budget_base",), "choix:bases"),
    ("budget_illimite", ("budget_illimite",), "bool"),
    ("nb_voyageurs", ("nb_voyageurs",), "entier"),
    ("nb_adultes", ("nb_adultes",), "entier"),
    ("nb_enfants", ("nb_enfants",), "entier"),
    ("type_voyage", ("type_voyage",), "choix:types"),
    ("preferences", ("preferences",), "liste"),
    ("niveau_marche_max", ("contraintes", "niveau_marche_max"), "entier"),
    ("mobilite_reduite", ("contraintes", "mobilite_reduite"), "bool"),
    ("horaires", ("contraintes", "horaires"), "texte"),
    ("langue", ("langue",), "choix:langues"),
    ("ville_depart", ("ville_depart",), "texte"),
    ("vol", ("besoins_transport", "vol"), "choix:besoins"),
    ("voiture", ("besoins_transport", "voiture"), "choix:besoins"),
    ("transfert", ("besoins_transport", "transfert"), "choix:besoins"),
    ("vol_direct", ("preferences_transport", "vol_direct"), "bool"),
    ("boite_auto", ("preferences_transport", "boite_auto"), "bool"),
    ("priorite", ("preferences_transport", "priorite"), "choix:priorites"),
    ("budget_inclut_transport", ("budget_inclut_transport",), "bool"),
    ("hors_sujet", ("hors_sujet",), "bool"),
)
VOCABULAIRES = {
    "villes": j.VILLES_CATALOGUE, "bases": j.BASES_BUDGET, "types": j.TYPES_VOYAGE, "langues": j.LANGUES,
    "besoins": j.BESOINS, "priorites": j.PRIORITES,
}
COLONNES_AVANT = ("id", "source", "jeu", "date_reference", "texte")
COLONNES_APRES = ("a_trancher", "ecarts_vs_equipe", "statut", "commentaire")
EN_TETES = COLONNES_AVANT + tuple(c[0] for c in COLONNES_CHAMPS) + COLONNES_APRES

FOND_ECART = PatternFill("solid", fgColor="FCE4D6")      # orange clair : écart avec l'équipe
FOND_A_TRANCHER = PatternFill("solid", fgColor="FFF2CC")  # jaune : cas à trancher à la main
FOND_LECTURE = PatternFill("solid", fgColor="EDEDED")     # gris : colonnes en lecture seule
FOND_SAISIE = PatternFill("solid", fgColor="E2EFDA")      # vert : statut / commentaire


def lire_champ(attendu: dict, chemin: tuple[str, ...]) -> Any:
    valeur: Any = attendu
    for cle in chemin:
        valeur = (valeur or {}).get(cle)
    return valeur


def vers_cellule(valeur: Any, type_: str) -> Any:
    if valeur is None:
        return None
    if type_ == "bool":
        return VRAI if valeur else FAUX
    if type_ == "liste":
        return ", ".join(valeur) or None
    return valeur


def repartir(demandes: list[dict], relecteurs: tuple[str, ...], graine: int) -> dict[str, list[dict]]:
    """Stratifié par langue : chaque langue est mélangée puis distribuée à tour de rôle ; le tour
    continue d'une langue à l'autre, donc les tailles ne diffèrent que d'une demande au plus."""
    alea = random.Random(graine)
    parts: dict[str, list[dict]] = {r: [] for r in relecteurs}
    tour = 0
    for langue in sorted({d["attendu"]["langue"] for d in demandes}):
        groupe = sorted((d for d in demandes if d["attendu"]["langue"] == langue), key=lambda d: d["id"])
        alea.shuffle(groupe)
        for d in groupe:
            parts[relecteurs[tour % len(relecteurs)]].append(d)
            tour += 1
    for r in relecteurs:
        alea.shuffle(parts[r])  # humaines et générées mélangées dans le fichier
    return parts


def ecrire_classeur(chemin: Path, relecteur: str, demandes: list[dict]) -> None:
    classeur = Workbook()
    feuille = classeur.active
    feuille.title = FEUILLE
    feuille.append(list(EN_TETES))
    for cellule in feuille[1]:
        cellule.font = Font(bold=True)
        cellule.alignment = Alignment(wrap_text=True, vertical="top")

    for d in demandes:
        a = d["attendu"]
        ecarts = j.ecarts_equipe(d)
        ligne = [d["id"], d["source"], d.get("jeu"), d["date_reference"], d["texte"]]
        ligne += [vers_cellule(lire_champ(a, chemin), type_) for _, chemin, type_ in COLONNES_CHAMPS]
        ligne += [d.get("a_trancher"), "\n".join(ecarts) or None, None, None]
        feuille.append(ligne)
        rangee = feuille.max_row
        fond = FOND_A_TRANCHER if d.get("a_trancher") else FOND_ECART if ecarts else None
        for col, nom in enumerate(EN_TETES, start=1):
            cellule = feuille.cell(rangee, col)
            cellule.alignment = Alignment(wrap_text=True, vertical="top")
            if nom in ("date_debut", "budget_devise", "ville_depart", "horaires", "autres_villes", "preferences"):
                cellule.number_format = "@"  # texte : Excel ne transforme pas 2026-12-20 en date
            if nom in ("statut", "commentaire"):
                cellule.fill = FOND_SAISIE
            elif nom in COLONNES_AVANT or nom in ("a_trancher", "ecarts_vs_equipe"):
                cellule.fill = fond or FOND_LECTURE
            elif fond:
                cellule.fill = fond

    derniere = feuille.max_row
    lettre = {nom: feuille.cell(1, i).column_letter for i, nom in enumerate(EN_TETES, start=1)}
    listes = {"statut": ("valide", "corrige")}
    for nom, _, type_ in COLONNES_CHAMPS:
        if type_ == "bool":
            listes[nom] = (VRAI, FAUX)
        elif type_.startswith("choix:"):
            listes[nom] = VOCABULAIRES[type_.split(":")[1]]
    for nom, valeurs in listes.items():
        validation = DataValidation(type="list", formula1='"' + ",".join(valeurs) + '"', allow_blank=nom != "statut",
                                    showErrorMessage=True, errorTitle="Valeur interdite",
                                    error="Choisir une valeur de la liste (vide = inconnu).")
        feuille.add_data_validation(validation)
        validation.add(f"{lettre[nom]}2:{lettre[nom]}{derniere}")

    largeurs = {"texte": 60, "ecarts_vs_equipe": 45, "a_trancher": 40, "commentaire": 40, "preferences": 22,
                "autres_villes": 24, "id": 8}
    for nom, col in lettre.items():
        feuille.column_dimensions[col].width = largeurs.get(nom, 13)
    feuille.freeze_panes = "F2"
    feuille.auto_filter.ref = f"A1:{lettre['commentaire']}{derniere}"

    aide = classeur.create_sheet("Lisez-moi")
    for texte in (
        f"Relecture du jeu NLU — relecteur : {relecteur} — {len(demandes)} demandes",
        "Règles d'annotation : services/ai/data/eval/README.md (à lire avant de commencer).",
        "1. Pour chaque ligne, vérifier chaque champ par rapport au texte.",
        "2. Corriger directement la cellule si besoin ; vide = inconnu (null).",
        "3. Colonne statut : « valide » si tout est juste, « corrige » si une cellule a été modifiée.",
        "4. Commentaire : expliquer toute correction ou tout doute.",
        "Lignes orange : annotation différente de celle de l'équipe (colonne ecarts_vs_equipe : équipe → jeu).",
        "Lignes jaunes : cas à trancher à la main (colonne a_trancher).",
        "Listes : séparer par des virgules (ex. « plage, culture »). Booléens : vrai / faux / vide. "
        "Dates : AAAA-MM-JJ. Devise : code ISO (TND, EUR…).",
        "Ne pas modifier les colonnes grises (id, source, jeu, date_reference, texte), ni l'ordre des colonnes.",
        "Champs recalculés à l'import, absents du fichier : budget_total_dt, champs_manquants.",
        "Import : cd services\\ai ; ..\\..\\.venv\\Scripts\\python scripts\\importer_relecture.py (simulation), "
        "puis avec --appliquer.",
    ):
        aide.append([texte])
    aide.column_dimensions["A"].width = 120
    classeur.save(chemin)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sortie", type=Path, default=DOSSIER_RELECTURE)
    parser.add_argument("--graine", type=int, default=GRAINE)
    parser.add_argument("--ecraser", action="store_true", help="remplacer des fichiers déjà présents")
    args = parser.parse_args()

    demandes = [d for lignes in j.charger_jeu().values() for d in lignes]
    parts = repartir(demandes, RELECTEURS, args.graine)
    args.sortie.mkdir(parents=True, exist_ok=True)
    for relecteur, lot in parts.items():
        chemin = args.sortie / f"relecture_{relecteur}.xlsx"
        if chemin.exists() and not args.ecraser:
            sys.exit(f"{chemin} existe déjà (relecture en cours ?) : relancer avec --ecraser pour le remplacer")
        ecrire_classeur(chemin, relecteur, lot)
        langues = {}
        for d in lot:
            langues[d["attendu"]["langue"]] = langues.get(d["attendu"]["langue"], 0) + 1
        print(f"{chemin.name}: {len(lot)} demandes "
              f"(humaines {sum(d['source'] == 'humain' for d in lot)}, générées {sum(d['source'] == 'genere' for d in lot)}, "
              f"écarts {sum(bool(j.ecarts_equipe(d)) for d in lot)}, à trancher {sum(bool(d.get('a_trancher')) for d in lot)}) "
              + " ".join(f"{k}={v}" for k, v in sorted(langues.items())))


if __name__ == "__main__":
    main()
