from pathlib import Path


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RESULTS_DATA_DIR = DATA_DIR / "results"

YAHOO_UNIVERSE_FILE = RAW_DATA_DIR / "yahoo_universe.csv"


# ---------------------------------------------------------
# Deep Value Core - initial universe settings
# ---------------------------------------------------------

REGION = "us"

MIN_MARKET_CAP = 50_000_000
MAX_MARKET_CAP = 2_500_000_000

MIN_UNLEVERED_FCF = 0


# ---------------------------------------------------------
# Yahoo Screener settings
# ---------------------------------------------------------

PAGE_SIZE = 250
MAX_PAGES = 20


# ---------------------------------------------------------
# Sectors
#
# We deliberately exclude:
# - Financial Services
# - Real Estate
#
# These require different valuation methods.
# ---------------------------------------------------------

ALLOWED_SECTORS = [
    "Basic Materials",
    "Communication Services",
    "Consumer Cyclical",
    "Consumer Defensive",
    "Energy",
    "Healthcare",
    "Industrials",
    "Technology",
    "Utilities",
]

# ---------------------------------------------------------
# Fundamentals output files
# ---------------------------------------------------------

YAHOO_FUNDAMENTALS_FILE = (
    PROCESSED_DATA_DIR / "yahoo_fundamentals.csv"
)

YAHOO_FUNDAMENTALS_ERRORS_FILE = (
    PROCESSED_DATA_DIR / "yahoo_fundamentals_errors.csv"
)

CALCULATED_METRICS_FILE = (
    PROCESSED_DATA_DIR / "calculated_metrics.csv"
)

# ---------------------------------------------------------
# Yahoo fundamentals download settings
# ---------------------------------------------------------

# Small delay between companies to reduce the chance
# of Yahoo rate limiting the script.
REQUEST_DELAY_SECONDS = 0.25

# Number of times to retry a ticker if Yahoo fails.
MAX_RETRIES = 3

# Save progress every N companies.
CHECKPOINT_EVERY = 25

# Set this to an integer such as 10 when testing.
# Set to None to process the full universe.
MAX_COMPANIES_TO_FETCH = None

# Number of annual periods we want to retain.
HISTORY_YEARS = 5


# ---------------------------------------------------------
# Deep Value Core output
# ---------------------------------------------------------

DEEP_VALUE_CORE_FILE = (
    RESULTS_DATA_DIR / "deep_value_core.csv"
)

DEEP_VALUE_PRIORITY_FILE = (
    RESULTS_DATA_DIR / "deep_value_priority.csv"
)


# ---------------------------------------------------------
# Deep Value Core filters
# ---------------------------------------------------------

DEEP_VALUE_MIN_MARKET_CAP = 50_000_000
DEEP_VALUE_MAX_MARKET_CAP = 2_500_000_000

DEEP_VALUE_MAX_EV_FCF = 8.0

# <= 5x is our preferred hunting ground.
DEEP_VALUE_PRIORITY_MAX_EV_FCF = 5.0

DEEP_VALUE_MIN_POSITIVE_FCF_YEARS = 3

DEEP_VALUE_MAX_NET_DEBT_EBITDA = 2.5

DEEP_VALUE_MIN_REVENUE_CAGR = -0.05

# Optional dilution warning threshold.
# 0.20 means +20%.
DEEP_VALUE_MAX_SHARE_DILUTION = 0.20


# ---------------------------------------------------------
# Quality analysis output
# ---------------------------------------------------------

QUALITY_METRICS_FILE = (
    PROCESSED_DATA_DIR / "quality_metrics.csv"
)