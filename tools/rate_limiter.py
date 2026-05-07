"""
tools/rate_limiter.py

Per-domain rate limiting for outbound SMTP verification requests.
Prevents hitting the same mail server too fast, which is the #1
cause of temporary blocks and greylisting.
"""

import time
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

# (max_attempts, window_seconds)
DOMAIN_RATE_LIMITS = {
    'default':     (5,  60),
    'gmail.com':   (2,  60),
    'outlook.com': (3,  60),
    'hotmail.com': (3,  60),
    'yahoo.com':   (2,  60),
    'icloud.com':  (2,  60),
    'protonmail.com': (2, 60),
}


class DomainRateLimiter:

    def should_throttle(self, mx_host: str):
        """
        Returns (throttled: bool, wait_seconds: int).
        Increments the counter for this domain if not yet throttled.
        """
        domain_key  = self._normalise(mx_host)
        limit, window = DOMAIN_RATE_LIMITS.get(domain_key, DOMAIN_RATE_LIMITS['default'])
        cache_key   = f"rate:{domain_key}"
        current     = cache.get(cache_key, 0)

        if current >= limit:
            # Try to read remaining TTL; fall back to full window
            try:
                ttl = cache.ttl(cache_key)
            except Exception:
                ttl = window
            logger.info(f"Rate limit hit for {domain_key}: {current}/{limit}, wait ~{ttl}s")
            return True, int(ttl or window)

        if current == 0:
            cache.set(cache_key, 1, timeout=window)
        else:
            try:
                cache.incr(cache_key)
            except Exception:
                cache.set(cache_key, current + 1, timeout=window)

        return False, 0

    def _normalise(self, mx_host: str) -> str:
        """Map an MX hostname to the canonical domain key."""
        host = mx_host.lower()
        if 'google' in host:
            return 'gmail.com'
        if any(k in host for k in ('outlook', 'microsoft', 'hotmail')):
            return 'outlook.com'
        if 'yahoo' in host:
            return 'yahoo.com'
        if 'icloud' in host or 'apple' in host:
            return 'icloud.com'
        if 'proton' in host:
            return 'protonmail.com'
        parts = host.split('.')
        return '.'.join(parts[-2:]) if len(parts) >= 2 else host


# Module-level singleton
rate_limiter = DomainRateLimiter()