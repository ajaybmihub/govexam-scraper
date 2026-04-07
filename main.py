"""
main.py — CLI Entry Point for the Government Exam Paper Scraper V4.

HUMAN-LIKE PIPELINE:
  1. Use direct exam-page slugs (Tier 0) if available.
  2. Fallback to official government board site (Tier 1).
  3. Search the web (human-like) and visit top 8 result pages.
  4. Collect ALL genuine question-paper PDFs for the year.
  5. Download each with unique names (e.g. IBPS_PO_2020_Prelims_Shift1.pdf).

Usage:
    python main.py "IBPS Clerk" 2020 2024
    python main.py "SSC CGL" 2019 2024 --no-llm
"""

from __future__ import annotations
import sys
import os
import re
import warnings

# Suppress all library technical noise globally
warnings.filterwarnings("ignore", message=".*Brotli.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="lxml")
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import box
from loguru import logger

import config
from utils.logger import setup_logger
from utils.file_manager import get_next_available_path, already_downloaded, make_save_path
from scraper.anti_detect import human_delay
from scraper.search_agent import search_for_papers
from scraper.link_scorer import score_and_rank
from scraper.browser_scraper import extract_pdf_links, build_tier0_url
from scraper.downloader import download_pdf

from config import EXAM_SOURCE_MAP, TIER2_EDUCATION


app = typer.Typer(
    name="govexam-scraper",
    help="🎓 Intelligent Government Exam Question Paper Scraper",
    add_completion=False,
)
console = Console()


# ─── Robust Labelling and Suffix Extraction ──────────────────────────────────

def _get_detailed_label(url: str, base_label: str) -> str:
    """Extract details like Shift 1, Set A, Slot 1, Morning/Evening, Tier 1, etc. from the filename/URL."""
    u_lower = url.lower().replace("%20", "-").replace("_", "-")
    
    parts = []
    
    # 1. Shift
    m_shift = re.search(r"shift[-_\s]?(\d+)", u_lower)
    if m_shift: parts.append(f"Shift{m_shift.group(1)}")
        
    # 2. Set
    m_set = re.search(r"set[-_\s]?([a-d])\b", u_lower)
    if m_set: parts.append(f"Set{m_set.group(1).upper()}")
        
    # 3. Session / Slot
    m_sess = re.search(r"(?:session|slot)[-_\s]?(\d+)", u_lower)
    if m_sess: parts.append(f"Slot{m_sess.group(1)}")

    # 4. Phase / Tier
    m_tier = re.search(r"(?:tier|phase|stage)[-_\s]?(\d+)", u_lower)
    if m_tier: parts.append(f"Tier{m_tier.group(1)}")

    # 5. Morning / Evening / Afternoon
    if "morn" in u_lower:    parts.append("Morning")
    if "even" in u_lower:    parts.append("Evening")
    if "afternoon" in u_lower: parts.append("Afternoon")

    # 6. Combined result
    if parts:
        # Join new details with the base label
        return f"{base_label}_" + "_".join(parts)
    
    # Fallback: if no metadata found, try to extract a tiny slug from the filename
    filename_part = url.split("/")[-1].split("?")[0].lower()
    # Clean it up: remove the exam name and extension to avoid long names
    slug = re.sub(r"(\.pdf|ibps|clerk|question|paper|year|previous|solved|20\d\d)", "", filename_part)
    slug = re.sub(r"[-_\s]+", "-", slug).strip("-")
    
    if slug and len(slug) > 3:
        # Only use the first 2 chunks of the slug if it's too long
        short_slug = "_".join(slug.split("-")[:2]).upper()
        return f"{base_label}_{short_slug}"

    return base_label


def _assign_labels(pdf_urls: list[str], paper_labels: list[str], target_year: int) -> list[tuple[str, str, int | str]]:
    """Assign each PDF URL a detail label and its identified year."""
    assignments = []
    
    for url in pdf_urls:
        u_lower = url.lower()
        primary = "Paper"
        
        # Check primary labels defined in config
        for lbl in paper_labels:
            if lbl.lower() in u_lower:
                primary = lbl
                break
        
        detailed = _get_detailed_label(url, primary)
        

        # --- Improved Year Identification ---
        # 1. Search in Filename specifically (most accurate)
        filename_part = url.split("/")[-1].split("?")[0]
        years_in_filename = re.findall(r"\b(20[123]\d)\b", filename_part)
        
        # 2. Search in the whole URL (path fallback)
        years_in_path = re.findall(r"\b(20[123]\d)\b", u_lower)
        
        if years_in_filename:
            year_found = int(years_in_filename[0])
        elif years_in_path:
            # If multiple in path, use the last one (it's often closer to the file)
            year_found = int(years_in_path[-1])
        else:
            year_found = target_year if target_year > 0 else "common"

        assignments.append((url, detailed, year_found))
        
    return assignments


# ─── Multi-PDF Downloader ───────────────────────────────────────────────────

def _download_all_relevant(pdf_urls: list[str], exam: str, year: int,
                          paper_labels: list[str], referer: str,
                          session_history: set[str]) -> int:
    """Download a list of PDFs, putting unknowns into 'common'."""
    if not pdf_urls: return 0
        
    new_downloads = 0
    assigned = _assign_labels(pdf_urls, paper_labels, year)
    
    for url, label, identified_year in assigned:
        if url in session_history: continue
        session_history.add(url)
        
        # Use the identified year (e.g. 2023 or 'common') instead of just the search year
        save_path = get_next_available_path(exam, identified_year, label)
        
        # Update logs to reflect folder destination
        dest = str(identified_year) if str(identified_year).isdigit() else "common"
        logger.info(f"    → [{dest}/{label}] Downloading: {url[:60]}...")
        
        if download_pdf(url, save_path, referer=referer):
            new_downloads += 1
            logger.success(f"      ✓ Saved to {dest}/ folder")
        
        human_delay(0.5, 1.2)
        
    return new_downloads


# ─── Per-Year Processing (New Strategy) ───────────────────────────────────────

def process_year(exam: str, year: int, skip_existing: bool) -> str:
    """
    Full pipeline for one exam + year.
    Returns status string for the Summary table.
    Now downloads ALL relevant question papers found.
    """
    if skip_existing and already_downloaded(exam, year):
        logger.info(f"[{exam} {year}] Already downloaded — skipping")
        return "⏭ Skipped"

    cfg = EXAM_SOURCE_MAP.get(exam, {})
    official_site = cfg.get("official")
    tier0_domains  = cfg.get("tier0", [])
    paper_labels   = cfg.get("papers", ["Prelims", "Mains"])

    found_count = 0
    session_history: set[str] = set()

    # ── Phase 1: Known slug URLs ───────────────────────────────────────────
    logger.info(f"[{exam} {year}] PHASE 1 — Checking direct exam portals…")
    for domain in tier0_domains:
        site_key = domain.replace(".com", "").replace(".in", "")
        slug_url = build_tier0_url(site_key, exam, year=year)
        
        if slug_url:
            logger.debug(f"  Visiting slug: {slug_url}")
            pdf_urls = extract_pdf_links(slug_url, exam, year)
            if pdf_urls:
                count = _download_all_relevant(pdf_urls, exam, year, paper_labels, slug_url, session_history)
                found_count += count
        
        # Early Exit within Phase 1
        if found_count >= 10:
            logger.success(f"[{exam} {year}] Found enough papers ({found_count}) from direct portals — Moving to next phase or finishing")
            break
    
    # ── Phase 2: Official government site ──────────────────────────────────
    if official_site:
        logger.info(f"[{exam} {year}] PHASE 2 — Visiting official board: {official_site}")
        official_url = f"https://{official_site}"
        pdf_urls = extract_pdf_links(official_url, exam, year)
        if pdf_urls:
            count = _download_all_relevant(pdf_urls, exam, year, paper_labels, official_url, session_history)
            found_count += count

    # ── Early Exit Strategy ───────────────────────────────────────────────
    # If we found enough papers (>=10) from Phases 1 & 2, skip the broad search
    if found_count >= 10:
        logger.success(f"[{exam} {year}] Found {found_count} papers from direct sources — Skip broad search")
        return f"✓ {found_count} Downloaded"

    # ── Phase 3: Web search (Main Strategy for multi-discovery) ────────────
    logger.info(f"[{exam} {year}] PHASE 3 — Professional web search…")
    candidates = search_for_papers(exam, year)
    
    if candidates:
        ranked_pages = score_and_rank(exam, year, candidates)
        
        # Increase limit if in Broad Discovery mode
        try:
            from config import BROAD_SEARCH_MODE, MAX_BROAD_CANDIDATES, MAX_CANDIDATES_TO_TRY
            limit = MAX_BROAD_CANDIDATES if BROAD_SEARCH_MODE else MAX_CANDIDATES_TO_TRY
        except:
            limit = 8 # Fallback
            
        logger.info(f"[{exam} {year}] Visiting top {limit} source pages…")

        for i, page_url in enumerate(ranked_pages[:limit], 1):
            logger.info(f"  [{i}/{limit}] Scraping: {page_url[:80]}")
            pdf_urls = extract_pdf_links(page_url, exam, year)
            if pdf_urls:
                count = _download_all_relevant(pdf_urls, exam, year, paper_labels, page_url, session_history)
                found_count += count
            
            # Delay between visiting different domains
            human_delay(1.5, 3.0)

    if found_count > 0:
        return f"✓ {found_count} Downloaded"
    return "✗ Not found"


# ─── CLI Command ──────────────────────────────────────────────────────────────

@app.command()
def scrape(
    exam: str = typer.Argument(..., help="Exam name e.g. 'IBPS Clerk'"),
    start_year: int = typer.Argument(..., help="Start year e.g. 2020"),
    end_year: int = typer.Argument(..., help="End year e.g. 2024"),
    no_llm: bool = typer.Option(
        False, "--no-llm", help="Disable LLM scoring (faster, heuristic only)"
    ),
    broad: bool = typer.Option(
        False, "--broad", help="Broad Discovery Mode: Skip scoring, visit up to 25 results"
    ),
    skip_existing: bool = typer.Option(
        True, "--skip-existing/--no-skip", help="Skip years already downloaded"
    ),
) -> None:

    setup_logger()

    if no_llm:
        config.USE_LLM_SCORER = False
    
    if broad:
        config.BROAD_SEARCH_MODE = True

    years = list(range(start_year, end_year + 1))

    console.print(
        Panel.fit(
            f"[bold cyan]🎓 GovExam Scraper V4[/bold cyan]\n"
            f"Exam: [yellow]{exam}[/yellow]  |  "
            f"Years: [yellow]{start_year}–{end_year}[/yellow]  |  "
            f"LLM: [green]{'on' if config.USE_LLM_SCORER else 'off'}[/green]\n"
            f"Mode: [magenta]Comprehensive Search (Download All)[/magenta]",
            border_style="cyan",
        )
    )

    all_results: dict[int, str] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[bold]{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]Processing {exam}…", total=len(years))

        for year in years:
            console.rule(f"[bold cyan]━━━ {exam} {year} ━━━")
            progress.update(task, description=f"[cyan]{exam} {year}…")
            status = process_year(exam, year, skip_existing)
            all_results[year] = status
            progress.advance(task)

    # ── Summary Table ─────────────────────────────────────────────────────
    table = Table(
        title=f"[bold]{exam} — Download Summary[/bold]",
        box=box.ROUNDED,
        border_style="cyan",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Year", style="bold", justify="center")
    table.add_column("Status", justify="left")

    total_dl = 0
    for year, status in all_results.items():
        c = "green" if "✓" in status else ("yellow" if "⏭" in status else "red")
        table.add_row(str(year), f"[{c}]{status}[/{c}]")
        if "✓" in status:
            # extract count if possible e.g. "✓ 2 Downloaded"
            match = re.search(r"(\d+)", status)
            total_dl += int(match.group(1)) if match else 1

    console.print()
    console.print(table)
    console.print(f"\n[bold green]Final Total: {total_dl} question papers downloaded.[/bold green]\n")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
