"""Seed des codes promo de démonstration (idempotent).

Usage (depuis services/booking) : python scripts/seed_promos.py
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import PromoCode  # noqa: E402

PROMOS = [
    {"code": "BIENVENUE10", "reduction": 10.0, "days": 365},
    {"code": "ETE2026", "reduction": 15.0, "days": 60},
]


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for data in PROMOS:
            if db.query(PromoCode).filter(PromoCode.code == data["code"]).first():
                print(f"  = {data['code']} (existe déjà)")
                continue
            db.add(
                PromoCode(
                    code=data["code"],
                    reduction=data["reduction"],
                    date_expiration=date.today() + timedelta(days=data["days"]),
                    actif=True,
                )
            )
            print(f"  + {data['code']} (-{data['reduction']:.0f} %)")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
