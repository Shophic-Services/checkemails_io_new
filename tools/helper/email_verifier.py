"""
tools/helper.py

Email verification helper — with:
  - Parallel DNS (MX + SPF + DMARC run concurrently)
  - Parallel SMTP + Swaks (race; first 250 wins)
  - Per-operation signal-based timeouts (no hanging)
  - Sender pool rotation with cooldowns
  - Realistic EHLO hostnames
  - Per-domain rate limiting
  - PTR record filter
  - Single RCPT (double RCPT removed — fingerprint)
  - All subprocess calls time-bounded
  - All HTTP calls time-bounded
"""

import os
import re
import time
import requests, copy
import pandas as pd
from bs4 import BeautifulSoup
from html import unescape
from urllib.parse import urlparse, urlunparse, urljoin, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Tuple, List, Set, Dict
import smtplib
import signal
import subprocess
import socket
import random
import string
import logging
import urllib.parse
from base64 import b64decode
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import timedelta
from difflib import SequenceMatcher
from urllib.parse import urljoin
from ddgs import DDGS
from difflib import SequenceMatcher
import dns.resolver
import psutil
import requests
import requests.exceptions
from bs4 import BeautifulSoup
from django.utils import timezone

from tools.models import EmailData
from tools import constants
from tools.sender_pool import sender_pool
from tools.ehlo_generator import generate_ehlo_hostname
from tools.rate_limiter import rate_limiter
from django.conf import settings
ZYTE_API_KEY = settings.ZYTE_API_KEY
ZYTE_TIMEOUT = (5, 20)   # (connect_timeout, read_timeout)
from tools.helper.scrape_email import normalize_url, scrape_single_url

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Block-pattern classification
# ---------------------------------------------------------------------------

BLOCK_PATTERNS_HARD = [
    'spamhaus', 'zen.spamhaus.org', 'pbl.spamhaus.org',
    'xbl.spamhaus.org', 'sbl.spamhaus.org',
    'barracudacentral', 'spamcop.net', 'uceprotect', 'sorbs.net',
    'spamrats', 'mailspike',
    'blocked', 'blacklist', 'blacklisted',
    'your ip', 'sending ip', 'ip address',
    'not authorized', 'access denied',
    'bad reputation', 'low reputation',
    'policy violation', 'banned',
    'client host',
]

BLOCK_PATTERNS_SOFT = [
    'greylisted', 'greylist', 'try again later',
    'temporary', 'temporarily', 'rate limit',
    'too many', 'too frequent', 'slow down',
    'come back later', 'connections exceeded',
    'service unavailable', 'try again',
    'defer',
]

BLOCK_PATTERNS_CONN = [
    'connection refused', 'connection timed out',
    'no route to host', 'network unreachable',
    'cannot connect',
]

MAX_WORKERS = 12          # concurrency
TIMEOUT = 30              # slightly lower to avoid hanging too long
REQUEST_DELAY = 0.1       # shorter delay for speed
MAX_PAGES_PER_SITE = 3    # main page + up to 2 internal pages
MAX_HTML_CHARS = 300_000  # don't scan unlimited HTML

HTML_OK_MIN_LEN = 4000


# ---------------------------------------------------------------------------
# Signal-based per-operation timeout
# ---------------------------------------------------------------------------

class SMTPTimeoutError(Exception):
    pass


@contextmanager
def smtp_timeout(seconds=25):
    """
    Raises SMTPTimeoutError if the wrapped block exceeds `seconds`.
    POSIX only (Linux/macOS). Silently skips on Windows.
    """
    if not hasattr(signal, 'SIGALRM'):
        yield
        return

    def _handler(signum, frame):
        raise SMTPTimeoutError(f"SMTP operation timed out after {seconds}s")

    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def generate_pattern(first_name='', last_name='', domain=''):
    fi = first_name[0] if first_name else ''
    li = last_name[0]  if last_name  else ''
    patterns = [
        first_name, last_name,
        first_name + last_name,        f"{first_name}.{last_name}",
        f"{fi}{last_name}",            f"{fi}.{last_name}",
        f"{first_name}{li}",           f"{first_name}.{li}",
        f"{fi}{li}",                   f"{fi}.{li}",
        last_name + first_name,        f"{last_name}.{first_name}",
        f"{last_name}{fi}",            f"{last_name}.{fi}",
        f"{li}{first_name}",           f"{li}.{first_name}",
        f"{li}{fi}",                   f"{li}.{fi}",
        f"{first_name}-{last_name}",   f"{fi}-{last_name}",
        f"{first_name}-{li}",          f"{fi}-{li}",
        f"{last_name}-{first_name}",   f"{last_name}-{fi}",
        f"{li}-{first_name}",          f"{li}-{fi}",
        f"{first_name}_{last_name}",   f"{fi}_{last_name}",
        f"{first_name}_{li}",          f"{fi}_{li}",
        f"{last_name}_{first_name}",   f"{last_name}_{fi}",
        f"{li}_{first_name}",          f"{li}_{fi}",
    ]
    if domain:
        patterns = [p + '@' + domain for p in patterns]
    return patterns


EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def is_valid_syntax(email: str) -> bool:
    return bool(email and EMAIL_REGEX.match(email.strip()))


# ---------------------------------------------------------------------------
# Main helper class
# ---------------------------------------------------------------------------

class EmailCheckHelper:

    def __init__(self, request=None, **kwargs):
        self.request = request
        self.user_id = kwargs.get('user_id', None)

        self.FREE_EMAIL_PROVIDERS = {
            "gmail.com", "googlemail.com",
            "yahoo.com", "yahoo.co.in", "yahoo.co.uk", "yahoo.ca",
            "yahoo.fr", "yahoo.co.jp",
            "hotmail.com", "hotmail.co.uk", "hotmail.fr", "hotmail.de",
            "hotmail.com.br",
            "outlook.com", "outlook.in", "outlook.co.uk",
            "live.com", "msn.com",
            "icloud.com", "me.com", "mac.com",
            "aol.com",
            "protonmail.com", "proton.me", "tutanota.com", "tuta.io",
            "hushmail.com", "mailfence.com", "countermail.com",
            "zoho.com", "mail.com", "gmx.com", "gmx.net",
            "yandex.com", "yandex.ru", "yandex.ua", "yandex.kz", "yandex.by",
            "mail.ru", "bk.ru", "inbox.ru", "list.ru", "rambler.ru", "ukr.net",
            "rediffmail.com", "rediff.com", "sify.com", "in.com",
            "qq.com", "163.com", "126.com", "yeah.net", "sina.com",
            "sina.cn", "sohu.com", "foxmail.com", "aliyun.com",
            "ezweb.ne.jp", "docomo.ne.jp", "softbank.ne.jp", "nifty.com",
            "naver.com", "daum.net", "hanmail.net",
            "orange.fr", "wanadoo.fr", "laposte.net", "free.fr", "sfr.fr",
            "web.de", "gmx.de", "t-online.de", "freenet.de",
            "btinternet.com", "virginmedia.com", "talktalk.net", "sky.com",
            "terra.es", "telefonica.net", "libero.it", "alice.it", "tiscali.it",
            "uol.com.br", "bol.com.br", "ig.com.br", "terra.com.br",
            "seznam.cz", "centrum.cz", "wp.pl", "o2.pl", "interia.pl",
            "inbox.com", "fastmail.com", "rocketmail.com", "aim.com",
        }

        self.disposable_domains = [
            "mailinator.com", "guerrillamail.com", "10minutemail.com",
            "temp-mail.org", "emailondeck.com", "throwawaymail.com",
            "yopmail.com", "mohmal.com", "burnermail.io", "inboxkitten.com",
            "fakemail.net", "emailfake.com", "maildrop.cc", "getnada.com",
        ]
        _session = requests.Session()
        retry = Retry(
            total=3, connect=3, read=3, backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
        _session.mount("http://", adapter)
        _session.mount("https://", adapter)
        _session.headers.update({
            'User-Agent': (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        })
        self.session = _session

    # ---------------------------------------------------------------
    # Public entry point
    # ---------------------------------------------------------------

    def validate_email(self, email, action=None):
        """
        Returns a 19-tuple:
        (email, is_role_based, has_domain_mx, has_spf, has_dmarc,
         status, quality, email_result, valid, email_source,
         catch_all, email_type, code, message, errors,
         retry_later, permanent_failure, needs_manual_review, has_smtp)
        """

        # --- Cache check — return immediately on hit ---
        try:
            ed = EmailData.objects.get(email=email)
            cache_fresh = (
                ed.modify_date and
                ed.modify_date >= (timezone.now() - timedelta(days=30))
            )
            if cache_fresh or ed.email_type == EmailData.SCRAPED:
                time.sleep(random.uniform(1.3, 2.8))
                return (
                    ed.email, ed.role_based, ed.has_domain_mx,
                    ed.has_spf, ed.has_dmarc, ed.status, ed.quality,
                    ed.email_result, ed.valid, ed.email_source,
                    ed.catch_all, ed.email_type, ed.code, ed.message, '',
                    ed.retry_later, ed.permanent_failure,
                    ed.needs_manual_review, ed.has_smtp,
                )
        except EmailData.DoesNotExist:
            pass

        domain = email.split('@')[1].lower()

        # --- Parallel DNS ---
        has_domain_mx, has_spf, has_dmarc = self._run_dns_checks(domain)

        is_role_based       = self.check_role_based(email)
        status              = EmailData.UNKNOWN
        quality             = EmailData.UNKNOWN
        email_result        = 'Do Not Send - Unable to Confirm'
        valid               = False
        email_source        = EmailData.SMTP
        catch_all           = False
        email_type          = EmailData.UNKNOWN
        code                = 204
        message             = ''
        errors              = ''
        retry_later         = False
        permanent_failure   = False
        needs_manual_review = False
        has_smtp            = False

        # --- Disposable short-circuit ---
        if domain in self.disposable_domains:
            status       = EmailData.DISPOSABLE
            quality      = EmailData.DISPOSABLE
            email_result = 'Do Not Send - Disposable'
            valid        = False
            catch_all    = True
            email_type   = EmailData.DISPOSABLE
            code         = 999
            message      = 'Disposable domain'
        else:
            result = (
                email, is_role_based, has_domain_mx, has_spf, has_dmarc,
                status, quality, email_result, valid, email_source,
                catch_all, email_type, code, message, errors,
                retry_later, permanent_failure, needs_manual_review, has_smtp,
            )
            result = self.update_response_validate(email, result)
            (
                email, is_role_based, has_domain_mx, has_spf, has_dmarc,
                status, quality, email_result, valid, email_source,
                catch_all, email_type, code, message, errors,
                retry_later, permanent_failure, needs_manual_review, has_smtp,
            ) = result
            if status != EmailData.UNKNOWN:
                # --- Persist ---
                ed, _ = EmailData.objects.get_or_create(email=email)
                ed.has_domain_mx       = has_domain_mx
                ed.has_spf             = has_spf
                ed.has_dmarc           = has_dmarc
                ed.professional        = (
                    domain not in self.FREE_EMAIL_PROVIDERS
                    and (has_dmarc or has_spf)
                    and domain not in self.disposable_domains
                )
                ed.retry_later         = retry_later
                ed.valid               = valid
                ed.message             = message
                ed.catch_all           = catch_all
                ed.role_based          = is_role_based
                ed.disposable          = status == EmailData.DISPOSABLE
                ed.status              = status
                ed.quality             = quality
                ed.email_source        = email_source
                ed.email_type          = email_type
                ed.code                = code
                ed.needs_manual_review = needs_manual_review
                ed.permanent_failure   = permanent_failure
                ed.email_result        = email_result
                if self.request:
                    ed.added_by = self.request.user
                if self.user_id and not self.request:
                    ed.added_by_id = self.user_id
                ed.save()

        return (
            email, is_role_based, has_domain_mx, has_spf, has_dmarc,
            status, quality, email_result, valid, email_source,
            catch_all, email_type, code, message, errors,
            retry_later, permanent_failure, needs_manual_review, has_smtp,
        )

    # ---------------------------------------------------------------
    # Parallel DNS
    # ---------------------------------------------------------------

    def _resolve_dns_safe(self, name, record_type, lifetime=5):
        """DNS lookup with hard lifetime — never hangs."""
        try:
            resolver          = dns.resolver.Resolver()
            resolver.lifetime = lifetime
            resolver.timeout  = 5
            return list(resolver.resolve(name, record_type))
        except dns.exception.Timeout:
            logger.warning(f"DNS timeout: {record_type} {name}")
        except Exception as e:
            logger.debug(f"DNS {record_type} failed for {name}: {e}")
        return []

    def _run_dns_checks(self, domain):
        """Run MX, SPF, DMARC lookups concurrently — saves 2-6s vs serial."""

        def check_mx():
            records = self._resolve_dns_safe(domain, 'MX', lifetime=5)
            hosts = [
                str(r.exchange).strip('.')
                for r in sorted(records, key=lambda r: r.preference)
                if str(r.exchange).strip('.')
            ]
            return bool(hosts)

        def check_spf():
            for r in self._resolve_dns_safe(domain, 'TXT', lifetime=5):
                for txt in r.strings:
                    if txt.decode().lower().startswith("v=spf1"):
                        return True
            return False

        def check_dmarc():
            for r in self._resolve_dns_safe(f"_dmarc.{domain}", 'TXT', lifetime=5):
                for txt in r.strings:
                    if txt.decode().lower().startswith("v=dmarc1"):
                        return True
            return False

        with ThreadPoolExecutor(max_workers=3) as ex:
            f_mx    = ex.submit(check_mx)
            f_spf   = ex.submit(check_spf)
            f_dmarc = ex.submit(check_dmarc)
            return f_mx.result(), f_spf.result(), f_dmarc.result()

    # ---------------------------------------------------------------
    # Role-based check
    # ---------------------------------------------------------------

    def check_role_based(self, email: str) -> bool:
        role_accounts = {
            'admin', 'administrator', 'info', 'contact', 'support', 'help',
            'sales', 'marketing', 'noreply', 'no-reply', 'postmaster',
            'webmaster', 'hostmaster', 'root', 'mailer-daemon',
        }
        return email.split('@')[0].lower() in role_accounts

    # ---------------------------------------------------------------
    # Network helpers
    # ---------------------------------------------------------------

    def get_system_ipv6_list(self):
        ipv6_list = []
        try:
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET6:
                        ip = addr.address.split('%')[0]
                        if not ip.startswith("fe80") and ip != "::1":
                            ipv6_list.append(ip)
        except Exception as e:
            logger.error(f"Failed to get IPv6 addresses: {e}")
        return ipv6_list

    def has_valid_ptr(self, ip: str) -> bool:
        """Filter source IPs with no PTR — mail servers reject them at connect."""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return bool(hostname)
        except (socket.herror, socket.gaierror):
            logger.debug(f"No PTR for {ip}")
            return False

    def resolve_mx_ip(self, mx_host: str):
        ip_addresses = set()
        ip_addresses.update(self.get_system_ipv6_list())

        # try:
        #     for info in socket.getaddrinfo(mx_host, 25, socket.AF_INET6, socket.SOCK_STREAM):
        #         ip_addresses.add(info[4][0])
        # except socket.gaierror:
        #     pass

        # try:
        #     for info in socket.getaddrinfo(mx_host, 25, socket.AF_INET, socket.SOCK_STREAM):
        #         ip_addresses.add(info[4][0])
        # except socket.gaierror as e:
        #     logger.error(f"Failed to resolve {mx_host} IPv4: {e}")

        # Remove IPs that are cooling down or lack PTR records
        valid = [
            ip for ip in ip_addresses
            if not sender_pool.is_ip_blocked(ip) and self.has_valid_ptr(ip)
        ]
        return valid if valid else list(ip_addresses)

    # ---------------------------------------------------------------
    # SMTP connection factory
    # ---------------------------------------------------------------

    def _create_smtp_connection(self, mx_host: str, ip: str, timeout=10):
        """
        smtplib.SMTP with sock.settimeout() so EHLO/MAIL/RCPT
        all time out — not just the initial connect.
        """
        server = smtplib.SMTP(timeout=timeout)
        if ip:
            sock = socket.create_connection(
                (mx_host, 25), source_address=(ip, 0), timeout=timeout
            )
            sock.settimeout(timeout)
            server._host = mx_host
            server.sock  = sock
            server.file  = sock.makefile("rb")
        else:
            server.connect(mx_host, 25)
            server.sock.settimeout(timeout)
        return server

    # ---------------------------------------------------------------
    # Orchestration
    # ---------------------------------------------------------------

    def update_response_validate(self, email, result):
        (
            email, is_role_based, has_domain_mx, has_spf, has_dmarc,
            status, quality, email_result, valid, email_source,
            catch_all, email_type, code, message, errors,
            retry_later, permanent_failure, needs_manual_review, has_smtp,
        ) = result

        _, email_domain = email.split('@')

        if not has_domain_mx:
            code, message = 500, 'MX check failed'
        else:
            # first SMTP then Swaks
            code, message, result = self._probe_parallel(email, result)
            (
                email, is_role_based, has_domain_mx, has_spf, has_dmarc,
                status, quality, email_result, valid, email_source,
                catch_all, email_type, code, message, errors,
                retry_later, permanent_failure, needs_manual_review, has_smtp,
            ) = result

        
        # if code in [204, 500, 551, 552, 553, 554]:
        #     result = (
        #         email, is_role_based, has_domain_mx, has_spf, has_dmarc,
        #         status, quality, email_result, valid, email_source,
        #         catch_all, email_type, code, message, errors,
        #         retry_later, permanent_failure, needs_manual_review, has_smtp,
        #     )
        #     code, message, _result = self.run_probe(
        #         'swaks', email,
        #         result=copy.copy(result),
        #         helo=generate_ehlo_hostname(),
        #         port=587
        #     )
        #     logger.debug(f"Swaks password probe succeeded for {email}: {code}")
        #     (
        #             email, is_role_based, has_domain_mx, has_spf, has_dmarc,
        #             status, quality, email_result, valid, email_source,
        #             catch_all, email_type, code, message, errors,
        #             retry_later, permanent_failure, needs_manual_review, has_smtp,
        #         ) = _result

        if has_domain_mx and code in [204, 500, 551, 552, 553, 554]:

            # Both probes failed — fall back to scrape + LinkedIn
            result = self._fallback_scrape_linkedin(email, email_domain, result)
            (
                email, is_role_based, has_domain_mx, has_spf, has_dmarc,
                status, quality, email_result, valid, email_source,
                catch_all, email_type, code, message, errors,
                retry_later, permanent_failure, needs_manual_review, has_smtp,
            ) = result
        # Human-readable label
        if status == EmailData.DISPOSABLE:
            email_result = 'Do Not Send - Disposable'
        elif status == EmailData.RISKY:
            email_result = 'Risky - Use with Caution'
        elif status == EmailData.UNKNOWN:
            email_result = 'Do Not Send - Unable to Confirm'
        elif valid:
            email_result = 'Safe to Send - Deliverable'
        else:
            email_result = 'Do Not Send - Undeliverable'

        return (
            email, is_role_based, has_domain_mx, has_spf, has_dmarc,
            status, quality, email_result, valid, email_source,
            catch_all, email_type, code, message, errors,
            retry_later, permanent_failure, needs_manual_review, has_smtp,
        )

    def _probe_parallel(self, email, result):
        """
        Fire SMTP first. If it returns 250/251, return immediately.
        Only start Swaks if SMTP did not return 250/251.
        Falls back to best available result.

        ### Key logic flow
        ```
        SMTP probe
            ├── code 250/251 → return immediately ✓
            ├── other code   → continue to Swaks
            └── exception    → continue to Swaks

                Swaks probe
                    ├── code 250/251 → return immediately ✓
                    ├── other code   → collect both results
                    └── exception    → collect SMTP result only

                        Best-effort fallback
                            ├── prefer lowest non-5xx code
                            └── otherwise return lowest 5xx

        """

        _code, _message, _result = None, None, None
        smtp_succeeded = False

        # ── Step 1: Try SMTP first ──────────────────────────────────────────
        try:
            _code, _message, _result = self.validate_email_smtp_dns(
                email, copy.copy(result)
            )
            if _code in [250, 251]:
                smtp_succeeded = True
                return _code, _message, _result
            logger.debug(
                f"SMTP probe returned {_code} for {email} — falling back to Swaks"
            )
        except Exception as e:
            logger.warning(f"SMTP probe raised exception for {email}: {e}")

        # ── Step 2: SMTP didn't give 250/251 — run Swaks ───────────────────
        try:
            _code, _message, _result = self.run_probe(
                'swaks', email,
                result=copy.copy(result),
                helo=generate_ehlo_hostname(),
            )
            logger.debug(f"Swaks probe succeeded for {email}: {_code}")
            return _code, _message, _result
        except Exception as e:
            logger.warning(f"Swaks probe raised exception for {email}: {e}")
        # ── Step 3: Neither gave 250/251 — return best available ───────────
        logger.error(f"All probes failed for {email}")
        return 500, "All probes failed", result

    # ---------------------------------------------------------------
    # Raw SMTP probe
    # ---------------------------------------------------------------

    def validate_email_smtp_dns(self, email, result, max_retries=1):
        (
            email, is_role_based, has_domain_mx, has_spf, has_dmarc,
            status, quality, email_result, valid, email_source,
            catch_all, email_type, code, message, errors,
            retry_later, permanent_failure, needs_manual_review, has_smtp,
        ) = result

        _, email_domain = email.split('@')
        
        _email, _email_domain = sender_pool.get_sender().split('@')

        mx_records = self._resolve_dns_safe(email_domain, 'MX', lifetime=15)
        if not mx_records:
            return 500, f"MX lookup failed for {email_domain}", result

        mx_hosts = [
            str(r.exchange).strip('.')
            for r in sorted(mx_records, key=lambda r: r.preference)
            if str(r.exchange).strip('.')
        ]

        error_msg = ''
        for mx_host in mx_hosts:
            if sender_pool.is_mx_blocked(mx_host):
                logger.info(f"Skipping blocked MX: {mx_host}")
                continue

            throttled, wait_secs = rate_limiter.should_throttle(mx_host)
            if throttled:
                sleep_secs = min(wait_secs, 8)
                logger.info(f"Rate-limiting {mx_host} — sleeping {sleep_secs}s")
                time.sleep(sleep_secs)
                throttled, _ = rate_limiter.should_throttle(mx_host)
                if throttled:
                    continue

            ip_addresses = self.resolve_mx_ip(mx_host)
            if not ip_addresses:
                logger.warning(f"No usable IPs for {mx_host}")
                continue

            for ip in ip_addresses:
                if sender_pool.is_ip_blocked(ip):
                    continue

                sender_email = sender_pool.get_sender(mx_host)
                ehlo_name    = generate_ehlo_hostname()

                try:
                    server = self._create_smtp_connection(mx_host, ip, timeout=10)
                    server.set_debuglevel(1)
                    server.ehlo(name=ehlo_name)
                    server.mail(sender_email)

                    # Human-like delay between MAIL FROM and RCPT TO
                    time.sleep(random.uniform(0.3, 1.0))

                    # Single RCPT — double RCPT is a known verifier fingerprint
                    code, message = server.rcpt(email)
                    time.sleep(random.uniform(1.3, 2.8))
                    if code in [250, 251]:
                        code, message = server.rcpt(email)
                    logger.debug(f"RCPT {email}: {code} {message}")

                    if code in [250, 251]:
                        # Catch-all probe
                        # try:
                        #     server.rset()
                        # except Exception:
                        try:
                            server.quit()
                        except Exception:
                            pass
                        server = self._create_smtp_connection(mx_host, ip, timeout=10)

                        sender2 = sender_pool.get_sender(mx_host)
                        server.ehlo(name=generate_ehlo_hostname())
                        server.mail(sender2)
                        rand_user  = ''.join(
                            random.choices(string.ascii_lowercase + string.digits, k=12)
                        )
                        fake_email = f"{rand_user}@{email_domain}"
                        code_fake, _ = server.rcpt(fake_email)
                        time.sleep(random.uniform(1.3, 2.8))
                        if code_fake in [250, 251]:
                            code_fake, _ = server.rcpt(fake_email)
                        catch_all    = code_fake in [250, 251]

                    try:
                        server.quit()
                    except Exception:
                        pass

                    has_smtp     = True
                    email_source = EmailData.SMTP
                    result       = self._classify_smtp_code(
                        code, email, is_role_based, has_domain_mx,
                        has_spf, has_dmarc, email_result, email_source,
                        catch_all, errors, retry_later, permanent_failure,
                        needs_manual_review, has_smtp, message,
                    )
                    return code, message, result

                except SMTPTimeoutError:
                    logger.warning(f"SMTP timed out on {mx_host} ({ip})")
                    sender_pool.mark_mx_blocked(mx_host)
                    sender_pool.mark_ip_blocked(ip)
                    try:
                        server.close()
                    except Exception:
                        pass
                    continue

                except smtplib.SMTPConnectError as e:
                    error_msg = str(e).lower()
                    logger.warning(f"SMTPConnectError {mx_host} ({ip}): {e}")
                    if any(kw in error_msg for kw in ['421', '554', 'refused', 'blocked']):
                        sender_pool.mark_mx_blocked(mx_host)
                        sender_pool.mark_ip_blocked(ip)
                    break

                except smtplib.SMTPHeloError as e:
                    logger.warning(f"EHLO rejected {mx_host}: {e}")
                    sender_pool.mark_mx_blocked(mx_host)
                    break

                except smtplib.SMTPSenderRefused as e:
                    logger.warning(f"Sender refused {mx_host}: {e}")
                    sender_pool.mark_sender_blocked(sender_email)
                    continue

                except Exception as e:
                    error_msg = str(e).lower()
                    logger.error(f"SMTP error {mx_host} ({ip}): {e}")
                    if any(kw in error_msg for kw in ['554', 'blocked', 'blacklist', 'spamhaus']):
                        sender_pool.mark_mx_blocked(mx_host)
                        sender_pool.mark_ip_blocked(ip)
                        break
                    if '421' in error_msg or 'greylist' in error_msg:
                        sender_pool.mark_mx_blocked(mx_host)
                        break
                    continue

        logger.error(f"All SMTP attempts failed for {email}")
        needs_manual_review = True
        result = (
            email, is_role_based, has_domain_mx, has_spf, has_dmarc,
            status, quality, email_result, valid, email_source,
            catch_all, email_type, code, message, errors,
            retry_later, permanent_failure, needs_manual_review, has_smtp,
        )
        return 500, "All SMTP attempts failed", result

    # ---------------------------------------------------------------
    # Classify SMTP response code → 19-tuple
    # ---------------------------------------------------------------

    def _classify_smtp_code(
        self, code, email, is_role_based, has_domain_mx, has_spf, has_dmarc,
        email_result, email_source, catch_all, errors,
        retry_later, permanent_failure, needs_manual_review, has_smtp, message,
    ):
        domain = email.split('@')[1]
        is_pro = domain not in self.FREE_EMAIL_PROVIDERS and (has_dmarc or has_spf)
        email_type = EmailData.PROFESSIONAL if is_pro else EmailData.WEBMAIL
        valid  = False
        status = quality = EmailData.UNKNOWN

        if code in [250, 251]:
            valid  = True
            status = quality = EmailData.VALID
        elif code == 550:
            status = quality = EmailData.INVALID
        elif code in [551, 552, 553, 554]:
            permanent_failure = True
            status = quality  = EmailData.UNKNOWN
        elif str(code).startswith('421') or code in [450, 451, 452]:
            retry_later = True
            status = quality = EmailData.RISKY
        else:
            needs_manual_review = True
            email_type = EmailData.UNKNOWN
            status = quality = EmailData.UNKNOWN

        if catch_all:
            needs_manual_review = False
            status = quality    = EmailData.RISKY
            email_type          = EmailData.PROFESSIONAL if is_pro else EmailData.WEBMAIL

        return (
            email, is_role_based, has_domain_mx, has_spf, has_dmarc,
            status, quality, email_result, valid, email_source,
            catch_all, email_type, code, message, errors,
            retry_later, permanent_failure, needs_manual_review, has_smtp,
        )

    # ---------------------------------------------------------------
    # Swaks probe
    # ---------------------------------------------------------------

    def resolve_mx(self, domain: str):
        try:
            proc = subprocess.run(
                ['dig', '+short', 'MX', domain],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip().split('\n')[0].split()[-1].rstrip('.')
        except subprocess.TimeoutExpired:
            logger.warning(f"dig timed out for {domain}")
        except Exception as e:
            logger.debug(f"dig failed for {domain}: {e}")
        return None

    def run_probe(self, tool, email, result, helo, port=25):
        (
            email, is_role_based, has_domain_mx, has_spf, has_dmarc,
            status, quality, email_result, valid, email_source,
            catch_all, email_type, code, message, errors,
            retry_later, permanent_failure, needs_manual_review, has_smtp,
        ) = result

        _, email_domain = email.split('@')

        _email, _email_domain = sender_pool.get_sender().split('@')
        if sender_pool.is_mx_blocked(email_domain):
            return 500, f"MX {email_domain} on cooldown", result

        mx = self.resolve_mx(email_domain)
        if not mx:
            return 500, f"No MX for {email}", result

        if helo is None:
            helo = generate_ehlo_hostname()

        sender_email = sender_pool.get_sender(mx)
        cmd = [
            'swaks', '--to', email, '--from', sender_email,
            '--server', f'{mx}','--port', str(port), '--helo', helo, '--quit-after', 'RCPT', '--timeout', '30',
        ]

        if port == 587:
            mx = 'smtp.gmail.com'
            cmd = [
                "swaks",
                "--to", email,
                "--from", "alexatreach@gmail.com",
                "--server", "smtp.gmail.com",
                "--port", str(port),
                "--helo", str(helo),
                "--tls",
                "--auth", "LOGIN",
                "--auth-user", "alexatreach@gmail.com",
                "--auth-password", "vcmm jxqi goaz pwhu",
                "--quit-after", "RCPT",
                "--suppress-data"
            ]
        try:
            proc   = subprocess.run(cmd, capture_output=True, text=False, timeout=30)
            stdout = proc.stdout or b''
        except subprocess.TimeoutExpired:
            logger.warning(f"swaks timed out for {email}")
            sender_pool.mark_mx_blocked(mx)
            return 500, "swaks timed out", result
        except Exception as e:
            logger.error(f"swaks failed: {e}")
            return 500, str(e), result
        if port == 587:
            code, block_type = self.get_rcpt_code_587(stdout)
        else:
            code, block_type = self.get_rcpt_code(stdout)

        if block_type == 'hard_block':
            sender_pool.mark_mx_blocked(mx)
            sender_pool.mark_sender_blocked(sender_email)

        msg = (
            f'✓ Recipient OK - {tool} 👉 {stdout}'
            if code in [250, 251, 450, 451, 452]
            else f"⚠️ Recipient not accepted - {tool} \n👉 {stdout}"
        )

        if code in [250, 251]:
            # Catch-all probe
            rand_user  = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
            fake_email = f"{rand_user}@{email_domain}"
            cmd2 = [
                'swaks', '--to', fake_email,
                '--from', sender_pool.get_sender(mx),
                '--server', f'{mx}',
                '--port', str(port),
                '--helo', generate_ehlo_hostname(), '--quit-after', 'RCPT', '--timeout', '30']
            if port == 587:
                mx = 'smtp.gmail.com'
                cmd2 = [
                    "swaks",
                    "--to", fake_email,
                    "--from", "alexatreach@gmail.com",
                    "--server", "smtp.gmail.com",
                    "--port", str(port),
                    "--helo", str(helo),
                    "--tls",
                    "--auth", "LOGIN",
                    "--auth-user", "alexatreach@gmail.com",
                    "--auth-password", "vcmm jxqi goaz pwhu",
                    "--quit-after", "RCPT",
                    "--suppress-data"
                ]
            try:
                proc2   = subprocess.run(cmd2, capture_output=True, text=False, timeout=30)

                if port == 587:
                    c2, _ = self.get_rcpt_code_587(proc2.stdout or b'')
                else:
                    c2, _ = self.get_rcpt_code(proc2.stdout or b'')
                # c2, _   = self.get_rcpt_code(proc2.stdout or b'')
                catch_all = c2 in [250, 251]
                msg += f" \n👉 {proc2.stdout}"
            except subprocess.TimeoutExpired:
                catch_all = False

        result = self._classify_smtp_code(
            code, email, is_role_based, has_domain_mx, has_spf, has_dmarc,
            email_result, EmailData.SWAKS, catch_all, errors,
            retry_later, permanent_failure, needs_manual_review, has_smtp, msg,
        )
        return code, msg, result

    # ---------------------------------------------------------------
    # Swaks output parser
    # ---------------------------------------------------------------

    def get_rcpt_code(self, stdout_bytes):
        """Returns (smtp_code: int, block_type: str)."""

        if not stdout_bytes:
            return 500, 'none'
        try:
            stdout = stdout_bytes.decode('utf-8', errors='ignore')
        except Exception:
            return 500, 'failed'

        lines         = stdout.splitlines()
        in_rcpt_block = False
        response_lines = []

        for line in lines:
            stripped = line.strip()
            if 'RCPT TO' in line:
                in_rcpt_block  = True
                response_lines = []
                continue

            if in_rcpt_block:
                if stripped.startswith('-> ') or stripped.startswith('=== '):
                    break
                if (stripped.startswith(('<** ', '<- '))
                        or '5' in stripped[:4]
                        or '4' in stripped[:4]):
                    response_lines.append(stripped)

        if not response_lines:
            return 500, 'none'

        full = ' '.join(response_lines).lower()

        # 🔴 Hard / Soft / Connection blocks
        for kw in BLOCK_PATTERNS_HARD:
            if kw in full:
                logger.warning(f"Hard block: '{kw}'")
                return 554, 'hard_block'

        for kw in BLOCK_PATTERNS_SOFT:
            if kw in full:
                logger.info(f"Soft block: '{kw}'")
                return 421, 'soft_block'

        for kw in BLOCK_PATTERNS_CONN:
            if kw in full:
                logger.info(f"Conn block: '{kw}'")
                return 421, 'connection_block'

        for line in response_lines:
            parts = line.split()
            if len(parts) >= 2:
                cs = parts[1] if parts[0].startswith('<') else parts[0]
                if cs.isdigit() and len(cs) == 3:
                    try:
                        c = int(cs)
                        if 200 <= c <= 599:
                            return (450 if 420 <= c <= 459 else c), 'parsed'
                    except ValueError:
                        pass

        logger.warning(f"No parsable SMTP code:\n{full[:200]}")
        return 500, 'unparsed'


    
    def get_rcpt_code_587(self, stdout_bytes):
        """Returns (smtp_code: int, block_type: str)."""

        if not stdout_bytes:
            return 500, 'failed'

        try:
            stdout = stdout_bytes.decode('utf-8', errors='ignore')
        except Exception:
            return 500, 'failed'

        lines = stdout.splitlines()

        in_rcpt_block = False
        response_lines = []

        for line in lines:
            stripped = line.strip()

            # Start capturing after RCPT
            if 'RCPT TO' in stripped:
                in_rcpt_block = True
                response_lines = []
                continue

            if in_rcpt_block:
                # Stop when next command starts
                if stripped.startswith('~>') or 'QUIT' in stripped:
                    break

                # Capture only server responses
                if stripped.startswith('<~'):
                    response_lines.append(stripped)

        if not response_lines:
            return 500, 'none'

        full = ' '.join(response_lines).lower()

        # 🔴 Hard / Soft / Connection blocks
        for kw in BLOCK_PATTERNS_HARD:
            if kw in full:
                logger.warning(f"Hard block: '{kw}'")
                return 554, 'hard_block'

        for kw in BLOCK_PATTERNS_SOFT:
            if kw in full:
                logger.info(f"Soft block: '{kw}'")
                return 421, 'soft_block'

        for kw in BLOCK_PATTERNS_CONN:
            if kw in full:
                logger.info(f"Conn block: '{kw}'")
                return 421, 'connection_block'

        # ✅ Extract SMTP code using regex
        for line in response_lines:
            match = re.search(r'<~\s*(\d{3})', line)
            if match:
                code = int(match.group(1))

                # Normalize greylisting range
                if 420 <= code <= 459:
                    return 450, 'parsed'

                return code, 'parsed'

        logger.warning(f"No parsable SMTP code:\n{full[:200]}")
        return 500, 'unparsed'

    # ---------------------------------------------------------------
    # Fallback: web scrape + LinkedIn
    # ---------------------------------------------------------------

    def _fallback_scrape_linkedin(self, email, email_domain, result):
        (
            email, is_role_based, has_domain_mx, has_spf, has_dmarc,
            status, quality, email_result, valid, email_source,
            catch_all, email_type, code, message, errors,
            retry_later, permanent_failure, needs_manual_review, has_smtp,
        ) = result

        is_role_based = self.check_role_based(email)
        # has_domain_mx = has_spf = has_dmarc = False
        status = quality   = EmailData.UNKNOWN
        email_result       = 'Do Not Send - Unable to Confirm'
        valid              = False
        email_source       = EmailData.SMTP
        catch_all          = False
        email_type         = EmailData.UNKNOWN
        code               = 204
        message = errors   = ''
        retry_later = permanent_failure = needs_manual_review = has_smtp = False
        found_emails = []
        profiles = self.find_linkedin_profile(email)
        # if profiles:
        #     code         = 111
        #     message      = "Recipient OK"
        #     email_source = EmailData.SOCIAL
        #     valid        = True
        #     status = quality = EmailData.VALID
        #     needs_manual_review = True
        #     email_type   = (
        #         EmailData.PROFESSIONAL
        #         if email_domain not in self.FREE_EMAIL_PROVIDERS
        #         else EmailData.WEBMAIL
        #     )
        url_norm = normalize_url(email_domain)
        if not url_norm:
            raise ValueError(f"Invalid URL: {email_domain!r}")
        scraped = scrape_single_url(url_norm)
        found_emails = sorted(scraped["emails"])
        # if scraped['status_code'] == 200:
        #     has_domain_mx = has_spf = has_dmarc = True
        if email.lower() in [e.lower() for e in found_emails]:
            code         = 250
            message      = "Recipient OK"
            email_source = EmailData.SCRAPED
            valid        = True
            status = quality = EmailData.VALID
            email_type   = (
                EmailData.PROFESSIONAL
                if email_domain not in self.FREE_EMAIL_PROVIDERS
                else EmailData.WEBMAIL
            )
            

        if found_emails:
            self._save_scraped_emails(found_emails, email_domain)

        return (
            email, is_role_based, has_domain_mx, has_spf, has_dmarc,
            status, quality, email_result, valid, email_source,
            catch_all, email_type, code, message, errors,
            retry_later, permanent_failure, needs_manual_review, has_smtp,
        )

    def _save_scraped_emails(self, found_emails, email_domain):
        for found_email in found_emails:
            ed, created = EmailData.objects.get_or_create(email=found_email)
            if created:
                ed.has_domain_mx       = True
                ed.has_dmarc           = True
                ed.has_spf             = True
                ed.professional        = (
                    email_domain not in self.FREE_EMAIL_PROVIDERS
                    and email_domain not in self.disposable_domains
                )
                ed.role_based          = self.check_role_based(found_email)
                ed.status              = EmailData.VALID
                ed.quality             = EmailData.VALID
                ed.email_type          = EmailData.PROFESSIONAL if ed.professional else EmailData.WEBMAIL
                ed.valid               = True
                ed.email_source        = EmailData.SCRAPED
                ed.code                = 250
                ed.catch_all           = False
                ed.has_smtp            = False
                ed.needs_manual_review = False
                ed.permanent_failure   = False
                ed.email_result        = 'Safe to Send - Deliverable'
                ed.message             = "Scraped from website"
                if self.request:
                    ed.added_by = self.request.user
                if self.user_id and not self.request:
                    ed.added_by_id = self.user_id
                ed.save()

    # ---------------------------------------------------------------
    # Domain scraping
    # ---------------------------------------------------------------

    def extract_emails_from_domain(self, domain):
        if domain in self.FREE_EMAIL_PROVIDERS:
            return []

        emails        = set()
        priority_kws  = ['contact', 'privacy', 'career', 'about', 'team', 'support', 'info']
        base_pages    = ['', '/contact', '/privacy-policy', '/career',
                         '/about', '/team', '/info', '/support']
        max_pages     = 10
        visited       = set()
        to_visit      = ['']
        crawled_pages = 0

        try:
            resp = requests.post(
                "https://api.zyte.com/v1/extract",
                auth=(ZYTE_API_KEY, ''),
                json={"url": f"https://{domain}", "httpResponseBody": True,
                      "followRedirect": True},
                timeout=ZYTE_TIMEOUT,
            )
            if resp.status_code == 200:
                html = b64decode(resp.json()["httpResponseBody"]).decode()
                soup = BeautifulSoup(html, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = urljoin(f"https://{domain}", link['href'])
                    if domain in href:
                        path = href.replace(f"https://{domain}", '').split('?')[0].split('#')[0]
                        if path and not path.startswith('/'):
                            path = f"/{path}"
                        if path not in to_visit and any(kw in path.lower() for kw in priority_kws):
                            to_visit.append(path)
        except Exception as e:
            logger.debug(f"Homepage fetch failed https://{domain}: {e}")

        to_visit = list(set(to_visit + base_pages))[:max_pages]

        for path in to_visit:
            for protocol in ['https', 'http']:
                url = f"{protocol}://{domain}{path}"
                if url in visited or crawled_pages >= max_pages:
                    continue
                try:
                    resp = requests.post(
                        "https://api.zyte.com/v1/extract",
                        auth=(ZYTE_API_KEY, ''),
                        json={"url": url, "httpResponseBody": True, "followRedirect": True},
                        timeout=ZYTE_TIMEOUT,
                    )
                    if resp.status_code == 200:
                        html  = b64decode(resp.json()["httpResponseBody"]).decode()
                        found = re.findall(
                            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', html
                        )
                        emails.update(found)
                        crawled_pages += 1
                        visited.add(url)
                except Exception as e:
                    logger.debug(f"Fetch failed {url}: {e}")
            time.sleep(random.uniform(1, 2))

        return [e for e in emails if domain in e]

    # ---------------------------------------------------------------
    # LinkedIn finder
    # ---------------------------------------------------------------

    def get_dynamic_headers(self):
        USER_AGENTS = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        ]
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": random.choice(["en-US,en;q=0.9", "en-GB,en;q=0.8"]),
            "Connection": "keep-alive",
        }

    def is_name_match(self, email_local, snippet_name):
        person = re.match(r"([a-z]+ [a-z]+)", snippet_name.lower(), re.IGNORECASE)
        if person:
            return SequenceMatcher(None, email_local.lower(), person.group(1)).ratio() > 0.6
        return False
    


    def direct_fetch_html(self, url: str) -> Tuple[Optional[int], Optional[str]]:
        try:
            time.sleep(REQUEST_DELAY)
            resp = self.session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            html = resp.text[:MAX_HTML_CHARS]
            return resp.status_code, html
        except requests.RequestException:
            return None, None


    def playwright_fetch_html(self, url: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Headless browser fetch using Playwright.
        Used ONLY when direct HTML looks weak or fails.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return None, None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                    locale="en-US",
                )

                # Remove webdriver flag (key bot signal)
                context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                page = context.new_page()

                # Use "domcontentloaded" instead of "networkidle" — much faster
                resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                status = resp.status if resp else None

                # Optional: wait briefly for JS to settle without full networkidle
                page.wait_for_timeout(1500)

                html = page.content()
                browser.close()

                if html:
                    return status, html
                return status, None

        except Exception:
            return None, None


    def zyte_fetch_html(self, url: str):
        """
        Zyte as LAST RESORT to save money.
        """
        if not ZYTE_API_KEY:
            return None, None
        payload = {
            "url": url,
            "browserHtml": True,
        }
        ZYTE_ENDPOINT = "https://api.zyte.com/v1/extract"
        try:
            time.sleep(REQUEST_DELAY)
            resp = self.session.post(
                ZYTE_ENDPOINT,
                json=payload,
                auth=(ZYTE_API_KEY, ""),
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("httpResponseStatus") or data.get("statusCode")
            html = data.get("browserHtml") or data.get("httpResponseBody")
            if isinstance(html, str):
                return status, html[:MAX_HTML_CHARS]
            return status, None
        except Exception:
            return None, None
        

    def fetch_main_html(self, url: str):
        """
        Cost-optimized strategy:
        1) Direct requests (free)
        2) Playwright (free but CPU-heavy)
        3) Zyte (paid, last resort)
        """
        # 1) PLAYWRIGHT
        status_pw, html_pw = self.playwright_fetch_html(url)
        if status_pw == 200 and html_pw:
            return status_pw, html_pw
        
        # 2) DIRECT
        status, html = self.direct_fetch_html(url)
        if status == 200 and html:
            # If HTML looks "good enough", use it (save money).
            # Good enough = big enough or clearly has emails/mailtos.
            if (
                len(html) >= HTML_OK_MIN_LEN
                or "mailto:" in html
                or "@" in html
            ):
                return status, html

        # 3) ZYTE (PAID FALLBACK)
        status_z, html_z = self.zyte_fetch_html(url)
        return status_z, html_z

    def find_linkedin_profile(self, email):
        try:
            local_part, domain = email.split("@")
            company = domain.split(".")[0]

            query = f'linkedin.com/in "{local_part}" "{company}" "{email}"'
            url   = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            resp_status, resp_html  = self.fetch_main_html(url)
            if resp_status != 200 or not resp_html:
                logger.warning(f"Failed to fetch results for {email}")

            pairs = []

            def _match(href, snippet):
                clean = "".join(snippet.split()).replace("\xa0", "")
                return (self.is_name_match(local_part, snippet)
                        and company.lower().replace(" ", "") in clean)
            
            if resp_html:
                soup = BeautifulSoup(resp_html, "html.parser")
                for div in soup.find_all(attrs={"data-rpos": True}):
                    div_text = div.get_text(strip=True).lower()
                    for a in div.find_all("a"):
                        href = a.get("href", "")
                        if "linkedin.com/" in href:
                            if href.startswith("/url?q="):
                                href = href.split("/url?q=")[1].split("&")[0]
                            pairs.append((href, div_text))

            urls = list(set(u for u, s in pairs if _match(u, s)))

            if not urls:
                q2  = f'linkedin.com "{local_part}" "{company}" "{email}"'
                ddg = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q2)}"
                # r2  = requests.get(ddg, headers=self.get_dynamic_headers(), timeout=30)
                r2_status, r2_html = self.fetch_main_html(ddg)
                pairs2 = []
                if r2_html:
                    soup2  = BeautifulSoup(r2_html, "html.parser")
                    for a in soup2.find_all("a", class_=["result__url", "result__a"]):
                        href = a.get("href", "")
                        snip = ""
                        nxt  = a.find_next(class_="result__snippet")
                        if nxt:
                            snip = nxt.get_text()
                        if "www.linkedin.com/" in href:
                            clean_href = urllib.parse.unquote(
                                href.split("uddg=")[1].split("&")[0]
                            )
                            pairs2.append((clean_href, snip))
                        elif "linkedin.com/" in href:
                            if href.startswith("/url?q="):
                                href = href.split("/url?q=")[1].split("&")[0]
                            pairs2.append((href, a.get_text(strip=True).lower()))
                urls = list(set(u for u, s in pairs2 if _match(u, s)))

            from ddgs import DDGS
            query = f'linkedin.com {local_part} {company} {email}'
            results = DDGS().text(query, max_results=150)
            rows = []

            QUERY = f"{local_part} {company} {email} linkedin"
            
            for item in results:
                url = item.get("href", "")
                title = item.get("title", "")
                body = item.get("body", "")

                # ✅ filter only profiles
                if "linkedin.com/" not in url:
                    continue

                combined_text = f"{title}"
                ratio = self.compute_ratio(combined_text, QUERY)

                rows.append({
                    "title": title,
                    "url": url,
                    "ratio": round(ratio, 4)
                })

            urls = sorted(rows, key=lambda x: x["ratio"], reverse=True)
            urls = urls[0] if urls else []

            for item in results:
                url = item.get("href", "")

                # ✅ Filter only LinkedIn profiles
                if not self.is_linkedin_profile(url):
                    continue
            logger.debug(f"LinkedIn results for {email}: {urls}")
            return urls

        except Exception as e:
            logger.error(f"LinkedIn search failed for {email}: {e}")
            return []
        
    def is_linkedin_profile(self, url):
        return "linkedin.com/" in url
    
    def clean_title(self, title):
        return re.split(r'\||LinkedIn', title)[0].strip()


    def compute_ratio(self, text, QUERY):
        return SequenceMatcher(None, text.lower(), QUERY.lower()).ratio()

    # ---------------------------------------------------------------
    # Bulk wrapper (legacy)
    # ---------------------------------------------------------------

    def validate_email_bulk(self, email_list):
        results = []
        for email in email_list:
            results.append(self.validate_email(email))
            time.sleep(random.uniform(1.5, 3.0))
        return results