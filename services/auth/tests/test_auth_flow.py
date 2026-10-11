import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete

from app.models.email_verification_tokens import EmailVerificationToken
from app.models.password_reset_tokens import PasswordResetToken
from app.models.users import User


def expire_token(db, token_row):
    token_row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()


def test_full_auth_flow(client, capture_email_tokens):
    # 1. Inscription
    r = client.post("/api/v1/auth/register", json={
        "email": "ali@test.com",
        "password": "Passw0rd!",
        "nom": "Ali",
        "prenom": "Test",
    })
    assert r.status_code == 201

    # 2. Login refusé tant que non vérifié
    r = client.post("/api/v1/auth/login", json={"email": "ali@test.com", "password": "Passw0rd!"})
    assert r.status_code == 403

    # 3. Vérification (on récupère le token depuis le mock email)
    assert capture_email_tokens["verify"] is not None
    r = client.post("/api/v1/auth/verify-email", json={"token": capture_email_tokens["verify"]})
    assert r.status_code == 200

    # 4. Login OK
    r = client.post("/api/v1/auth/login", json={"email": "ali@test.com", "password": "Passw0rd!"})
    assert r.status_code == 200
    tokens = r.json()
    assert "access_token" in tokens and "refresh_token" in tokens

    # 5. Forgot + reset
    r = client.post("/api/v1/auth/forgot-password", json={"email": "ali@test.com"})
    assert r.status_code == 200
    assert capture_email_tokens["reset"] is not None
    r = client.post(
        "/api/v1/auth/reset-password",
        json={"token": capture_email_tokens["reset"], "new_password": "NewPassw0rd!"},
    )
    assert r.status_code == 200

    # 6. L'ancien mot de passe ne marche plus
    r = client.post("/api/v1/auth/login", json={"email": "ali@test.com", "password": "Passw0rd!"})
    assert r.status_code == 401


def test_verification_token_cannot_be_reused(client, capture_email_tokens):
    r = client.post("/api/v1/auth/register", json={
        "email": "reuse@test.com",
        "password": "Passw0rd!",
        "nom": "Reuse",
        "prenom": "Test",
    })
    assert r.status_code == 201
    assert capture_email_tokens["verify"] is not None

    r = client.post("/api/v1/auth/verify-email", json={"token": capture_email_tokens["verify"]})
    assert r.status_code == 200

    r = client.post("/api/v1/auth/verify-email", json={"token": capture_email_tokens["verify"]})
    assert r.status_code == 400


def test_reset_token_expired_and_cannot_be_reused(client, test_db_session, capture_email_tokens):
    r = client.post("/api/v1/auth/register", json={
        "email": "expire@test.com",
        "password": "Passw0rd!",
        "nom": "Expire",
        "prenom": "Test",
    })
    assert r.status_code == 201
    assert capture_email_tokens["verify"] is not None

    r = client.post("/api/v1/auth/verify-email", json={"token": capture_email_tokens["verify"]})
    assert r.status_code == 200

    r = client.post("/api/v1/auth/forgot-password", json={"email": "expire@test.com"})
    assert r.status_code == 200
    assert capture_email_tokens["reset"] is not None

    reset_row = test_db_session.query(PasswordResetToken).order_by(PasswordResetToken.token_hash.desc()).first()
    assert reset_row is not None
    expire_token(test_db_session, reset_row)

    r = client.post(
        "/api/v1/auth/reset-password",
        json={"token": capture_email_tokens["reset"], "new_password": "NewPassw0rd!"},
    )
    assert r.status_code == 400

    # Reset token reuse after successful reset should also fail
    reset_row.expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    reset_row.used_at = None
    test_db_session.commit()

    r = client.post(
        "/api/v1/auth/reset-password",
        json={"token": capture_email_tokens["reset"], "new_password": "NewPassw0rd!"},
    )
    assert r.status_code == 200

    r = client.post(
        "/api/v1/auth/reset-password",
        json={"token": capture_email_tokens["reset"], "new_password": "AnotherNewPass1!"},
    )
    assert r.status_code == 400


def test_forgot_password_nonexistent_email_returns_200(client):
    r = client.post("/api/v1/auth/forgot-password", json={"email": "doesnotexist@test.com"})
    assert r.status_code == 200


def test_password_too_weak_returns_422(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "weak@test.com",
        "password": "weak",
        "nom": "Weak",
        "prenom": "Test",
    })
    assert r.status_code == 422

