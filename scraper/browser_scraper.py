"""
scraper/browser_scraper.py — Stealth browser + requests-based PDF extractor.

KEY DESIGN PRINCIPLE:
  This module is called with specific page URLs found via web search.
  It extracts PDF links that are ACTUAL question papers — not admin docs.

Strategies (in order):
  1. Scrapling StealthyFetcher for JS-heavy pages
  2. Plain requests + regex fallback for simple pages

All results are filtered through is_question_paper_pdf() to reject
notifications, advisories, recruitment notices, etc.
"""

from __future__ import annotations

import re
import asyncio
import warnings
from urllib.parse import urljoin, urlparse
from loguru import logger
from urllib3.exceptions import InsecureRequestWarning

from config import SITE_SELECTORS, SITE_REGISTRY
import tldextract

# Suppress noisy library warnings
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="lxml")
warnings.filterwarnings("ignore", message=".*Brotli.*")


# ─── Question Paper Relevance Filter ─────────────────────────────────────────
#
# This is the most important piece. We only accept PDFs whose URL/filename
# suggests they are actual exam question papers.

# ─── Question Paper Relevance Filter ─────────────────────────────────────────

_QP_POSITIVE_PATTERNS = [
    r"question[-_\s]?paper",
    r"prev(?:ious)?[-_\s]?year",
    r"\bpyq\b",
    r"general[-_\s]?studies",
    r"\bgs[-_\s]?paper\d?\b",
    r"\bcsat\b",
    r"prelim",
    r"mains?[-_\s]?paper",
    r"memory[-_\s]?based",
    r"solved[-_\s]?paper",
    r"exam[-_\s]?paper",
    r"practice[-_\s]?paper",
    r"sample[-_\s]?paper",
    r"solved",
    r"mock[-_\s]?(?:online)?[-_\s]?paper",
    r"\bqp\b",
    r"shift[-_\s]?\d",
    r"paper[-_\s]?\d",
    r"set[-_\s]?[a-d]\b",
    r"english\.(pdf|PDF)",
    r"hindi\.(pdf|PDF)",
]

_QP_NEGATIVE_PATTERNS = [
    r"advisory",
    r"notification",
    r"iso[-_]ibps",
    r"sop[-_]",
    r"circular",
    r"recruitment",
    r"admit[-_]?card",
    r"call[-_]?letter",
    r"result",
    r"syllabus",
    r"cut[-_]?off",
    r"answer[-_]?key",
    r"vacancy",
    r"schedule",
    r"calendar",
    r"press[-_]?release",
    r"notice",
    r"policy",
    r"guidelines",
    r"format",
    r"application",
    r"exam[-_]?(?:kit|tips|material|strategy|pattern|analysis|analysis-shift|syllabus-and-exam-pattern|overview)",
    r"batches",
    r"course",
    r"foundation",
    r"free[-_]?pdf",
    r"ebook",
    r"book",
    r"study[-_]?material",
    r"notes",
    r"current[-_]?affairs",
    r"gk[-_]?digest",
    r"test[-_]?series",
    r"mock[-_]?test",     # Actual online mock tests, not PDFs
]

_QP_POS_RE = [re.compile(p, re.I) for p in _QP_POSITIVE_PATTERNS]
_QP_NEG_RE = [re.compile(p, re.I) for p in _QP_NEGATIVE_PATTERNS]


def _extract_years(text: str) -> list[str]:
    """Find all 4-digit years between 2010 and 2030."""
    return re.findall(r"\b(20[12]\d)\b", text)


def is_question_paper_pdf(url: str, exam: str = "", year: int = 0, context: str = "", page_url: str = "") -> bool:
    """
    Return True if the URL looks like a genuine question paper PDF.
    Rules:
    1. Must end in .pdf OR be a Google Drive download link
    2. Must NOT match any rejection patterns in URL or context
    3. If year is provided, NO OTHER year (2010-2030) must be present in URL, context or page_url.
    4. Must match a positive pattern in URL, context, or filename.
    """
    url_lower = url.lower()
    url_no_qs = url_lower.split("?")[0]
    ctx_lower = context.lower()
    page_lower = page_url.lower()
    
    # Combined context for scanning signals
    combined = f"{url_lower} {ctx_lower} {page_lower}"

    # 1. Format check
    # Avoid social sharing links (often contain "pdf" or "download" in the text)
    SOCIAL_DOMAINS = ["whatsapp.com", "facebook.com", "twitter.com", "telegram.me", "plus.google.com", "linkedin.com", "pinterest.com"]
    if any(sd in url_lower for sd in SOCIAL_DOMAINS):
        return False

    # Relaxed: Allow non-pdf extensions if the domain is trusted OR context is strong
    is_pdf_ext = url_no_qs.endswith(".pdf") or "drive.google.com/uc" in url_lower
    
    # Check for trusted download patterns (e.g. /download-pdf-..., /pdf-link/...)
    has_download_hint = any(h in url_lower for h in ["download", "pdf", "get-link", "view-paper"])
    is_trusted = any(d in url_lower for d in ["prepp.in", "testbook.com", "adda247.com", "careerpower.in", "bankersadda.com", "cracku.in"])
    
    if not is_pdf_ext:
        # If not .pdf, only allow if it's a trusted site AND has a download hint
        if not (is_trusted and has_download_hint):
            return False

    # 2. Hard reject on negative keywords
    if any(neg.search(combined) for neg in _QP_NEG_RE):
        return False

    # 3. YEAR CHECK
    if year:
        target_year_str = str(year)
        # Find all 4-digit years in combined context (URL + link text + page title)
        years_found = _extract_years(combined)
        
        # If the target year is found, we proceed! 
        # (We no longer reject if OTHER years are also mentioned on the same page, 
        # as these "Mega Pages" list all years together.)
        has_target_year = target_year_str in combined
        
        # Heuristic: If target year is 2023, also look for " 23 " or "-23" 
        short_year = target_year_str[2:]
        if not has_target_year:
            if re.search(rf"[^0-9]{short_year}[^0-9]", combined):
                has_target_year = True
        
        if not has_target_year:
            return False
    else:
        has_target_year = True # Ignore year

    # 4. Final verification: Positive signals (Question Paper, PYQ, etc.)
    has_pos = any(pos.search(combined) for pos in _QP_POS_RE)
    
    # Check exam name match
    exam_words = [w.lower() for w in exam.split() if len(w) > 2]
    has_exam_name = exam_words and sum(1 for w in exam_words if w in combined) >= 1

    if year:
        # Require target year match + some indicator it's a question paper
        return has_target_year and (has_pos or has_exam_name)
    
    return has_pos or has_exam_name


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _full_domain(url: str) -> str:
    ext = tldextract.extract(url)
    return f"{ext.domain}.{ext.suffix}"


def _score_url(url: str, exam: str, year: int) -> int:
    """Score a candidate PDF URL for relevance (higher = better)."""
    u = url.lower()
    score = 0

    year_str = str(year) if year else ""
    other_years = [str(y) for y in range(2010, 2030) if str(y) != year_str]

    if year_str and year_str in url:
        score += 200
    if any(neg.search(u) for neg in _QP_NEG_RE):
        score -= 500
    if any(pos.search(u) for pos in _QP_POS_RE):
        score += 100

    exam_words = [w.lower() for w in exam.split() if len(w) > 2]
    if exam_words:
        matched = sum(1 for w in exam_words if w in u)
        score += matched * 30

    if any(y in url for y in other_years):
        score -= 80  # Penalise wrong-year links

    if "prelim" in u:
        score += 20
    if "mains" in u or "main" in u:
        score += 20
    if "english" in u:
        score += 10

    return score


def _filter_and_rank(urls: list[str], exam: str, year: int) -> list[str]:
    """Filter to question papers only, then rank by relevance."""
    filtered = [u for u in urls if is_question_paper_pdf(u, exam, year)]
    if not filtered:
        return []
    ranked = sorted(set(filtered), key=lambda u: _score_url(u, exam, year), reverse=True)
    return ranked


def _extract_from_html(html: str, base_url: str) -> set[str]:
    """Extract all PDF-like URLs from raw HTML."""
    found: set[str] = set()

    # href ending in .pdf
    found.update(re.findall(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', html, re.I))

    # Full http URLs containing .pdf
    found.update(re.findall(
        r'["\']?(https?://[^"\'<>\s]+\.pdf(?:\?[^"\'<>\s]*)?)["\']?', html, re.I
    ))

    # Google Drive /d/<id> patterns
    for fid in re.findall(r'/d/([A-Za-z0-9_-]{25,})', html):
        found.add(f"https://drive.google.com/uc?export=download&id={fid}")

    # Resolve relative to absolute
    resolved = set()
    for h in found:
        h = h.strip()
        if not h:
            continue
        if h.startswith("http"):
            resolved.add(h)
        else:
            resolved.add(urljoin(base_url, h))

    return resolved


# ─── Build Tier 0 Slug URL ────────────────────────────────────────────────────

def build_tier0_url(site_key: str, exam: str, year: int = 0) -> str | None:
    """
    Return the specific exam question-paper index page for a portal.
    If the slug has a {year} placeholder, it formats it.
    Returns None if we don't have a known slug.
    """
    registry = SITE_REGISTRY.get(site_key, {})
    slug_template = registry.get(exam)
    if not slug_template:
        return None

    # Format the slug if it's a year-specific template
    if year and "{year}" in slug_template:
        slug = slug_template.format(year=year)
    else:
        # If it's a template but no year provided, or it's a static slug
        slug = slug_template.replace("{year}", "previous-year") 

    templates = {
        "testbook":    f"https://testbook.com/{slug}",
        "adda247":     f"https://www.adda247.com/{slug}/",
        "careerpower": f"https://www.careerpower.in/{slug}",
        "prepp":       f"https://prepp.in/{slug}",
        "cracku":      f"https://cracku.in/{slug}",
        "bankersadda": f"https://www.bankersadda.com/{slug}/",
        "oliveboard":  f"https://www.oliveboard.in/{slug}/",
    }
    return templates.get(site_key)


# ─── Scrapling Async Fetch ────────────────────────────────────────────────────

async def _scrapling_fetch(url: str, exam: str, year: int) -> list[str]:
    """Fetch a page using Scrapling StealthyFetcher and extract PDF links."""
    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError:
        logger.warning("scrapling not installed — skipping stealth fetch")
        return []

    logger.debug(f"Scrapling → {url}")
    try:
        page = await StealthyFetcher.async_fetch(
            url,
            disable_resources=True,
            wait_until="domcontentloaded",
        )
    except Exception as exc:
        logger.debug(f"StealthyFetcher failed for {url}: {exc}")
        return []

    found_with_text: dict[str, str] = {} # href -> anchor text

    # 1. All anchor hrefs + their text
    try:
        for a in page.css("a"):
            href = a.attrib.get("href", "")
            if href and href.strip():
                h = urljoin(url, href.strip())
                # Accumulate text for the same href
                text = a.text.strip() if hasattr(a, 'text') else ""
                
                # SENSITIVE CONTEXT GRAB:
                # If text is generic (like "Download" or "Click Here"), 
                # grab text from the parent (the table cell or row)
                if len(text) < 15 or any(kw in text.lower() for kw in ["download", "click", "here", "pdf"]):
                    try:
                        # Grab text from parent, grandparent, or preceding header
                        # This captures year headers like "IBPS Clerk 2020" from nearby <td>s or <h2>s
                        parent_text = a.parent.text if a.parent else ""
                        text = f"{text} {parent_text}"[:300]
                    except:
                        pass
                
                found_with_text[h] = found_with_text.get(h, "") + " " + text
    except Exception:
        pass

    # 2. Site-specific CSS selectors
    try:
        domain = _full_domain(url)
        selector = SITE_SELECTORS.get(domain, SITE_SELECTORS["default"])
        for a in page.css(selector):
            href = a.attrib.get("href", "")
            if href and href.strip():
                h = urljoin(url, href.strip())
                text = a.text.strip() if hasattr(a, 'text') else ""
                found_with_text[h] = found_with_text.get(h, "") + " " + text
    except Exception:
        pass

    # --- Filtering Logic with Context ---
    final_links = []
    
    for href, anchor_text in found_with_text.items():
        if is_question_paper_pdf(href, exam, year, context=anchor_text, page_url=url):
            final_links.append(href)

    # 3. Handle hidden links found in JS/HTML
    try:
        raw_html = page.text if hasattr(page, "text") else str(page)
        hidden = _extract_from_html(raw_html, url)
        for h in hidden:
            if h not in found_with_text and is_question_paper_pdf(h, exam, year, page_url=url):
                final_links.append(h)
    except Exception:
        pass

    result = _filter_and_rank(list(set(final_links)), exam, year)
    logger.info(f"Scrapling → {len(result)} question-paper PDFs from {url}")
    return result


# ─── Requests Fallback ────────────────────────────────────────────────────────

def _requests_fetch(url: str, exam: str, year: int) -> list[str]:
    """Plain requests fallback — filter to question-paper PDFs only."""
    import requests
    from scraper.anti_detect import build_headers

    logger.debug(f"Requests fallback → {url}")
    try:
        resp = requests.get(
            url,
            headers=build_headers(referer="https://www.google.com/"),
            timeout=20,
            verify=False,
            allow_redirects=True,
        )
        resp.raise_for_status()
        html = resp.text
    except Exception as exc:
        logger.debug(f"Requests fallback failed for {url}: {exc}")
        return []

    found = _extract_from_html(html, url)
    result = []
    for h in found:
        if is_question_paper_pdf(h, exam, year):
            result.append(h)
    
    result = _filter_and_rank(result, exam, year)
    logger.info(f"Requests fallback → {len(result)} question-paper PDFs from {url}")
    return result


# ─── Public API ───────────────────────────────────────────────────────────────

def extract_pdf_links(url: str, exam: str = "", year: int = 0) -> list[str]:
    """
    Extract genuine question-paper PDF links from `url`.

    Returns a filtered, ranked list of PDF URLs that are actual exam papers.
    Non-question PDFs (notifications, advisories, etc.) are excluded.
    """
    parsed = urlparse(url)
    # If the URL itself IS a PDF, check relevance first
    if parsed.path.lower().endswith(".pdf"):
        if is_question_paper_pdf(url, exam, year):
            return [url]
        else:
            logger.debug(f"Rejected direct PDF (not a question paper): {url}")
            return []

    # ── Try Scrapling ──────────────────────────────────────────────────────
    links: list[str] = []
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, _scrapling_fetch(url, exam, year))
                    links = future.result(timeout=60)
            else:
                links = loop.run_until_complete(_scrapling_fetch(url, exam, year))
        except RuntimeError:
            links = asyncio.run(_scrapling_fetch(url, exam, year))
    except Exception as exc:
        logger.debug(f"Async fetch wrapper failed for {url}: {exc}")

    # ── Plain requests fallback ────────────────────────────────────────────
    if not links:
        links = _requests_fetch(url, exam, year)

    return list(dict.fromkeys(links))  # Final dedup
