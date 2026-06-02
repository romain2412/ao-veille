"""
Utilitaires de date/heure.

L'application stocke et compare des datetimes en **UTC naïf** (sans fuseau),
cohérent avec les colonnes PostgreSQL `timestamp without time zone`.

- `now_utc()` remplace `datetime.utcnow()` (déprécié en Python 3.12) tout en
  conservant exactement la même sémantique (UTC naïf).
- `as_utc()` marque un datetime naïf (supposé UTC) comme *aware* UTC : utile
  au moment de la **sérialisation par l'API**, pour que le JSON porte un fuseau
  explicite (`...+00:00`) et soit interprété sans ambiguïté par les clients.
"""
from __future__ import annotations

from datetime import datetime, timezone


def now_utc() -> datetime:
    """Heure UTC actuelle, en datetime naïf (compatible stockage/comparaisons)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def as_utc(dt: datetime | None) -> datetime | None:
    """Marque un datetime naïf (supposé UTC) comme aware UTC. None reste None."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
