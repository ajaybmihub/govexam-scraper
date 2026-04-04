"""
scraper/downloader.py — Resilient PDF downloader with retry + validation.

Uses tenacity for exponential-backoff retries and validates every
downloaded file before accepting it.
"""

from __future__ import annotations
from pathlib import Path
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)
import logging
import requests
import warnings
from urllib3.exceptions import InsecureRequestWarning

# Suppress noisy library warnings
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
warnings.filterwarnings("ignore", message=".*Brotli.*")

from config import DOWNLOAD_TIMEOUT_SEC, MAX_RETRIES, CHUNK_SIZE
from scraper.anti_detect import build_pdf_headers, human_delay
from utils.file_manager import ensure_dir
from utils.pdf_validator import validate_pdf, delete_invalid


# ─── Core Download Function ───────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.RequestException, OSError)),
    before_sleep=before_sleep_log(logging.getLogger("tenacity"), logging.DEBUG),
    reraise=False,
)
def _download_raw(url: str, save_path: Path, referer: str = "") -> None:
    """
    Download a URL to save_path using streaming chunks.
    Raises on HTTP errors or OS errors — tenacity will retry.
    """
    headers = build_pdf_headers(referer or url)
    response = requests.get(
        url,
        headers=headers,
        timeout=DOWNLOAD_TIMEOUT_SEC,
        stream=True,
        allow_redirects=True,
        verify=False,  # Bypass SSL for govt sites
    )
    response.raise_for_status()

    ensure_dir(save_path)
    with open(save_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)

    logger.debug(f"Raw download complete → {save_path.name} ({save_path.stat().st_size:,} bytes)")


# ─── Public Download + Validate ──────────────────────────────────────────────

def download_pdf(url: str, save_path: Path, referer: str = "") -> bool:
    """
    Download a PDF from `url` to `save_path`.
    Returns True if the download succeeded and the file is a valid PDF.
    Cleans up invalid/partial files automatically.
    """
    logger.info(f"Downloading → {url}")
    try:
        _download_raw(url, save_path, referer)
    except RetryError as exc:
        logger.error(f"Download failed after {MAX_RETRIES} retries: {exc}")
        delete_invalid(save_path)
        return False
    except Exception as exc:
        logger.error(f"Unexpected download error: {exc}")
        delete_invalid(save_path)
        return False

    if validate_pdf(save_path):
        logger.success(f"Valid PDF saved → {save_path}")
        return True
    else:
        logger.warning(f"Downloaded file is not a valid PDF — removing: {save_path.name}")
        delete_invalid(save_path)
        return False


# ─── Try Multiple PDF URLs ────────────────────────────────────────────────────

def try_download_any(
    pdf_urls: list[str],
    save_path: Path,
    page_url: str = "",
) -> bool:
    """
    Try each url in pdf_urls in order.
    Returns True as soon as one download succeeds.
    """
    for i, pdf_url in enumerate(pdf_urls, 1):
        logger.info(f"  Trying PDF URL {i}/{len(pdf_urls)}: {pdf_url[:80]}")
        human_delay(0.5, 1.5)  # Short delay between PDF attempts
        if download_pdf(pdf_url, save_path, referer=page_url):
            return True
    return False
