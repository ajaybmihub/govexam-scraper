"""
scraper/anti_detect.py — User-agent rotation, human-like delays, and headers
"""

import time
import random
from loguru import logger

_ua = None        # Lazy-loaded on first call
_HAS_FAKE_UA: bool | None = None  # None = not yet checked


def _init_ua() -> bool:
    """Lazily initialise fake-useragent on first use."""
    global _ua, _HAS_FAKE_UA
    if _HAS_FAKE_UA is not None:
        return _HAS_FAKE_UA
    try:
        from fake_useragent import UserAgent
        _ua = UserAgent()
        _HAS_FAKE_UA = True
    except Exception:
        _HAS_FAKE_UA = False
        logger.warning("fake-useragent not available; using hardcoded UA pool.")
    return _HAS_FAKE_UA

# Fallback UA pool in case fake-useragent fails / is not installed
_FALLBACK_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
]


def random_user_agent() -> str:
    """Return a randomised, realistic browser User-Agent string."""
    if _init_ua():
        try:
            return _ua.chrome
        except Exception:
            pass
    return random.choice(_FALLBACK_UAS)


def build_headers(referer: str = "https://www.google.com/") -> dict:
    """Build a realistic HTTP header dict to avoid detection."""
    return {
        "User-Agent": random_user_agent(),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": referer,
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def build_pdf_headers(referer: str = "https://www.google.com/") -> dict:
    """Headers tuned for PDF download requests."""
    headers = build_headers(referer)
    headers["Accept"] = "application/pdf,application/octet-stream,*/*;q=0.8"
    return headers


def human_delay(min_sec: float = None, max_sec: float = None) -> None:
    """
    Sleep for a random duration to mimic human browsing behaviour.
    Defaults to values from config if not overridden.
    """
    from config import MIN_DELAY_SEC, MAX_DELAY_SEC
    lo = min_sec if min_sec is not None else MIN_DELAY_SEC
    hi = max_sec if max_sec is not None else MAX_DELAY_SEC
    delay = random.uniform(lo, hi)
    logger.debug(f"Human delay: {delay:.2f}s")
    time.sleep(delay)
