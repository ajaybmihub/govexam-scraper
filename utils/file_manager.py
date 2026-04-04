"""
utils/file_manager.py — Folder creation, filename normalisation, deduplication
"""

import re
from pathlib import Path
from loguru import logger

from config import BASE_DOWNLOAD_DIR


def safe_name(text: str) -> str:
    """Convert an arbitrary string into a safe filesystem name."""
    text = text.strip().upper()
    # Replace spaces and special chars with underscores
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s]+", "_", text)
    return text


def make_filename(exam: str, year: int, label: str = "") -> str:
    """Build a descriptive PDF filename with an optional label (e.g., GS1)."""
    safe_exam = safe_name(exam)
    label = f"_{label}" if label else "_Paper"
    return f"{safe_exam}_{year}{label}.pdf"


def make_save_path(exam: str, year: int, label: str = "", index: int = 1) -> Path:
    """Return the full save path for a paper PDF."""
    if not label:
        label = f"Paper{index}"
    elif index > 1:
        label = f"{label}_{index}"
    
    filename = make_filename(exam, year, label)
    return BASE_DOWNLOAD_DIR / safe_name(exam) / str(year) / filename


def get_next_available_path(exam: str, year: int, label: str = "") -> Path:
    """
    Find the next available path for a given exam, year, and label.
    Increments index (e.g. Prelims, Prelims_2, Prelims_3) until available.
    """
    index = 1
    while True:
        path = make_save_path(exam, year, label, index)
        if not path.exists():
            return path
        index += 1


def ensure_dir(path: Path) -> None:
    """Create all parent directories for a file path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Directory ready: {path.parent}")


def already_downloaded(exam: str, year: int) -> bool:
    """Return True if at least one paper for this exam+year already exists."""
    folder = BASE_DOWNLOAD_DIR / safe_name(exam) / str(year)
    if not folder.exists():
        return False
    pdfs = list(folder.glob("*.pdf"))
    return len(pdfs) > 0
