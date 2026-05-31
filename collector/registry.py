"""
Registre des sources de collecte.

Pour ajouter une nouvelle source :
  1. Créer collector/ma_source.py  (hériter de BaseSource)
  2. L'enregistrer ici avec registry.register("ma_source")(MaSource)
  3. C'est tout.
"""
from __future__ import annotations

import logging
from typing import Type

from collector.base import BaseSource

logger = logging.getLogger(__name__)


class SourceRegistry:
    """Annuaire des connecteurs disponibles."""

    def __init__(self) -> None:
        self._sources: dict[str, Type[BaseSource]] = {}

    def register(self, name: str):
        def decorator(cls: Type[BaseSource]) -> Type[BaseSource]:
            cls.name = name
            self._sources[name] = cls
            logger.debug("Source enregistrée : %s → %s", name, cls.__name__)
            return cls
        return decorator

    def get(self, name: str) -> Type[BaseSource] | None:
        return self._sources.get(name)

    def all_names(self) -> list[str]:
        return list(self._sources.keys())

    def build_all(self, sources_config: dict) -> list[BaseSource]:
        """Instancie toutes les sources enregistrées avec leur config."""
        instances: list[BaseSource] = []
        for name, cls in self._sources.items():
            cfg = sources_config.get(name, {}) or {}
            instances.append(cls(config=cfg))
        return instances


# --- Instance globale ---
registry = SourceRegistry()

# --- Enregistrement des sources (ajouter ici chaque nouveau connecteur) ---
from collector.boamp import BOAMPSource                        # noqa: E402
from collector.demat_ampa import DematAmpaSource               # noqa: E402
from collector.e_marches_publics import EMarchesPublicsSource  # noqa: E402
from collector.noalis import NoalisSource                      # noqa: E402
from collector.vilogia import VilogiaSource                    # noqa: E402

registry.register("boamp")(BOAMPSource)
registry.register("demat_ampa")(DematAmpaSource)
registry.register("e_marches_publics")(EMarchesPublicsSource)
registry.register("noalis")(NoalisSource)
registry.register("vilogia")(VilogiaSource)
