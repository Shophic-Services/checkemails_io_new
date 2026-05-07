"""
tools/ehlo_generator.py

Generates realistic-looking EHLO hostnames so SMTP sessions
don't fingerprint as automated verifiers.
"""

import random

EHLO_TEMPLATES = [
    "mail.{company}.com",
    "smtp.{company}.net",
    "outbound.{company}.io",
    "mta{n}.{company}.com",
    "relay{n}.{company}.net",
    "send.{company}.co",
    "{company}-smtp.com",
    "mx{n}.{company}.org",
    "post.{company}.com",
    "mailer.{company}.net",
]

COMPANY_WORDS = [
    "nexus", "orbit", "pulse", "nova", "apex", "core",
    "delta", "echo", "forge", "grid", "helix", "ionic",
    "juno", "kite", "lumen", "mesh", "node", "onyx",
    "prism", "relay", "solar", "titan", "ultra",
    "vega", "wave", "zenith", "atlas", "brio", "crest",
    "dune", "flux", "haven", "iris", "jade", "lyra",
]


def generate_ehlo_hostname() -> str:
    """Return a plausible mail-server hostname for use in EHLO."""
    template = random.choice(EHLO_TEMPLATES)
    company  = random.choice(COMPANY_WORDS)
    n        = random.randint(1, 9)
    return template.format(company=company, n=n)