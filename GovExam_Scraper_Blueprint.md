# Government Exam Question Paper Scraper — Full Architecture Blueprint

> Build a human-like, intelligent web-scraping agent that finds, downloads, and organises government exam question papers across year ranges.

---

## 1. Project Overview

**Goal**: Given an exam name (e.g., `UPSC CSE`, `SSC CGL`, `TNPSC Group 2`) and a year range (e.g., `2017–2025`), the scraper should:

1. Intelligently search multiple websites for question papers year by year (in series)
2. Identify the correct PDF link using heuristics + LLM-based link scoring
3. Download the PDF with retry logic and anti-bot bypass
4. Save into a clean folder structure: `./downloads/<ExamName>/<Year>/paper.pdf`
5. Log success/failure for every year

---

## 2. Solid Tech Stack

### Core Language
```
Python 3.11+
```

### Libraries & Their Role

| Library | Role | Install |
|---|---|---|
| `scrapling` | Intelligent scraping with anti-bot bypass (stealth browser) | `pip install scrapling` |
| `playwright` | Headless browser for JS-heavy sites (Scrapling backend) | `pip install playwright` |
| `duckduckgo-search` | Free, no-API-key web search | `pip install duckduckgo-search` |
| `requests` + `httpx` | HTTP downloads, async support | `pip install requests httpx` |
| `anthropic` | LLM link scorer (Claude API) to pick the best PDF link | `pip install anthropic` |
| `pdfplumber` | Validate downloaded PDF is real and not a captcha page | `pip install pdfplumber` |
| `rich` | Beautiful terminal progress UI | `pip install rich` |
| `tenacity` | Retry logic with exponential backoff | `pip install tenacity` |
| `python-dotenv` | Manage API keys from `.env` file | `pip install python-dotenv` |
| `loguru` | Structured logging | `pip install loguru` |
| `fake-useragent` | Rotate user agents to avoid detection | `pip install fake-useragent` |
| `tldextract` | Domain parsing for source ranking | `pip install tldextract` |

### Optional (Power-Up)
| Library | Role |
|---|---|
| `selenium-wire` | Intercept network traffic to catch PDF URLs dynamically |
| `cloudscraper` | Cloudflare bypass for protected sites |
| `google-search-results` | SerpAPI for reliable Google results (paid) |

---

## 3. Folder Structure

```
govexam-scraper/
├── main.py                    # CLI entry point
├── config.py                  # Config, constants, trusted domains list
├── .env                       # API keys (ANTHROPIC_API_KEY)
├── requirements.txt
│
├── scraper/
│   ├── __init__.py
│   ├── search_agent.py        # DuckDuckGo + Google multi-engine search
│   ├── link_scorer.py         # LLM-based PDF link ranker
│   ├── downloader.py          # PDF downloader with retry + validation
│   ├── browser_scraper.py     # Scrapling / Playwright for JS sites
│   └── anti_detect.py        # User-agent rotation, headers, timing
│
├── utils/
│   ├── file_manager.py        # Folder creation, naming, dedup
│   ├── pdf_validator.py       # Check if downloaded file is a real PDF
│   └── logger.py              # Loguru setup
│
├── downloads/                 # Output — auto-created
│   └── UPSC_CSE/
│       ├── 2017/
│       │   └── UPSC_CSE_2017_GS1.pdf
│       └── 2018/
│           └── UPSC_CSE_2018_GS1.pdf
│
└── logs/
    └── scraper_2024-01-01.log
```

---

## 4. System Architecture

```
┌────────────────────────────────────────────────────────┐
│                     CLI Entry (main.py)                │
│         Input: exam_name="UPSC CSE", years=2017-2025   │
└──────────────────────────┬─────────────────────────────┘
                           │  Loop year-by-year (serial)
                           ▼
┌────────────────────────────────────────────────────────┐
│                   Search Agent Layer                   │
│  • Build smart queries: "UPSC CSE 2019 question paper  │
│    PDF download" + 5 variants                          │
│  • Query DuckDuckGo + Bing (fallback)                  │
│  • Collect top 20 candidate URLs                       │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                   Link Scorer (LLM)                    │
│  • Score each URL: domain trust + PDF likelihood       │
│  • Claude API ranks URLs by relevance                  │
│  • Returns top 3 candidates                            │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                 Browser Scraper (Scrapling)             │
│  • Visit each candidate URL with stealth browser       │
│  • Detect PDF links on page using CSS selectors        │
│  • Handle JS-rendered pages, redirects, popups         │
│  • Collect final direct .pdf URL                       │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               Downloader + Validator                   │
│  • Download PDF with rotating user-agent               │
│  • Retry up to 3 times on failure                      │
│  • Validate: file size > 50KB, header = %PDF           │
│  • Save to downloads/<ExamName>/<Year>/                │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                   Logger + Reporter                    │
│  • Log success/skip/fail per year                      │
│  • Print rich summary table at end                     │
└────────────────────────────────────────────────────────┘
```

---

## 5. Key Module Code Plans

### 5.1 `search_agent.py` — Multi-Query Search

**Strategy**: Build 5 query variants per year to maximise hit rate.

```python
QUERY_TEMPLATES = [
    "{exam} {year} question paper PDF download",
    "{exam} {year} previous year paper PDF",
    "{exam} {year} solved paper download site:gov.in OR site:examrace.com OR site:testbook.com",
    "{exam} question paper {year} filetype:pdf",
    "download {exam} {year} original question paper",
]

def build_queries(exam_name: str, year: int) -> list[str]:
    return [t.format(exam=exam_name, year=year) for t in QUERY_TEMPLATES]

def search_web(query: str, max_results: int = 10) -> list[dict]:
    from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))
```

**Multi-engine fallback**: If DuckDuckGo returns < 5 results, fall back to Bing via `requests`.

---

### 5.2 `link_scorer.py` — LLM-Based URL Ranker

**Strategy**: Pass all candidate URLs + metadata to Claude. Ask it to return the top 3 most likely to have the real question paper PDF.

```python
TRUSTED_DOMAINS = [
    "upsc.gov.in", "ssc.nic.in", "tnpsc.gov.in", "ibps.in",
    "examrace.com", "testbook.com", "gradeup.co", "mrunal.org",
    "drishtijudiciary.com", "insightsonindia.com"
]

def score_links_with_llm(exam: str, year: int, candidates: list[dict]) -> list[str]:
    import anthropic, os
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    prompt = f"""
You are an expert at finding government exam question papers online.
Exam: {exam}, Year: {year}

Here are candidate URLs found via web search:
{json.dumps(candidates, indent=2)}

Rank the top 3 URLs most likely to directly contain or link to the 
original {exam} {year} question paper PDF. 
Prefer .gov.in domains, official exam board sites, and URLs with 
'question-paper', 'previous-year', or 'pdf' in the path.

Return ONLY a JSON array of 3 URLs in order of confidence.
"""
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(response.content[0].text)
```

---

### 5.3 `browser_scraper.py` — Scrapling Stealth Browser

**Strategy**: Use Scrapling's `AsyncPlaywrightFetcher` for JS-heavy pages. It handles Cloudflare, dynamic loading, and cookie prompts.

```python
from scrapling.fetchers import AsyncPlaywrightFetcher

async def extract_pdf_links(url: str) -> list[str]:
    fetcher = AsyncPlaywrightFetcher(
        stealth=True,           # Anti-detection mode
        humanize=True,          # Human-like mouse + scroll
        disable_resources=True, # Block images/fonts for speed
    )
    page = await fetcher.fetch(url)
    
    # Strategy 1: Direct .pdf links in <a href>
    pdf_links = page.css("a[href$='.pdf']").attrib("href")
    
    # Strategy 2: Look for download buttons / links
    download_links = page.css("a:contains('Download'), a:contains('PDF'), button:contains('Download')")
    
    # Strategy 3: Check for Google Drive / OneDrive embed iframes
    iframes = page.css("iframe[src*='drive.google'], iframe[src*='onedrive']").attrib("src")
    
    # Strategy 4: Intercept network requests for .pdf
    # (done via playwright network interception in the fetcher config)
    
    return list(set(pdf_links + iframes))
```

---

### 5.4 `downloader.py` — Resilient PDF Downloader

```python
from tenacity import retry, stop_after_attempt, wait_exponential
from fake_useragent import UserAgent
import requests

ua = UserAgent()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def download_pdf(url: str, save_path: Path) -> bool:
    headers = {
        "User-Agent": ua.random,
        "Accept": "application/pdf,*/*",
        "Referer": "https://www.google.com/",
    }
    response = requests.get(url, headers=headers, timeout=30, stream=True)
    response.raise_for_status()
    
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return validate_pdf(save_path)

def validate_pdf(path: Path) -> bool:
    if path.stat().st_size < 50_000:  # < 50KB = likely an error page
        return False
    with open(path, "rb") as f:
        header = f.read(4)
    return header == b"%PDF"
```

---

### 5.5 `main.py` — CLI Entry Point (Serial Processing)

```python
import typer
from rich.console import Console
from rich.progress import track

app = typer.Typer()
console = Console()

@app.command()
def scrape(
    exam: str = typer.Argument(..., help="Exam name e.g. 'UPSC CSE'"),
    start_year: int = typer.Argument(..., help="Start year e.g. 2017"),
    end_year: int = typer.Argument(..., help="End year e.g. 2025"),
):
    years = list(range(start_year, end_year + 1))
    console.print(f"\n[bold]Scraping {exam} from {start_year} to {end_year}[/bold]\n")
    
    results = {}
    for year in years:  # SERIAL: one year at a time
        console.print(f"[cyan]→ Processing {exam} {year}...[/cyan]")
        success = process_year(exam, year)
        results[year] = "✓ Downloaded" if success else "✗ Not found"
    
    # Print final summary table
    from rich.table import Table
    table = Table(title=f"{exam} — Download Summary")
    table.add_column("Year"); table.add_column("Status")
    for year, status in results.items():
        table.add_row(str(year), status)
    console.print(table)

if __name__ == "__main__":
    app()
```

---

## 6. Anti-Bot & Anti-Block Strategies

### Strategy 1: Scrapling Stealth Mode
```python
fetcher = AsyncPlaywrightFetcher(
    stealth=True,       # Patches navigator, webdriver flags
    humanize=True,      # Random mouse movements, human scroll speed
    real_chrome=True,   # Use actual installed Chrome binary
)
```

### Strategy 2: Request Throttling
```python
import time, random

def human_delay():
    time.sleep(random.uniform(1.5, 4.0))  # 1.5–4 second delay between requests
```

### Strategy 3: User-Agent Rotation
```python
from fake_useragent import UserAgent
ua = UserAgent()
headers = {"User-Agent": ua.chrome}  # Random realistic Chrome UA
```

### Strategy 4: Proxy Rotation (Optional)
```python
# Use free proxies from proxyscrape or paid residential proxies
PROXIES = {"http": "http://proxy_ip:port", "https": "http://proxy_ip:port"}
requests.get(url, proxies=PROXIES)
```

### Strategy 5: Cloudflare Bypass
```python
import cloudscraper
scraper = cloudscraper.create_scraper()
response = scraper.get(url)
```

### Strategy 6: Cookie Persistence
```python
# Scrapling can persist sessions across requests
fetcher = AsyncPlaywrightFetcher(
    stealth=True,
    persist_cookies=True,  # Maintain session like a real user
)
```

---

## 7. Target Websites & Scraping Strategies

| Website Type | Example Sites | Scraping Method |
|---|---|---|
| Official exam board | upsc.gov.in, ssc.nic.in, tnpsc.gov.in | Scrapling (stealth) |
| Education portals | examrace.com, testbook.com | Scrapling + CSS selectors |
| PDF hosting | drive.google.com, scribd.com | Network intercept + direct URL |
| Education blogs | mrunal.org, insights | requests + BeautifulSoup |
| Archive sites | archive.org | Direct requests |

### CSS Selectors for Common Sites

```python
SITE_SELECTORS = {
    "examrace.com": "a.btn-download, a[href*='pdf']",
    "testbook.com": "a.download-btn, a[href$='.pdf']",
    "upsc.gov.in": "table a[href$='.pdf'], .content a[href*='question']",
    "default": "a[href$='.pdf'], a[href*='download'], a:contains('PDF')",
}
```

---

## 8. `config.py` — Central Configuration

```python
from pathlib import Path

BASE_DOWNLOAD_DIR = Path("./downloads")
LOG_DIR = Path("./logs")

# Search settings
MAX_SEARCH_RESULTS = 20
MAX_CANDIDATES_TO_SCORE = 10
MAX_CANDIDATES_TO_TRY = 3

# Download settings
MIN_PDF_SIZE_BYTES = 50_000   # 50 KB
DOWNLOAD_TIMEOUT_SEC = 30
MAX_RETRIES = 3

# Anti-bot settings
MIN_DELAY_SEC = 1.5
MAX_DELAY_SEC = 4.0

# LLM
LLM_MODEL = "claude-opus-4-5"
USE_LLM_SCORER = True  # Set False to skip LLM scoring (faster, less accurate)
```

---

## 9. Naming Convention for Downloaded Files

```
downloads/
  UPSC_CSE/
    2017/
      UPSC_CSE_2017_Paper1.pdf
      UPSC_CSE_2017_Paper2.pdf   (if multiple papers found)
    2018/
      UPSC_CSE_2018_Paper1.pdf
  SSC_CGL/
    2019/
      SSC_CGL_2019_Tier1.pdf
```

**File naming logic**:
```python
def make_filename(exam: str, year: int, index: int = 1) -> str:
    safe_exam = exam.replace(" ", "_").upper()
    return f"{safe_exam}_{year}_Paper{index}.pdf"

def make_save_path(exam: str, year: int, index: int = 1) -> Path:
    return BASE_DOWNLOAD_DIR / exam.replace(" ", "_") / str(year) / make_filename(exam, year, index)
```

---

## 10. Logging & Reporting

```python
from loguru import logger

logger.add("logs/scraper_{time:YYYY-MM-DD}.log", 
           rotation="1 day", 
           format="{time} | {level} | {message}")

# Usage
logger.info(f"[{exam} {year}] Searching for paper...")
logger.success(f"[{exam} {year}] Downloaded → {save_path}")
logger.warning(f"[{exam} {year}] PDF invalid (size: {size}B) — retrying")
logger.error(f"[{exam} {year}] All candidates failed — skipping")
```

---

## 11. Full Process Flow

```
START
  │
  ├─ Input: exam="UPSC CSE", start=2017, end=2025
  │
  └─ FOR year IN [2017, 2018, ..., 2025]:   ← SERIAL LOOP
       │
       ├─ STEP 1: Build 5 search query variants
       │
       ├─ STEP 2: Search DuckDuckGo (+ Bing fallback)
       │          → Collect up to 20 URLs
       │
       ├─ STEP 3: LLM scores URLs → Top 3 candidates
       │
       ├─ FOR candidate IN top_3:
       │    │
       │    ├─ STEP 4: Scrapling visits URL (stealth browser)
       │    │          → Finds direct PDF link on page
       │    │
       │    ├─ STEP 5: Download PDF (3 retries, exponential backoff)
       │    │
       │    ├─ STEP 6: Validate PDF (size + header check)
       │    │
       │    ├─ IF valid → Save to downloads/<exam>/<year>/
       │    │             Log SUCCESS → BREAK to next year
       │    │
       │    └─ IF invalid → Try next candidate
       │
       ├─ IF all 3 candidates fail → Log FAILURE, continue to next year
       │
       └─ Human delay: random 1.5–4 seconds before next year

END → Print summary table
```

---

## 12. Usage

```bash
# Install dependencies
pip install scrapling playwright duckduckgo-search anthropic \
            pdfplumber rich tenacity loguru fake-useragent \
            python-dotenv httpx typer

# Install Playwright browsers
playwright install chromium

# Set your API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# Run the scraper
python main.py "UPSC CSE" 2017 2025
python main.py "SSC CGL" 2019 2024
python main.py "TNPSC Group 2" 2017 2023
```

---

## 13. Limitations & How to Handle Them

| Problem | Solution |
|---|---|
| Site blocks bots | Use Scrapling stealth + `real_chrome=True` |
| PDF behind login wall | Skip + log, flag for manual download |
| Scribd / paid sites | Skip those domains in `BLOCKED_DOMAINS` list |
| No PDF found after 3 tries | Log as FAILED, continue to next year |
| Google Drive PDFs | Intercept direct download URL from network traffic |
| Multi-paper exams (Paper 1, 2) | Collect all `.pdf` links on page, download all |
| Wrong year's paper downloaded | Validate: check filename + first-page OCR for year |

---

## 14. GitHub Open Source Checklist

- [ ] `README.md` with usage, screenshots, feature list
- [ ] `requirements.txt` + `pyproject.toml`
- [ ] `.env.example` (never commit real keys)
- [ ] `.gitignore` — exclude `downloads/`, `logs/`, `.env`
- [ ] `LICENSE` — MIT recommended
- [ ] GitHub Actions CI to test search + download on a dummy PDF
- [ ] `CONTRIBUTING.md` — how to add new site scrapers
- [ ] Docker support — `Dockerfile` for reproducible environment

---

*Built with Scrapling + Claude API. Designed to work like a human researcher: search, evaluate, click, download.*
