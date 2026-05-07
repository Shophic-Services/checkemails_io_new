"""
scraper/tasks/scrape_batch.py

Processes a batch of DataSourceItem IDs: fetches each URL, extracts
emails & company name, saves results.

Mirrors tools/tasks/validate_batch.py exactly:

  soft_time_limit=82800 (23 h)  → raises SoftTimeLimitExceeded; we catch
                                   it, stamp current + remaining items as
                                   TimedOut, flush to DB, push WebSocket.
  time_limit=86400      (24 h)  → hard kill; always > soft so the graceful
                                   save finishes first.

Both limits are conservative defaults for long-running scrapes.
Tune them for your needs (e.g. soft=300 / hard=360 for fast jobs).
"""

import re
import time
import requests

from urllib.parse import urlparse, urlunparse
from typing import Optional, Tuple

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.db.models import F
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tools.helper.scrape_email import scrape_single_url
from tools.models import DataSourceItem, DataSourceJob, ScraperResult
from tools.websocket import push_scraper_job_update

# ---------------------------------------------------------------------------
# Config (mirrors your standalone script)
# ---------------------------------------------------------------------------

TIMEOUT          = 15
REQUEST_DELAY    = 0.1
MAX_PAGES_PER_SITE = 15
MAX_HTML_CHARS   = 300_000
HTML_OK_MIN_LEN  = 4_000

CANDIDATE_KEYWORDS = [
    "contact", "kontakt", "imprint", "impressum",
    "about", "support", "help", "team", "company",
    "legal", "privacy", "locations",
]

PATTERN = re.compile(
    r"(?:^|[\s\-_/])("
    + "|".join(CANDIDATE_KEYWORDS) +
    r")(?:[\s\-_/]|$)",
    re.IGNORECASE
)

JUNK_PREFIXES = {
    "gif", "img", "logo", "svg", "test",
    "noreply", "no-reply", "example", "sample",
    "webmaster", "mailer-daemon", "donotreply", "do-not-reply",
    "dummy", "placeholder", "filler",
}

JUNK_DOMAINS = {
    "facebook.com", "instagram.com", "linkedin.com",
    "twitter.com", "x.com", "youtube.com", "tiktok.com",
    "godaddy.com",
}

IMAGE_TLDS  = {"png", "jpg", "jpeg", "gif", "svg", "webp", "bmp"}
HEX_LOCAL_RE = re.compile(r"^[0-9a-f]{24,64}$")
TRIM_PUNCT  = '.,;:|/\\[](){}<>"\'\u2013\u2014%'

EMAIL_REGEX = re.compile(
    r"(?<![A-Za-z0-9._%+\-])"
    r"([A-Za-z0-9._%+\-]{1,64}"
    r"@"
    r"[A-Za-z0-9.\-]{1,255}\.[A-Za-z]{2,24})"
    r"(?![A-Za-z0-9._%+\-])"
)

# Zyte (optional, last-resort paid fallback)
from django.conf import settings
ZYTE_API_KEY = settings.ZYTE_API_KEY
ZYTE_ENDPOINT = "https://api.zyte.com/v1/extract"


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

def _make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3, connect=3, read=3, backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=50, pool_maxsize=50)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        )
    })
    return s


_session = _make_session()


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def normalize_url(raw: str) -> Optional[str]:
    if not raw:
        return None
    raw = str(raw).strip().rstrip(").,; \t\n\r").strip("'\"")
    if raw.startswith("//"):
        raw = "http:" + raw
    if raw.lower().startswith("https//"):
        raw = "https://" + raw[7:]
    if raw.lower().startswith("http//"):
        raw = "http://" + raw[6:]
    if raw.lower().startswith("www."):
        raw = "http://" + raw
    if not raw.startswith(("http://", "https://")):
        raw = "http://" + raw
    try:
        p    = urlparse(raw)
        host = (p.netloc or "").strip().lower().lstrip(".").rstrip(".")
        if not host:
            return None
        path = re.sub(r"/+", "/", p.path or "/")
        return urlunparse((p.scheme.lower(), host, path or "/", p.params, p.query, ""))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def _direct_fetch(url: str) -> Tuple[Optional[int], Optional[str]]:
    try:
        time.sleep(REQUEST_DELAY)
        resp = _session.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.status_code, resp.text[:MAX_HTML_CHARS]
    except requests.RequestException:
        return None, None


def _playwright_fetch(url: str) -> Tuple[Optional[int], Optional[str]]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_context().new_page()
            resp    = page.goto(url, wait_until="domcontentloaded", timeout=10000)
            status  = resp.status if resp else None
            html    = page.content()
            browser.close()
            return status, (html[:MAX_HTML_CHARS] if html else None)
    except Exception:
        return None, None


def _zyte_fetch(url: str) -> Tuple[Optional[int], Optional[str]]:
    if not ZYTE_API_KEY:
        return None, None
    try:
        time.sleep(REQUEST_DELAY)
        resp = _session.post(
            ZYTE_ENDPOINT,
            json={"url": url, "browserHtml": True},
            auth=(ZYTE_API_KEY, ""),
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data   = resp.json()
        status = data.get("httpResponseStatus") or data.get("statusCode")
        html   = data.get("browserHtml") or data.get("httpResponseBody")
        return status, (html[:MAX_HTML_CHARS] if isinstance(html, str) else None)
    except Exception:
        return None, None


def fetch_main_html(url: str) -> Tuple[Optional[int], Optional[str]]:
    status, html = _direct_fetch(url)
    if html and (len(html) >= HTML_OK_MIN_LEN or "mailto:" in html):
        return status, html
    status_pw, html_pw = _playwright_fetch(url)
    if html_pw:
        return status_pw, html_pw
    return _zyte_fetch(url)


def fetch_sub_html(url: str) -> Tuple[Optional[int], Optional[str]]:
    """Subpages: direct only (no Playwright / Zyte) to keep cost low."""
    return _direct_fetch(url)



# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@shared_task(
    queue="scraper_worker",
    bind=True,
    acks_late=True,
    soft_time_limit=82800,   # 23 h → raises SoftTimeLimitExceeded → graceful save
    time_limit=86400,        # 24 h → hard kill; always > soft_time_limit
)
def scrape_url_batch_task(self, job_id: str, item_ids: list, user_id: int):
    """
    1. Mark batch INPROGRESS.
    2. For each item: fetch URL, extract emails/company, save ScraperResult rows.
    3. On SoftTimeLimitExceeded: stamp current + remaining as TimedOut, flush, exit.
    4. On any per-item exception: stamp as Error, continue.
    5. Normal exit: flush all counters.
    """

    DataSourceItem.objects.filter(
        id__in=item_ids,
        status=DataSourceItem.PENDING,
    ).update(status=DataSourceItem.INPROGRESS)

    items = list(
        DataSourceItem.objects
        .filter(id__in=item_ids, status=DataSourceItem.INPROGRESS)
        .exclude(source_job__status=DataSourceJob.ERROR)
        .only("id", "input_value")
    )

    if not items:
        return 0

    completed        = 0
    ok_count         = 0
    no_email_count   = 0
    error_count      = 0
    timed_out_count  = 0
    total_emails     = 0   # sum of email rows created

    processed_ids    = set()
    result_rows      = []   # ScraperResult objects to bulk_create at flush

    # ------------------------------------------------------------------
    def _flush(timed_out_item=None):
        """Timeout path only — stamps remaining items and does a final DB + WS sync."""
        nonlocal timed_out_count, completed

        if timed_out_item is not None:
            timed_out_item.result_data = {
                "url":         timed_out_item.input_value,
                "status":      "timed_out",
                "scrape_name": None,
                "emails":      [],
                "error":       "Task time limit exceeded during scrape",
                "http_status": 408,
            }
            timed_out_item.status = DataSourceItem.COMPLETED
            timed_out_count += 1
            completed       += 1
            processed_ids.add(timed_out_item.id)

        remaining_items = [i for i in items if i.id not in processed_ids]
        for remaining in remaining_items:
            remaining.result_data = {
                "url":         remaining.input_value,
                "status":      "timed_out",
                "scrape_name": None,
                "emails":      [],
                "error":       "Batch timed out before this URL was reached",
                "http_status": 408,
            }
            remaining.status = DataSourceItem.COMPLETED
            timed_out_count += 1
            completed       += 1

        if timed_out_item or remaining_items:
            DataSourceItem.objects.bulk_update(
                ([timed_out_item] if timed_out_item else []) + remaining_items,
                ["status", "result_data"],
            )

        if result_rows:
            ScraperResult.objects.bulk_create(result_rows, ignore_conflicts=True)

        DataSourceJob.objects.filter(uuid=job_id).update(
            valid_count=F("valid_count")     + ok_count,
            invalid_count=F("invalid_count") + error_count,
            unknown_count=F("unknown_count") + timed_out_count,
        )

        job = DataSourceJob.objects.get(uuid=job_id)
        push_scraper_job_update(job)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    for item in items:
        try:
            url_norm = normalize_url(item.input_value)
            if not url_norm:
                raise ValueError(f"Invalid URL: {item.input_value!r}")

            scraped = scrape_single_url(url_norm)

            emaildata = sorted(scraped["emails"])
            item.result_data = {
                "url":         item.input_value,
                "final_url":   url_norm,
                "status":      "ok" if not scraped["error"] else "fetch_failed",
                "scrape_name": scraped["scrape_name"],
                "emails":      emaildata,
                "error":       scraped["error"],
                "http_status": scraped["status_code"],
            }
            item.status = DataSourceItem.COMPLETED
            completed  += 1
            processed_ids.add(item.id)

            if scraped["error"]:
                error_count += 1
            elif scraped:
                ok_count     += 1
                total_emails += len(emaildata)
                result_rows.append(
                    ScraperResult(
                        scrape_name=scraped["scrape_name"],
                        source_item=item,
                        source_job_id=job_id,
                        belongs_to_id=user_id,
                        url=item.input_value,
                        final_url=url_norm,
                        emaildata=emaildata,
                        scrapedata=scraped["extract_data_result"],
                        http_status=scraped["status_code"],
                    )
                )
            else:
                no_email_count += 1

            # ✅ Save this item immediately and push WS update
            item.save(update_fields=["status", "result_data"])
            ScraperResult.objects.bulk_create(
                [result_rows[-1]] if result_rows and not scraped["error"] else [],
                ignore_conflicts=True,
            )
            DataSourceJob.objects.filter(uuid=job_id).update(
                valid_count=F("valid_count")     + (1 if not scraped["error"] and scraped else 0),
                invalid_count=F("invalid_count") + (1 if scraped["error"] else 0),
            )
            job = DataSourceJob.objects.get(uuid=job_id)
            push_scraper_job_update(job)

        except SoftTimeLimitExceeded:
            _flush(timed_out_item=item)
            return completed

        except Exception as exc:
            item.result_data = {
                "url":    item.input_value,
                "status": "error",
                "error":  str(exc),
                "emails": [],
            }
            item.status  = DataSourceItem.COMPLETED
            error_count += 1
            completed   += 1
            processed_ids.add(item.id)

            # ✅ Save and push WS on error too
            item.save(update_fields=["status", "result_data"])
            DataSourceJob.objects.filter(uuid=job_id).update(
                invalid_count=F("invalid_count") + 1,
            )
            job = DataSourceJob.objects.get(uuid=job_id)
            push_scraper_job_update(job)

    # Final flush (handles timeout stragglers; no-op on normal exit)
    # _flush()
    return completed