import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app

# ============================================================================
# BASE DE TEST — isolation par transaction (rollback après chaque test)
# ============================================================================


@pytest.fixture(scope="session")
def test_engine():
    """Moteur connecté à la base réelle du service, avec isolation par
    transaction : chaque test s'exécute dans une transaction annulée à la fin.
    """
    engine = create_engine(settings.DATABASE_URL, echo=False, future=True)
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture
def test_db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(bind=connection, expire_on_commit=False)
    session = TestingSessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(test_db_session):
    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()


# ============================================================================
# MOCK DES NOTIFICATIONS — capture les tokens au lieu d'appeler le
# notification-service (l'envoi d'e-mail n'appartient plus à ce service)
# ============================================================================


@pytest.fixture
def capture_email_tokens(monkeypatch):
    from app.clients import notification

    tokens = {"verify": None, "reset": None}

    async def fake_send_verification_email(email: str, name: str, token: str) -> None:
        tokens["verify"] = token

    async def fake_send_reset_password_email(email: str, name: str, token: str) -> None:
        tokens["reset"] = token

    monkeypatch.setattr(notification, "send_verification_email", fake_send_verification_email)
    monkeypatch.setattr(notification, "send_reset_password_email", fake_send_reset_password_email)

    return tokens
