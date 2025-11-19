"""Token usage tracking for AI API calls.

This module provides centralized tracking of token usage across all AI operations,
with separate tracking for input (prompt) and output (completion) tokens.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import threading

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TokenUsage:
    """Token usage statistics for a single API call or accumulated totals."""

    input_tokens: int = 0  # prompt_tokens
    output_tokens: int = 0  # completion_tokens
    total_tokens: int = 0

    def __add__(self, other: 'TokenUsage') -> 'TokenUsage':
        """Add two TokenUsage objects together."""
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens
        )

    def to_millions(self) -> Dict[str, float]:
        """Convert token counts to millions for display."""
        return {
            'input_M': round(self.input_tokens / 1_000_000, 3),
            'output_M': round(self.output_tokens / 1_000_000, 3),
            'total_M': round(self.total_tokens / 1_000_000, 3)
        }

    def format_display(self) -> str:
        """Format token usage for display in GUI.

        Returns:
            Formatted string like "Input: 0.123M | Output: 0.045M | Total: 0.168M"
        """
        m = self.to_millions()
        return f"Input: {m['input_M']:.3f}M | Output: {m['output_M']:.3f}M | Total: {m['total_M']:.3f}M"

    def format_summary(self) -> str:
        """Format token usage summary for logs/reports.

        Returns:
            Formatted string like "Total: 168,432 tokens (Input: 123,456 | Output: 44,976)"
        """
        return (
            f"Total: {self.total_tokens:,} tokens "
            f"(Input: {self.input_tokens:,} | Output: {self.output_tokens:,})"
        )

    @classmethod
    def from_api_response(cls, usage_dict: Optional[Dict]) -> 'TokenUsage':
        """Create TokenUsage from OpenAI API response usage object.

        Args:
            usage_dict: The 'usage' field from API response

        Returns:
            TokenUsage object with parsed values
        """
        if not usage_dict:
            return cls()

        return cls(
            input_tokens=usage_dict.get('prompt_tokens', 0),
            output_tokens=usage_dict.get('completion_tokens', 0),
            total_tokens=usage_dict.get('total_tokens', 0)
        )


class TokenUsageTracker:
    """Thread-safe tracker for cumulative token usage across multiple API calls."""

    def __init__(self):
        self._lock = threading.Lock()
        self._usage = TokenUsage()
        self._call_count = 0

    def add_usage(self, usage: TokenUsage) -> None:
        """Add token usage from a single API call.

        Args:
            usage: TokenUsage object to add to cumulative total
        """
        with self._lock:
            self._usage = self._usage + usage
            self._call_count += 1
            logger.debug(
                f"Token usage added (call #{self._call_count}): "
                f"+{usage.input_tokens} input, +{usage.output_tokens} output"
            )

    def get_usage(self) -> TokenUsage:
        """Get current cumulative token usage (thread-safe).

        Returns:
            Copy of current TokenUsage
        """
        with self._lock:
            return TokenUsage(
                input_tokens=self._usage.input_tokens,
                output_tokens=self._usage.output_tokens,
                total_tokens=self._usage.total_tokens
            )

    def get_call_count(self) -> int:
        """Get number of API calls tracked.

        Returns:
            Number of calls
        """
        with self._lock:
            return self._call_count

    def reset(self) -> None:
        """Reset tracker to zero."""
        with self._lock:
            self._usage = TokenUsage()
            self._call_count = 0
            logger.debug("Token usage tracker reset")

    def get_summary(self) -> Dict:
        """Get comprehensive summary of token usage.

        Returns:
            Dictionary with all statistics
        """
        with self._lock:
            usage = self._usage
            millions = usage.to_millions()
            return {
                'call_count': self._call_count,
                'input_tokens': usage.input_tokens,
                'output_tokens': usage.output_tokens,
                'total_tokens': usage.total_tokens,
                'input_M': millions['input_M'],
                'output_M': millions['output_M'],
                'total_M': millions['total_M'],
                'avg_tokens_per_call': usage.total_tokens / max(self._call_count, 1),
                'display_text': usage.format_display(),
                'summary_text': usage.format_summary()
            }
