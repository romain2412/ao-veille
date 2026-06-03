"""
Routes d'administration / monitoring (réservées aux administrateurs).

GET /admin/monitoring → état du DERNIER run par source/collecteur :
  - status / error      : issue du dernier run
  - collected_count     : AO récupérés du site avant scoring
  - inserted_count      : AO ayant passé le score et insérés en base
  - started_at / finished_at / duration_seconds : horodatage et durée du run
"""
from __future__ import annotations

import logging
import os
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_admin_user, get_db
from api.schemas import InvitationCreate, InvitationResponse
from storage.database import (
    AppStateORM, CollectionRequestORM, CollectionRunORM, InvitationORM, UserORM,
)
from timeutils import as_utc, now_utc

logger = logging.getLogger(__name__)

# Durée de validité d'une invitation (jours)
INVITATION_TTL_DAYS = 7

router = APIRouter(prefix="/admin", tags=["admin"])


def _invitation_status(inv: InvitationORM) -> str:
    """Statut lisible d'une invitation : used / expired / pending."""
    if inv.used_at is not None:
        return "used"
    if inv.expires_at < now_utc():
        return "expired"
    return "pending"


def _invite_link(token: str) -> str:
    """Construit le lien public d'invitation à partir de APP_BASE_URL."""
    base = os.getenv("APP_BASE_URL", "").rstrip("/")
    return f"{base}/invite/{token}" if base else f"/invite/{token}"


@router.post("/collect/{source}", status_code=status.HTTP_202_ACCEPTED)
async def trigger_collection(
    source: str,
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(get_admin_user),
):
    """Demande une collecte manuelle d'une source.

    L'API n'exécute pas la collecte elle-même (elle n'a pas Playwright) : elle
    enregistre une demande (status=pending) que le collecteur traitera en
    arrière-plan. N'affecte pas le planning du scheduler ni next_collect_run.
    """
    from collector.registry import registry

    if source not in registry.all_names():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source inconnue : {source}",
        )

    # Évite d'empiler les demandes : réutilise celle en cours s'il y en a une
    existing = (await db.execute(
        select(CollectionRequestORM).where(
            CollectionRequestORM.source == source,
            CollectionRequestORM.status.in_(["pending", "processing"]),
        ).order_by(CollectionRequestORM.requested_at.desc()).limit(1)
    )).scalar_one_or_none()

    if existing is not None:
        return {"status": "requested", "source": source, "request_id": existing.id}

    req = CollectionRequestORM(source=source, status="pending")
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return {"status": "requested", "source": source, "request_id": req.id}


@router.post("/collect-all", status_code=status.HTTP_202_ACCEPTED)
async def trigger_collection_all(
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(get_admin_user),
):
    """Demande une collecte manuelle de TOUTES les sources enregistrées.

    Crée une demande par source (en réutilisant celle déjà en cours s'il y en a),
    que le collecteur traitera en arrière-plan. Renvoie la liste des request_id.
    """
    from collector.registry import registry

    results = []
    for source in sorted(registry.all_names()):
        existing = (await db.execute(
            select(CollectionRequestORM).where(
                CollectionRequestORM.source == source,
                CollectionRequestORM.status.in_(["pending", "processing"]),
            ).order_by(CollectionRequestORM.requested_at.desc()).limit(1)
        )).scalar_one_or_none()

        if existing is not None:
            results.append({"source": source, "request_id": existing.id})
            continue

        req = CollectionRequestORM(source=source, status="pending")
        db.add(req)
        await db.flush()
        results.append({"source": source, "request_id": req.id})

    await db.commit()
    return {"status": "requested", "requests": results}


@router.get("/collect-status/{request_id}")
async def collection_status(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(get_admin_user),
):
    """Statut d'une demande de collecte (pour le suivi côté admin)."""
    req = (await db.execute(
        select(CollectionRequestORM).where(CollectionRequestORM.id == request_id)
    )).scalar_one_or_none()
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable"
        )
    return {
        "id": req.id,
        "source": req.source,
        "status": req.status,   # pending | processing | done | error
        "requested_at": as_utc(req.requested_at),
        "processed_at": as_utc(req.processed_at),
    }


@router.get("/monitoring")
async def monitoring(
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(get_admin_user),
):
    from collector.registry import registry

    now = now_utc()
    sources = sorted(registry.all_names())
    result = []

    for src in sources:
        # Dernier run de cette source
        last_run = (await db.execute(
            select(CollectionRunORM)
            .where(CollectionRunORM.source == src)
            .order_by(CollectionRunORM.started_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        if last_run is None:
            result.append({"source": src, "last_run": None})
            continue

        # Durée du run en secondes (si terminé)
        duration = None
        if last_run.finished_at and last_run.started_at:
            duration = (last_run.finished_at - last_run.started_at).total_seconds()

        result.append({
            "source": src,
            "last_run": {
                "status": last_run.status,
                "error": last_run.error,
                "collected_count": last_run.collected_count,
                "score_validated_count": last_run.score_validated_count,
                "inserted_count": last_run.inserted_count,
                "updated_count": last_run.updated_count,
                # marquées UTC (suffixe de fuseau explicite dans le JSON)
                "started_at": as_utc(last_run.started_at),
                "finished_at": as_utc(last_run.finished_at),
                "duration_seconds": duration,
            },
        })

    # Date du prochain run planifié (écrite par le collecteur dans app_state)
    next_run_raw = (await db.execute(
        select(AppStateORM.value).where(AppStateORM.key == "next_collect_run")
    )).scalar_one_or_none()

    return {
        "sources": result,
        "generated_at": as_utc(now),
        "next_collect_run": next_run_raw,
    }


# ---------------------------------------------------------------------------
# Invitations (création de compte par lien) — réservé aux admins
# ---------------------------------------------------------------------------

@router.post("/invitations", status_code=status.HTTP_201_CREATED)
async def create_invitation(
    body: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(get_admin_user),
):
    """Crée une invitation et renvoie le lien. Tente aussi l'envoi par mail."""
    email = body.email.lower().strip()

    # Refuse si un compte existe déjà avec cet email
    existing_user = (await db.execute(
        select(UserORM).where(UserORM.email == email)
    )).scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe déjà avec cet email.",
        )

    token = secrets.token_urlsafe(32)
    inv = InvitationORM(
        token=token,
        email=email,
        full_name=body.full_name,
        is_admin=body.is_admin,
        expires_at=now_utc() + timedelta(days=INVITATION_TTL_DAYS),
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)

    link = _invite_link(token)

    # Envoi par mail (no-op si SMTP non configuré) — n'échoue jamais l'appelant
    email_sent = False
    try:
        from notifier.mailer import send_email
        role = "administrateur" if body.is_admin else "utilisateur"
        subject = "Invitation — Veille AO FB VRD"
        text = (
            f"Bonjour,\n\nVous êtes invité(e) à créer votre compte {role} "
            f"sur le portail Veille AO FB VRD.\n\n"
            f"Cliquez sur ce lien pour choisir votre mot de passe :\n{link}\n\n"
            f"Ce lien est valable {INVITATION_TTL_DAYS} jours.\n"
        )
        html = (
            f"<p>Bonjour,</p><p>Vous êtes invité(e) à créer votre compte "
            f"<b>{role}</b> sur le portail Veille AO FB VRD.</p>"
            f"<p><a href=\"{link}\">Cliquez ici pour choisir votre mot de passe</a></p>"
            f"<p>Ce lien est valable {INVITATION_TTL_DAYS} jours.</p>"
        )
        email_sent = send_email(email, subject, text, html)
    except Exception:
        logger.exception("[admin] Erreur lors de l'envoi du mail d'invitation")

    return {
        "id": inv.id,
        "email": inv.email,
        "is_admin": inv.is_admin,
        "link": link,
        "expires_at": as_utc(inv.expires_at),
        "email_sent": email_sent,
    }


@router.get("/invitations")
async def list_invitations(
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(get_admin_user),
):
    """Liste les invitations (les plus récentes d'abord)."""
    rows = (await db.execute(
        select(InvitationORM).order_by(InvitationORM.created_at.desc())
    )).scalars().all()

    return {
        "invitations": [
            {
                "id": inv.id,
                "email": inv.email,
                "full_name": inv.full_name,
                "is_admin": inv.is_admin,
                "status": _invitation_status(inv),
                "created_at": as_utc(inv.created_at),
                "expires_at": as_utc(inv.expires_at),
                "used_at": as_utc(inv.used_at),
                "link": _invite_link(inv.token),
            }
            for inv in rows
        ]
    }
