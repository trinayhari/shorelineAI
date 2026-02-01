// Zoning-related keywords for relevance scoring
export const ZONING_KEYWORDS = [
  "zoning",
  "regulation",
  "ordinance",
  "land-use",
  "landuse",
  "code",
];

// PDF detection patterns
export const PDF_DIRECTORY_PATTERNS = [
  "/files/",
  "/documents/",
  "/docs/",
  "/uploads/",
  "/media/",
];

export const WEB_PAGE_EXTENSIONS = [
  ".html",
  ".htm",
  ".php",
  ".asp",
  ".aspx",
  ".jsp",
  ".cfm",
];

export const ZONING_FILE_KEYWORDS = ["zoning", "regulation", "ordinance", "code"];

// LLM Configuration
export const LLM_MODEL = "openai/gpt-4o-mini";
export const LLM_TEMPERATURE = 0.3;
export const LLM_MAX_TOKENS = 500;

// RAG Configuration
export const RAG_LLM_MODEL = "openai/gpt-4o-mini";
export const RAG_LLM_TEMPERATURE = 0.3;
export const RAG_MAX_TOKENS = 2000;
export const CHUNK_SIZE = 2000;

// Embedding model
export const EMBEDDING_MODEL = "openai/text-embedding-3-small";

// Scraping Configuration
export const SCRAPE_TIMEOUT = 30000;

// Relevance Scoring
export const SCORE_LINK_TEXT_KEYWORD = 20;
export const SCORE_URL_KEYWORD = 10;
export const SCORE_IS_PDF = 5;
export const SCORE_RECENT_YEAR = 3;
export const PENALTY_UNWANTED_TERMS = -15;
export const PENALTY_UNWANTED_URL = -10;

// Terms to avoid in links
export const UNWANTED_TERMS = [
  "summary",
  "proposed",
  "amendment",
  "changes to",
  "revised",
  "draft",
  "application",
];
