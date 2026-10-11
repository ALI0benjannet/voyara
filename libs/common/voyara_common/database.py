"""Fabrique SQLAlchemy partagée — chaque service possède SA base de données."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_session_factory(database_url: str, echo: bool = False):
    """Retourne (engine, SessionLocal) pour la base du service."""
    engine = create_engine(database_url, echo=echo, future=True, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, SessionLocal


def build_postgres_url(user: str, password: str, host: str, port: int, db: str) -> str:
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
