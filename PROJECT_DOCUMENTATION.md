# 🎓 GovExam Scraper V4 — Technical Documentation

## 1. Project Overview
The **GovExam Scraper** is a production-grade automated pipeline designed to discover, filter, and download government exam question papers (PDFs) from across the web. It prioritizes English-medium papers and targets specific years (e.g., 2020–2024) while blocking irrelevant notifications and administrative documents.

---

## 2. How the Scraper Works (The 3-Phase Pipeline)
The scraper mimics a "Human Expert" search behavior to find the highest-quality papers with minimal noise.

### Phase 1: Tier-0 Direct Access (Slug Builder)
- Instead of random searching, the tool "guesses" the exact URL of exam-paper index pages on top education portals like **Prepp**, **Testbook**, and **CareerPower**.
- It uses **Year-Aware Templates** (e.g., `prepp.in/ibps-clerk-exam/question-paper-2024`) to jump directly to the target content.

### Phase 2: Official Board Check
- It visits the official board site (e.g., `ibps.in`, `ssc.nic.in`) to check for recent archives or official releases.

### Phase 3: Professional Web Search
- If direct access fails, it runs 8 different search query variants using **DuckDuckGo** and **Bing**.
- It identifies top candidates and uses **Intelligent Scrutiny** (Heuristic + LLM) to pick the best links.

---

## 3. Technology Stack
- **UI Framework**: [Streamlit](https://streamlit.io/) for a real-time web dashboard.
- **Browser Engine**: [Scrapling (Playwright)](https://github.com/Dataliner/scrapling) for steering through anti-bot measures and JavaScript-heavy portals.
- **AI Brain**: [Google Gemini Pro / Flash](https://aistudio.google.com/) for scoring and ranking URLs based on relevance.
- **Search Engine**: [DDGS (DuckDuckGo Search)](https://pypi.org/project/duckduckgo-search/) for broad web discovery.
- **Networking**: `Requests` with `Tenacity` for resilient, retrying downloads.
- **Logging**: `Loguru` for clean, professional terminal and file logging.

---

## 4. Real-World Blockers & Solutions

| Blocker | Impact | Solution Implemented |
| :--- | :--- | :--- |
| **Hidden Table Links** | 2024 papers on Adda247/Prepp were missed because they aren't direct `.pdf` URLs. | **Relaxed Format Check**: The scraper now allows links from trusted sites that say "Download PDF" even if the URL doesn't end in `.pdf`. |
| **Library Noise** | Screen was flooded with Brotli, lxml, and SSL warnings. | **Global Warning Filter**: Moved suppression to the global entrance (`main.py`) to silence deep technical noise before it starts. |
| **Search Pollution** | Results from Zhihu (Chinese) and Quora wasted time and resources. | **Domain Blocking**: Added a strict list of `BLOCKED_DOMAINS` in `config.py`. |
| **Thread NameErrors** | Missing `logger` or `traceback` caused background threads to crash silently. | **Import Repair**: Refactored `app.py` and `browser_scraper.py` to ensure all core libraries are available. |
| **Anti-Bot Blocking** | Sites like Testbook block basic scripts. | **Stealth Headers**: Implemented a dynamic header builder and "Human Delay" generator in `anti_detect.py`. |

---

## 5. Key Features
- **Context-Aware Filtering**: Checks not just the link, but the **Anchor Text** and **Page Header** to confirm the year and exam match.
- **Early Exit Discovery**: If 10+ papers are found on a high-quality site (like CareerPower), it stops searching to save time and bandwidth.
- **Strict Year Rejection**: Automatically deletes folders if paper years don't match the user's target, preventing "folder pollution."
- **Auto-Duplicate Handling**: Checks if a file exists (or a similar one exists) before downloading again.

---

## 6. How to Run
```powershell
# Run the Web Dashboard
streamlit run app.py

# Run the CLI version
python main.py "IBPS Clerk" 2020 2024
```

---
> [!TIP]
> **Priority Sites**: Always ensure `testbook.com`, `adda247.com`, and `prepp.in` are in your `TIER0_SITES` for the fastest results.
