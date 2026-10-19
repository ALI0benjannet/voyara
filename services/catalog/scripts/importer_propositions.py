"""Importe un CSV de pré-étiquetage dans le catalogue — sans jamais valider.

Écrit les propositions de scripts/pre_etiqueter.py dans les colonnes IA
(`tags_valides` reste à faux) et en garde une copie dans `tags_proposes`
(source, modèle, date, raisons) pour mesurer plus tard les corrections humaines.
Règle de sûreté : une activité déjà validée par un humain n'est JAMAIS
modifiée. Chaque ligne est revalidée par app.tags_ia.TagsIA avant écriture.
Idempotent : relancer avec le même CSV ne change rien.

Usage (depuis services/catalog) :
    python scripts/importer_propositions.py                      # data/etiquetage/propositions_regles.csv
    python scripts/importer_propositions.py --csv data/etiquetage/propositions_ollama.csv
    python scripts/importer_propositions.py --simulation         # affiche sans écrire
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

RACINE_SERVICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE_SERVICE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pydantic import ValidationError  # noqa: E402

from app.tags_ia import TagsIA  # noqa: E402

CSV_DEFAUT = RACINE_SERVICE / "data" / "etiquetage" / "propositions_regles.csv"
CHAMPS = ("themes", "public", "niveau_marche", "interieur", "moment_ideal")


def lire_ligne(ligne: dict) -> TagsIA:
    """Ligne CSV → TagsIA validé (lève ValidationError / ValueError sinon)."""
    interieur = ligne["interieur"].strip().lower()
    if interieur not in {"oui", "non"}:
        raise ValueError(f"interieur invalide : {ligne['interieur']!r}")
    return TagsIA(
        themes=[v for v in ligne["themes"].split("|") if v],
        public=[v for v in ligne["public"].split("|") if v],
        niveau_marche=int(ligne["niveau_marche"]),
        interieur=interieur == "oui",
        moment_ideal=ligne["moment_ideal"].strip(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", type=Path, default=CSV_DEFAUT)
    parser.add_argument("--simulation", action="store_true", help="n'écrit rien, affiche le bilan")
    args = parser.parse_args()
    chemin = args.csv if args.csv.is_absolute() else RACINE_SERVICE / args.csv

    os.chdir(RACINE_SERVICE)  # .env du service (connexion à la base)
    from app.database import SessionLocal
    from app.models import Activity

    with chemin.open(encoding="utf-8-sig", newline="") as f:
        lignes = list(csv.DictReader(f))

    bilan = {"importees": 0, "inchangees": 0, "deja_validees": 0, "absentes": 0,
             "en_erreur_csv": 0, "invalides": 0}
    horodatage = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with SessionLocal() as db:
        for ligne in lignes:
            if ligne.get("statut") != "ok":
                bilan["en_erreur_csv"] += 1
                continue
            try:
                tags = lire_ligne(ligne)
            except (ValidationError, ValueError) as exc:
                bilan["invalides"] += 1
                print(f"  ligne ignorée (activité {ligne.get('activity_id')}) : {exc}".splitlines()[0])
                continue
            activite = db.get(Activity, int(ligne["activity_id"]))
            if activite is None:
                bilan["absentes"] += 1
                continue
            if activite.tags_valides:
                bilan["deja_validees"] += 1  # jamais écraser une validation humaine
                continue
            valeurs = tags.model_dump()
            proposition = {
                **valeurs,
                "source": ligne["fournisseur"],
                "modele": ligne["modele"],
                "confiance": ligne.get("confiance") or None,
                "raisons": ligne.get("raisons") or None,
                "fichier": chemin.name,
            }
            ancienne = dict(activite.tags_proposes or {})
            ancienne.pop("importe_le", None)
            deja = ancienne == proposition and all(
                getattr(activite, c) == valeurs[c] for c in CHAMPS
            )
            if deja:
                bilan["inchangees"] += 1
                continue
            for champ, valeur in valeurs.items():
                setattr(activite, champ, valeur)
            activite.tags_proposes = {**proposition, "importe_le": horodatage}
            bilan["importees"] += 1
        if args.simulation:
            db.rollback()
        else:
            db.commit()

    mode = "SIMULATION — rien n'a été écrit. " if args.simulation else ""
    print(
        f"{mode}{len(lignes)} ligne(s) lue(s) dans {chemin.name} : "
        f"{bilan['importees']} importée(s), {bilan['inchangees']} inchangée(s), "
        f"{bilan['deja_validees']} déjà validée(s) (non touchées), {bilan['absentes']} absente(s) de la base, "
        f"{bilan['en_erreur_csv']} en erreur dans le CSV, {bilan['invalides']} invalide(s)."
    )


if __name__ == "__main__":
    main()
