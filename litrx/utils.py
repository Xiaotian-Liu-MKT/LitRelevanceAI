"""
Utility functions and classes for the LitRx Toolkit.
Provides shared functionality to reduce code duplication.
"""
import json
import re
import threading
from typing import Any, Callable, Dict, Optional

from .logging_config import get_logger

logger = get_logger(__name__)


class AsyncTaskRunner:
    """Unified async task execution for GUI operations.

    Provides consistent pattern for running long operations in background threads
    while keeping UI responsive and thread-safe.
    """

    def __init__(self, parent_window):
        """Initialize task runner.

        Args:
            parent_window: Parent window with root attribute for after() calls
        """
        self.parent = parent_window
        self.task = None
        self.stop_requested = False

    def run_async(
        self,
        func: Callable,
        on_complete: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None
    ) -> None:
        """Run function asynchronously with callbacks.

        Args:
            func: Function to run in background thread
            on_complete: Called in main thread with function result
            on_error: Called in main thread if exception occurs
        """
        self.stop_requested = False

        def wrapper():
            try:
                logger.debug(f"Starting async task: {func.__name__}")
                result = func()

                if not self.stop_requested and on_complete:
                    self.parent.root.after(0, on_complete, result)

                logger.debug(f"Async task completed: {func.__name__}")
            except Exception as e:
                logger.error(f"Async task failed: {func.__name__}", exc_info=True)
                if not self.stop_requested and on_error:
                    self.parent.root.after(0, on_error, e)

        self.task = threading.Thread(target=wrapper, daemon=True)
        self.task.start()

    def stop(self) -> None:
        """Request task to stop (cooperative)."""
        self.stop_requested = True
        logger.debug("Task stop requested")


class AIResponseParser:
    """Unified AI response parsing with fallback strategies.

    Handles common patterns of AI responses:
    - Markdown code blocks (```json ... ```)
    - Plain JSON
    - Malformed JSON with regex extraction
    """

    @staticmethod
    def clean_json_response(text: str) -> str:
        """Remove markdown formatting from JSON response.

        Args:
            text: Raw AI response text

        Returns:
            Cleaned JSON string
        """
        text = text.strip()

        # Remove ```json prefix
        if text.startswith("```json"):
            text = text[7:]
        # Remove ``` prefix
        elif text.startswith("```"):
            text = text[3:]

        # Remove ``` suffix
        if text.endswith("```"):
            text = text[:-3]

        return text.strip()

    @staticmethod
    def parse_json_with_fallback(text: str) -> Dict[str, Any]:
        """Parse JSON with regex fallback for malformed responses.

        Args:
            text: AI response text (possibly with markdown)

        Returns:
            Parsed dictionary

        Raises:
            ValueError: If parsing fails completely
        """
        # Try standard JSON parsing first
        try:
            cleaned = AIResponseParser.clean_json_response(text)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("JSON parsing failed, attempting regex fallback")
            return AIResponseParser._regex_fallback(text)

    @staticmethod
    def _regex_fallback(text: str) -> Dict[str, Any]:
        """Extract JSON fields using regex when JSON parsing fails.

        Args:
            text: Malformed JSON text

        Returns:
            Dictionary with extracted fields

        Raises:
            ValueError: If extraction fails
        """
        result = {}

        # Extract numeric fields (relevance_score, etc.)
        number_pattern = r'"(\w+)"\s*:\s*(\d+(?:\.\d+)?)'
        for match in re.finditer(number_pattern, text):
            key, value = match.groups()
            try:
                result[key] = int(value) if '.' not in value else float(value)
            except ValueError:
                pass

        # Extract string fields (analysis, literature_review_suggestion, etc.)
        string_pattern = r'"(\w+)"\s*:\s*"([^"]*)"'
        for match in re.finditer(string_pattern, text):
            key, value = match.groups()
            if key not in result:  # Don't overwrite numeric fields
                result[key] = value

        # Extract boolean fields (yes/no questions)
        bool_pattern = r'"(\w+)"\s*:\s*(true|false)'
        for match in re.finditer(bool_pattern, text):
            key, value = match.groups()
            if key not in result:
                result[key] = value.lower() == 'true'

        if not result:
            logger.error(f"Regex fallback failed to extract any fields from: {text[:200]}...")
            raise ValueError("Failed to parse AI response with both JSON and regex")

        logger.debug(f"Regex fallback extracted {len(result)} fields")
        return result

    @staticmethod
    def parse_relevance_response(text: str) -> Dict[str, Any]:
        """Parse CSV relevance analysis response with specific fallback.

        Args:
            text: AI response for relevance analysis

        Returns:
            Dictionary with relevance_score, analysis, and optional literature_review_suggestion
        """
        try:
            return AIResponseParser.parse_json_with_fallback(text)
        except ValueError:
            # Specific fallback for relevance analysis
            result = {}

            # Extract relevance score
            score_match = re.search(r'relevance_score["\']?\s*:\s*(\d+)', text)
            if score_match:
                result['relevance_score'] = int(score_match.group(1))
            else:
                result['relevance_score'] = 0

            # Extract analysis text
            analysis_match = re.search(r'analysis["\']?\s*:\s*["\']([^"\']*)["\']', text)
            if analysis_match:
                result['analysis'] = analysis_match.group(1)
            else:
                result['analysis'] = "Unable to extract analysis from AI response"

            # Extract literature review suggestion (optional)
            lit_match = re.search(r'literature_review_suggestion["\']?\s*:\s*["\']([^"\']*)["\']', text)
            if lit_match:
                result['literature_review_suggestion'] = lit_match.group(1)
            else:
                result['literature_review_suggestion'] = ""

            logger.warning(f"Used specific fallback for relevance response: {result}")
            return result


class ColumnDetector:
    """Unified column name detection for flexible CSV/Excel handling.

    Handles different column naming conventions (English, Chinese, etc.)
    """

    # Common column name variants
    COLUMN_VARIANTS = {
        'title': ['Title', '文献标题', 'Article Title', '标题', 'title'],
        'abstract': ['Abstract', '摘要', 'abstract'],
        'author': ['Author', 'Authors', '作者', 'author'],
        'year': ['Year', '年份', 'Publication Year', 'year'],
        'doi': ['DOI', 'doi'],
        'journal': ['Journal', 'Source title', '期刊', 'journal'],
    }

    @staticmethod
    def find_column(df, column_type: str) -> Optional[str]:
        """Find column by type using common variants.

        Args:
            df: pandas DataFrame
            column_type: Type of column ('title', 'abstract', etc.)

        Returns:
            Column name if found, None otherwise
        """
        variants = ColumnDetector.COLUMN_VARIANTS.get(column_type, [])

        for variant in variants:
            if variant in df.columns:
                logger.debug(f"Found {column_type} column: {variant}")
                return variant

        logger.warning(f"Column type '{column_type}' not found. Available: {list(df.columns)}")
        return None

    @staticmethod
    def get_required_column(df, column_type: str) -> str:
        """Get required column or raise error.

        Args:
            df: pandas DataFrame
            column_type: Type of column

        Returns:
            Column name

        Raises:
            ValueError: If column not found
        """
        col = ColumnDetector.find_column(df, column_type)
        if col is None:
            variants = ', '.join(ColumnDetector.COLUMN_VARIANTS.get(column_type, []))
            raise ValueError(
                f"Required column '{column_type}' not found. "
                f"Tried: {variants}. "
                f"Available columns: {', '.join(df.columns)}"
            )
        return col
