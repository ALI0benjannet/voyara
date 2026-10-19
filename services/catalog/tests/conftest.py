import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from voyara_common.auth import require_admin
from voyara_common.internal import internal_headers

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import Activity, Category

# Les scripts (pre_etiqueter, importer_propositions) sont importables par les tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

# ============================================================================
# BASE DE TEST — `voyara_catalog` réelle (conteneur postgres :5434), isolation
# par transaction : chaque test s'exécute dans une transaction annulée à la
# fin. Prérequis : migration scripts/add_tags_ia_columns.py appliquée.
# ============================================================================


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(settings.DATABASE_URL, echo=False, future=True)
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


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(client):
    """Client dont le JWT admin est simulé (la vérification du jeton est
    couverte par les tests d'auth ; ici on teste les règles métier)."""
    app.dependency_overrides[require_admin] = lambda: None
    return client


@pytest.fixture
def cle_interne() -> dict[str, str]:
    return internal_headers()


@pytest.fixture
def activite(db) -> Activity:
    """Activité jetable (annulée avec la transaction du test)."""
    categorie = Category(nom="Catégorie de test IA")
    db.add(categorie)
    db.flush()
    activite = Activity(
        titre="Croisière de test au couchant",
        description="Voilier, baignade dans une crique et coucher de soleil sur la lagune.",
        prix=80, duree=180, localisation="Djerba", latitude=33.8, longitude=10.9,
        category_id=categorie.id,
    )
    db.add(activite)
    db.commit()
    return activite
