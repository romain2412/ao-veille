"""
Routes publiques d'invitation (création de compte par lien).

Pas de login requis, mais un token d'invitation valide est nécessaire.

GET  /invite/{token}  → infos de l'invitation (email/nom) si valide
POST /invite/{token}  → finalise le compte (choix du mot de passe)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import hash_password
from api.deps import get_db
from api.schemas import InvitationAccept, InvitationInfo
from storage.database import InvitationORM, UserORM
from timeutils import now_utc

router = APIRouter(prefix="/invite", tags=["invite"])

MIN_PASSWORD_LEN = 8


async def _get_valid_invitation(token: str, db: AsyncSession) -> InvitationORM:
    inv = (await db.execute(
        select(InvitationORM).where(InvitationORM.token == token)
    )).scalar_one_or_none()

    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Invitation introuvable.")
    if inv.used_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE,
                            detail="Cette invitation a déjà été utilisée.")
    if inv.expires_at < now_utc():
        raise HTTPException(status_code=status.HTTP_410_GONE,
                            detail="Cette invitation a expiré.")
    return inv


@router.get("/{token}", response_model=InvitationInfo)
async def get_invitation(token: str, db: AsyncSession = Depends(get_db)):
    """Renvoie les infos de l'invitation (pour pré-remplir le formulaire)."""
    inv = await _get_valid_invitation(token, db)
    return InvitationInfo(email=inv.email, full_name=inv.full_name)


@router.post("/{token}", status_code=status.HTTP_201_CREATED)
async def accept_invitation(
    token: str,
    body: InvitationAccept,
    db: AsyncSession = Depends(get_db),
):
    """Finalise la création du compte : l'utilisateur choisit son mot de passe."""
    inv = await _get_valid_invitation(token, db)

    if len(body.password) < MIN_PASSWORD_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LEN} caractères.",
        )

    # Sécurité : si un compte a été créé entre-temps avec cet email, on refuse
    existing = (await db.execute(
        select(UserORM).where(UserORM.email == inv.email)
    )).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe déjà avec cet email.",
        )

    user = UserORM(
        email=inv.email,
        full_name=inv.full_name,
        hashed_password=hash_password(body.password),
        is_active=True,
        is_admin=inv.is_admin,
    )
    db.add(user)
    inv.used_at = now_utc()
    await db.commit()

    return {"status": "created", "email": inv.email}
