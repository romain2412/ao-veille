"""
Classe abstraite dont héritent tous les connecteurs de sources.
Pour ajouter une nouvelle source : créer une classe qui hérite de BaseSource
et implémenter fetch().
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import AsyncGenerator

from models.tender import Tender

logger = logging.getLogger(__name__)


class BaseSource(ABC):
    """
    Interface commune à toutes les sources d'appels d'offres.

    Exemple d'implémentation minimale :
    -------
    class MaSuperSource(BaseSource):
        name = "masupersource"

        async def fetch(self, since: datetime) -> AsyncGenerator[Tender, None]:
            yield Tender(uid="masupersource_123", source=self.name, ...)
    """

    name: str = "unknown"
    description: str = ""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def fetch(self, since: datetime) -> AsyncGenerator[Tender, None]:
        """Génère des Tender publiés depuis `since`."""
        ...
        yield  # make it a generator

    async def test_connection(self) -> bool:
        """Vérifie que la source est joignable."""
        try:
            since = datetime.utcnow() - timedelta(days=1)
            async for _ in self.fetch(since):
                return True
            return True
        except Exception as exc:
            logger.warning("[%s] test_connection failed: %s", self.name, exc)
            return False
