"""Niveau 0 (baseline par règles) pour la classification des demandes.

Lance l'extracteur par règles de l'étape 4 (app/nlu, méthode « regles ») sur les
115 demandes du jeu test et calcule le F1 macro de type_voyage, vol et voiture,
au même format que docs/ia/resultats/dl_classif.csv (mêmes labels, même fusion
« groupe » → « amis »), pour compléter la progression Règles → ML → DL.

Usage (depuis services/ai) :
    ..\\..\\.venv\\Scripts\\python scripts\\baseline_regles_classif.py
"""
import asyncio
import csv
import json
import sys
from datetime import date
from pathlib import Path

from sklearn.metrics import f1_score

RACINE_AI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE_AI))
from app.nlu.extraction import comprendre  # noqa: E402

EVAL = RACINE_AI / "data" / "eval" / "nlu_demandes.jsonl"
SORTIE = RACINE_AI.parents[1] / "docs" / "ia" / "resultats" / "dl_classif_regles.csv"
CHAMPS = ["type_voyage", "vol", "voiture"]
LANGUES = ["fr", "en", "ar", "darija"]


def label(attendu: dict, champ: str) -> str:
    if champ == "type_voyage":
        t = attendu.get("type_voyage")
        return "amis" if t == "groupe" else (t or "non_precise")
    return (attendu.get("besoins_transport") or {}).get(champ) or "indifferent"


async def predire(demandes: list[dict]) -> list[dict]:
    sorties = []
    for d in demandes:
        res = await comprendre(d["texte"], date.fromisoformat(d["date_reference"]), methode="regles")
        sorties.append(res.demande.vers_attendu())
    return sorties


def main() -> None:
    lignes = [json.loads(l) for l in EVAL.read_text(encoding="utf-8").splitlines() if l.strip()]
    test = [r for r in lignes if r["jeu"] == "test"]
    preds = asyncio.run(predire(test))
    resultats = []
    for champ in CHAMPS:
        y = [label(r["attendu"], champ) for r in test]
        yp = [label(p, champ) for p in preds]
        ligne = {"approche": "Baseline : règles (étape 4)", "champ": champ,
                 "F1_macro": round(f1_score(y, yp, average="macro"), 3)}
        for lg in LANGUES:
            idx = [i for i, r in enumerate(test) if r["attendu"]["langue"] == lg]
            ligne[f"F1_{lg}"] = round(f1_score([y[i] for i in idx], [yp[i] for i in idx], average="macro"), 3)
        resultats.append(ligne)
        print(ligne)
    with SORTIE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(resultats[0]))
        w.writeheader(); w.writerows(resultats)
    print("Écrit :", SORTIE)


if __name__ == "__main__":
    main()
