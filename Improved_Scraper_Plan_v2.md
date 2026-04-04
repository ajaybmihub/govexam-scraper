# Government Exam Scraper — Improved Plan v2
## Direct Multi-Source Targeting (No Web Search Dependency)

> **Core Problem Solved**: Web search is unreliable and inaccurate for finding PDFs.  
> **New Strategy**: Go directly to trusted sources in priority order. Web search is now only a last-resort fallback.

---

## 1. The Core Shift in Architecture

### ❌ Old Approach (Unreliable)
```
Web Search → Score URLs → Hope one has a PDF
```

### ✅ New Approach (Reliable)
```
Exam Input → Map to Source Priority List → Direct Scrape Each Site in Order → Download PDF
```

Every exam is mapped to a **ranked source list**. The scraper visits sites directly — no search engine needed. Web search is only triggered if ALL trusted sources fail.

---

## 2. Source Priority Tiers (from your XLSX + your chat links)

### 🔴 TIER 0 — Your High-Priority Sites (Always Try First)
These are tried for EVERY exam, in this order:

| # | Website | Best Query Style |
|---|---|---|
| 1 | `testbook.com` | `/previous-papers/{exam-slug}/` |
| 2 | `adda247.com` | `/question-papers/{exam-slug}/` |
| 3 | `careerpower.in` | `/blog/{exam} question paper {year}` |
| 4 | `prepp.in` | `/previous-year-papers/{exam-slug}/` |
| 5 | `cracku.in` | `/{exam-slug}-previous-papers/` |

### 🟠 TIER 1 — Official Government Sites (Exam-Specific)
Direct PDF links. Highest authority, slowest to navigate.

| Website | Mapped Exams |
|---|---|
| `upsc.gov.in` | UPSC CSE, UPSC CDS, UPSC CAPF, IFS |
| `ssc.nic.in` | SSC CGL, SSC CHSL, SSC MTS, SSC CPO |
| `ibps.in` | IBPS PO, IBPS Clerk, IBPS SO, IBPS RRB |
| `rbi.org.in` | RBI Grade B, RBI Assistant |
| `rrbcdg.gov.in` | RRB NTPC, RRB Group D, RRB JE |
| `tnpsc.gov.in` | TNPSC Group 1, Group 2, Group 4 |
| `mpsc.gov.in` | MPSC Rajyaseva, MPSC STI |
| `rpsc.rajasthan.gov.in` | RPSC RAS, RPSC 2nd Grade |

### 🟡 TIER 2 — Top Priority Education Sites (from your XLSX)
High content volume, structured, easy to scrape.

| Website | Category | Difficulty |
|---|---|---|
| `affairscloud.com` | GK, SSC, Banking | Easy |
| `gktoday.in` | GK, Current Affairs | Easy |
| `bankersadda.com` | Banking, SSC | Medium |
| `jagranjosh.com` | Govt Exams | Medium |
| `examrace.com` | All Govt PYQs | Medium |

### 🟢 TIER 3 — Static Easy Sites
No JS rendering needed, scrape-friendly HTML.

| Website | Best For |
|---|---|
| `indiabix.com` | Aptitude, Reasoning |
| `examveda.com` | GK, Aptitude |
| `freejobalert.com` | Govt exams |

### ⚪ TIER 4 — Fallback (Web Search)
Only triggered if TIER 0–3 all return nothing.

```python
query = f'"{exam_full_name}" {year} question paper PDF -site:youtube.com'
# Use DuckDuckGo, then Bing as second fallback
```

---

## 3. Exam → Site Mapping (Intelligent Router)

```python
EXAM_SOURCE_MAP = {
    # UPSC Exams
    "UPSC CSE": {
        "full_name": "Civil Services Examination",
        "official": "upsc.gov.in",
        "tier0": ["testbook.com", "adda247.com", "prepp.in", "cracku.in", "careerpower.in"],
        "tier2": ["affairscloud.com", "gktoday.in", "examrace.com", "jagranjosh.com"],
        "search_query": 'Civil Services Examination (CSE) {year} question paper PDF',
        "papers": ["GS1", "GS2", "GS3", "GS4", "Essay"],  # multiple papers per year
    },
    "UPSC CDS": {
        "full_name": "Combined Defence Services",
        "official": "upsc.gov.in",
        "tier0": ["testbook.com", "adda247.com", "cracku.in", "careerpower.in"],
        "tier2": ["examrace.com", "affairscloud.com"],
        "search_query": 'CDS {year} question paper PDF Combined Defence Services',
        "papers": ["Math", "GK", "English"],
    },
    
    # SSC Exams
    "SSC CGL": {
        "full_name": "SSC Combined Graduate Level",
        "official": "ssc.nic.in",
        "tier0": ["testbook.com", "adda247.com", "careerpower.in", "prepp.in", "cracku.in"],
        "tier2": ["bankersadda.com", "affairscloud.com", "examrace.com"],
        "search_query": 'SSC CGL {year} question paper PDF Tier 1',
        "papers": ["Tier1", "Tier2"],
    },
    "SSC CHSL": {
        "full_name": "SSC Combined Higher Secondary Level",
        "official": "ssc.nic.in",
        "tier0": ["testbook.com", "adda247.com", "careerpower.in", "cracku.in"],
        "tier2": ["bankersadda.com", "affairscloud.com"],
        "search_query": 'SSC CHSL {year} question paper PDF',
        "papers": ["Tier1"],
    },
    
    # Banking Exams
    "IBPS PO": {
        "full_name": "IBPS Probationary Officer",
        "official": "ibps.in",
        "tier0": ["testbook.com", "adda247.com", "careerpower.in", "prepp.in", "cracku.in"],
        "tier2": ["bankersadda.com", "affairscloud.com", "gktoday.in"],
        "search_query": 'IBPS PO {year} question paper PDF Probationary Officer',
        "papers": ["Prelims", "Mains"],
    },
    "IBPS Clerk": {
        "full_name": "IBPS Clerk",
        "official": "ibps.in",
        "tier0": ["testbook.com", "adda247.com", "careerpower.in", "cracku.in"],
        "tier2": ["bankersadda.com", "affairscloud.com"],
        "search_query": 'IBPS Clerk {year} question paper PDF',
        "papers": ["Prelims", "Mains"],
    },
    "RBI Grade B": {
        "full_name": "Reserve Bank of India Grade B",
        "official": "rbi.org.in",
        "tier0": ["testbook.com", "adda247.com", "careerpower.in", "prepp.in"],
        "tier2": ["bankersadda.com", "examrace.com"],
        "search_query": 'RBI Grade B {year} question paper PDF',
        "papers": ["Phase1", "Phase2"],
    },
    
    # Railway Exams
    "RRB NTPC": {
        "full_name": "Railway Recruitment Board NTPC",
        "official": "rrbcdg.gov.in",
        "tier0": ["testbook.com", "adda247.com", "careerpower.in", "cracku.in"],
        "tier2": ["affairscloud.com", "examrace.com", "freejobalert.com"],
        "search_query": 'RRB NTPC {year} question paper PDF Railway',
        "papers": ["CBT1", "CBT2"],
    },
    
    # State PSC
    "TNPSC Group 2": {
        "full_name": "TNPSC Group 2",
        "official": "tnpsc.gov.in",
        "tier0": ["testbook.com", "adda247.com", "cracku.in", "careerpower.in"],
        "tier2": ["affairscloud.com", "examrace.com"],
        "search_query": 'TNPSC Group 2 {year} question paper PDF Tamil Nadu',
        "papers": ["Paper1", "Paper2"],
    },
    # Add more exams following the same pattern...
}
```

---

## 4. Site-Specific Scraper Strategies

Each site needs its own scraping method. Here's the blueprint for each:

---

### 4.1 `testbook.com` — Tier 0 Priority

**URL pattern**: `https://testbook.com/question-paper/{exam-slug}-question-paper`  
**Method**: Scrapling stealth (JS-rendered page)

```python
TESTBOOK_EXAM_SLUGS = {
    "UPSC CSE": "upsc",
    "SSC CGL": "ssc-cgl",
    "IBPS PO": "ibps-po",
    "RRB NTPC": "rrb-ntpc",
    "TNPSC Group 2": "tnpsc-group-2",
}

async def scrape_testbook(exam: str, year: int):
    slug = TESTBOOK_EXAM_SLUGS.get(exam)
    url = f"https://testbook.com/question-paper/{slug}-question-paper"
    
    page = await fetcher.fetch(url)
    
    # Find year-specific section
    year_sections = page.css(f"[data-year='{year}'], h3:contains('{year}'), div:contains('{year}')")
    
    # Find download links near year mentions
    pdf_links = page.css(f"a[href*='{year}'][href$='.pdf'], a[href*='download'][href*='{year}']")
    
    # Testbook often has "Download PDF" buttons
    download_btns = page.css("a.download-btn, button:contains('Download PDF'), a:contains('Download')")
    
    return extract_pdf_urls(pdf_links + download_btns, year)
```

---

### 4.2 `adda247.com` — Tier 0 Priority

**URL patterns**:
- `https://www.adda247.com/question-paper/{exam-slug}/`
- `https://www.adda247.com/{exam-slug}-previous-year-question-paper/`

```python
ADDA247_EXAM_SLUGS = {
    "UPSC CSE": "upsc-previous-year-question-papers",
    "SSC CGL": "ssc-cgl-previous-year-papers",
    "IBPS PO": "ibps-po-previous-year-papers",
    "RRB NTPC": "rrb-ntpc-previous-year-papers",
}

async def scrape_adda247(exam: str, year: int):
    slug = ADDA247_EXAM_SLUGS.get(exam)
    urls_to_try = [
        f"https://www.adda247.com/{slug}/",
        f"https://www.adda247.com/question-paper/{slug}/",
    ]
    for url in urls_to_try:
        page = await fetcher.fetch(url)
        # Adda247 uses article cards with year in title
        year_links = page.css(f"a[href*='{year}'], .card-title:contains('{year}')")
        if year_links:
            return await follow_and_find_pdf(year_links[0], year)
```

---

### 4.3 `careerpower.in` — Tier 0 Priority

**URL pattern**: Blog post style — search within site

```python
async def scrape_careerpower(exam: str, year: int):
    # CareerPower uses blog structure — search their site
    search_url = f"https://www.careerpower.in/?s={exam}+{year}+question+paper"
    page = await fetcher.fetch(search_url)
    
    # Get first matching blog post
    post_links = page.css("article a.read-more, h2.entry-title a, .post-title a")
    
    for post_link in post_links[:3]:
        post_page = await fetcher.fetch(post_link)
        pdf_links = post_page.css("a[href$='.pdf'], a:contains('Download'), .download-link")
        if pdf_links:
            return filter_by_year(pdf_links, year)
```

---

### 4.4 `prepp.in` — Tier 0 Priority

**URL pattern**: `https://prepp.in/{exam-slug}-previous-year-question-papers/`

```python
PREPP_EXAM_SLUGS = {
    "UPSC CSE": "ias",
    "SSC CGL": "ssc-cgl",
    "IBPS PO": "ibps-po",
    "TNPSC Group 2": "tnpsc-group-2",
}

async def scrape_prepp(exam: str, year: int):
    slug = PREPP_EXAM_SLUGS.get(exam)
    url = f"https://prepp.in/{slug}-previous-year-question-papers/"
    page = await fetcher.fetch(url)
    
    # Prepp uses tables with year column
    rows = page.css("table tr, .paper-row, .year-row")
    year_rows = [r for r in rows if str(year) in r.text]
    
    for row in year_rows:
        pdf_link = row.css("a[href$='.pdf'], a.download")
        if pdf_link:
            return pdf_link[0].attrib("href")
```

---

### 4.5 `cracku.in` — Tier 0 Priority

**URL pattern**: `https://cracku.in/{exam-slug}-previous-papers`

```python
CRACKU_EXAM_SLUGS = {
    "UPSC CSE": "upsc-previous-papers",
    "SSC CGL": "ssc-cgl-previous-papers",
    "IBPS PO": "ibps-po-previous-papers",
    "RRB NTPC": "rrb-ntpc-previous-papers",
    "TNPSC Group 2": "tnpsc-group-2-previous-papers",
}

async def scrape_cracku(exam: str, year: int):
    slug = CRACKU_EXAM_SLUGS.get(exam)
    url = f"https://cracku.in/{slug}"
    page = await fetcher.fetch(url)
    
    # Cracku organises by year sections
    year_section = page.css(f"[id*='{year}'], h2:contains('{year}'), h3:contains('{year}')")
    if year_section:
        nearby_links = year_section[0].css("~ a[href$='.pdf'], ~ .download-btn")
        return nearby_links
```

---

### 4.6 `upsc.gov.in` — Tier 1 Official

**Navigation**: Question Papers → Civil Services (Preliminary) → Year

```python
UPSC_PAPER_PATHS = {
    "UPSC CSE": "/ExamNotifications.aspx?exam=5",
    "UPSC CDS": "/ExamNotifications.aspx?exam=13",
    "UPSC CAPF": "/ExamNotifications.aspx?exam=10",
}

async def scrape_upsc_gov(exam: str, year: int):
    base = "https://upsc.gov.in"
    path = UPSC_PAPER_PATHS.get(exam)
    
    page = await fetcher.fetch(base + path)
    
    # UPSC lists PDFs in table rows with year in filename
    all_links = page.css("table a[href*='.pdf'], .content a[href$='.pdf']")
    year_links = [l for l in all_links if str(year) in l.attrib("href") or str(year) in l.text]
    
    return [base + l.attrib("href") if l.attrib("href").startswith("/") else l.attrib("href") 
            for l in year_links]
```

---

### 4.7 `affairscloud.com` — Tier 2 (Easy)

**URL pattern**: `https://affairscloud.com/{exam}-question-papers/`

```python
async def scrape_affairscloud(exam: str, year: int):
    # Very structured — find year heading then download link
    exam_slug = exam.lower().replace(" ", "-")
    url = f"https://affairscloud.com/{exam_slug}-question-papers/"
    page = await fetcher.fetch(url)  # No JS needed — static HTML
    
    year_anchors = page.css(f"h2:contains('{year}'), h3:contains('{year}'), strong:contains('{year}')")
    for anchor in year_anchors:
        links = anchor.css("~ a[href$='.pdf'], + p a, + ul a")
        if links:
            return links
```

---

## 5. Improved Search Query Tuning (Fallback Only)

When all direct sources fail, use these tuned query formats:

```python
SEARCH_QUERY_FORMATS = [
    # Format 1: Full official name (most precise)
    '"{full_name}" {year} question paper filetype:pdf',
    
    # Format 2: Short name with site restrictions
    '{exam} {year} previous year question paper pdf site:testbook.com OR site:adda247.com OR site:cracku.in',
    
    # Format 3: Official site first
    '{exam} {year} question paper site:{official_site}',
    
    # Format 4: Broad with year
    '"{exam}" "{year}" "question paper" "download" pdf',
    
    # Format 5: Alternative phrasing
    '{exam} {year} solved paper pdf download -youtube -instagram',
]

# Example output for UPSC CSE 2020:
# → 'Civil Services Examination (CSE) 2020 question paper filetype:pdf'
# → 'UPSC CSE 2020 previous year question paper pdf site:testbook.com OR site:adda247.com'
# → 'UPSC CSE 2020 question paper site:upsc.gov.in'
```

---

## 6. Updated Full Process Flow

```
INPUT: exam="UPSC CSE", year_range=2017-2025
       ↓
       Map exam → source list from EXAM_SOURCE_MAP
       
FOR EACH YEAR (serial: 2017 → 2018 → ... → 2025):
  │
  ├─ TIER 0 — Try your high-priority sites (testbook, adda247, careerpower, prepp, cracku)
  │   FOR EACH site in Tier 0:
  │     → Direct URL visit using site-specific scraper
  │     → Find PDF link for this exact year
  │     → If found → Download → Validate → SAVE ✓ → Skip to next year
  │
  ├─ TIER 1 — Official government site
  │     → Navigate to exam's page on official site
  │     → Find PDF link with year in filename/text
  │     → If found → Download → Validate → SAVE ✓ → Skip to next year
  │
  ├─ TIER 2 — Education portals (affairscloud, gktoday, bankersadda, examrace)
  │     FOR EACH site in Tier 2:
  │       → Direct URL visit
  │       → If found → Download → Validate → SAVE ✓
  │
  ├─ TIER 3 — Static easy sites (indiabix, examveda, freejobalert)
  │     → Only for aptitude/reasoning exams
  │
  └─ TIER 4 — FALLBACK: Web search (last resort)
        → 5 tuned query variants
        → DuckDuckGo → Bing
        → Score results → Visit top 3
        → If found → Download → Validate → SAVE ✓
        → If still nothing → LOG as FAILED ✗
  
  Human delay: 1.5–3.5 seconds before next year
```

---

## 7. Updated Folder + Naming Structure

```
downloads/
  UPSC_CSE/
    2017/
      UPSC_CSE_2017_GS1.pdf
      UPSC_CSE_2017_GS2.pdf
      UPSC_CSE_2017_GS3.pdf
      UPSC_CSE_2017_GS4.pdf
      UPSC_CSE_2017_Essay.pdf
    2018/
      UPSC_CSE_2018_GS1.pdf
  SSC_CGL/
    2019/
      SSC_CGL_2019_Tier1.pdf
      SSC_CGL_2019_Tier2.pdf
  IBPS_PO/
    2020/
      IBPS_PO_2020_Prelims.pdf
      IBPS_PO_2020_Mains.pdf
```

**Naming logic**:
```python
def make_save_path(exam: str, year: int, paper_label: str) -> Path:
    safe_exam = exam.strip().replace(" ", "_").upper()
    safe_label = paper_label.replace(" ", "_")
    filename = f"{safe_exam}_{year}_{safe_label}.pdf"
    return BASE_DOWNLOAD_DIR / safe_exam / str(year) / filename
```

---

## 8. Site Slug Registry (Central Config)

Maintain one central `SITE_SLUGS` dict that maps `(exam, site)` → URL path:

```python
SITE_SLUGS = {
    # (exam_key, site_key): url_path_or_slug
    ("UPSC CSE", "testbook"):  "upsc-question-paper",
    ("UPSC CSE", "adda247"):   "upsc-previous-year-question-papers",
    ("UPSC CSE", "prepp"):     "ias-previous-year-question-papers",
    ("UPSC CSE", "cracku"):    "upsc-previous-papers",
    ("UPSC CSE", "careerpower"): None,  # blog search style

    ("SSC CGL", "testbook"):   "ssc-cgl-question-paper",
    ("SSC CGL", "adda247"):    "ssc-cgl-previous-year-papers",
    ("SSC CGL", "cracku"):     "ssc-cgl-previous-papers",
    ("SSC CGL", "prepp"):      "ssc-cgl-previous-year-question-papers",
    
    ("IBPS PO", "testbook"):   "ibps-po-question-paper",
    ("IBPS PO", "adda247"):    "ibps-po-previous-year-papers",
    ("IBPS PO", "cracku"):     "ibps-po-previous-papers",
    
    ("RRB NTPC", "testbook"):  "rrb-ntpc-question-paper",
    ("RRB NTPC", "adda247"):   "rrb-ntpc-previous-year-papers",
    ("RRB NTPC", "cracku"):    "rrb-ntpc-previous-papers",
    
    ("TNPSC Group 2", "cracku"): "tnpsc-group-2-previous-papers",
    # ... expand for all exam+site combinations
}
```

---

## 9. PDF Link Detection — Universal Logic

After loading any page, use this layered detection to find PDF links:

```python
def detect_pdf_links(page, year: int) -> list[str]:
    found = []
    
    # Layer 1: Direct .pdf hrefs
    direct = page.css("a[href$='.pdf']").attrib("href")
    found.extend(direct)
    
    # Layer 2: Download buttons with PDF context
    btn_links = page.css(
        "a[href*='download'], "
        "a.btn-download, "
        "a.download-link, "
        "a:contains('Download PDF'), "
        "a:contains('Download Question Paper'), "
        "button:contains('Download')"
    ).attrib("href")
    found.extend(btn_links)
    
    # Layer 3: Google Drive embeds
    drive_iframes = page.css("iframe[src*='drive.google.com']").attrib("src")
    for src in drive_iframes:
        # Convert embed URL to direct download URL
        file_id = re.search(r'/d/([^/]+)', src)
        if file_id:
            found.append(f"https://drive.google.com/uc?export=download&id={file_id.group(1)}")
    
    # Layer 4: Filter by year (keep only year-relevant links)
    year_filtered = [url for url in found 
                     if str(year) in url or not any(str(y) in url for y in range(2010, 2030))]
    
    return list(set(year_filtered))
```

---

## 10. Updated Requirements

```txt
# requirements.txt

# Scraping
scrapling>=0.2.0
playwright>=1.40.0

# HTTP
requests>=2.31.0
httpx>=0.25.0
cloudscraper>=1.2.71

# AI Scoring (optional — only for fallback web search scoring)
anthropic>=0.20.0

# PDF
pdfplumber>=0.10.0

# Search fallback
duckduckgo-search>=5.0.0

# Retry & timing
tenacity>=8.2.0

# Anti-detection
fake-useragent>=1.4.0

# CLI & UI
typer>=0.9.0
rich>=13.0.0

# Utilities
python-dotenv>=1.0.0
loguru>=0.7.0
tldextract>=5.1.0
openpyxl>=3.1.0  # to read your source xlsx at runtime
```

---

## 11. Usage

```bash
# Basic usage
python main.py "UPSC CSE" 2017 2025

# Single year
python main.py "SSC CGL" 2022 2022

# With verbose logging
python main.py "IBPS PO" 2018 2024 --verbose

# Skip fallback web search (faster)
python main.py "TNPSC Group 2" 2017 2023 --no-search-fallback

# Force re-download even if file exists
python main.py "RRB NTPC" 2019 2023 --force
```

---

## 12. What Changed from v1

| v1 (Old) | v2 (New — This Plan) |
|---|---|
| Web search → hope for results | Direct site visit using known URL patterns |
| Generic URL scraping | Site-specific scrapers per domain |
| LLM scores all URLs | LLM only used for fallback web search results |
| Single paper assumed | Multiple papers per year (GS1, GS2, Prelims, Mains...) |
| No exam mapping | EXAM_SOURCE_MAP with full_name, papers, official site |
| No slug registry | SITE_SLUGS registry for deterministic URL construction |
| Web search = Step 1 | Web search = Last Resort (Tier 4) |
| No Google Drive handling | Google Drive embed → direct download URL conversion |

---

*Sources from your XLSX incorporated. Tier 0 = your 5 priority sites. Tier 1 = official boards. Tier 2 = XLSX Top Priority. Tier 3 = XLSX Static Easy.*
