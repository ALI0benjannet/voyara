from sqlalchemy.orm import declarative_base

from voyara_common.database import create_session_factory

from app.config import settings

engine, SessionLocal = create_session_factory(settings.DATABASE_URL)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
