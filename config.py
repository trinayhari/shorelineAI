"""
Configuration for state-specific zoning regulation finder
"""

# State configurations
STATES = {
    "Connecticut": {
        "abbreviation": "CT",
        "municipality_term": "town",
        "source_url": "https://portal.ct.gov/government/cities-and-towns"
    },
}

# Default state
DEFAULT_STATE = "Connecticut"

# Zoning-related keywords for relevance scoring
ZONING_KEYWORDS = ['zoning', 'regulation', 'ordinance', 'land-use', 'landuse', 'code']

# PDF detection patterns
PDF_DIRECTORY_PATTERNS = ['/files/', '/documents/', '/docs/', '/uploads/', '/media/']
WEB_PAGE_EXTENSIONS = ['.html', '.htm', '.php', '.asp', '.aspx', '.jsp', '.cfm']
ZONING_FILE_KEYWORDS = ['zoning', 'regulation', 'ordinance', 'code']

# LLM Configuration
LLM_MODEL = "anthropic/claude-3.5-sonnet"
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 500

# RAG Configuration
RAG_LLM_MODEL = "anthropic/claude-3.5-sonnet"
RAG_LLM_TEMPERATURE = 0.3
RAG_MAX_TOKENS = 2000
CHUNK_SIZE = 2000  # Characters per chunk for processing

# Scraping Configuration
SCRAPE_TIMEOUT = 30000  # 30 seconds for JavaScript rendering

# Relevance Scoring
SCORE_LINK_TEXT_KEYWORD = 20  # Link text contains zoning keywords
SCORE_URL_KEYWORD = 10         # URL contains zoning keywords
SCORE_IS_PDF = 5               # Link is a PDF or document
SCORE_RECENT_YEAR = 3          # Contains recent year (2024, 2025)
PENALTY_UNWANTED_TERMS = -15   # Link text has unwanted terms (draft, amendment, etc.)
PENALTY_UNWANTED_URL = -10     # URL has unwanted terms

# Terms to avoid in links (summaries, drafts, amendments)
UNWANTED_TERMS = ['summary', 'proposed', 'amendment', 'changes to', 'revised', 'draft', 'application']
