# 🎓 GovExam Scraper

> **A multi-source intelligent scraping agent** that hunts, downloads, and organises government exam question papers like a human researcher.

---

## ✨ Features

| Feature | Detail |
|---|---|
| 🔍 Multi-source search | DuckDuckGo primary + Bing fallback, 5 query variants/year |
| 🧠 LLM-powered ranking | Claude API ranks URLs by relevance before visiting |
| 🥷 Stealth browser | Scrapling + Playwright handles JS, Cloudflare, popups |
| 🔁 Retry logic | Tenacity exponential backoff — 3 retries per download |
| ✅ PDF validation | Size check + `%PDF` magic-byte header verification |
| 🚦 Anti-bot | UA rotation, human delays (1.5–4s), realistic headers |
| 📁 Structured output | `downloads/<ExamName>/<Year>/paper.pdf` |
| 📋 Rich UI | Progress bar + colour-coded summary table in terminal |

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
cd govexam-scraper
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure API key (optional but recommended)

```bash
copy .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Run

```bash
# Scrape UPSC CSE 2017–2025
python main.py "UPSC CSE" 2017 2025

# Without LLM scoring (faster, no API key needed)
python main.py "SSC CGL" 2019 2024 --no-llm

# Force re-download even if files exist
python main.py "TNPSC Group 2" 2020 2023 --no-skip
```

---

## 📂 Output Structure

```
downloads/
  UPSC_CSE/
    2017/
      UPSC_CSE_2017_Paper1.pdf
    2018/
      UPSC_CSE_2018_Paper1.pdf
  SSC_CGL/
    2022/
      SSC_CGL_2022_Paper1.pdf
```

---

## 🏗️ Architecture

```
main.py (CLI)
  │
  ├─ search_agent.py    → DuckDuckGo + Bing, 5 query variants
  ├─ link_scorer.py     → Claude API ranks URLs (heuristic fallback)
  ├─ browser_scraper.py → Scrapling stealth browser extracts PDFs
  ├─ downloader.py      → Retry download + %PDF validation
  │
  ├─ utils/
  │   ├─ file_manager.py   → Path construction, deduplication
  │   ├─ pdf_validator.py  → Size + header checks
  │   └─ logger.py         → Loguru: console + daily rotating file
  │
  └─ config.py         → All constants & settings
```

---

## ⚙️ Configuration (`config.py`)

| Setting | Default | Description |
|---|---|---|
| `USE_LLM_SCORER` | `True` | Enable Claude API ranking |
| `MAX_CANDIDATES_TO_TRY` | `3` | Top-N URLs to attempt per year |
| `MIN_PDF_SIZE_BYTES` | `50,000` | Minimum valid PDF size |
| `MIN_DELAY_SEC` | `1.5` | Minimum delay between requests |
| `MAX_DELAY_SEC` | `4.0` | Maximum delay between requests |

---

## 🛡️ Anti-Bot Strategies

1. **Scrapling stealth mode** — patches navigator/webdriver flags, humanises mouse movements
2. **User-agent rotation** — `fake-useragent` serves randomised, up-to-date browser UAs
3. **Human delays** — random 1.5–4 second pauses between every request
4. **Realistic headers** — Accept-Language, DNT, Referer mimicking real browsers
5. **Domain filtering** — blocked list skips Scribd, social media, etc.

---

## 📜 Logging

Logs rotate daily in `logs/scraper_YYYY-MM-DD.log`.

---

*Built with Scrapling + Claude API. Designed to work like a human researcher: search → evaluate → click → download.*
