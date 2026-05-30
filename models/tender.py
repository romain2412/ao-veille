"""
Modèle de données central : un Appel d'Offres normalisé.
Toutes les sources (BOAMP, Marchés Online, etc.) doivent produire ce format.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MarketType(str, Enum):
    TRAVAUX = "TRAVAUX"
    SERVICES = "SERVICES"
    FOURNITURES = "FOURNITURES"
    OTHER = "OTHER"


class NoticeNature(str, Enum):
    APPEL_OFFRE = "APPEL_OFFRE"
    MARCHE_SIMPLIF = "MARCHE_SIMPLIF"
    MARCHE_NEGOC = "MARCHE_NEGOC"
    CONCESSION = "CONCESSION"
    OTHER = "OTHER"


class Tender(BaseModel):
    """Appel d'offres normalisé, indépendant de la source."""

    # --- Identification ---
    uid: str = Field(..., description="Identifiant unique : <source>_<id_source>")
    source: str = Field(..., description="Nom de la source (ex: boamp)")
    source_id: str = Field(..., description="Identifiant dans la source d'origine")
    url: Optional[str] = Field(None, description="Lien vers l'avis complet")

    # --- Contenu ---
    title: str = Field(..., description="Objet du marché")
    buyer_name: Optional[str] = Field(None, description="Nom du pouvoir adjudicateur")
    buyer_city: Optional[str] = Field(None, description="Ville du pouvoir adjudicateur")
    description: Optional[str] = Field(None, description="Description détaillée")
    cpv_codes: list[str] = Field(default_factory=list, description="Codes CPV")

    # --- Classement ---
    market_type: MarketType = Field(MarketType.OTHER)
    notice_nature: NoticeNature = Field(NoticeNature.OTHER)

    # --- Géographie ---
    departments: list[str] = Field(default_factory=list)
    execution_location: Optional[str] = Field(None)

    # --- Dates ---
    publication_date: Optional[datetime] = None
    deadline: Optional[datetime] = Field(None, description="Date limite de réponse")
    collected_at: datetime = Field(default_factory=datetime.utcnow)

    # --- Scoring ---
    score: int = Field(0)
    matched_keywords: list[str] = Field(default_factory=list)
    is_priority_region: bool = Field(False)

    # --- Workflow ---
    is_new: bool = Field(True)
    is_relevant: bool = Field(False)

    model_config = {"use_enum_values": True}
