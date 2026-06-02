"""
Routes d'authentification.

POST /auth/login   → retourne un JWT
GET  /auth/me      → retourne l'utilisateur courant
"""
# NB : pas de `from __future__ import annotations` ici — il transforme les
# annotations en chaînes différées, ce qui casse la résolution du type du
# paramètre `body` quand on empile les décorateurs FastAPI + slowapi.

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import create_access_token, verify_password
from api.deps import get_current_user, get_db
from api.rate_limit import limiter
from api.schemas import LoginRequest, TokenResponse, UserResponse
from storage.database import UserORM

router = APIRouter(prefix="/auth", tags=["auth"])


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
