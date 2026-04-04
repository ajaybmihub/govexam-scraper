"""
utils/pdf_validator.py — Validate that a downloaded file is a real PDF
"""

from pathlib import Path
from loguru import logger

from config import MIN_PDF_SIZE_BYTES


def validate_pdf(path: Path) -> bool:
    """
    Check two things:
    1. File size is above the minimum threshold (50 KB)
    2. First 4 bytes are the PDF magic number %PDF
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

    logger.debug(f"PDF valid — {size:,} bytes: {path.name}")
    return True


def delete_invalid(path: Path) -> None:
    """Remove a file that failed validation to avoid polluting the output folder."""
    try:
        path.unlink(missing_ok=True)
        logger.debug(f"Deleted invalid file: {path.name}")
    except OSError as exc:
        logger.error(f"Could not delete invalid file {path.name}: {exc}")
