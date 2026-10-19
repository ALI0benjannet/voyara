"""Collecte des points d'intérêt OpenStreetMap pour le moteur IA (idempotent).

Une requête Overpass par ville (centre + rayon, voir app/villes.py). Les tags OSM
sont convertis en 7 types Voyara (app/osm.py) puis enregistrés dans `voyara_ai.pois`
par upsert sur `source_id` : relancer le script met à jour, sans doublon.

Usage (depuis services/ai, conteneur `postgres-ai` démarré) :
    python scripts/collecter_pois.py                         # les 8 villes
    python scripts/collecter_pois.py --ville Djerba --ville Tozeur
    python scripts/collecter_pois.py --max-par-type 80 --dry-run

Code de sortie 1 si au moins une ville a échoué (les autres sont enregistrées).
"""

import argparse
import logging
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.collecte import OverpassIndisponible, collecter_ville, enregistrer, nouveau_client  # noqa: E402
from app.villes import VILLES, trouver_ville  # noqa: E402

PAUSE_ENTRE_VILLES_S = 5


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collecte des POI OpenStreetMap (Overpass).")
    parser.add_argument("--ville", action="append", help="ville à collecter (répétable) ; défaut : toutes")
    parser.add_argument("--max-par-type", type=int, default=60, help="plafond par (ville, type), défaut 60")
    parser.add_argument("--dry-run", action="store_true", help="interroge Overpass sans écrire en base")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # une ligne par requête : trop bavard

    try:
        villes = [trouver_ville(v) for v in args.ville] if args.ville else list(VILLES)
    except ValueError as exc:
        print(exc)
        return 2

    from app.config import settings
    from app.database import Base, SessionLocal, engine

    if not args.dry_run:
        Base.metadata.create_all(bind=engine)

    bilan: dict[str, Counter[str]] = {}
    echecs: list[str] = []
    with nouveau_client() as client, SessionLocal() as db:
        for i, ville in enumerate(villes):
            if i:
                time.sleep(PAUSE_ENTRE_VILLES_S)  # politesse envers le serveur public Overpass
            print(f"→ {ville.nom} (rayon {ville.rayon_m / 1000:g} km)...", flush=True)
            try:
                pois = collecter_ville(client, settings.OVERPASS_URL, ville, args.max_par_type)
            except OverpassIndisponible as exc:
                print(f"  ✗ {ville.nom} : {exc}")
                echecs.append(ville.nom)
                continue
            bilan[ville.nom] = Counter(p["type"] for p in pois)
            if args.dry_run:
                print(f"  {len(pois)} POI (dry-run, rien d'écrit)")
            else:
                inseres, mis_a_jour = enregistrer(db, pois)
                print(f"  {len(pois)} POI : {inseres} insérés, {mis_a_jour} mis à jour")

    types = sorted({t for c in bilan.values() for t in c})
    print("\nBilan de cette collecte (POI par ville et par type) :")
    print(f"{'ville':<15}" + "".join(f"{t:>11}" for t in types) + f"{'total':>8}")
    for nom, compte in bilan.items():
        print(f"{nom:<15}" + "".join(f"{compte[t]:>11}" for t in types) + f"{sum(compte.values()):>8}")
    print(f"{'total':<15}" + "".join(f"{sum(c[t] for c in bilan.values()):>11}" for t in types)
          + f"{sum(sum(c.values()) for c in bilan.values()):>8}")

    if not args.dry_run:
        from sqlalchemy import func

        from app.models import Poi

        with SessionLocal() as db:
            total = db.query(func.count(Poi.id)).scalar()
            nb_villes = db.query(func.count(func.distinct(Poi.ville))).scalar()
        print(f"\nBase voyara_ai : {total} POI sur {nb_villes} villes.")

    if echecs:
        print(f"Villes en échec : {', '.join(echecs)} — relancer avec --ville.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
