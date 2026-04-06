"""
utils/pdf_validator.py — Validate that a downloaded file is a real PDF
"""

from pathlib import Path
import pdfplumber
import re
from loguru import logger

from config import MIN_PDF_SIZE_BYTES


def _has_solution_text(path: Path) -> bool:
    """Scan first 2 pages for keywords indicating this is a solved paper."""
    try:
        with pdfplumber.open(path) as pdf:
            if not pdf.pages: return False
            # Check top 2 pages
            for i in range(min(2, len(pdf.pages))):
                text = pdf.pages[i].extract_text()
                if not text: continue
                low = text.lower()
                # Indicators of a solved paper / answer key
                # We use word boundaries to avoid matching "expansion" or "transition"
                if any(re.search(rf"\b{k}\b", low) for k in ["solution", "solved", "answer-key", "ans:"]):
                    return True
                if "(solution)" in low or "memory based paper (solved)" in low:
                    return True
    except Exception as e:
        logger.debug(f"Could not scan internal PDF text: {e}")
    return False


def validate_pdf(path: Path) -> bool:
    """
    Check three things:
    1. File size is above the minimum threshold (50 KB)
    2. First 4 bytes are the PDF magic number %PDF
    3. (New) Internal text does NOT contain 'Solution' or 'Solved'
    Returns True if valid, False otherwise.
    """
    if not path.exists():
        logger.warning(f"Validation failed — file does not exist: {path}")
        return False

    size = path.stat().st_size
    if size < MIN_PDF_SIZE_BYTES:
        logger.warning(
            f"Validation failed — file too small ({size:,} bytes < {MIN_PDF_SIZE_BYTES:,} minimum): {path.name}"
        )
        return False

    try:
        with open(path, "rb") as f:
            header = f.read(4)
        if header != b"%PDF":
            logger.warning(
                f"Validation failed — invalid PDF header ({header!r}): {path.name}"
            )
            return False
    except OSError as exc:
        logger.error(f"Could not read file for validation: {exc}")
        return False

    # --- New Internal Content Check ---
    if _has_solution_text(path):
        logger.warning(f"Validation failed — internal content identifies as a 'Solved/Solution' paper: {path.name}")
        return False

    logger.debug(f"PDF valid — {size:,} bytes: {path.name}")
    return True


def delete_invalid(path: Path) -> None:
    """Remove a file that failed validation to avoid polluting the output folder."""
    try:
        path.unlink(missing_ok=True)
        logger.debug(f"Deleted invalid file: {path.name}")
    except OSError as exc:
        logger.error(f"Could not delete invalid file {path.name}: {exc}")
