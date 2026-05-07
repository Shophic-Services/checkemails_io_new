"""
tools/sender_pool.py

Rotating sender pool with per-sender, per-MX and per-IP cooldowns
stored in Django's cache backend (Redis recommended).
"""

import random
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Base sender addresses
# ---------------------------------------------------------------------------
SENDER_POOL = [
    "sandysoorma407@gmail.com",
    "reachalex009@gmail.com",
    "reachalex332@gmail.com",
    "alexatreach@gmail.com",
    "alexuserus002@gmail.com",
    "reachalex333@gmail.com",
    "reachalex078@gmail.com",
    "reachalex10@gmail.com",
]

# Cooldown durations (seconds)
SENDER_COOLDOWN = 30 #60 * 30   # 30 min — after a sender is refused
MX_COOLDOWN     = 60 * 15   # 15 min — after a hard block on an MX host
IP_COOLDOWN     = 60 * 60   # 60 min — after a source IP is flagged


class SenderPool:

    # ------------------------------------------------------------------
    # Sender selection
    # ------------------------------------------------------------------

    def get_sender(self, mx_host=None):
        """
        Return a randomised +tag sender that is not currently cooling down.
        Falls back to a random pick if every sender is on cooldown.
        """
        available = [
            b for b in SENDER_POOL
            if not cache.get(f"sender_blocked:{b}")
        ]
        if not available:
            logger.warning("All senders on cooldown — using random fallback")
            available = SENDER_POOL

        base = random.choice(available)
        username, domain = base.split('@')
        tag = random.randint(100, 9999)
        return f"{username}+{tag}@{domain}"

    # ------------------------------------------------------------------
    # Mark / check sender
    # ------------------------------------------------------------------

    def mark_sender_blocked(self, sender_email: str):
        """Strip the +tag and cool down the base address."""
        local, domain = sender_email.split('@')
        base_local = local.split('+')[0]
        base = f"{base_local}@{domain}"
        cache.set(f"sender_blocked:{base}", True, timeout=SENDER_COOLDOWN)
        logger.info(f"Sender cooling down: {base} for {SENDER_COOLDOWN}s")

    # ------------------------------------------------------------------
    # Mark / check MX host
    # ------------------------------------------------------------------

    def mark_mx_blocked(self, mx_host: str):
        cache.set(f"mx_blocked:{mx_host}", True, timeout=MX_COOLDOWN)
        logger.info(f"MX host cooling down: {mx_host} for {MX_COOLDOWN}s")

    def is_mx_blocked(self, mx_host: str) -> bool:
        return bool(cache.get(f"mx_blocked:{mx_host}"))

    # ------------------------------------------------------------------
    # Mark / check source IP
    # ------------------------------------------------------------------

    def mark_ip_blocked(self, ip: str):
        cache.set(f"ip_blocked:{ip}", True, timeout=IP_COOLDOWN)
        logger.warning(f"Source IP cooling down: {ip} for {IP_COOLDOWN}s")

    def is_ip_blocked(self, ip: str) -> bool:
        return bool(cache.get(f"ip_blocked:{ip}"))


# Module-level singleton
sender_pool = SenderPool()