"""Small cache-backed rate limits.

Counters live in Django's default cache, the in-process memory cache, so
they reset when the server restarts and aren't shared between server
processes. A production deployment would point the cache at a shared store.
"""

import math
from dataclasses import dataclass
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone


@dataclass(frozen=True)
class RateLimit:
    """At most ``limit`` counted events per key in each ``window``.

    A key's window opens with its first counted event and lasts
    ``window``; once it ends, the key starts fresh. Limits are always
    temporary.
    """

    name: str
    limit: int
    window: timedelta

    def _cache_key(self, key: object) -> str:
        return f"ratelimit:{self.name}:{key}"

    def _open_window(self, key: object) -> dict | None:
        """The key's current window, or None if none is open."""
        entry = cache.get(self._cache_key(key))
        if entry is None or timezone.now() >= entry["started"] + self.window:
            return None
        return entry

    def is_limited(self, key: object) -> bool:
        """Has ``key`` used up its events for the current window?"""
        entry = self._open_window(key)
        return entry is not None and entry["count"] >= self.limit

    def hit(self, key: object) -> None:
        """Count one event for ``key``, opening a window if none is open."""
        now = timezone.now()
        entry = self._open_window(key) or {"started": now, "count": 0}
        entry["count"] += 1
        remaining = entry["started"] + self.window - now
        cache.set(
            self._cache_key(key),
            entry,
            timeout=max(1, math.ceil(remaining.total_seconds())),
        )


# Confirmation emails per account: signup, add/change requests, replacement
# addresses, and resends all share this budget.
confirmation_emails = RateLimit(
    "confirmation-email", limit=3, window=timedelta(hours=1)
)
