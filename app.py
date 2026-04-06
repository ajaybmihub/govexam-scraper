"""
app.py — Streamlit UI for GovExam Scraper.

Run with:  streamlit run app.py
"""

from __future__ import annotations
import sys, os
import asyncio

# Windows-specific fix for Scrapling/Playwright subprocesses
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# ── Ensure modules resolve from this folder ───────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import queue
import threading
import time
from datetime import datetime
from pathlib import Path
import traceback
from loguru import logger

import streamlit as st
from dotenv import load_dotenv

# Load .env before anything else
load_dotenv()

# ── Page config (MUST be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="GovExam Scraper",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Internal imports ──────────────────────────────────────────────────────────
import config
from utils.file_manager import already_downloaded, get_next_available_path, safe_name
from scraper.anti_detect import human_delay
from scraper.search_agent import search_for_papers
from scraper.link_scorer import score_and_rank
from scraper.browser_scraper import extract_pdf_links
from scraper.downloader import try_download_any, download_pdf

# ── Inject custom CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Root & base ─────────── */
:root {
    --bg-primary:   #0d0f18;
    --bg-card:      #13162a;
    --bg-input:     #1a1e35;
    --accent:       #6c63ff;
    --accent-2:     #00e5ff;
    --success:      #00e676;
    --warning:      #ffd740;
    --danger:       #ff5252;
    --text-primary: #e8eaf6;
    --text-muted:   #7986cb;
    --border:       rgba(108,99,255,0.18);
    --glow:         rgba(108,99,255,0.25);
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg-primary) !important;
    font-family: 'Inter', sans-serif;
    color: var(--text-primary);
}

/* Main content area */
[data-testid="stMain"] { background: var(--bg-primary) !important; }
[data-testid="stMainBlockContainer"] { padding-top: 1rem !important; }

/* ── Sidebar ─────────────── */
[data-testid="stSidebar"] {
    background: var(--bg-card) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text-primary) !important; }

/* ── Metric cards ─────────── */
[data-testid="stMetric"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    backdrop-filter: blur(6px);
    transition: transform 0.2s, box-shadow 0.2s;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 32px var(--glow);
}
[data-testid="stMetricValue"]  { color: var(--accent-2) !important; font-weight: 700; }
[data-testid="stMetricLabel"]  { color: var(--text-muted) !important; font-size: 0.8rem !important; }

/* ── Buttons ─────────────── */
.stButton > button {
    background: linear-gradient(135deg, var(--accent), #8b5cf6) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.6rem 2rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.3px;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 20px rgba(108,99,255,0.35) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(108,99,255,0.55) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* Stop button */
.stop-btn > button {
    background: linear-gradient(135deg, #ff5252, #d32f2f) !important;
    box-shadow: 0 4px 20px rgba(255,82,82,0.35) !important;
}

/* ── Inputs ──────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--glow) !important;
}

/* ── Progress bar ────────── */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, var(--accent), var(--accent-2)) !important;
    border-radius: 50px !important;
}

/* ── Toggle / checkbox ───── */
.stCheckbox > label { color: var(--text-muted) !important; }

/* ── Expander ────────────── */
.streamlit-expanderHeader {
    background: var(--bg-card) !important;
    border-radius: 10px !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
}

/* ── Scrollable log box ──── */
.log-box {
    background: #090b14;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem;
    height: 320px;
    overflow-y: auto;
    font-family: 'Fira Code', 'Cascadia Code', monospace;
    font-size: 0.78rem;
    line-height: 1.7;
    color: #b0bec5;
}
.log-box .log-info    { color: #82b1ff; }
.log-box .log-success { color: #00e676; }
.log-box .log-warn    { color: #ffd740; }
.log-box .log-error   { color: #ff5252; }

/* ── Status badge ────────── */
.badge-ok   { background:#00e67622; color:#00e676; border:1px solid #00e67655; padding:2px 10px; border-radius:20px; font-size:0.8rem; }
.badge-skip { background:#ffd74022; color:#ffd740; border:1px solid #ffd74055; padding:2px 10px; border-radius:20px; font-size:0.8rem; }
.badge-fail { background:#ff525222; color:#ff5252; border:1px solid #ff525255; padding:2px 10px; border-radius:20px; font-size:0.8rem; }
.badge-run  { background:#6c63ff22; color:#6c63ff; border:1px solid #6c63ff55; padding:2px 10px; border-radius:20px; font-size:0.8rem; }

/* ── Year table ──────────── */
.year-table { width:100%; border-collapse:collapse; }
.year-table th { color:var(--text-muted); font-size:0.78rem; text-transform:uppercase; letter-spacing:1px; padding:8px 12px; border-bottom:1px solid var(--border); }
.year-table td { padding:10px 12px; border-bottom:1px solid rgba(255,255,255,0.04); font-size:0.88rem; }
.year-table tr:hover td { background:rgba(108,99,255,0.06); }

/* ── Section headers ─────── */
.section-title {
    font-size:1rem; font-weight:700; text-transform:uppercase;
    letter-spacing:1.5px; color:var(--accent); margin-bottom:0.6rem;
    display:flex; align-items:center; gap:8px;
}

/* ── Hero banner ─────────── */
.hero {
    background: linear-gradient(135deg, #1a1e35 0%, #12102a 100%);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content:'';
    position:absolute; top:-40px; right:-40px;
    width:200px; height:200px;
    background:radial-gradient(circle, rgba(108,99,255,0.2) 0%, transparent 70%);
    border-radius:50%;
}
.hero h1 { font-size:2rem; font-weight:800; margin:0; letter-spacing:-0.5px; }
.hero h1 span { background:linear-gradient(135deg,#6c63ff,#00e5ff); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.hero p  { color:var(--text-muted); margin:0.4rem 0 0; font-size:0.95rem; }

/* ── File card ───────────── */
.file-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 12px;
    transition: border-color 0.2s;
}
.file-card:hover { border-color: var(--accent); }
.file-icon { font-size:1.4rem; }
.file-info { flex:1; }
.file-name { font-size:0.88rem; font-weight:500; color:var(--text-primary); }
.file-meta { font-size:0.75rem; color:var(--text-muted); }

/* ── Divider ─────────────── */
hr { border-color: var(--border) !important; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# State management
# ═══════════════════════════════════════════════════════════
def _init_state():
    defaults = {
        "running":      False,
        "results":      {},       # {year: status_str}
        "log_lines":    [],       # list of (level, message) tuples
        "current_year": None,
        "current_step": "",
        "done":         False,
        "_queue":       None,
        "_thread":      None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ═══════════════════════════════════════════════════════════
# Log capture helpers
# ═══════════════════════════════════════════════════════════
def _enqueue(q: queue.Queue, level: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    q.put((level, f"[{ts}] {msg}"))


# ═══════════════════════════════════════════════════════════
# Scraper runner (runs in background thread)
# ═══════════════════════════════════════════════════════════
def _run_scraper(exam: str, years: list[int], skip_existing: bool, use_llm: bool, q: queue.Queue):
    """Runs the V4 search-first pipeline in a background thread."""
    # Windows fix: must set policy in EACH new thread using asyncio
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        # We also need a fresh loop for this thread if it doesn't have one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    import config as cfg
    cfg.USE_LLM_SCORER = use_llm
    
    # Import the main pipeline function
    from main import process_year

    _enqueue(q, "info", f"🚀 Starting V4 Pipeline: {exam} | years {years[0]}–{years[-1]}")
    _enqueue(q, "info", "Mode: Comprehensive Search (Download All)")

    for year in years:
        _enqueue(q, "info", f"━━━ {exam} {year} ━━━")
        q.put(("YEAR_START", year))
        q.put(("STEP", f"Processing {exam} {year}…"))

        try:
            # We call the already -tested sync process_year from main.py
            # This handles Phase 1 (Slugs), Phase 2 (Official), Phase 3 (Search)
            status = process_year(exam, year, skip_existing)
            
            # Translate status to UI log
            if "✓" in status:
                _enqueue(q, "success", f"[{exam} {year}] {status}")
            elif "⏭" in status:
                _enqueue(q, "warn", f"[{exam} {year}] {status}")
            else:
                _enqueue(q, "error", f"[{exam} {year}] {status}")
                
            q.put(("YEAR_DONE", (year, status)))
            
        except Exception as exc:
            import traceback
            logger.error(traceback.format_exc())
            _enqueue(q, "error", f"[{exam} {year}] Unexpected error: {exc}")
            q.put(("YEAR_DONE", (year, f"✗ Error")))

    _enqueue(q, "success", f"🏁 Scraping complete for {exam}!")
    q.put(("DONE", None))


# ═══════════════════════════════════════════════════════════
# File browser helpers
# ═══════════════════════════════════════════════════════════
def _get_downloaded_files() -> dict[str, dict[str, list[Path]]]:
    """Returns {exam_folder: {year: [paths]}}"""
    result = {}
    dl = config.BASE_DOWNLOAD_DIR
    if not dl.exists():
        return result
    for exam_dir in sorted(dl.iterdir()):
        if not exam_dir.is_dir():
            continue
        result[exam_dir.name] = {}
        for year_dir in sorted(exam_dir.iterdir(), reverse=True):
            if not year_dir.is_dir():
                continue
            pdfs = sorted(year_dir.glob("*.pdf"))
            if pdfs:
                # Store PDF paths along with their verification status
                files_info = []
                for p in pdfs:
                    meta_p = p.with_suffix(".pdf.json")
                    verified = False
                    if meta_p.exists():
                        try:
                            import json
                            with open(meta_p, "r") as f:
                                meta = json.load(f)
                                verified = meta.get("verified", False)
                        except: pass
                    files_info.append({"path": p, "verified": verified})
                result[exam_dir.name][year_dir.name] = files_info
    return result


def _human_size(path: Path) -> str:
    b = path.stat().st_size
    if b < 1024:      return f"{b} B"
    if b < 1024**2:   return f"{b/1024:.1f} KB"
    return f"{b/1024**2:.1f} MB"


# ═══════════════════════════════════════════════════════════
# Sidebar
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.markdown("---")

    # Exam selector (presets + custom)
    from config import EXAM_SOURCE_MAP
    PRESET_EXAMS = ["Custom…"] + sorted(list(EXAM_SOURCE_MAP.keys()))
    preset = st.selectbox("📋 Exam Preset", PRESET_EXAMS, index=1)
    exam_input = st.text_input(
        "Exam Name",
        value="" if preset == "Custom…" else preset,
        placeholder="e.g. UPSC CSE",
    )

    st.markdown("")
    col_s, col_e = st.columns(2)
    with col_s:
        start_year = st.number_input("Start Year", min_value=2000, max_value=2025, value=2020)
    with col_e:
        end_year = st.number_input("End Year", min_value=2000, max_value=2025, value=2024)

    st.markdown("---")
    st.markdown("### 🛠️ Options")
    use_llm = st.toggle("🧠 LLM Ranking (Gemini)", value=bool(os.getenv("GEMINI_API_KEY")),
                        help="Uses Google Gemini API to intelligently rank candidate URLs. Requires GEMINI_API_KEY in .env")
    skip_existing = st.toggle("⏭ Skip Already Downloaded", value=True)

    st.markdown("---")

    # API key status
    api_key = os.getenv("GEMINI_API_KEY", "")
    if api_key and len(api_key) > 10:
        st.success("✅ API Key Loaded", icon="🔑")
    else:
        st.warning("No API Key — LLM off", icon="⚠️")
        use_llm = False

    st.markdown("---")
    st.markdown("### 🛠️ Tools")
    
    with st.expander("🗑️ Cleanup", expanded=False):
        if st.button("Clear Logs", use_container_width=True):
            for f in config.LOG_DIR.glob("*.log"):
                f.unlink()
            st.toast("Logs cleared!")
            time.sleep(0.5)
            st.rerun()
            
        if st.button("Clear Downloads", use_container_width=True):
            import shutil
            if config.BASE_DOWNLOAD_DIR.exists():
                shutil.rmtree(config.BASE_DOWNLOAD_DIR)
                config.BASE_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
            st.toast("Downloads cleared!")
            time.sleep(0.5)
            st.rerun()

    with st.expander("📤 Export Data", expanded=False):
        dl_files = _get_downloaded_files()
        if dl_files:
            import json
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "exams": {k: [str(p["path"].name) for year_v in v.values() for p in year_v] for k, v in dl_files.items()}
            }
            st.download_button(
                "Download Inventory (JSON)",
                data=json.dumps(export_data, indent=2),
                file_name="scraper_inventory.json",
                mime="application/json",
                use_container_width=True
            )
        else:
            st.info("No data to export.")

    st.markdown("---")
    st.markdown(
        "<div style='color:#7986cb;font-size:0.75rem;text-align:center'>"
        "Built with Scrapling + Claude API<br>"
        "Search → Rank → Download"
        "</div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════
# Main layout
# ═══════════════════════════════════════════════════════════
# Hero banner
st.markdown("""
<div class="hero">
  <h1>🎓 <span>GovExam</span> Scraper</h1>
  <p>Multi-source intelligent agent · Searches, ranks, and downloads question papers automatically</p>
</div>
""", unsafe_allow_html=True)

# Top metrics row
dl_snapshot = _get_downloaded_files()
total_files = sum(
    len(files)
    for exam_v in dl_snapshot.values()
    for files in exam_v.values()
)
total_verified = sum(
    1 for exam_v in dl_snapshot.values()
    for files in exam_v.values()
    for f in files if f["verified"]
)
total_exams = len(dl_snapshot)

mc1, mc2, mc3, mc4 = st.columns(4)
mc1.metric("📚 Total PDFs", total_files)
mc2.metric("✅ Verified Papers", total_verified)
mc3.metric("🎯 Exams Scraped", total_exams)
mc4.metric("💾 Storage", f"{sum(f['path'].stat().st_size for exam_v in dl_snapshot.values() for files in exam_v.values() for f in files) / 1024**2:.1f} MB" if total_files else "0 MB")

st.markdown("---")

# ── Two-column layout: controls | progress ────────────────────────────────────
left_col, right_col = st.columns([1, 1.6], gap="large")

with left_col:
    st.markdown('<div class="section-title">⚡ Run Scraper</div>', unsafe_allow_html=True)
    
    tabs = st.tabs(["Auto Agent", "Manual URL"])
    
    with tabs[0]:
        years_count = max(0, int(end_year) - int(start_year) + 1)
        st.markdown(
            f"<div style='color:#7986cb;font-size:0.85rem;margin-bottom:0.8rem'>"
            f"Will process <b style='color:#6c63ff'>{years_count}</b> year(s) for "
            f"<b style='color:#00e5ff'>{exam_input or '…'}</b></div>",
            unsafe_allow_html=True,
        )

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            start_btn = st.button("▶ Start Scraping", disabled=st.session_state.running, use_container_width=True)
        with btn_col2:
            with st.container():
                st.markdown('<div class="stop-btn">', unsafe_allow_html=True)
                stop_btn = st.button("■ Stop", disabled=not st.session_state.running, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.markdown("<p style='font-size:0.8rem; color:var(--text-muted)'>Found a direct page? Paste it here to extract PDFs instantly.</p>", unsafe_allow_html=True)
        manual_url = st.text_input("Page URL", placeholder="https://example.com/papers")
        manual_exam = st.text_input("Target Exam Folder", value=exam_input, placeholder="e.g. UPSC CSE")
        manual_year = st.number_input("Target Year", min_value=2000, max_value=2025, value=2024, key="man_year")
        
        if st.button("🔍 Extract from URL", use_container_width=True, disabled=st.session_state.running or not manual_url):
            with st.spinner("Visiting page..."):
                found_links = extract_pdf_links(manual_url)
                if found_links:
                    st.success(f"Found {len(found_links)} PDF(s)!")
                    save_path = get_next_available_path(manual_exam, manual_year)
                    if try_download_any(found_links, save_path, page_url=manual_url):
                        st.balloons()
                        st.info(f"Saved to: {save_path.name}")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("No PDFs found on this page.")

    # Current step indicator
    step_box = st.empty()
    if st.session_state.current_step and st.session_state.running:
        step_box.info(st.session_state.current_step)

    st.markdown("")
    st.markdown('<div class="section-title">📊 Year Results</div>', unsafe_allow_html=True)

    # Year results table
    results_container = st.empty()

    def _render_results_table(results: dict):
        if not results:
            results_container.markdown(
                "<div style='color:#7986cb;font-size:0.85rem;padding:1rem 0'>"
                "Results will appear here as each year is processed…</div>",
                unsafe_allow_html=True,
            )
            return

        rows = ""
        for year in sorted(results.keys(), reverse=True):
            status = results[year]
            if "✓" in status:
                badge = f'<span class="badge-ok">✓ Downloaded</span>'
            elif "⏭" in status:
                badge = f'<span class="badge-skip">⏭ Skipped</span>'
            elif "⟳" in status:
                badge = f'<span class="badge-run">⟳ Running…</span>'
            else:
                badge = f'<span class="badge-fail">✗ Failed</span>'
            rows += f"<tr><td><b>{year}</b></td><td>{badge}</td></tr>"

        results_container.markdown(
            f"<table class='year-table'>"
            f"<thead><tr><th>Year</th><th>Status</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>",
            unsafe_allow_html=True,
        )

    _render_results_table(st.session_state.results)


with right_col:
    st.markdown('<div class="section-title">📋 Live Log</div>', unsafe_allow_html=True)

    log_placeholder = st.empty()

    def _render_log(lines: list):
        if not lines:
            log_placeholder.markdown(
                "<div class='log-box'><span style='color:#3d4a7a'>Waiting to start…</span></div>",
                unsafe_allow_html=True,
            )
            return
        # Keep last 100 lines
        shown = lines[-100:]
        html_lines = []
        for level, msg in shown:
            esc = msg.replace("<", "&lt;").replace(">", "&gt;")
            css = {"info": "log-info", "success": "log-success", "warn": "log-warn", "error": "log-error"}.get(level, "")
            html_lines.append(f'<div class="{css}">{esc}</div>')
        content = "\n".join(html_lines)
        log_placeholder.markdown(
            f"<div class='log-box' id='logbox'>{content}"
            "<script>document.getElementById('logbox').scrollTop=9999</script>"
            "</div>",
            unsafe_allow_html=True,
        )

    _render_log(st.session_state.log_lines)

    # Progress bar
    st.markdown("")
    progress_label = st.empty()
    progress_bar = st.empty()

    if st.session_state.running or st.session_state.done:
        total = years_count or 1
        done_count = len(st.session_state.results)
        pct = done_count / total
        progress_label.markdown(
            f"<div style='color:#7986cb;font-size:0.8rem;margin-bottom:4px'>"
            f"Progress: {done_count}/{total} years completed</div>",
            unsafe_allow_html=True,
        )
        progress_bar.progress(pct)


# ═══════════════════════════════════════════════════════════
# Event handling — Start
# ═══════════════════════════════════════════════════════════
if start_btn and not st.session_state.running:
    if not exam_input.strip():
        st.error("Please enter an exam name.")
    elif int(start_year) > int(end_year):
        st.error("Start year must be ≤ end year.")
    else:
        # Reset state
        st.session_state.running      = True
        st.session_state.done         = False
        st.session_state.results      = {}
        st.session_state.log_lines    = []
        st.session_state.current_step = ""

        q: queue.Queue = queue.Queue()
        st.session_state._queue = q

        years = list(range(int(start_year), int(end_year) + 1))
        t = threading.Thread(
            target=_run_scraper,
            args=(exam_input.strip(), years, skip_existing, use_llm, q),
            daemon=True,
        )
        st.session_state._thread = t
        t.start()
        st.rerun()


# ═══════════════════════════════════════════════════════════
# Event handling — Stop
# ═══════════════════════════════════════════════════════════
if stop_btn and st.session_state.running:
    # We can't forcefully kill the thread, but we mark done to stop polling
    st.session_state.running = False
    st.session_state.done = True
    st.session_state.log_lines.append(("warn", "[--:--:--] ⛔ Stopped by user"))
    st.rerun()


# ═══════════════════════════════════════════════════════════
# Real-time polling loop (while scraper is running)
# ═══════════════════════════════════════════════════════════
if st.session_state.running and st.session_state._queue is not None:
    q = st.session_state._queue
    updates = 0

    # Drain queue with a short window
    deadline = time.time() + 1.0
    while time.time() < deadline:
        try:
            msg = q.get_nowait()
        except queue.Empty:
            time.sleep(0.05)
            continue

        kind, payload = msg

        if kind in ("info", "success", "warn", "error"):
            st.session_state.log_lines.append((kind, payload))
            updates += 1

        elif kind == "STEP":
            st.session_state.current_step = payload
            updates += 1

        elif kind == "YEAR_START":
            st.session_state.results[payload] = "⟳ Running…"
            updates += 1

        elif kind == "YEAR_DONE":
            year, status = payload
            st.session_state.results[year] = status
            updates += 1

        elif kind == "DONE":
            st.session_state.running = False
            st.session_state.done = True
            st.session_state.current_step = ""
            updates += 1
            break

    if updates:
        st.rerun()
    else:
        # No messages yet — re-run after a short pause to keep polling
        time.sleep(0.3)
        st.rerun()


# ═══════════════════════════════════════════════════════════
# Summary banner (shown when done)
# ═══════════════════════════════════════════════════════════
if st.session_state.done and st.session_state.results:
    res = st.session_state.results
    n_ok   = sum(1 for s in res.values() if "✓" in s)
    n_skip = sum(1 for s in res.values() if "⏭" in s)
    n_fail = len(res) - n_ok - n_skip

    st.markdown("---")
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("✅ Downloaded", n_ok)
    sc2.metric("⏭ Skipped",   n_skip)
    sc3.metric("❌ Failed",    n_fail)

    if n_ok:
        st.success(f"🎉 {n_ok} paper(s) successfully downloaded to `downloads/` folder!")
    elif n_skip == len(res):
        st.info("All papers were already downloaded.")
    else:
        st.error("No papers could be downloaded. Check the logs above for details.")


# ═══════════════════════════════════════════════════════════
# Downloaded Files Browser
# ═══════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<div class="section-title">📁 Downloaded Files Browser</div>', unsafe_allow_html=True)

dl_data = _get_downloaded_files()

if not dl_data:
    st.markdown(
        "<div style='color:#7986cb;font-size:0.9rem;padding:1rem 0'>"
        "No files downloaded yet. Run the scraper to get started.</div>",
        unsafe_allow_html=True,
    )
else:
    # Exam selector
    exam_names = list(dl_data.keys())
    selected_exam = st.selectbox("Filter by Exam", ["All"] + exam_names, key="browser_exam")

    exams_to_show = exam_names if selected_exam == "All" else [selected_exam]

    for exam_folder in exams_to_show:
        years_data = dl_data[exam_folder]
        total_papers = sum(len(v) for v in years_data.values())
        with st.expander(f"📚 {exam_folder.replace('_', ' ')}  —  {total_papers} paper(s)", expanded=True):
            for year_folder, files in sorted(years_data.items(), reverse=True):
                st.markdown(f"**{year_folder}**")
                cols = st.columns(min(len(files), 3))
                for idx, file_info in enumerate(files):
                    fpath = file_info["path"]
                    is_ver = file_info["verified"]
                    with cols[idx % 3]:
                        size_str = _human_size(fpath)
                        verified_tag = '<span class="badge-ok" style="margin-left:5px; font-size:0.65rem">VERIFIED</span>' if is_ver else ""
                        st.markdown(
                            f"<div class='file-card'>"
                            f"<div class='file-icon'>📄</div>"
                            f"<div class='file-info'>"
                            f"<div class='file-name'>{fpath.name} {verified_tag}</div>"
                            f"<div class='file-meta'>{size_str}</div>"
                            f"</div></div>",
                            unsafe_allow_html=True,
                        )
                        # Download button
                        with open(fpath, "rb") as f:
                            st.download_button(
                                label="⬇ Download",
                                data=f,
                                file_name=fpath.name,
                                mime="application/pdf",
                                key=f"dl_{fpath}",
                                use_container_width=True,
                            )
