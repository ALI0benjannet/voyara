import logging
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from voyara_common.limiter import limiter
from voyara_common.security import create_access_token, hash_token, is_valid

from app.clients import notification
from app.database import get_db
from app.deps import get_current_active_user
from app.models.password_reset_tokens import PasswordResetToken
from app.models.users import User
from app.schemas.token import (
    ChangePasswordIn,
    EmailIn,
    LoginRequest,
    RefreshRequest,
    ResendVerificationRequest,
    ResetPasswordIn,
    Token,
    TokenIn,
)
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["Authentification"])

logger = logging.getLogger(__name__)

# services/auth/static/avatars
AVATAR_UPLOAD_DIR = Path(__file__).resolve().parents[2] / "static" / "avatars"


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(
    request: Request,
    payload: UserCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if user_service.get_by_email(db, payload.email):
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet e-mail")

    user, raw = auth_service.register_user(
        db, payload.email, payload.nom, payload.prenom, payload.password
    )
    nom = f"{payload.prenom} {payload.nom}"
    background.add_task(notification.send_verification_email, user.email, nom, raw)
    return {"message": "Compte créé. Vérifiez votre boîte mail pour l'activer."}


def _issue_tokens(user: User, refresh_token: str) -> Token:
    return Token(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=refresh_token,
    )


def _check_login_allowed(user: User | None) -> User:
    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "invalid_credentials",
                "message": "E-mail ou mot de passe incorrect",
            },
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "email_not_verified",
                "message": "Confirmez votre e-mail avant de vous connecter",
            },
        )
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "account_disabled",
                "message": "Compte désactivé",
            },
        )
    return user


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    user = _check_login_allowed(user_service.authenticate(db, payload.email, payload.password))
    raw_refresh = auth_service.create_refresh_token(db, user, request.headers.get("user-agent"))
    return _issue_tokens(user, raw_refresh)


# Permet le bouton "Authorize" de Swagger
@router.post("/login/form", response_model=Token, include_in_schema=False)
@limiter.limit("5/minute")
def login_form(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = _check_login_allowed(user_service.authenticate(db, form.username, form.password))
    raw_refresh = auth_service.create_refresh_token(db, user, request.headers.get("user-agent"))
    return _issue_tokens(user, raw_refresh)


@router.post("/refresh", response_model=Token)
@limiter.limit("10/minute")
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    try:
        user, new_raw = auth_service.rotate_refresh_token(
            db, payload.refresh_token, request.headers.get("user-agent")
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Session expirée, reconnectez-vous")
    return _issue_tokens(user, new_raw)


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    payload: EmailIn,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = user_service.get_by_email(db, payload.email.lower())

    if user and user.is_active:
        raw = auth_service.create_password_reset_token(db, user)
        nom = f"{user.prenom} {user.nom}"
        background.add_task(notification.send_reset_password_email, user.email, nom, raw)

    return {"message": "Si un compte existe avec cet e-mail, un lien vient d'être envoyé."}


@router.get("/validate-reset-token")
@limiter.limit("10/minute")
def validate_reset_token(request: Request, token: str, db: Session = Depends(get_db)):
    row = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token))
    )

    if not is_valid(row):
        raise HTTPException(status_code=400, detail="Lien invalide ou expiré")

    return {"message": "Token valide"}


@router.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, payload: ResetPasswordIn, db: Session = Depends(get_db)):
    try:
        auth_service.reset_password(db, payload.token, payload.new_password)
    except ValueError:
        raise HTTPException(status_code=400, detail="Lien invalide ou expiré")
    return {"message": "Mot de passe réinitialisé. Vous pouvez vous connecter."}


@router.post("/change-password")
@limiter.limit("10/minute")
def change_password(
    request: Request,
    payload: ChangePasswordIn,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        auth_service.change_password(
            db, current_user, payload.old_password, payload.new_password, payload.refresh_token
        )
    except ValueError as exc:
        if str(exc) == "old_password_incorrect":
            raise HTTPException(status_code=400, detail="Ancien mot de passe incorrect")
        if str(exc) == "new_same_as_old":
            raise HTTPException(
                status_code=400,
                detail="Le nouveau mot de passe doit être différent de l'ancien",
            )
        raise
    return {"message": "Mot de passe changé avec succès."}


@router.post("/logout")
@limiter.limit("10/minute")
def logout(request: Request, payload: TokenIn, db: Session = Depends(get_db)):
    auth_service.revoke_refresh_token(db, payload.token)
    return {"message": "Déconnecté"}


@router.post("/resend-verification")
@limiter.limit("5/minute")
def resend_verification(
    request: Request,
    payload: ResendVerificationRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = user_service.get_by_email(db, payload.email)
    if user:
        raw = auth_service.resend_verification(db, user)
        nom = f"{user.prenom} {user.nom}"
        background.add_task(notification.send_verification_email, user.email, nom, raw)

    return {"message": "Si cet e-mail existe, un nouveau lien de vérification a été envoyé."}


@router.post("/verify-email")
@limiter.limit("5/minute")
def verify_email(request: Request, payload: TokenIn, db: Session = Depends(get_db)):
    try:
        auth_service.verify_email(db, None, payload.token)
    except ValueError:
        raise HTTPException(status_code=400, detail="Code invalide ou expiré")
    return {"message": "Compte activé avec succès"}


@router.post("/me/avatar", response_model=dict)
async def upload_avatar(
    request: Request,
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not avatar.content_type or not avatar.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Le fichier doit être une image")

    AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    extension = Path(avatar.filename).suffix.lower() or ".png"
    if extension not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise HTTPException(status_code=415, detail="Format d'image non supporté")

    filename = f"{current_user.id}-{uuid4().hex}{extension}"
    avatar_path = AVATAR_UPLOAD_DIR / filename
    avatar_path.write_bytes(await avatar.read())

    if current_user.avatar_url:
        parsed = urlparse(current_user.avatar_url)
        if parsed.path.startswith("/static/avatars/"):
            old_file = AVATAR_UPLOAD_DIR / parsed.path.split("/static/avatars/", 1)[1]
            if old_file.exists():
                old_file.unlink()

    current_user.avatar_url = str(request.url_for("static", path=f"avatars/{filename}"))
    db.commit()
    db.refresh(current_user)
    return {"avatar_url": current_user.avatar_url}


@router.delete("/me/avatar", status_code=status.HTTP_204_NO_CONTENT)
def delete_avatar(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.avatar_url:
        parsed = urlparse(current_user.avatar_url)
        if parsed.path.startswith("/static/avatars/"):
            file_path = AVATAR_UPLOAD_DIR / parsed.path.split("/static/avatars/", 1)[1]
            if file_path.exists():
                file_path.unlink()

    current_user.avatar_url = None
    db.commit()


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/minute")
def delete_me(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Suppression de compte (RGPD) : anonymisation + révocation des sessions.

    On anonymise plutôt que supprimer physiquement : les réservations des autres
    services référencent user_id (ADR-002) et doivent rester cohérentes.
    """
    from app.models.email_verification_tokens import EmailVerificationToken
    from app.models.refresh_tokens import RefreshToken
    from voyara_common.security import generate_raw_token, hash_password as hash_pw

    # Avatar : suppression du fichier
    if current_user.avatar_url:
        parsed = urlparse(current_user.avatar_url)
        if parsed.path.startswith("/static/avatars/"):
            file_path = AVATAR_UPLOAD_DIR / parsed.path.split("/static/avatars/", 1)[1]
            if file_path.exists():
                file_path.unlink()

    # Révocation de toutes les sessions + purge des tokens e-mail
    db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).update(
        {"revoked": True}, synchronize_session=False
    )
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == current_user.id
    ).delete(synchronize_session=False)
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == current_user.id
    ).delete(synchronize_session=False)

    # Anonymisation du compte
    current_user.email = f"deleted-{current_user.id}@anonymise.voyara.local"
    current_user.nom = "Supprimé"
    current_user.prenom = "Compte"
    current_user.hashed_password = hash_pw(generate_raw_token())
    current_user.phone = None
    current_user.preferences = None
    current_user.avatar_url = None
    current_user.is_active = False
    current_user.is_verified = False
    db.commit()
    logger.info("Compte %s anonymisé (RGPD)", current_user.id)


@router.patch("/me", response_model=UserRead)
@limiter.limit("10/minute")
def update_me(
    request: Request,
    payload: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    if updates:
        for key, value in updates.items():
            setattr(current_user, key, value)
        db.commit()
        db.refresh(current_user)
    return current_user
