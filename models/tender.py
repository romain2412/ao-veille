"""
Modèle de données central : un Appel d'Offres normalisé.
Toutes les sources (BOAMP, Marchés Online, etc.) doivent produire ce format.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

import hashlib
import unicodedata

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
    source: str = Field(..., description="Source principale (ex: boamp)")
    source_id: str = Field(..., description="Identifiant dans la source d'origine")
    sources: list[str] = Field(default_factory=list, description="Toutes les sources")
    source_urls: dict[str, str] = Field(default_factory=dict, description="URLs par source")
    fingerprint: Optional[str] = Field(None, description="Hash pour déduplication inter-sources")
    url: Optional[str] = Field(None, description="Lien vers l'avis (source principale)")

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

    def compute_fingerprint(self) -> str:
        """
        Calcule un hash de déduplication basé sur le contenu de l'AO.
        Deux AO du même marché provenant de sources différentes
        auront le même fingerprint.
        """
        def normalize(text: str) -> str:
            if not text:
                return ""
            text = text.lower().strip()
            text = unicodedata.normalize("NFD", text)
            text = "".join(c for c in text if unicodedata.category(c) != "Mn")
            # Supprimer la ponctuation et espaces multiples
            text = " ".join(text.split())
            return text

        # Titre tronqué (les 80 premiers caractères normalisés)
        title_norm = normalize(self.title)[:80]
        # Acheteur normalisé
        buyer_norm = normalize(self.buyer_name or "")[:50]
        # Date limite (juste la date, pas l'heure)
        deadline_str = self.deadline.strftime("%Y-%m-%d") if self.deadline else ""

        raw = f"{title_norm}|{buyer_norm}|{deadline_str}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
