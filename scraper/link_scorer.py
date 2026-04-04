"""
scraper/link_scorer.py — LLM-Based URL Ranker via Claude API.

Sends the top candidate URLs to Claude and asks it to return the 3 most likely
to contain the real exam paper PDF.
Falls back to basic heuristic scoring when USE_LLM_SCORER=False or API is unavailable.
"""

from __future__ import annotations
import json
import os
import re
import tldextract
from loguru import logger

from config import (
    TRUSTED_DOMAINS,
    BLOCKED_DOMAINS,
    GEMINI_MODEL,
    LLM_MAX_TOKENS,
    USE_LLM_SCORER,
    MAX_CANDIDATES_TO_SCORE,
    MAX_CANDIDATES_TO_TRY,
)


# ─── Heuristic Scorer (no LLM) ───────────────────────────────────────────────

_URL_BOOST_PATTERNS = [
    r"question[-_]?paper",
    r"previous[-_]?year",
    r"\.pdf",
    r"download",
    r"pyq",
    r"solved",
    r"sample",
    r"old[-_]?paper",
]


def _heuristic_score(url: str, exam: str, year: int) -> float:
    """Score a URL heuristically between 0.0 and 1.0."""
    score = 0.0
    url_lower = url.lower()

    # Year match
    if str(year) in url:
        score += 0.3

    # Exam name partial match
    exam_words = exam.lower().split()
    matched = sum(1 for w in exam_words if w in url_lower)
    score += 0.2 * (matched / max(len(exam_words), 1))

    # URL keyword boosts
    for pattern in _URL_BOOST_PATTERNS:
        if re.search(pattern, url_lower):
            score += 0.05

    # Trusted domain boost
    try:
        ext = tldextract.extract(url)
        # Use top_domain_under_public_suffix instead of registered_domain to avoid deprecation warning
        domain = f"{ext.domain}.{ext.suffix}"
        registered = f"{ext.top_domain_under_public_suffix}"
        if any(td in registered for td in TRUSTED_DOMAINS):
            score += 0.25
    except Exception:
        pass

    # Penalise blocked domains
    if any(bd in url_lower for bd in BLOCKED_DOMAINS):
        score -= 1.0

    return min(max(score, 0.0), 1.0)


def _rank_heuristically(
    exam: str, year: int, candidates: list[dict]
) -> list[str]:
    """Return top URLs sorted by heuristic score."""
    scored = [
        (c.get("href", ""), _heuristic_score(c.get("href", ""), exam, year))
        for c in candidates
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    urls = [url for url, _ in scored if url]
    return urls[:MAX_CANDIDATES_TO_TRY]


# ─── LLM Scorer (Google Gemini API) ───────────────────────────────────────────

def _rank_with_llm(exam: str, year: int, candidates: list[dict]) -> list[str]:
    """Ask Gemini to rank URLs and return the top MAX_CANDIDATES_TO_TRY."""
    try:
        import google.generativeai as genai
    except ImportError:
        logger.warning("google-generativeai package not installed — falling back to heuristic scorer")
        return _rank_heuristically(exam, year, candidates)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — falling back to heuristic scorer")
        return _rank_heuristically(exam, year, candidates)

    # Trim to MAX_CANDIDATES_TO_SCORE before sending to LLM
    slim_candidates = [
        {"title": c.get("title", ""), "url": c.get("href", ""), "body": c.get("body", "")[:200]}
        for c in candidates[:MAX_CANDIDATES_TO_SCORE]
    ]

    prompt = f"""You are an expert at finding government exam question papers online.

Exam: {exam}
Year: {year}

Here are candidate URLs found via web search:
{json.dumps(slim_candidates, indent=2)}

Rank the top {MAX_CANDIDATES_TO_TRY} URLs most likely to directly contain or link to the 
original {exam} {year} question paper PDF.

Ranking criteria (in priority order):
1. Official government domains (.gov.in) — highest trust
2. URL contains keywords: 'question-paper', 'previous-year', 'pdf', 'pyq', 'download'
3. URL contains the exam year {year}
4. Known education portals: examrace.com, testbook.com, adda247.com, prepp.in
5. Archive/repository sites

Return ONLY a valid JSON array of exactly {MAX_CANDIDATES_TO_TRY} URLs (strings), 
ordered by confidence. No explanation, no markdown fencing. Example:
["https://...", "https://...", "https://..."]
"""

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=GEMINI_MODEL)
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=LLM_MAX_TOKENS,
                temperature=0.0,
            ),
        )
        
        raw = response.text.strip()
        # Try to extract a JSON array even if the model wraps it
        match = re.search(r"\[\s*\".*\"\s*\]", raw, re.DOTALL)
        if not match:
             # Fallback to simple split if regex fails but response looks like list
             if raw.startswith("[") and raw.endswith("]"):
                 urls = json.loads(raw)
             else:
                 raise ValueError(f"No JSON array found in Gemini response: {raw[:300]}")
        else:
            urls = json.loads(match.group())
            
        logger.info(f"Gemini scored {len(urls)} candidates")
        return [u for u in urls if isinstance(u, str)][:MAX_CANDIDATES_TO_TRY]
    except Exception as exc:
        logger.warning(f"Gemini scoring failed ({exc}) — falling back to heuristic scorer")
        return _rank_heuristically(exam, year, candidates)


# ─── Public API ───────────────────────────────────────────────────────────────

def score_and_rank(exam: str, year: int, candidates: list[dict]) -> list[str]:
    """
    Rank candidate search results and return the top URLs to try.
    Uses LLM if USE_LLM_SCORER=True and key is available, otherwise heuristic.
    """
    if not candidates:
        return []

    if USE_LLM_SCORER:
        return _rank_with_llm(exam, year, candidates)
    else:
        return _rank_heuristically(exam, year, candidates)
