"""Project-wide constants for LitRelevanceAI.

This module centralizes all magic numbers and configuration constants
to improve maintainability and reduce errors.
"""

# ========================================
# Cache Settings
# ========================================
CACHE_DEFAULT_TTL_DAYS = 30
"""Default time-to-live for cache entries in days."""

CACHE_CLEANUP_INTERVAL_DAYS = 7
"""Interval for cache cleanup operations."""

# ========================================
# Matching Thresholds
# ========================================
TITLE_SIMILARITY_THRESHOLD = 80.0
"""Minimum similarity score (0-100) for fuzzy title matching."""

FUZZY_MATCH_MIN_SCORE = 80
"""Minimum fuzzy match score for considering a match valid."""

DOI_MATCH_CONFIDENCE = 1.0
"""Confidence score for DOI-based matches (always 100%)."""

# ========================================
# Progress & Checkpoint
# ========================================
CHECKPOINT_INTERVAL = 5
"""Save checkpoint every N items processed."""

CHECKPOINT_TIMEOUT_WRITE = 30
"""File lock timeout in seconds for checkpoint write operations."""

CHECKPOINT_TIMEOUT_READ = 10
"""File lock timeout in seconds for checkpoint read operations."""

# ========================================
# Threading & Concurrency
# ========================================
DEFAULT_MAX_WORKERS = 3
"""Default number of concurrent worker threads for parallel processing."""

API_REQUEST_DELAY_SECONDS = 0.5
"""Delay between API requests to avoid rate limiting."""

# ========================================
# File Format
# ========================================
SUPPORTED_INPUT_FORMATS = ['.csv', '.xlsx', '.xls']
"""Supported input file formats for data processing."""

SUPPORTED_OUTPUT_FORMATS = ['.csv', '.xlsx']
"""Supported output file formats for results."""

DEFAULT_ENCODING = 'utf-8-sig'
"""Default file encoding (UTF-8 with BOM support for Excel compatibility)."""

# ========================================
# Retry Logic
# ========================================
MAX_RETRY_ATTEMPTS = 3
"""Maximum number of retry attempts for failed operations."""

RETRY_DELAY_BASE = 2
"""Base delay in seconds for exponential backoff (2^n seconds)."""

RETRY_DELAYS = [2, 4, 8, 16]
"""Predefined retry delays for exponential backoff (in seconds)."""

# ========================================
# API Configuration
# ========================================
DEFAULT_TEMPERATURE = 0.3
"""Default temperature for AI model inference."""

DEFAULT_MODEL = "gpt-4o-mini"
"""Default AI model to use when not specified."""

# ========================================
# Validation
# ========================================
MIN_API_KEY_LENGTH = 10
"""Minimum length for API key validation."""

MIN_TITLE_LENGTH = 3
"""Minimum title length for valid paper metadata."""

MIN_ABSTRACT_LENGTH = 10
"""Minimum abstract length for valid paper content."""
