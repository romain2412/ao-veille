"""
Schémas Pydantic pour les réponses et requêtes de l'API.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, EmailStr, model_validator


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
    sources: Optional[list[str]] = None
    source_urls: Optional[dict[str, str]] = None
    url: Optional[str]

    title: str
    buyer_name: Optional[str]
    buyer_city: Optional[str]
    description: Optional[str]
    cpv_codes: Optional[list[str]] = None

    market_type: Optional[str]
    notice_nature: Optional[str]

    departments: Optional[list[str]] = None
    execution_location: Optional[str]

    publication_date: Optional[datetime]
    deadline: Optional[datetime]
    collected_at: datetime

    score: int
    matched_keywords: Optional[list[str]] = None
    is_priority_region: bool
    is_relevant: bool
    is_new: bool

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def fill_defaults(self) -> "TenderResponse":
        """Remplace les NULL par des valeurs par défaut."""
        if not self.sources:
            self.sources = [self.source] if self.source else []
        if self.source_urls is None:
            self.source_urls = {}
        if self.cpv_codes is None:
            self.cpv_codes = []
        if self.departments is None:
            self.departments = []
        if self.matched_keywords is None:
            self.matched_keywords = []
        return self


class TenderListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TenderResponse]
