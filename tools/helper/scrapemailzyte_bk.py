import os
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from html import unescape
from urllib.parse import urlparse, urlunparse, urljoin, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Tuple, List, Set, Dict

# ========= CONFIG =========
INPUT_XLSX = "/home/sophic/Python/excel-generator/scripts/input/inputemails.xlsx"
OUTPUT_XLSX = "/home/sophic/Python/excel-generator/scripts/input/outputemails.xlsx"

MAX_WORKERS = 12          # concurrency
TIMEOUT = 15              # slightly lower to avoid hanging too long
REQUEST_DELAY = 0.1       # shorter delay for speed
MAX_PAGES_PER_SITE = 15    # main page + up to 2 internal pages
MAX_HTML_CHARS = 300_000  # don't scan unlimited HTML

HTML_OK_MIN_LEN = 4000    # if direct HTML shorter than this, we consider it "maybe JS / weak"

# how often to checkpoint (in number of websites processed)
CHECKPOINT_EVERY = 20

# Zyte Extract API (used ONLY as last resort)
from django.conf import settings
ZYTE_API_KEY = settings.ZYTE_API_KEY
ZYTE_ENDPOINT = "https://api.zyte.com/v1/extract"

CANDIDATE_KEYWORDS = [
    "contact", "kontakt", "imprint", "impressum",
    "about", "support", "help", "team", "company",
    "legal", "privacy", "locations"
]

# Junk we never want as emails
JUNK_PREFIXES = {
    'gif', 'img', 'logo', 'svg', 'test',
    'noreply', 'no-reply', 'example', 'sample',
    'webmaster', 'mailer-daemon', 'donotreply', 'do-not-reply',
    'dummy', 'placeholder', 'filler'
}
JUNK_DOMAINS = {
    'facebook.com', 'instagram.com', 'linkedin.com',
    'twitter.com', 'x.com', 'youtube.com', 'tiktok.com',
    'godaddy.com'  # system / registrar emails
}
IMAGE_TLDS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'bmp'}

# hex-like random locals (for sentry / wix / system ids)
HEX_LOCAL_RE = re.compile(r'^[0-9a-f]{24,64}$')

# ===== STRICT EMAIL REGEX =====
EMAIL_REGEX = re.compile(
    r'(?<![A-Za-z0-9._%+\-])'
    r'([A-Za-z0-9._%+\-]{1,64}'
    r'@'
    r'[A-Za-z0-9.\-]{1,255}\.[A-Za-z]{2,24})'
    r'(?![A-Za-z0-9._%+\-])'
)

TRIM_PUNCT = '.,;:|/\\[](){}<>"\'\u2013\u2014%'  # includes % to trim %20sales@

# ========= EXCEL STRING SANITIZER =========
# Remove illegal control characters that Excel / openpyxl cannot handle
ILLEGAL_EXCEL_CHARS_RE = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]")


def clean_for_excel(value):
    if isinstance(value, str):
        return ILLEGAL_EXCEL_CHARS_RE.sub("", value)
    return value

# ========= SESSIONS =========
def make_retry_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3, connect=3, read=3, backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({
        'User-Agent': (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        )
    })
    return s


session = make_retry_session()

# ========= URL UTILITIES =========
def normalize_url(raw: str) -> Optional[str]:
    """
    Accepts:
      - https://www.example.com
      - https://example.com
      - http://example.com
      - www.example.com
      - example.com
      - //example.com
    and normalizes to: http://host/path
    """
    if not raw:
        return None

    # convert non-string (NaN, numbers) to str
    raw = str(raw)

    # strip whitespace + some trailing punctuation
    raw = raw.strip().rstrip(').,; \t\n\r')

    if not raw:
        return None

    # remove any surrounding quotes
    raw = raw.strip('\'"')

    # handle protocol-relative: //example.com
    if raw.startswith("//"):
        raw = "http:" + raw

    # fix common typo "https//example.com"
    if raw.lower().startswith("https//"):
        raw = "https://" + raw[7:]
    if raw.lower().startswith("http//"):
        raw = "http://" + raw[6:]

    # if starts with www. add scheme
    if raw.lower().startswith("www."):
        raw = "http://" + raw

    # if still no scheme, assume http
    if not raw.startswith(("http://", "https://")):
        raw = "http://" + raw

    try:
        p = urlparse(raw)
        host = (p.netloc or "").strip().lower().lstrip('.')
        if not host:
            return None
        while host.endswith('.'):
            host = host[:-1]
        # normalize path: at least "/"
        path = re.sub(r'/+', '/', p.path or '/')
        return urlunparse((p.scheme.lower(), host, path or '/', p.params, p.query, ''))
    except Exception:
        return None

# ========= FETCH HELPERS =========
def direct_fetch_html(url: str) -> Tuple[Optional[int], Optional[str]]:
    try:
        time.sleep(REQUEST_DELAY)
        resp = session.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        html = resp.text[:MAX_HTML_CHARS]
        return resp.status_code, html
    except requests.RequestException:
        return None, None


def playwright_fetch_html(url: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Headless browser fetch using Playwright.
    Used ONLY when direct HTML looks weak or fails.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        # Playwright not installed
        return None, None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            resp = page.goto(url, wait_until="networkidle", timeout=TIMEOUT * 1000)
            status = resp.status if resp else None
            html = page.content()
            browser.close()
            if html:
                return status, html[:MAX_HTML_CHARS]
            return status, None
    except Exception:
        return None, None


def zyte_fetch_html(url: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Zyte as LAST RESORT to save money.
    """
    if not ZYTE_API_KEY:
        return None, None
    payload = {
        "url": url,
        "browserHtml": True,
    }
    try:
        time.sleep(REQUEST_DELAY)
        resp = session.post(
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


def fetch_main_html(url: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Cost-optimized strategy:
      1) Direct requests (free)
      2) Playwright (free but CPU-heavy)
      3) Zyte (paid, last resort)
    """
    # 1) DIRECT
    status, html = direct_fetch_html(url)
    if html:
        # If HTML looks "good enough", use it (save money).
        # Good enough = big enough or clearly has emails/mailtos.
        if (
            len(html) >= HTML_OK_MIN_LEN
            or "mailto:" in html
            or "@" in html
        ):
            return status, html

    # 2) PLAYWRIGHT
    status_pw, html_pw = playwright_fetch_html(url)
    if html_pw:
        return status_pw, html_pw

    # 3) ZYTE (PAID FALLBACK)
    status_z, html_z = zyte_fetch_html(url)
    return status_z, html_z


def fetch_sub_html(url: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Subpages: we keep them CHEAP.
    - Only direct requests (no Playwright, no Zyte) to control cost.
    """
    return direct_fetch_html(url)

# ========= EMAILS =========
def is_good_email(e: str) -> bool:
    """Filter out logos, dummy emails, image filenames, social emails, etc."""
    if not e:
        return False
    e = e.strip().lower()
    if "@" not in e:
        return False

    local, domain = e.split("@", 1)
    local = local.strip()
    domain = domain.strip()

    # hex-like random ids (e.g. sentry/wix)
    if HEX_LOCAL_RE.match(local):
        return False

    # junk prefixes
    for junk in JUNK_PREFIXES:
        if local.startswith(junk):
            return False

    # dummy-like patterns
    if any(x in local for x in ["dummy", "placeholder", "example", "logo", "@2x", "_small", "_large"]):
        return False

    # domain filters
    dom_lower = domain.lower()
    if dom_lower in JUNK_DOMAINS:
        return False
    if "wixpress.com" in dom_lower:
        return False

    # image-like TLDs
    parts = domain.split(".")
    if len(parts) >= 2:
        tld = parts[-1]
        if tld in IMAGE_TLDS:
            return False

    return True


def trim_email(e: str) -> Optional[str]:
    if not e:
        return None

    # decode URL encoded crap like %20sales@...
    e = unquote(e)

    # strip whitespace + punctuation around
    e = e.strip().strip(TRIM_PUNCT)

    m = EMAIL_REGEX.search(e)
    if not m:
        return None
    email = m.group(1).lower()
    return email if is_good_email(email) else None


def extract_emails_from_text(text: str) -> Set[str]:
    if not text:
        return set()
    text = unescape(text)
    out = set()
    for m in EMAIL_REGEX.finditer(text):
        e = trim_email(m.group(1))
        if e:
            out.add(e)
    return out


def extract_mailto_emails_from_html(html: str) -> Set[str]:
    emails = set()
    # lightweight mailto parsing: regex instead of full soup
    for m in re.finditer(r'href=[\'"]mailto:([^\'">]+)', html, flags=re.IGNORECASE):
        addr = m.group(1).split('?', 1)[0]
        # decode URL encoding BEFORE trimming
        addr = unquote(addr)
        e = trim_email(addr)
        if e:
            emails.add(e)
    return emails

# ========= PAGE MINING (ONLY FOR EMAILS) =========
def guess_candidate_links(base_url: str, soup: BeautifulSoup) -> List[str]:
    """Pick a few internal pages likely to have contact info."""
    links = set()
    base_host = urlparse(base_url).netloc
    for a in soup.find_all('a', href=True):
        text = (a.get_text(strip=True) or "").lower()
        href = a['href']
        url = urljoin(base_url, href)
        if urlparse(url).netloc != base_host:
            continue
        target = (text + " " + url.lower())
        if any(k in target for k in CANDIDATE_KEYWORDS):
            links.add(url)
    # canonical guesses
    for slug in ["contact", "kontakt", "impressum", "imprint", "about"]:
        links.add(urljoin(base_url, f"/{slug}"))
    # keep tiny for speed
    return list(links)[:MAX_PAGES_PER_SITE - 1]


def extract_scrape_name(soup: BeautifulSoup) -> Optional[str]:
    og = soup.find('meta', attrs={'property': 'og:site_name'})
    if og and og.get('content'):
        return og['content'].strip()[:255]
    if soup.title and soup.title.string:
        return soup.title.string.strip().split("|")[0][:255]
    return None

# ========= CORE WORKER =========
def process_site(idx: int, total: int, raw_url: str) -> List[dict]:
    url_norm = normalize_url(raw_url)
    print(f"[{idx}/{total}] Processing: {raw_url}")
    if not url_norm:
        return [{
            "Website": raw_url,
            "FinalURL": None,
            "Status": "Invalid URL",
            "HTTPStatus": None,
            "CompanyName": None,
            "Email": None,
            "SourceURL": None
        }]

    status_code, html = fetch_main_html(url_norm)
    if not html:
        print(f"[{idx}/{total}] Failed: {raw_url}")
        return [{
            "Website": raw_url,
            "FinalURL": url_norm,
            "Status": "Fetch failed",
            "HTTPStatus": status_code,
            "CompanyName": None,
            "Email": None,
            "SourceURL": url_norm
        }]

    # MAIN PAGE: soup once
    soup = BeautifulSoup(html, "html.parser")

    emails = extract_emails_from_text(html) | extract_mailto_emails_from_html(html)
    scrape_name = extract_scrape_name(soup)

    # SUBPAGES: contact/imprint/about etc via direct requests (cheap)
    for link in guess_candidate_links(url_norm, soup):
        sc, sub_html = fetch_sub_html(link)
        if not sub_html:
            continue
        emails |= extract_emails_from_text(sub_html) | extract_mailto_emails_from_html(sub_html)

    emails = {e for e in emails if is_good_email(e)}

    print(f"[{idx}/{total}] Finished: {raw_url} ✅  ({len(emails)} emails)")

    if not emails:
        return [{
            "Website": raw_url,
            "FinalURL": url_norm,
            "Status": "No emails found",
            "HTTPStatus": status_code,
            "CompanyName": scrape_name,
            "Email": None,
            "SourceURL": url_norm
        }]

    rows = []
    for e in sorted(emails):
        rows.append({
            "Website": raw_url,
            "FinalURL": url_norm,
            "Status": "OK",
            "HTTPStatus": status_code,
            "CompanyName": scrape_name,
            "Email": e,
            "SourceURL": url_norm
        })
    return rows

# ========= IO HELPERS =========
def load_seed_urls_from_excel() -> List[str]:
    if not os.path.exists(INPUT_XLSX):
        print(f"❌ Input file not found: {INPUT_XLSX}")
        return []
    df = pd.read_excel(INPUT_XLSX)
    # be a bit forgiving with column name spacing/case
    col_candidates = [c for c in df.columns if str(c).strip().lower() == "website"]
    if not col_candidates:
        raise ValueError("Input Excel must have a 'Website' column (case-insensitive).")
    col = col_candidates[0]
    return [v for v in df[col].dropna().tolist()]


def join_non_null_unique(series: pd.Series) -> str:
    seen, out = set(), []
    for v in series:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                continue
            v = clean_for_excel(v)   # clean aggregator strings too
            if v not in seen:
                seen.add(v)
                out.append(v)
    return "; ".join(out)


def write_results(results: List[dict], out_xlsx: str, is_checkpoint: bool = False):
    if not results:
        return
    df = pd.DataFrame(results)

    # Clean illegal characters in ALL string cells for flat sheet
    # (use Series.map via DataFrame.apply to avoid applymap deprecation)
    flat_df = df.apply(lambda col: col.map(clean_for_excel))

    grouped = (
        df.groupby(
            ["Website", "FinalURL", "Status", "HTTPStatus", "CompanyName"],
            dropna=False,
            as_index=False
        )
        .agg({"Email": join_non_null_unique})
    )

    # Also clean grouped data using Series.map
    grouped = grouped.apply(lambda col: col.map(clean_for_excel))

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        flat_df.to_excel(w, index=False, sheet_name="emails_flat")
        grouped.to_excel(w, index=False, sheet_name="by_site")

    if is_checkpoint:
        print(f"💾 Checkpoint saved: {len(flat_df)} rows -> {out_xlsx}")
    else:
        print(f"\n✅ Final write: {len(flat_df)} rows to {out_xlsx}")

# ========= BULK DRIVER WITH CHECKPOINTS =========
def fetch_emails_bulk(urls: List[str], out_xlsx: str, checkpoint_every: int = CHECKPOINT_EVERY) -> List[dict]:
    all_rows: List[dict] = []
    clean_urls = [str(u).strip() for u in urls if u and str(u).strip()]
    total = len(clean_urls)
    processed = 0

    if total == 0:
        return all_rows

    print(f"🚀 Starting scrape for {total} sites (checkpoint every {checkpoint_every} sites)")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process_site, i + 1, total, u): u for i, u in enumerate(clean_urls)}
        for fut in as_completed(futures):
            site = futures[fut]
            processed += 1
            try:
                rows = fut.result()
                all_rows.extend(rows)
            except Exception as e:
                print(f"[ERROR] {site}: {e}")
                all_rows.append({
                    "Website": site,
                    "FinalURL": None,
                    "Status": f"Error: {e}",
                    "HTTPStatus": None,
                    "CompanyName": None,
                    "Email": None,
                    "SourceURL": None
                })

            # checkpoint after every N processed sites
            if checkpoint_every > 0 and processed % checkpoint_every == 0:
                try:
                    write_results(all_rows, out_xlsx, is_checkpoint=True)
                except Exception as we:
                    print(f"[WARN] Failed to write checkpoint: {we}")

    return all_rows

# ========= MAIN =========1zxc
if __name__ == "__main__":
    sites = load_seed_urls_from_excel()
    if not sites:
        exit(0)
    results = fetch_emails_bulk(sites, OUTPUT_XLSX, CHECKPOINT_EVERY)
    # final write (will overwrite last checkpoint with full data)
    write_results(results, OUTPUT_XLSX, is_checkpoint=False)
