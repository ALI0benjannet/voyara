"""Crée le compte administrateur initial (idempotent).

Usage (depuis services/auth) : python scripts/seed_admin.py
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voyara_common.security import hash_password  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.users import User  # noqa: E402


def run() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == settings.FIRST_ADMIN_EMAIL).first():
            print("Admin déjà présent")
            return

        db.add(
            User(
                email=settings.FIRST_ADMIN_EMAIL,
                hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
                nom="Administrateur",
                prenom="Principal",
                role=UserRole.admin,
                is_verified=True,
                is_active=True,
                email_verified_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        print(f"Admin créé : {settings.FIRST_ADMIN_EMAIL}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
