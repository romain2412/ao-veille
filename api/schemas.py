"""
Schémas Pydantic pour les réponses et requêtes de l'API.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_admin: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Appels d'offres
# ---------------------------------------------------------------------------

SOURCE_LABELS = {
    "boamp": "BOAMP",
    "demat_ampa": "AMPA",
}

class TenderResponse(BaseModel):
    id: int
    uid: str
    source: str
    sources: list[str]
    source_urls: dict[str, str]
    url: Optional[str]

    title: str
    buyer_name: Optional[str]
    buyer_city: Optional[str]
    description: Optional[str]
    cpv_codes: list[str]

    market_type: Optional[str]
    notice_nature: Optional[str]

    departments: list[str]
    execution_location: Optional[str]

    publication_date: Optional[datetime]
    deadline: Optional[datetime]
    collected_at: datetime

    score: int
    matched_keywords: list[str]
    is_priority_region: bool
    is_relevant: bool
    is_new: bool

    model_config = {"from_attributes": True}


class TenderListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TenderResponse]
