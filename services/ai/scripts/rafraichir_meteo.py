"""Remplit le cache météo (`voyara_ai.meteo_cache`) depuis Open-Meteo.

Usage (depuis services/ai, conteneur `postgres-ai` démarré) :
    python scripts/rafraichir_meteo.py                   # les 8 villes, 7 jours
    python scripts/rafraichir_meteo.py --ville Djerba --jours 3
"""

import argparse
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.villes import VILLES, trouver_ville  # noqa: E402


def _n(valeur: float | None) -> str:
    return "  n/d" if valeur is None else f"{valeur:>5.1f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rafraîchit le cache météo Open-Meteo.")
    parser.add_argument("--ville", action="append", help="ville (répétable) ; défaut : toutes")
    parser.add_argument("--jours", type=int, default=7, help="nombre de jours à partir d'aujourd'hui (1-16)")
    args = parser.parse_args(argv)

    try:
        villes = [trouver_ville(v) for v in args.ville] if args.ville else list(VILLES)
    except ValueError as exc:
        print(exc)
        return 2

    from app.database import Base, SessionLocal, engine
    from app.meteo import MeteoIndisponible, obtenir_meteo

    Base.metadata.create_all(bind=engine)
    echecs = 0
    with SessionLocal() as db:
        for ville in villes:
            try:
                jours = obtenir_meteo(db, ville.nom, date.today(), args.jours)
            except MeteoIndisponible as exc:
                print(f"✗ {exc}")
                echecs += 1
                continue
            print(f"{ville.nom}{' (cache périmé)' if jours and jours[0].perime else ''}")
            for j in jours:
                print(f"  {j.date}  {_n(j.temp_min)} / {_n(j.temp_max)} °C"
                      f"  pluie {_n(j.precipitations)} mm  code WMO {j.code_meteo}")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
