"""
config.py — Central Configuration for GovExam Scraper
All constants, paths, and settings live here.
"""

from pathlib import Path

# ─── Directories ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
BASE_DOWNLOAD_DIR = BASE_DIR / "downloads"
LOG_DIR = BASE_DIR / "logs"

# Ensure directories exist at import time
BASE_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ─── Search Settings ──────────────────────────────────────────────────────────
MAX_SEARCH_RESULTS = 40         # Max results collected across all queries
MAX_CANDIDATES_TO_SCORE = 20    # Send top-N to LLM for scoring
MAX_CANDIDATES_TO_TRY = 10      # Try top-N candidates for download

# ─── Download Settings ────────────────────────────────────────────────────────
MIN_PDF_SIZE_BYTES = 50_000     # 50 KB — anything smaller is likely an error page
DOWNLOAD_TIMEOUT_SEC = 30
MAX_RETRIES = 3
CHUNK_SIZE = 8192               # Streaming chunk size in bytes

# ─── Anti-Bot / Rate Limiting ─────────────────────────────────────────────────
MIN_DELAY_SEC = 1.5
MAX_DELAY_SEC = 4.0

# ─── LLM Settings ────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash-lite"  # Standard stable model
LLM_MAX_TOKENS = 600
USE_LLM_SCORER = True           # Set False to skip LLM scoring (faster, less accurate)
BROAD_SEARCH_MODE = False        # If True, skips scoring and visits ALL search results
MAX_BROAD_CANDIDATES = 25       # Max pages to visit in Broad Discovery mode

# ─── Trusted Domains (boosted in scoring) ────────────────────────────────────
TRUSTED_DOMAINS = [
    "upsc.gov.in",
    "ssc.nic.in",
    "tnpsc.gov.in",
    "ibps.in",
    "rrbcdg.gov.in",
    "nta.ac.in",
    "bpsc.bih.nic.in",
    "mppsc.mp.gov.in",
    "kpsc.kar.nic.in",
    "examrace.com",
    "testbook.com",
    "adda247.com",
    "cracku.in",
    "prepp.in",
    "careerpower.in",
    "gradeup.co",
    "oliveboard.in",
    "mrunal.org",
    "drishtijudiciary.com",
    "insightsonindia.com",
    "selfstudysolution.com",
    "previouspapers.in",
    "educationobserver.com",
    "sarkaripaperwale.com",
    "archive.org",
    "bankersadda.com",
    "affairscloud.com",
    "jagranjosh.com",
    "gktoday.in",
    "shiksha.com",
    "careers360.com",
    "educationobserver.com",
]

# ─── Blocked Domains (skip entirely) ─────────────────────────────────────────
BLOCKED_DOMAINS = [
    "scribd.com",       # Paywall
    "slideshare.net",   # No direct download
    "facebook.com",
    "youtube.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "amazon.com",
    "flipkart.com",
    "zhihu.com",
    "quora.com",
    "byjus.com",
    "medium.com",
]

# ─── Source Priority Tiers ──────────────────────────────────────────────────
TIER0_SITES = ["testbook.com", "adda247.com", "careerpower.in", "prepp.in", "cracku.in", "oliveboard.in"]

TIER1_OFFICIALS = {
    "UPSC": "upsc.gov.in",
    "SSC": "ssc.nic.in",
    "IBPS": "ibps.in",
    "RBI": "rbi.org.in",
    "RRB": "rrbcdg.gov.in",
    "TNPSC": "tnpsc.gov.in",
    "MPSC": "mpsc.gov.in",
    "RPSC": "rpsc.rajasthan.gov.in",
}

TIER2_EDUCATION = [
    "affairscloud.com",
    "gktoday.in",
    "bankersadda.com",
    "jagranjosh.com",
    "examrace.com",
    "oliveboard.in",
    "selfstudysolution.com",
    "previouspapers.in",
    "questionpaperspdf.com",
    "educationobserver.com",
]

# ─── Exam → Source Mapping (Intelligent Router) ─────────────────────────────
EXAM_SOURCE_MAP = {
    "UPSC CSE": {
        "full_name": "Civil Services Examination",
        "official": "upsc.gov.in",
        "tier0": ["testbook.com", "adda247.com", "prepp.in", "cracku.in", "careerpower.in"],
        "tier2": ["affairscloud.com", "gktoday.in", "examrace.com", "jagranjosh.com"],
        "search_query": 'Civil Services Examination (CSE) {year} question paper PDF',
        "papers": ["GS1", "GS2", "GS3", "GS4", "Essay"],
    },
    "UPSC CDS": {
        "full_name": "Combined Defence Services",
        "official": "upsc.gov.in",
        "tier0": ["testbook.com", "adda247.com", "cracku.in", "careerpower.in"],
        "tier2": ["examrace.com", "affairscloud.com"],
        "search_query": 'CDS {year} question paper PDF Combined Defence Services',
        "papers": ["Math", "GK", "English"],
    },
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
    "IBPS PO": {
        "full_name": "IBPS Probationary Officer",
        "official": "ibps.in",
        "tier0": ["testbook.com", "adda247.com", "careerpower.in", "prepp.in", "cracku.in", "bankersadda.com", "oliveboard.in"],
        "tier2": ["bankersadda.com", "affairscloud.com", "gktoday.in", "educationobserver.com"],
        "search_query": 'IBPS PO {year} question paper PDF Prelims Mains Solved',
        "papers": ["Prelims", "Mains", "Solved", "MemoryBased"],
    },
    "IBPS Clerk": {
        "full_name": "IBPS Clerk",
        "official": "ibps.in",
        "tier0": ["testbook.com", "adda247.com", "careerpower.in", "cracku.in", "prepp.in", "oliveboard.in"],
        "tier2": ["bankersadda.com", "affairscloud.com", "examrace.com", "selfstudysolution.com", "previouspapers.in"],
        "search_query": 'IBPS Clerk {year} prelims mains question paper PDF download',
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
    "RRB NTPC": {
        "full_name": "Railway Recruitment Board NTPC",
        "official": "rrbcdg.gov.in",
        "tier0": ["testbook.com", "adda247.com", "careerpower.in", "cracku.in"],
        "tier2": ["affairscloud.com", "examrace.com", "freejobalert.com"],
        "search_query": 'RRB NTPC {year} question paper PDF Railway',
        "papers": ["CBT1", "CBT2"],
    },
    "TNPSC Group 2": {
        "full_name": "TNPSC Group 2",
        "tier0": ["testbook.com", "adda247.com", "cracku.in", "careerpower.in"],
        "search_query": 'TNPSC Group 2 {year} question paper PDF Tamil Nadu',
        "papers": ["Paper1", "Paper2"],
    },
    # ─── JUDICIARY & LEGAL ────────────────────────────────────────────────
    "State Judicial Services": {"full_name": "Civil Judge Recruitment", "search_query": "{exam} {year} question paper PDF solved"},
    "District Judge Recruitment": {"full_name": "District Judge Exam", "search_query": "{exam} {year} question paper PDF"},
    "High Court Clerk": {"full_name": "High Court Clerk Junior Assistant", "search_query": "{exam} {year} question paper PDF"},
    "Lower Judiciary": {"full_name": "Judicial Magistrate", "search_query": "{exam} {year} question paper PDF"},
    "Supreme Court Junior Assistant": {"full_name": "Supreme Court Junior Assistant Recruitment", "search_query": "{exam} {year} question paper PDF"},
    
    # ─── PSU & TECHNICAL ──────────────────────────────────────────────────
    "ONGC Graduate Trainee": {"full_name": "ONGC GATE Recruitment", "search_query": "{exam} {year} question paper PDF"},
    "IOCL Recruitment": {"full_name": "IOCL Executive Technical", "search_query": "{exam} {year} question paper PDF"},
    "BHEL Recruitment": {"full_name": "BHEL Executive Technician", "search_query": "{exam} {year} question paper PDF"},
    "SAIL Recruitment": {"search_query": "{exam} {year} question paper PDF"},
    "NTPC Executive Trainee": {"search_query": "{exam} {year} question paper PDF"},
    "BEL Recruitment": {"search_query": "{exam} {year} question paper PDF"},
    "DRDO Scientist": {"full_name": "DRDO Scientist B Technician", "search_query": "{exam} {year} question paper PDF"},
    "ISRO Scientist": {"full_name": "ISRO Technical Assistant Scientist", "search_query": "{exam} {year} question paper PDF"},
    "HAL Recruitment": {"search_query": "{exam} {year} question paper PDF"},
    "Coal India Recruitment": {"search_query": "{exam} {year} question paper PDF"},
    "Power Grid Recruitment": {"search_query": "{exam} {year} question paper PDF"},
    "NPCIL Recruitment": {"search_query": "{exam} {year} question paper PDF"},
    "GAIL Executive Trainee": {"search_query": "{exam} {year} question paper PDF"},
    "BEML Recruitment": {"search_query": "{exam} {year} question paper PDF"},
    
    # ─── STATE SERVICES (General) ─────────────────────────────────────────
    "State TET": {"full_name": "Teacher Eligibility Test", "search_query": "{exam} {year} previous year question paper PDF"},
    "State Medical Officer": {"search_query": "{exam} {year} question paper PDF"},
    "Pharmacist Recruitment": {"search_query": "{exam} {year} question paper PDF"},
    "CPWD JE AE": {"search_query": "{exam} {year} question paper PDF"},
    "Cantonment Board": {"search_query": "{exam} {year} question paper PDF"},
    "Apprenticeship": {"search_query": "{exam} {year} apprenticeship exam paper PDF"},
    "Municipal Corporation": {"search_query": "{exam} {year} recruitment paper PDF"},
    "State Cooperative Bank": {"search_query": "{exam} {year} question paper clerk officer PDF"},
    "State Lecturer": {"full_name": "Assistant Professor Recruitment", "search_query": "{exam} {year} question paper PDF"},
    "State Forest Guard": {"full_name": "Forest Ranger Recruitment", "search_query": "{exam} {year} question paper PDF"},
    
    # ─── STATE SPECIFIC PSCs ──────────────────────────────────────────────
    "Arunachal Pradesh PSC": {"search_query": "APPSC {year} question paper PDF Arunachal Pradesh"},
    "Assam PSC": {"search_query": "APSC {year} question paper PDF Assam"},
    "Bihar PSC": {"search_query": "BPSC {year} question paper PDF Bihar"},
    "Chhattisgarh PSC": {"search_query": "CGPSC {year} question paper PDF Chhattisgarh"},
    "Goa PSC": {"search_query": "GPSC {year} question paper PDF Goa"},
    "Gujarat PSC": {"search_query": "GPSC {year} question paper PDF Gujarat"},
    "Haryana PSC": {"search_query": "HPSC {year} question paper PDF Haryana"},
    "Himachal Pradesh PSC": {"search_query": "HPPSC {year} question paper PDF Himachal"},
    "Jharkhand PSC": {"search_query": "JPSC {year} question paper PDF Jharkhand"},
    "Karnataka PSC": {"search_query": "KPSC {year} question paper PDF Karnataka"},
    "Kerala PSC": {"search_query": "KPSC {year} question paper PDF Kerala"},
    "Madhya Pradesh PSC": {"search_query": "MPPSC {year} question paper PDF Madhya Pradesh"},
    "Maharashtra PSC": {"search_query": "MPSC {year} question paper PDF Maharashtra"},
    "Manipur PSC": {"search_query": "MPSC {year} question paper PDF Manipur"},
    "Meghalaya PSC": {"search_query": "MPSC {year} question paper PDF Meghalaya"},
    "Mizoram PSC": {"search_query": "MPSC {year} question paper PDF Mizoram"},
    "Nagaland PSC": {"search_query": "NPSC {year} question paper PDF Nagaland"},
    "Odisha PSC": {"search_query": "OPSC {year} question paper PDF Odisha"},
    "Punjab PSC": {"search_query": "PPSC {year} question paper PDF Punjab"},
    "Rajasthan PSC": {"search_query": "RPSC {year} question paper PDF Rajasthan"},
    "Sikkim PSC": {"search_query": "SPSC {year} question paper PDF Sikkim"},
    "Tamil Nadu PSC": {"search_query": "TNPSC {year} question paper PDF Tamil Nadu"},
    "Telangana PSC": {"search_query": "TSPSC {year} question paper PDF Telangana"},
    "Tripura PSC": {"search_query": "TPSC {year} question paper PDF Tripura"},
    "Uttar Pradesh PSC": {"search_query": "UPPSC {year} question paper PDF Uttar Pradesh"},
    "Uttarakhand PSC": {"search_query": "UKPSC {year} question paper PDF Uttarakhand"},
    "West Bengal PSC": {"search_query": "WBPSC {year} question paper PDF West Bengal"},
}

# ─── Site Slug Registry ─────────────────────────────────────────────────────
SITE_REGISTRY = {
    "testbook": {
        "UPSC CSE": "upsc-question-paper",
        "SSC CGL": "ssc-cgl-question-paper",
        "SSC CHSL": "ssc-chsl-question-paper",
        "IBPS PO": "ibps-po/previous-year-papers",
        "IBPS Clerk": "ibps-clerk-question-paper",
        "RBI Grade B": "rbi-grade-b-question-paper",
        "RRB NTPC": "rrb-ntpc-question-paper",
        "TNPSC Group 2": "tnpsc-group-2-question-paper",
    },
    "adda247": {
        "UPSC CSE": "jobs/upsc-previous-year-question-papers",
        "SSC CGL": "jobs/ssc-cgl-previous-year-papers",
        "SSC CHSL": "jobs/ssc-chsl-previous-year-question-paper",
        "IBPS PO": "jobs/ibps-po-previous-year-question-paper",
        "IBPS Clerk": "jobs/ibps-clerk-previous-year-question-paper",
        "RBI Grade B": "jobs/rbi-grade-b-previous-year-question-paper",
        "RRB NTPC": "jobs/rrb-ntpc-previous-year-papers",
    },
    "careerpower": {
        "SSC CGL": "ssc-cgl-previous-year-question-papers-pdf",
        "SSC CHSL": "ssc-chsl-previous-year-question-papers",
        "IBPS PO": "ibps-po-previous-year-question-paper.html",
        "IBPS Clerk": "ibps-clerk-previous-year-question-paper.html",
        "RBI Grade B": "rbi-grade-b-previous-year-question-papers",
        "RRB NTPC": "rrb-ntpc-previous-year-question-papers",
    },
    "prepp": {
        "UPSC CSE": "ias-previous-year-question-papers",
        "SSC CGL": "ssc-cgl-previous-year-question-papers",
        "SSC CHSL": "ssc-chsl-previous-year-question-papers",
        "IBPS PO": "ibps-po-exam/practice-papers",
        "IBPS Clerk": "ibps-clerk-exam/question-paper-{year}",
        "RRB NTPC": "rrb-ntpc-previous-year-question-papers",
        "TNPSC Group 2": "tnpsc-group-2-previous-year-question-papers",
    },
    "cracku": {
        "UPSC CSE": "upsc-previous-papers",
        "SSC CGL": "ssc-cgl-previous-papers",
        "SSC CHSL": "ssc-chsl-previous-papers",
        "IBPS PO": "ibps-po-previous-papers",
        "IBPS Clerk": "ibps-clerk-previous-papers",
        "RBI Grade B": "rbi-grade-b-previous-papers",
        "RRB NTPC": "rrb-ntpc-previous-papers",
        "TNPSC Group 2": "tnpsc-group-2-previous-papers",
    },
    "bankersadda": {
        "IBPS PO": "ibps-po-previous-year-question-paper",
        "IBPS Clerk": "ibps-clerk-previous-year-question-paper",
    },
    "oliveboard": {
        "IBPS PO": "ibps-po-previous-year-question-papers",
        "IBPS Clerk": "ibps-clerk-previous-year-question-papers",
        "RBI Grade B": "rbi-grade-b-previous-year-papers",
        "SSC CGL": "ssc-cgl-previous-year-papers",
    },
}

# ─── Site-Specific Selectors ─────────────────────────────────────────────────
SITE_SELECTORS = {
    "examrace.com":         "a.btn-download, a[href*='pdf'], .download a",
    "testbook.com":         "a.download-btn, a[href$='.pdf'], a[href*='question-paper'], table a, a.btn-link",
    "upsc.gov.in":          "table a[href$='.pdf'], .content a[href*='question'], a[href*='qp']",
    "ssc.nic.in":           "a[href$='.pdf'], table a, a[href*='download']",
    "tnpsc.gov.in":         "a[href*='.pdf'], a[href*='download']",
    "ibps.in":              "a[href$='.pdf'], table a[href*='pdf'], .download a",
    "adda247.com":          "table a, a[href*='question-paper'], a[href*='pdf'], .card a, h3 a, h4 a, a:contains('Download')",
    "prepp.in":             "table tr a, .paper-row a, a[href*='pdf'], a[href*='download'], a.btn",
    "cracku.in":            "a[href$='.pdf'], h2 + div a, .previous-paper a, section a",
    "affairscloud.com":     "a[href$='.pdf'], article a[href*='pdf'], h2+p a, h3+ul a",
    "bankersadda.com":      "table a, a[href*='pdf'], .article a, h3 a, a:contains('Download')",
    "oliveboard.in":        "a[href*='pdf'], .download-btn, a[href*='question']",
    "selfstudysolution.com":"a[href$='.pdf'], a[href*='download']",
    "previouspapers.in":    "a[href$='.pdf'], .download a",
    "questionpaperspdf.com":"a[href$='.pdf'], a.download",
    "careerpower.in":       "table a, a[href*='pdf'], a[href*='download'], .paper-link a, a:contains('Download')",
    "default":              "table a, a[href$='.pdf'], a[href*='download'], a[href*='PDF'], a[href*='question-paper'], a[href*='view-paper']",
}

# ─── Fallback Search Query Templates (legacy, now managed in search_agent.py) ──
SEARCH_QUERY_FORMATS = [
    '"{full_name}" {year} question paper filetype:pdf',
    '{exam} {year} previous year question paper pdf site:testbook.com OR site:adda247.com OR site:cracku.in',
    '{exam} {year} question paper site:{official_site}',
    '"{exam}" "{year}" "question paper" "download" pdf',
    '{exam} {year} solved paper pdf download -youtube -instagram',
]
