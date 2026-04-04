"""
scraper/search_agent.py — Aggressive multi-engine search for exam paper URLs.

Strategy:
  - Runs multiple targeted query variants (DuckDuckGo primary)
  - Each query variant targets different keyword combinations
  - Falls back to Bing if DDG yields < 5 results
  - Collects MAX_SEARCH_RESULTS unique, unblocked URLs
"""

from __future__ import annotations
import warnings
from urllib3.exceptions import InsecureRequestWarning

# Suppress noisy library warnings
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="lxml")
warnings.filterwarnings("ignore", message=".*Brotli.*")

import re
import time
import urllib.parse
from loguru import logger

from config import MAX_SEARCH_RESULTS, BLOCKED_DOMAINS, EXAM_SOURCE_MAP


# ─── Query Builder ─────────────────────────────────────────────────────────────

def build_queries(exam_name: str, year: int) -> list[str]:
    """
    Generate diverse search queries to maximise PDF discovery.
    Combines filetype hints, site-specific operators, and keyword variations.
    """
    mapping = EXAM_SOURCE_MAP.get(exam_name, {})
    full_name = mapping.get("full_name", exam_name)
    official = mapping.get("official", "")

    # Core short name (e.g. "IBPS Clerk" → ibps clerk)
    short = exam_name.lower()

    queries = [
        # 1. Direct filetype:pdf — most likely to find raw PDFs
        f'"{exam_name}" {year} question paper filetype:pdf',

        # 2. Site-restricted to top exam portals
        f'{exam_name} {year} previous year question paper pdf site:testbook.com OR site:adda247.com OR site:cracku.in OR site:prepp.in',

        # 3. Full name with year
        f'"{full_name}" {year} question paper PDF download',

        # 4. PYQ / solved paper keyword
        f'{exam_name} {year} PYQ solved paper pdf download',

        # 5. Prelims + Mains variant
        f'{exam_name} {year} prelims mains question paper pdf',

        # 6. Official site search
        f'{exam_name} {year} question paper site:{official}' if official else f'{exam_name} {year} official question paper pdf',

        # 7. "Previous year" keyword variant
        f'{exam_name} previous year {year} paper pdf -youtube -instagram -facebook',

        # 8. Broad download variant
        f'download {short} {year} question paper pdf',
    ]
    return queries


# ─── DuckDuckGo Search ─────────────────────────────────────────────────────────

def _search_duckduckgo(query: str, max_results: int = MAX_SEARCH_RESULTS) -> list[dict]:
    """Search DuckDuckGo using the latest ddgs pattern."""
    try:
        from duckduckgo_search import DDGS
        # The latest version recommends using the context manager or simply ddgs.text()
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]
        logger.debug(f"DDG '{query[:60]}' → {len(results)} results")
        return results
    except Exception as exc:
        # Check if the error is just the rename warning (already suppressed but just in case)
        if "renamed to ddgs" in str(exc).lower():
            try:
                import ddgs
                with ddgs.DDGS() as d:
                    results = [r for r in d.text(query, max_results=max_results)]
                return results
            except:
                pass
        logger.warning(f"DuckDuckGo failed: {exc}")
        return []


# ─── Bing Scrape Fallback ──────────────────────────────────────────────────────

def _search_bing(query: str, max_results: int = 15) -> list[dict]:
    """Scrape Bing search results using requests + regex."""
    import requests
    from scraper.anti_detect import build_headers

    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.bing.com/search?q={encoded}&count={max_results}"
        resp = requests.get(url, headers=build_headers(), timeout=15, verify=False)
        resp.raise_for_status()

        # Extract hrefs from Bing result anchors
        hrefs = re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>', resp.text)
        # Filter out Bing's own internal/tracking links
        clean = [h for h in hrefs if "bing.com" not in h and "microsoft.com" not in h]

        results = [{"title": "", "href": h, "body": ""} for h in clean[:max_results]]
        logger.debug(f"Bing '{query[:60]}' → {len(results)} results")
        return results
    except Exception as exc:
        logger.warning(f"Bing search failed: {exc}")
        return []


# ─── Google Scrape Fallback ────────────────────────────────────────────────────

def _search_google(query: str, max_results: int = 10) -> list[dict]:
    """Scrape Google search results as last resort."""
    import requests
    from scraper.anti_detect import build_headers

    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={encoded}&num={max_results}"
        headers = build_headers(referer="https://www.google.com/")
        resp = requests.get(url, headers=headers, timeout=15, verify=False)
        resp.raise_for_status()

        # Extract result links (Google wraps real URLs in /url?q=<url>)
        raw_links = re.findall(r'/url\?q=(https?://[^&"<\s]+)', resp.text)
        clean = [urllib.parse.unquote(h) for h in raw_links
                 if "google.com" not in h and "webcache" not in h]

        results = [{"title": "", "href": h, "body": ""} for h in clean[:max_results]]
        logger.debug(f"Google '{query[:60]}' → {len(results)} results")
        return results
    except Exception as exc:
        logger.warning(f"Google search failed: {exc}")
        return []


# ─── Domain Filter ─────────────────────────────────────────────────────────────

def _is_blocked(url: str) -> bool:
    return any(domain in url for domain in BLOCKED_DOMAINS)


# ─── Main Entry Point ──────────────────────────────────────────────────────────

def search_for_papers(exam_name: str, year: int) -> list[dict]:
    """
    Run multiple query variants through DDG, Bing, and Google.
    Returns a deduplicated, unblocked list of candidate result dicts
    (up to MAX_SEARCH_RESULTS items).
    """
    queries = build_queries(exam_name, year)
    seen_urls: set[str] = set()
    all_results: list[dict] = []

    logger.info(f"[{exam_name} {year}] Running {len(queries)} search query variants…")

    # ── Phase 1: DuckDuckGo ────────────────────────────────────────────────
    for i, query in enumerate(queries):
        if len(all_results) >= MAX_SEARCH_RESULTS:
            break
        results = _search_duckduckgo(query, max_results=10)
        for r in results:
            href = r.get("href", "")
            if href and href not in seen_urls and not _is_blocked(href):
                seen_urls.add(href)
                all_results.append(r)
        # Be polite between queries
        if i < len(queries) - 1:
            time.sleep(1.0)

    logger.info(f"[{exam_name} {year}] DDG → {len(all_results)} candidates")

    # ── Phase 2: Bing fallback ─────────────────────────────────────────────
    if len(all_results) < 8:
        logger.info(f"[{exam_name} {year}] Too few DDG results — trying Bing…")
        for query in queries[:3]:
            if len(all_results) >= MAX_SEARCH_RESULTS:
                break
            bing_results = _search_bing(query, max_results=10)
            for r in bing_results:
                href = r.get("href", "")
                if href and href not in seen_urls and not _is_blocked(href):
                    seen_urls.add(href)
                    all_results.append(r)
            time.sleep(1.0)

    # ── Phase 3: Google last resort ────────────────────────────────────────
    if len(all_results) < 5:
        logger.info(f"[{exam_name} {year}] Still few results — trying Google…")
        google_q = f'"{exam_name}" {year} question paper filetype:pdf'
        google_results = _search_google(google_q, max_results=10)
        for r in google_results:
            href = r.get("href", "")
            if href and href not in seen_urls and not _is_blocked(href):
                seen_urls.add(href)
                all_results.append(r)

    logger.info(f"[{exam_name} {year}] Total search candidates: {len(all_results)}")
    return all_results[:MAX_SEARCH_RESULTS]
