"""Export du catalogue d'activités pour la validation DL « recherche » (guide d'Ons, étape A).

Produit deux fichiers dans services/ai/data/dl/ :
- activites.json       : { clé : texte } — le texte indexé d'une activité
                         (titre + description + catégorie + thèmes + lieu) ;
- activites_meta.json  : [ { cle, id, titre_en, titre_ar, ville, categorie, themes, public } ]
                         pour écrire le jeu de test et analyser par ville.

La clé d'une activité est son **titre français** : il est unique (les seeds s'en
servent comme identifiant d'idempotence) et identique hors ligne et en base, alors
que l'id SQL dépend de l'ordre d'insertion. Le jeu de test et les paires
d'entraînement référencent donc les activités par titre, ce qui les rend aussi
lisibles pour la relecture.

Deux sources :
- `--source seed` (défaut, sans Docker) : les 8 activités de seed_catalog.py et les
  108 de seed_catalogue_demo.py ; thèmes et public calculés par les règles de
  pre_etiqueter.py (étape 2), comme les propositions importées en base ;
- `--source api` : route interne de catalog (services démarrés, INTERNAL_API_KEY dans
  l'environnement), activités publiées, thèmes réels (validés ou proposés).

Usage (depuis la racine) :
    .venv\\Scripts\\python services\\ai\\scripts\\dl_recherche_catalogue.py
    .venv\\Scripts\\python services\\ai\\scripts\\dl_recherche_catalogue.py --source api
"""

import argparse
import ast
import json
import os
import sys
from datetime import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RACINE = Path(__file__).resolve().parents[3]
CATALOG = RACINE / "services" / "catalog"
SORTIE = RACINE / "services" / "ai" / "data" / "dl"
URL_EXPORT = "http://127.0.0.1:8002/internal/activities/export"


def texte_activite(titre: str, description: str, categorie: str, themes: list[str], lieu: str) -> str:
    """Texte indexé : même format que le guide (étape A)."""
    return (f"{titre}. {description} Catégorie : {categorie}. "
            f"Thèmes : {', '.join(themes)}. Lieu : {lieu}")


def _seed_catalog_ancien() -> list[dict]:
    """ACTIVITIES de seed_catalog.py, lu sans l'importer (il ouvre la base à l'import)."""
    source = (CATALOG / "scripts" / "seed_catalog.py").read_text(encoding="utf-8")
    for noeud in ast.parse(source).body:
        if isinstance(noeud, ast.Assign) and getattr(noeud.targets[0], "id", "") == "ACTIVITIES":
            return ast.literal_eval(noeud.value)
    raise SystemExit("ACTIVITIES introuvable dans seed_catalog.py")


def depuis_seed() -> tuple[dict, list[dict]]:
    sys.path.insert(0, str(CATALOG / "scripts"))
    sys.path.insert(0, str(CATALOG))
    import pre_etiqueter as pe  # noqa: E402  (règles de l'étape 2, hors ligne)
    import seed_catalogue_demo as demo  # noqa: E402

    brutes = []
    for a in _seed_catalog_ancien():
        ville = a["localisation"].split(",")[0].strip()
        brutes.append({"titre": a["titre"], "description": a["description"], "categorie": a["categorie"],
                       "duree": a["duree"], "heures": [], "lieu": a["localisation"], "ville": ville,
                       "titre_en": None, "titre_ar": None})
    for a in demo.ACTIVITES:
        brutes.append({"titre": a["fr"][0], "description": a["fr"][1], "categorie": a["categorie"],
                       "duree": a["duree"], "heures": a["heures"], "lieu": a["localisation"],
                       "ville": a["ville"], "titre_en": a["en"][0], "titre_ar": a["ar"][0]})

    docs, meta = {}, []
    for a in brutes:
        if a["titre"] in docs:
            raise SystemExit(f"Titre en double : {a['titre']}")
        heures = [time.fromisoformat(h) for h in a["heures"]]
        prop = pe.proposer_regles(pe.ActiviteSource(id=0, titre=a["titre"], description=a["description"],
                                                    categorie=a["categorie"], duree=a["duree"], heures=heures))
        themes, public = list(prop.tags.themes), list(prop.tags.public)
        docs[a["titre"]] = texte_activite(a["titre"], a["description"], a["categorie"], themes, a["lieu"])
        meta.append({"cle": a["titre"], "id": None, "titre_en": a["titre_en"], "titre_ar": a["titre_ar"],
                     "ville": a["ville"], "categorie": a["categorie"], "themes": themes, "public": public})
    return docs, meta


def depuis_api() -> tuple[dict, list[dict]]:
    import httpx

    entetes = {"X-Internal-Api-Key": os.environ["INTERNAL_API_KEY"]}
    acts, page = [], 1
    while True:
        r = httpx.get(URL_EXPORT, headers=entetes, timeout=30,
                      params={"page": page, "size": 500, "statut": "publiee"})
        r.raise_for_status()
        corps = r.json()
        acts += corps["items"]
        if page >= corps["pages"]:
            break
        page += 1
    docs, meta = {}, []
    for a in acts:
        cat = (a.get("category") or {}).get("nom", "")
        themes = a.get("themes") or []
        docs[a["titre"]] = texte_activite(a["titre"], a["description"], cat, themes, a["localisation"])
        meta.append({"cle": a["titre"], "id": a["id"], "titre_en": a.get("titre_en"),
                     "titre_ar": a.get("titre_ar"), "ville": a["localisation"].split(",")[0].strip(),
                     "categorie": cat, "themes": themes, "public": a.get("public") or []})
    return docs, meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", choices=["seed", "api"], default="seed")
    args = parser.parse_args()

    docs, meta = depuis_seed() if args.source == "seed" else depuis_api()
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / "activites.json").write_text(json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")
    (SORTIE / "activites_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    villes: dict[str, int] = {}
    for m in meta:
        villes[m["ville"]] = villes.get(m["ville"], 0) + 1
    print(f"{len(docs)} activités (source : {args.source}) → {SORTIE}")
    print("Par ville :", ", ".join(f"{v} {n}" for v, n in sorted(villes.items(), key=lambda x: -x[1])))


if __name__ == "__main__":
    main()
