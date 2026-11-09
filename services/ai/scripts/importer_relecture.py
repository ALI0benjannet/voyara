"""Import des fichiers Excel de relecture (docs/ia/relecture/relecture_*.xlsx) dans les JSONL.

Pour chaque ligne relue (statut `valide` ou `corrige`) : applique les valeurs saisies, recalcule les
champs dérivés, valide la demande avec les règles de `data/eval/README.md`, puis enregistre le statut,
le relecteur et le commentaire. Une ligne invalide n'est **jamais** appliquée.

Signale :
- erreurs (bloquantes pour la ligne) : identifiant inconnu ou en double, valeur interdite ou mal
  formée, statut inconnu, colonne manquante ;
- avertissements : statut `valide` alors que des valeurs ont changé (passé en `corrige`), statut
  `corrige` sans aucune modification ;
- lignes non relues (statut vide) et demandes du jeu absentes de tous les fichiers.

    cd services\\ai
    ..\\..\\.venv\\Scripts\\python scripts\\importer_relecture.py              # simulation : rien n'est écrit
    ..\\..\\.venv\\Scripts\\python scripts\\importer_relecture.py --appliquer  # écrit les JSONL
"""

import argparse
import copy
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jeu_nlu as j  # noqa: E402
from generer_relecture import COLONNES_CHAMPS, DOSSIER_RELECTURE, FAUX, FEUILLE, VRAI  # noqa: E402


class ValeurInvalide(ValueError):
    pass


@dataclass
class Rapport:
    erreurs: list[str] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)
    non_relues: list[str] = field(default_factory=list)
    non_distribuees: list[str] = field(default_factory=list)
    appliquees: dict[str, int] = field(default_factory=lambda: {"valide": 0, "corrige": 0})


def depuis_cellule(valeur: Any, type_: str, nom: str) -> Any:
    """Valeur Excel → valeur JSON du jeu. Vide = None."""
    if isinstance(valeur, str):
        valeur = valeur.strip()
    if valeur is None or valeur == "":
        return [] if type_ == "liste" else None
    if type_ == "bool":
        if valeur is True or str(valeur).lower() in (VRAI, "true", "oui"):
            return True
        if valeur is False or str(valeur).lower() in (FAUX, "false", "non"):
            return False
        raise ValeurInvalide(f"{nom} = {valeur!r} : vrai, faux ou vide attendu")
    if type_ == "entier":
        try:
            nombre = float(str(valeur).replace(",", "."))
        except ValueError:
            raise ValeurInvalide(f"{nom} = {valeur!r} : nombre entier attendu") from None
        if not nombre.is_integer():
            raise ValeurInvalide(f"{nom} = {valeur!r} : nombre entier attendu")
        return int(nombre)
    if type_ == "nombre":
        try:
            nombre = float(str(valeur).replace(" ", "").replace(",", "."))
        except ValueError:
            raise ValeurInvalide(f"{nom} = {valeur!r} : nombre attendu") from None
        return int(nombre) if nombre.is_integer() else nombre
    if type_ == "liste":
        return [v.strip() for v in str(valeur).split(",") if v.strip()]
    texte = valeur.isoformat()[:10] if hasattr(valeur, "isoformat") else str(valeur)  # date saisie par Excel
    if nom == "budget_devise":
        texte = texte.upper()
    return texte


def ecrire_champ(attendu: dict, chemin: tuple[str, ...], valeur: Any) -> None:
    cible = attendu
    for cle in chemin[:-1]:
        cible = cible.setdefault(cle, {})
    cible[chemin[-1]] = valeur


def lire_classeur(chemin: Path) -> tuple[list[tuple[int, dict]], list[str]]:
    """[(numéro de rangée, {en-tête: valeur})], erreurs de structure."""
    feuille = load_workbook(chemin, data_only=True)[FEUILLE]
    rangees = feuille.iter_rows(values_only=True)
    en_tetes = [str(c).strip() if c is not None else "" for c in next(rangees)]
    attendues = {"id", "statut", "commentaire"} | {c[0] for c in COLONNES_CHAMPS}
    manquantes = sorted(attendues - set(en_tetes))
    if manquantes:
        return [], [f"{chemin.name} : colonnes manquantes {manquantes}"]
    lignes = []
    for numero, valeurs in enumerate(rangees, start=2):
        ligne = dict(zip(en_tetes, valeurs))
        if ligne.get("id") is None and all(v is None for v in valeurs):
            continue
        lignes.append((numero, ligne))
    return lignes, []


def importer(dossier_relecture: Path, dossier_eval: Path, appliquer: bool = False) -> Rapport:
    rapport = Rapport()
    jeu = j.charger_jeu(dossier_eval)
    index = {d["id"]: d for lignes in jeu.values() for d in lignes}
    vus: dict[str, str] = {}

    fichiers = sorted(dossier_relecture.glob("relecture_*.xlsx"))
    if not fichiers:
        rapport.erreurs.append(f"aucun fichier relecture_*.xlsx dans {dossier_relecture}")
        return rapport

    for fichier in fichiers:
        relecteur = fichier.stem.removeprefix("relecture_")
        lignes, erreurs = lire_classeur(fichier)
        rapport.erreurs += erreurs
        for numero, ligne in lignes:
            ou = f"{fichier.name} l.{numero}"
            ident = str(ligne.get("id") or "").strip()
            if ident not in index:
                rapport.erreurs.append(f"{ou} : identifiant inconnu {ident!r}")
                continue
            if ident in vus:
                rapport.erreurs.append(f"{ou} : {ident} déjà présent dans {vus[ident]}")
                continue
            vus[ident] = ou
            statut = str(ligne.get("statut") or "").strip().lower()
            if not statut:
                rapport.non_relues.append(f"{ident} ({relecteur})")
                continue
            if statut not in j.STATUTS_RELUS:
                rapport.erreurs.append(f"{ou} ({ident}) : statut {statut!r} interdit (valide | corrige)")
                continue

            demande = index[ident]
            nouveau = copy.deepcopy(demande["attendu"])
            erreurs_ligne = []
            for nom, chemin, type_ in COLONNES_CHAMPS:
                try:
                    ecrire_champ(nouveau, chemin, depuis_cellule(ligne.get(nom), type_, nom))
                except ValeurInvalide as exc:
                    erreurs_ligne.append(str(exc))
            if not erreurs_ligne:
                j.deriver(nouveau)
                candidat = {**demande, "attendu": nouveau, "statut": statut}
                erreurs_ligne = j.valider(candidat)
            if erreurs_ligne:
                rapport.erreurs += [f"{ou} ({ident}) : {e}" for e in erreurs_ligne]
                continue

            modifie = nouveau != demande["attendu"]
            if statut == "valide" and modifie:
                rapport.avertissements.append(f"{ou} ({ident}) : valeurs modifiées mais statut « valide » → « corrige »")
                statut = "corrige"
            elif statut == "corrige" and not modifie:
                rapport.avertissements.append(f"{ou} ({ident}) : statut « corrige » sans aucune modification")
            demande["attendu"] = nouveau
            demande["statut"] = statut
            demande["relu_par"] = relecteur
            commentaire = str(ligne.get("commentaire") or "").strip()
            if commentaire:
                demande["commentaire_relecture"] = commentaire
            demande.pop("a_trancher", None)  # tranché par le relecteur
            rapport.appliquees[statut] += 1

    rapport.non_distribuees = sorted(set(index) - set(vus))
    if appliquer:
        for nom, lignes in jeu.items():
            j.ecrire_jsonl(dossier_eval / nom, lignes)
    return rapport


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dossier", type=Path, default=DOSSIER_RELECTURE)
    parser.add_argument("--appliquer", action="store_true", help="écrire les JSONL (sinon : simulation)")
    args = parser.parse_args()

    rapport = importer(args.dossier, j.DOSSIER_EVAL, args.appliquer)
    for titre, elements in (("ERREURS (lignes non appliquées)", rapport.erreurs),
                            ("Avertissements", rapport.avertissements),
                            ("Non relues (statut vide)", rapport.non_relues),
                            ("Absentes de tous les fichiers", rapport.non_distribuees)):
        print(f"\n{titre} : {len(elements)}")
        for e in elements:
            print(f"  - {e}")
    print(f"\nAppliquées : valide {rapport.appliquees['valide']}, corrige {rapport.appliquees['corrige']}"
          + ("" if args.appliquer else "  (simulation : relancer avec --appliquer pour écrire)"))
    sys.exit(1 if rapport.erreurs else 0)


if __name__ == "__main__":
    main()
