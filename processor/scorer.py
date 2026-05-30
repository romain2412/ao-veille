"""
Moteur de scoring de pertinence.

Score basé sur :
  - présence de mots-clés métier dans titre / description (pondérés par groupe)
  - bonus géographique Nouvelle-Aquitaine
  - léger malus si type de marché hors périmètre

Configuration via settings.yml.
"""
from __future__ import annotations

import re
import unicodedata

from models.tender import Tender


def _normalize(text: str) -> str:
    """Minuscule + suppression des accents."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _build_pattern(term: str) -> re.Pattern:
    return re.compile(r"\b" + re.escape(_normalize(term)) + r"\b")


class TenderScorer:
    """Calcule et injecte le score de pertinence dans un Tender."""

    def __init__(self, settings: dict) -> None:
        self._priority_depts: set[str] = set(
            str(d)
            for d in settings.get("geography", {}).get("priority_departments", [])
        )
        self._priority_boost: int = (
            settings.get("geography", {}).get("priority_boost", 20)
        )
        self._min_score: int = settings.get("scoring", {}).get("min_score", 20)

        # Pré-compilation des patterns
        self._keyword_groups: list[dict] = []
        for group in settings.get("keywords", []):
            compiled = [
                (term, _build_pattern(term)) for term in group.get("terms", [])
            ]
            self._keyword_groups.append(
                {
                    "group": group.get("group", ""),
                    "weight": group.get("weight", 10),
                    "patterns": compiled,
                }
            )

        self._valid_market_types: set[str] = set(
            settings.get("market_types", ["TRAVAUX", "SERVICES"])
        )

    def score(self, tender: Tender) -> Tender:
        """Calcule le score et met à jour le Tender."""
        search_text = _normalize(
            " ".join(
                filter(None, [tender.title, tender.description, tender.execution_location])
            )
        )

        total_score = 0
        matched: list[str] = []

        for group in self._keyword_groups:
            group_matched = False
            for term, pattern in group["patterns"]:
                if pattern.search(search_text):
                    if not group_matched:
                        total_score += group["weight"]
                        group_matched = True
                    matched.append(term)

        # Bonus géographique
        is_priority = bool(self._priority_depts & set(tender.departments))
        if is_priority:
            total_score += self._priority_boost

        # Malus type hors périmètre
        if (
            tender.market_type not in self._valid_market_types
            and tender.market_type != "OTHER"
        ):
            total_score = max(0, total_score - 10)

        tender.score = total_score
        tender.matched_keywords = matched
        tender.is_priority_region = is_priority
        tender.is_relevant = total_score >= self._min_score

        return tender
