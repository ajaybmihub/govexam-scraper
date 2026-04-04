"""
utils/logger.py — Loguru-based structured logging setup
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logger(log_dir: Path = None) -> None:
    """Configure loguru with file + console sinks."""
    if log_dir is None:
        log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Remove default sink
    logger.remove()

    # Console sink — INFO and above, coloured
    logger.add(
        sys.stdout,
        level="INFO",
        colorize=True,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
    )

    # File sink — DEBUG and above, rotated daily
    logger.add(
        log_dir / "scraper_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="1 day",
        retention="14 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} — {message}",
    )


# Auto-setup when imported
setup_logger()
