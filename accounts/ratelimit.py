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
    ``window``; once it ends, the key starts fresh. With a ``cooldown``,
    the event that reaches the limit instead holds the key limited for
    ``cooldown`` from that moment. Limits are always temporary.
    """

    name: str
    limit: int
    window: timedelta
    cooldown: timedelta | None = None

    def _cache_key(self, key: object) -> str:
        return f"ratelimit:{self.name}:{key}"

    def _open_window(self, key: object) -> dict | None:
        """The key's current window, or None if none is open."""
        entry = cache.get(self._cache_key(key))
        if entry is None or timezone.now() >= entry["ends"]:
            return None
        return entry

    def is_limited(self, key: object) -> bool:
        """Has ``key`` used up its events for the current window?"""
        entry = self._open_window(key)
        return entry is not None and entry["count"] >= self.limit

    def hit(self, key: object) -> None:
        """Count one event for ``key``, opening a window if none is open."""
        now = timezone.now()
        entry = self._open_window(key) or {"ends": now + self.window, "count": 0}
        entry["count"] += 1
        if self.cooldown is not None and entry["count"] == self.limit:
            entry["ends"] = now + self.cooldown
        remaining = entry["ends"] - now
        cache.set(
            self._cache_key(key),
            entry,
            timeout=max(1, math.ceil(remaining.total_seconds())),
        )

    def clear(self, key: object) -> None:
        """Forget every counted event for ``key``."""
        cache.delete(self._cache_key(key))


# Confirmation emails per account: signup, add/change requests, replacement
# addresses, and resends all share this budget.
confirmation_emails = RateLimit(
    "confirmation-email", limit=3, window=timedelta(hours=1)
)

# Failed sign-ins per submitted username, whether or not it exists. The
# fifth failure locks the username for 15 minutes from that failure.
failed_sign_ins = RateLimit(
    "sign-in",
    limit=5,
    window=timedelta(minutes=15),
    cooldown=timedelta(minutes=15),
)

# Password-reset requests per submitted email, lowercased, whether or not
# it matches an account. Over the limit, requests are dropped silently.
reset_requests = RateLimit("password-reset", limit=3, window=timedelta(hours=1))
