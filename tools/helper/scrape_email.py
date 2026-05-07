
import re
import time
import requests

from html import unescape
from urllib.parse import urlparse, urlunparse, urljoin, unquote
from typing import Optional, Set, List, Tuple

from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tools.models import ScraperResult
from tools.services.ollama_client import decode_cfemail, decode_emails_inplace, extract_with_qwen


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
# Email extraction
# ---------------------------------------------------------------------------

def _is_good_email(e: str) -> bool:
    if not e or "@" not in e:
        return False
    local, domain = e.split("@", 1)
    if HEX_LOCAL_RE.match(local):
        return False
    if any(local.startswith(j) for j in JUNK_PREFIXES):
        return False
    if any(x in local for x in ["dummy", "placeholder", "example", "logo"]):
        return False
    dom = domain.lower()
    if dom in JUNK_DOMAINS or "wixpress.com" in dom:
        return False
    parts = dom.split(".")
    if len(parts) >= 2 and parts[-1] in IMAGE_TLDS:
        return False
    return True


def _trim_email(raw: str) -> Optional[str]:
    if not raw:
        return None
    raw = unquote(raw).strip().strip(TRIM_PUNCT)
    m = EMAIL_REGEX.search(raw)
    if not m:
        return None
    e = m.group(1).lower()
    return e if _is_good_email(e) else None


def extract_emails_from_text(text: str) -> Set[str]:
    if not text:
        return set()
    out = set()
    for m in EMAIL_REGEX.finditer(unescape(text)):
        e = _trim_email(m.group(1))
        if e:
            out.add(e)
    return out


def extract_mailto_emails(html: str) -> Set[str]:
    emails = set()
    for m in re.finditer(r'href=[\'"]mailto:([^\'">]+)', html, re.IGNORECASE):
        e = _trim_email(unquote(m.group(1).split("?", 1)[0]))
        if e:
            emails.add(e)
    return emails

def extract_cf_protected_emails(html: str) -> Set[str]:
    emails = set()

    # pattern for data-cfemail
    matches = re.findall(r'data-cfemail="([0-9a-fA-F]+)"', html)

    for encoded in matches:
        decoded = decode_cfemail(encoded)
        if decoded:
            emails.add(decoded)

    return emails

def guess_candidate_links(base_url: str, soup: BeautifulSoup) -> List[str]:
    base_host = urlparse(base_url).netloc
    links: Set[str] = set()
    for a in soup.find_all("a", href=True):
        text = (a.get_text(strip=True) or "").lower()
        url  = urljoin(base_url, a["href"])
        if urlparse(url).netloc != base_host:
            continue
        if any(k in (text + " " + url.lower()) for k in CANDIDATE_KEYWORDS):
            links.add(url)
        if PATTERN.search(url.lower()):
            links.add(url)
    for slug in ["contact", "kontakt", "impressum", "imprint", "about","contact-us","about-us",'contactus','aboutus']:
        links.add(urljoin(base_url, f"/{slug}"))
    return list(links)[: MAX_PAGES_PER_SITE - 1]


def extract_scrape_name(soup: BeautifulSoup) -> Optional[str]:
    og = soup.find("meta", attrs={"property": "og:site_name"})
    if og and og.get("content"):
        return og["content"].strip()[:255]
    if soup.title and soup.title.string:
        return soup.title.string.strip().split("|")[0][:255]
    return None

def extract_emails_from_html(raw_html: str) -> list[str]:
    emails = set()

    # Method 1: Cloudflare encoded emails
    cf_pattern = r'data-cfemail="([a-fA-F0-9]+)"'
    for match in re.findall(cf_pattern, raw_html):
        try:
            r = int(match[:2], 16)
            email = ''.join(
                chr(int(match[i:i+2], 16) ^ r)
                for i in range(2, len(match), 2)
            )
            emails.add(email)
        except:
            pass

    # Method 2: mailto links
    soup = BeautifulSoup(raw_html, "html.parser")
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("mailto:"):
            email = a["href"].replace("mailto:", "").split("?")[0].strip()
            emails.add(email)

    # Method 3: plain regex (last resort)
    plain = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', raw_html)
    emails.update(plain)

    return list(emails)




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
            resp    = page.goto(url, wait_until="domcontentloaded", timeout=15000)
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
    status_pw, html_pw = _playwright_fetch(url)
    if html_pw:
        return status_pw, html_pw
    status, html = _direct_fetch(url)
    if html and (len(html) >= HTML_OK_MIN_LEN or "mailto:" in html):
        return status, html
    return _zyte_fetch(url)


def fetch_sub_html(url: str) -> Tuple[Optional[int], Optional[str]]:
    """Subpages: direct only (no Playwright / Zyte) to keep cost low."""
    return _direct_fetch(url)



def scrape_single_url(url_norm: str):
    """
    Returns a dict with keys:
      status_code, scrape_name, emails (set), error
    """
    error = None
    website_obj = ScraperResult.without_user.filter(final_url=url_norm).first()
    if website_obj and website_obj.http_status == 200:

        time.sleep(5)
        result_data = website_obj.scrapedata or {}
        return {
            "status_code": website_obj.http_status,
            "scrape_name": website_obj.scrape_name,
            "emails": set(website_obj.emaildata or []),
            "extract_data_result": result_data or [],
            "error": error,
        }
    status_code, html = fetch_main_html(url_norm)

    if not html:
        return {"status_code": status_code, "scrape_name": None, "emails": set(), "extract_data_result": [], "error": "Fetch failed"}

    soup    = BeautifulSoup(html, "html.parser")
    soup = decode_emails_inplace(soup)  # Decode Cloudflare emails directly in the soup for better extraction
    extract_data_result, error = [], '' #extract_with_qwen(html, url_norm)  # Use raw HTML for extraction to leverage Qwen's pattern recognition, but decode CF emails in the soup for better email extraction below
    emails  = extract_emails_from_text(html) | extract_mailto_emails(html) | extract_cf_protected_emails(html)
    company = extract_scrape_name(soup)

    for link in guess_candidate_links(url_norm, soup):
        _, sub_html = fetch_sub_html(link)
        if sub_html:
            # extract_data_result |= extract_with_qwen(sub_html)
            emails |= extract_emails_from_text(sub_html) | extract_mailto_emails(sub_html) | extract_cf_protected_emails(sub_html)

    emails = {e for e in emails if _is_good_email(e)}
    return {"status_code": status_code, "scrape_name": company, "emails": emails, "extract_data_result": extract_data_result, "error": error}
