import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base

# ============================================================================
# BASE DE TEST — `voyara_ai` réelle (conteneur postgres-ai), isolation par
# transaction : chaque test s'exécute dans une transaction annulée à la fin.
# Aucun appel réseau réel : Overpass et Open-Meteo sont simulés par
# httpx.MockTransport dans chaque test.
# ============================================================================


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(settings.DATABASE_URL, echo=False, future=True)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    # Les commit() du code testé deviennent des points de sauvegarde
    session = sessionmaker(bind=connection, expire_on_commit=False,
                           join_transaction_mode="create_savepoint")()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
