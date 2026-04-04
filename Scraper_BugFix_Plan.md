# GovExam Scraper — Bug Fix & Simplification Plan
## Based on Live Log Analysis (IBPS Clerk 2020–2024 run)

---

## What the Logs Actually Reveal

### Bug 1 — WhatsApp Share Links Treated as PDFs
```
Downloading → https://api.whatsapp.com/send?text=IBPS+Clerk+Previous+Year...
Validation failed — invalid PDF header (b'<!DO')
```
The scraper finds `<a href="https://api.whatsapp.com/send?...">` on adda247 and bankersadda pages because
the link text contains "Download PDF". The link detector is matching anchor text, not URL structure.

### Bug 2 — Wrong Year Papers Saved in Wrong Year Folder
```
[IBPS Clerk 2021] Saved as IBPS_CLERK_2021_Prelims_5.pdf
← URL: IBPS_Clerk_Prelims_2017_Memory_Based_English_Language_Questions.pdf
[IBPS Clerk 2021] Saved as IBPS_CLERK_2021_Mains_7.pdf  
← URL: IBPS_CLERK_MAINS_2017_Reasoning_Memory_Based_Questions.pdf
[IBPS Clerk 2021] Saved as IBPS_CLERK_2021_Mains_20.pdf
← URL: IBPS_PO_Mains_2017_memory_based...  ← This is IBPS PO, not Clerk!
```
adda247's page `/ibps-clerk-previous-year-question-paper/` contains ALL years (2017–2024)
in one page. The scraper downloads every PDF on the page regardless of which year is being targeted.
39 PDFs downloaded for "2021" — most are from 2017, 2018, 2019.

### Bug 3 — Gemini Scorer 404 on Every Call
```
WARNING | Gemini scoring failed (404 models/gemini-1.5-flash is not found...)
— falling back to heuristic scorer
```
This fires for EVERY search phase. It's dead weight — burning time and showing warnings.
Either fix the model name or remove the Gemini scorer entirely.

### Bug 4 — prepp.in Year-Specific URLs Work Perfectly
```
Scrapling → https://prepp.in/ibps-clerk-exam/question-paper-2020 → 3 PDFs ✓
Scrapling → https://prepp.in/ibps-clerk-exam/question-paper-2022 → 6 PDFs ✓  
Scrapling → https://prepp.in/ibps-clerk-exam/question-paper-2023 → 6 PDFs ✓
```
Every PDF from prepp.in has the correct year in the CDN filename:
`IBPS_Clerk_Prelims_Memory_Based_Paper_Held_on_4th_September_2022_...pdf`
This is your best source. It should be tried FIRST for every year.

---

## The 5 Fixes (in priority order)

---

### FIX 1 — Block Social Share and Junk Links (2 lines of code)

**File**: `scraper/browser_scraper.py`

Add a blocklist that rejects URLs before any download attempt:

```python
JUNK_URL_PATTERNS = [
    "api.whatsapp.com",
    "facebook.com/sharer",
    "twitter.com/intent",
    "t.me/",
    "telegram.me/",
    "linkedin.com/sharing",
    "youtube.com",
    "instagram.com",
    "#",                    # anchor-only links
    "javascript:",          # JS void links
    "mailto:",              # email links
]

def is_junk_url(url: str) -> bool:
    url_lower = url.lower()
    return any(pattern in url_lower for pattern in JUNK_URL_PATTERNS)

# In your PDF link collection loop:
pdf_links = [
    link for link in all_found_links
    if not is_junk_url(link)
    and (link.endswith(".pdf") or is_trusted_download_cdn(link))
]
```

**Trusted CDN check** (real PDF hosts, not share buttons):
```python
TRUSTED_CDNS = [
    "cdn-images.prepp.in",
    "adda247.com/jobs/wp-content/uploads",
    "bankersadda.com/wp-content/uploads",
    "careerpower.in/",
    "ssc.nic.in",
    "upsc.gov.in",
    "ibps.in",
]

def is_trusted_download_cdn(url: str) -> bool:
    return any(cdn in url for cdn in TRUSTED_CDNS)
```

---

### FIX 2 — Year Filter on Every Downloaded URL

**File**: `scraper/downloader.py` or `main.py`

Before downloading any PDF, check if the target year appears in:
- the URL/filename
- OR the anchor text that linked to it

```python
import re

def url_matches_year(url: str, anchor_text: str, target_year: int) -> bool:
    """Return True if this link is relevant to the target year."""
    
    # Extract all 4-digit years found in URL and anchor text
    years_in_url = set(int(y) for y in re.findall(r'\b(20\d{2})\b', url))
    years_in_text = set(int(y) for y in re.findall(r'\b(20\d{2})\b', anchor_text))
    all_years_found = years_in_url | years_in_text
    
    # If the URL/text mentions a DIFFERENT year explicitly, reject it
    if all_years_found and target_year not in all_years_found:
        return False
    
    # If no year is mentioned at all in the URL, allow it (general page)
    return True

# Usage in download loop:
for link, anchor_text in found_links:
    if not url_matches_year(link, anchor_text, target_year=2021):
        logger.debug(f"Skipping — year mismatch: {link[:80]}")
        continue
    download_pdf(link, save_path)
```

**This alone eliminates the 2017/2018 papers being saved into the 2021 folder.**

---

### FIX 3 — Reorder Sources: prepp.in First, Always

**File**: `config.py` or `EXAM_SOURCE_MAP`

From the logs, prepp.in's year-specific URL pattern works for 2020, 2022, 2023 and returns
only that year's papers from CDN. Make it the FIRST source tried for every exam:

```python
IBPS_CLERK_SOURCES = [
    # FIRST: prepp.in year-specific URL (most reliable from logs)
    {
        "site": "prepp.in",
        "url_template": "https://prepp.in/ibps-clerk-exam/question-paper-{year}",
        "year_aware": True,      # URL changes per year — always correct papers
    },
    # SECOND: bankersadda (found real 2024 paper)
    {
        "site": "bankersadda.com",
        "url_template": "https://www.bankersadda.com/ibps-clerk-previous-year-question-papers/",
        "year_aware": False,     # Has ALL years — MUST apply year filter on links
    },
    # THIRD: adda247 (has all years — apply strict year filter)
    {
        "site": "adda247.com",
        "url_template": "https://www.adda247.com/jobs/ibps-clerk-previous-year-question-paper/",
        "year_aware": False,     # Apply year filter aggressively
    },
    # SKIP: testbook (consistent 404 in every log line)
    # SKIP: oliveboard (consistent 520 errors in every log line)
    # SKIP: cracku (consistent 0 results)
]
```

**Remove testbook, oliveboard, cracku for IBPS Clerk** — they return 0 results in 100% of log entries.

---

### FIX 4 — Replace Broken Gemini Scorer with Simple Heuristic

**File**: `scraper/link_scorer.py`

Gemini throws 404 on every call. Remove it. The heuristic is already running anyway.
Replace with a clean local scorer — no API needed:

```python
DOMAIN_SCORES = {
    "cdn-images.prepp.in": 100,     # Direct CDN — always real PDFs
    "prepp.in": 90,
    "bankersadda.com/wp-content": 90,
    "adda247.com/jobs/wp-content": 85,
    "careerpower.in": 80,
    "cracku.in": 70,
    "examrace.com": 65,
    "affairscloud.com": 60,
    "sarkaripaperwale.com": 30,     # Low quality from logs
    "zhihu.com": -100,              # Block
    "quora.com": -100,              # Block
    "api.whatsapp.com": -100,       # Block
}

URL_BONUS = {
    ".pdf": +20,
    str(target_year): +15,          # Year in URL = strong signal
    "memory-based": +10,
    "previous-year": +8,
    "question-paper": +8,
    "prelims": +5,
    "mains": +5,
    "solution": -5,                 # Solutions != question papers
    "notification": -20,            # Admin docs
    "admit-card": -20,
    "result": -20,
    "syllabus": -15,
}

def score_url(url: str, target_year: int) -> int:
    score = 0
    url_lower = url.lower()
    
    for domain, pts in DOMAIN_SCORES.items():
        if domain in url_lower:
            score += pts
            break
    
    for keyword, pts in URL_BONUS.items():
        key = str(keyword).lower().replace("{target_year}", str(target_year))
        if key in url_lower:
            score += pts
    
    return score

def rank_candidates(urls: list[str], target_year: int) -> list[str]:
    scored = [(url, score_url(url, target_year)) for url in urls]
    scored = [(url, s) for url, s in scored if s > 0]   # reject negatives
    scored.sort(key=lambda x: x[1], reverse=True)
    return [url for url, _ in scored]
```

---

### FIX 5 — Playwright Full-Page Analysis for Fallback

When all known URLs fail, use Playwright to **read the page like a human** and find PDFs:

```python
from playwright.async_api import async_playwright
import re

async def playwright_full_page_scan(url: str, target_year: int, exam: str) -> list[str]:
    """
    Load the full page in a real browser.
    Find all links that could be question paper PDFs for the target year.
    """
    found_pdfs = []
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        
        # Intercept network — catch PDF downloads that don't show as <a href>
        pdf_urls_from_network = []
        async def handle_request(request):
            if ".pdf" in request.url and str(target_year) in request.url:
                pdf_urls_from_network.append(request.url)
        page.on("request", handle_request)
        
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        # Strategy 1: All <a> tags — filter by year and exam
        all_links = await page.eval_on_selector_all(
            "a[href]",
            """elements => elements.map(el => ({
                href: el.href,
                text: el.textContent.trim(),
                title: el.title || ''
            }))"""
        )
        
        for link in all_links:
            href = link["href"]
            text = link["text"].lower()
            
            # Reject junk
            if is_junk_url(href):
                continue
            
            # Must match year
            if not url_matches_year(href, text, target_year):
                continue
            
            # Must look like a paper (not a notification/result/admit card)
            bad_keywords = ["admit", "result", "notification", "syllabus", 
                           "answer-key", "answer_key", "whatsapp", "telegram"]
            if any(bk in href.lower() or bk in text for bk in bad_keywords):
                continue
            
            # Good keywords
            good_keywords = [".pdf", "question-paper", "previous-year", 
                           "prelims", "mains", "paper", str(target_year)]
            if any(gk in href.lower() or gk in text for gk in good_keywords):
                found_pdfs.append(href)
        
        # Strategy 2: Click "Download" buttons and intercept the resulting PDF URL
        download_buttons = await page.query_selector_all(
            "button:has-text('Download'), a:has-text('Download PDF'), "
            "a:has-text('Click Here'), [data-action='download']"
        )
        
        for btn in download_buttons[:10]:   # limit to 10 buttons
            btn_text = await btn.text_content()
            if not url_matches_year("", btn_text or "", target_year):
                continue
            try:
                async with page.expect_download(timeout=5000) as dl:
                    await btn.click()
                download = await dl.value
                found_pdfs.append(download.url)
            except Exception:
                pass    # button didn't trigger a download — skip
        
        # Strategy 3: Network-intercepted PDF URLs
        found_pdfs.extend(pdf_urls_from_network)
        
        await browser.close()
    
    # Deduplicate and rank
    found_pdfs = list(set(found_pdfs))
    return rank_candidates(found_pdfs, target_year)
```

---

## Simplified Main Loop (what main.py should look like)

```python
async def process_year(exam: str, year: int, exam_config: dict) -> list[Path]:
    saved = []

    # ── PHASE 1: Year-aware direct URLs (prepp.in style) ──────────────────
    for source in exam_config["sources"]:
        if not source.get("year_aware"):
            continue
        url = source["url_template"].format(year=year)
        links = await scrape_page_for_pdfs(url, year)      # basic Scrapling
        links = [l for l in links if url_matches_year(l, "", year)]
        for link in links:
            path = await download_and_validate(link, exam, year)
            if path:
                saved.append(path)
        if saved:
            logger.success(f"[{exam} {year}] Phase 1 done — {len(saved)} papers")
            return saved

    # ── PHASE 2: Non-year-aware sites WITH strict year filter ─────────────
    for source in exam_config["sources"]:
        if source.get("year_aware"):
            continue                                        # already tried above
        url = source["url_template"]
        links = await scrape_page_for_pdfs(url, year)
        links = [l for l in links if url_matches_year(l, "", year)]
        for link in links:
            path = await download_and_validate(link, exam, year)
            if path:
                saved.append(path)
        if saved:
            logger.success(f"[{exam} {year}] Phase 2 found papers from {source['site']}")
            return saved

    # ── PHASE 3: Playwright full-page scan on best candidates ─────────────
    for source in exam_config["sources"]:
        url = source["url_template"].format(year=year)
        links = await playwright_full_page_scan(url, year, exam)
        for link in links[:5]:                              # top 5 only
            path = await download_and_validate(link, exam, year)
            if path:
                saved.append(path)
        if saved:
            return saved

    # ── PHASE 4: Web search (last resort) ─────────────────────────────────
    query = f'"{exam}" {year} question paper filetype:pdf -youtube -whatsapp'
    candidates = web_search(query)
    candidates = rank_candidates(candidates, year)
    for url in candidates[:5]:
        links = await playwright_full_page_scan(url, year, exam)
        for link in links[:3]:
            path = await download_and_validate(link, exam, year)
            if path:
                saved.append(path)
        if saved:
            return saved

    logger.error(f"[{exam} {year}] All phases failed")
    return []
```

---

## Summary: What Changes

| Issue in Logs | Root Cause | Fix |
|---|---|---|
| WhatsApp URLs downloaded | Link detector matches anchor text, not URL | Block `api.whatsapp.com` and social domains |
| 2017 papers in 2021 folder | adda247 page has all years, no year filter | Year filter on every URL before download |
| 39 PDFs per year (most wrong) | No year check on filenames from CDN | Regex year check on URL path/filename |
| Gemini 404 on every call | Wrong model name | Remove Gemini, use local heuristic scorer |
| testbook 404 every time | Wrong URL slug for IBPS Clerk | Remove testbook from IBPS Clerk sources |
| oliveboard 520 every time | Site blocks scrapers | Remove oliveboard, it never works |
| cracku 0 results every time | PDFs hidden behind JS login | Remove cracku for banking exams |
| prepp.in works perfectly | Year-specific CDN URLs | Make prepp.in FIRST source, always |

---

## Files to Change

```
scraper/
  browser_scraper.py   ← Add is_junk_url(), is_trusted_cdn()
  link_scorer.py       ← Replace Gemini with local domain scorer
  downloader.py        ← Add url_matches_year() check before every download
  playwright_scanner.py  ← NEW: full-page scan + network intercept
config.py              ← Reorder sources: prepp first, remove testbook/oliveboard/cracku
main.py                ← Simplified 4-phase loop (no more 8 DDG queries per year)
```

Total code changes: ~150 lines across 5 files.
```
