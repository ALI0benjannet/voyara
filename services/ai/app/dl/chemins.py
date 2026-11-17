"""Emplacements des données, résultats et modèles de la validation DL."""

from pathlib import Path

RACINE_AI = Path(__file__).resolve().parents[2]          # services/ai
RACINE_DEPOT = RACINE_AI.parents[1]                      # racine du dépôt

DOSSIER_DL = RACINE_AI / "data" / "dl"
ACTIVITES = DOSSIER_DL / "activites.json"
ACTIVITES_META = DOSSIER_DL / "activites_meta.json"
CLASSIF_TRAIN = DOSSIER_DL / "classif_train.jsonl"
REQUETES_TEST = RACINE_AI / "data" / "eval" / "recherche_requetes.jsonl"
DEMANDES_NLU = RACINE_AI / "data" / "eval" / "nlu_demandes.jsonl"

RESULTATS = RACINE_DEPOT / "docs" / "ia" / "resultats"

# Modèles (jamais versionnés) : téléchargés ou copiés depuis Kaggle / Drive.
MODELES = RACINE_DEPOT / "modeles"
E5_LOCAL = MODELES / "multilingual-e5-base"
# Copie bfloat16 (scripts/dl_convertir_e5_bf16.py) pour les postes à peu de mémoire.
E5_LOCAL_BF16 = MODELES / "multilingual-e5-base-bf16"
E5_HUB = "intfloat/multilingual-e5-base"
E5_FINE_TUNE = MODELES / "e5-voyara-ft"
XLMR_FINE_TUNE = {champ: MODELES / f"xlmr-voyara-{champ}" for champ in ("type_voyage", "vol", "voiture")}
