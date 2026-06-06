"""
Routes d'authentification.

POST /auth/login   → retourne un JWT
GET  /auth/me      → retourne l'utilisateur courant
"""
# NB : pas de `from __future__ import annotations` ici — il transforme les
# annotations en chaînes différées, ce qui casse la résolution du type du
# paramètre `body` quand on empile les décorateurs FastAPI + slowapi.

import logging
import os
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import create_access_token, hash_password, verify_password
from api.deps import get_current_user, get_db
from api.rate_limit import limiter
from api.schemas import (
    LoginRequest, PasswordResetConfirm, PasswordResetInfo,
    PasswordResetRequest, TokenResponse, UserResponse,
)
from storage.database import PasswordResetORM, UserORM
from timeutils import now_utc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Durée de validité d'un lien de réinitialisation (minutes)
PASSWORD_RESET_TTL_MINUTES = 60
MIN_PASSWORD_LEN = 8

# Message générique renvoyé à toute demande de réinitialisation : volontairement
# identique que l'email existe ou non, pour ne pas révéler les comptes enregistrés.
_RESET_GENERIC_MESSAGE = (
    "Si un compte est associé à cette adresse, un email contenant un lien de "
    "réinitialisation vient d'être envoyé."
)


def _reset_link(token: str) -> str:
    """Construit le lien public de réinitialisation à partir de APP_BASE_URL."""
    base = os.getenv("APP_BASE_URL", "").rstrip("/")
    return f"{base}/reset-password/{token}" if base else f"/reset-password/{token}"


async def _get_valid_reset(token: str, db: AsyncSession) -> PasswordResetORM:
    """Renvoie une demande de réinit valide (non utilisée, non expirée)."""
    pr = (await db.execute(
        select(PasswordResetORM).where(PasswordResetORM.token == token)
    )).scalar_one_or_none()

    if pr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Lien de réinitialisation introuvable.")
    if pr.used_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE,
                            detail="Ce lien a déjà été utilisé.")
    if pr.expires_at < now_utc():
        raise HTTPException(status_code=status.HTTP_410_GONE,
                            detail="Ce lien a expiré.")
    return pr


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserORM).where(UserORM.email == body.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: UserORM = Depends(get_current_user)):
    return current_user


# ---------------------------------------------------------------------------
# Mot de passe oublié — réinitialisation par lien email (routes publiques)
# ---------------------------------------------------------------------------

@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    body: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """Demande un lien de réinitialisation.

    Renvoie TOUJOURS le même message générique : on ne crée une demande et on
    n'envoie un email que si l'adresse correspond à un compte ACTIF, mais la
    réponse ne permet pas de distinguer les deux cas (anti-énumération d'emails).
    """
    email = body.email.lower().strip()

    user = (await db.execute(
        select(UserORM).where(UserORM.email == email)
    )).scalar_one_or_none()

    # Compte inexistant ou désactivé : on ne fait rien, réponse identique.
    if user is None or not user.is_active:
        return {"status": "ok", "message": _RESET_GENERIC_MESSAGE}

    # Invalide les éventuelles demandes encore en attente pour ce compte
    # (un seul lien actif à la fois).
    previous = (await db.execute(
        select(PasswordResetORM).where(
            PasswordResetORM.user_id == user.id,
            PasswordResetORM.used_at.is_(None),
        )
    )).scalars().all()
    for old in previous:
        old.used_at = now_utc()

    token = secrets.token_urlsafe(32)
    pr = PasswordResetORM(
        token=token,
        user_id=user.id,
        expires_at=now_utc() + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES),
    )
    db.add(pr)
    await db.commit()

    link = _reset_link(token)

    # Envoi par mail (no-op si SMTP non configuré) — n'échoue jamais l'appelant.
    try:
        from notifier.mailer import send_email
        subject = "Réinitialisation de votre mot de passe — Veille AO FB VRD"
        text = (
            f"Bonjour,\n\nVous avez demandé la réinitialisation de votre mot de "
            f"passe sur le portail Veille AO FB VRD.\n\n"
            f"Cliquez sur ce lien pour choisir un nouveau mot de passe :\n{link}\n\n"
            f"Ce lien est valable {PASSWORD_RESET_TTL_MINUTES} minutes.\n\n"
            f"Si vous n'êtes pas à l'origine de cette demande, ignorez cet email : "
            f"votre mot de passe reste inchangé.\n"
        )
        html = (
            f"<p>Bonjour,</p><p>Vous avez demandé la réinitialisation de votre "
            f"mot de passe sur le portail Veille AO FB VRD.</p>"
            f"<p><a href=\"{link}\">Cliquez ici pour choisir un nouveau mot de passe</a></p>"
            f"<p>Ce lien est valable {PASSWORD_RESET_TTL_MINUTES} minutes.</p>"
            f"<p>Si vous n'êtes pas à l'origine de cette demande, ignorez cet "
            f"email : votre mot de passe reste inchangé.</p>"
        )
        send_email(user.email, subject, text, html)
    except Exception:
        logger.exception("[auth] Erreur lors de l'envoi du mail de réinitialisation")

    return {"status": "ok", "message": _RESET_GENERIC_MESSAGE}


@router.get("/reset-password/{token}", response_model=PasswordResetInfo)
async def get_reset_info(token: str, db: AsyncSession = Depends(get_db)):
    """Valide le token et renvoie l'email associé (pour affichage du formulaire)."""
    pr = await _get_valid_reset(token, db)
    user = (await db.execute(
        select(UserORM).where(UserORM.id == pr.user_id)
    )).scalar_one_or_none()
    if user is None or not user.is_active:
        # Compte supprimé ou désactivé entre-temps → lien invalide.
        raise HTTPException(status_code=status.HTTP_410_GONE,
                            detail="Ce lien n'est plus valide.")
    return PasswordResetInfo(email=user.email)


@router.post("/reset-password/{token}")
async def confirm_reset(
    token: str,
    body: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Finalise la réinitialisation : enregistre le nouveau mot de passe."""
    if len(body.password) < MIN_PASSWORD_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LEN} caractères.",
        )

    pr = await _get_valid_reset(token, db)
    user = (await db.execute(
        select(UserORM).where(UserORM.id == pr.user_id)
    )).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_410_GONE,
                            detail="Ce lien n'est plus valide.")

    user.hashed_password = hash_password(body.password)
    pr.used_at = now_utc()
    await db.commit()

    return {"status": "reset", "email": user.email}
