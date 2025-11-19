"""Test suite for secure logging functionality.

This test verifies that API keys and sensitive information are properly
sanitized in logs and error messages.
"""

import logging
import tempfile
from pathlib import Path

import pytest

from litrx.security_utils import SecureLogger, safe_log_config, safe_log_error
from litrx.logging_config import setup_logging


class TestSecureLogger:
    """Test SecureLogger sanitization methods."""

    def test_sanitize_config_openai(self):
        """Test that OpenAI API keys are sanitized in config."""
        config = {
            "OPENAI_API_KEY": "sk-1234567890abcdefghijklmnopqrstuvwxyz",
            "MODEL_NAME": "gpt-4o",
            "AI_SERVICE": "openai"
        }

        sanitized = SecureLogger.sanitize_config(config)

        # API key should be redacted
        assert sanitized["OPENAI_API_KEY"] == "sk-12345***"
        # Other fields should be unchanged
        assert sanitized["MODEL_NAME"] == "gpt-4o"
        assert sanitized["AI_SERVICE"] == "openai"

    def test_sanitize_config_siliconflow(self):
        """Test that SiliconFlow API keys are sanitized."""
        config = {
            "SILICONFLOW_API_KEY": "sfc-abcdefghijklmnopqrstuvwxyz123456",
            "AI_SERVICE": "siliconflow"
        }

        sanitized = SecureLogger.sanitize_config(config)

        assert sanitized["SILICONFLOW_API_KEY"] == "sfc-abcd***"
        assert sanitized["AI_SERVICE"] == "siliconflow"

    def test_sanitize_config_nested(self):
        """Test sanitization of nested config dictionaries."""
        config = {
            "api_settings": {
                "OPENAI_API_KEY": "sk-secretkey123456789012345678901234567890",
                "API_BASE": "https://api.openai.com"
            },
            "model": "gpt-4"
        }

        sanitized = SecureLogger.sanitize_config(config)

        assert sanitized["api_settings"]["OPENAI_API_KEY"] == "sk-secre***"
        assert sanitized["api_settings"]["API_BASE"] == "https://api.openai.com"
        assert sanitized["model"] == "gpt-4"

    def test_sanitize_string_api_key_patterns(self):
        """Test sanitization of various API key patterns in strings."""
        test_cases = [
            (
                "Error: Invalid API key sk-1234567890abcdefghijklmnopqrstuvwxyz",
                "Error: Invalid API key ***REDACTED***"
            ),
            (
                "Token: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc",
                "Token: ***REDACTED***"
            ),
            (
                "Using key sk-proj-abc123def456ghi789jkl012mno345pqr678stu",
                "Using key ***REDACTED***"
            ),
        ]

        for original, expected in test_cases:
            sanitized = SecureLogger.sanitize_string(original)
            assert "***REDACTED***" in sanitized
            # Verify original sensitive data is not in sanitized version
            assert "sk-" not in sanitized or sanitized == original
            assert "eyJ" not in sanitized or sanitized == original

    def test_sanitize_error(self):
        """Test sanitization of exception messages."""
        error = RuntimeError("API request failed with key sk-1234567890abcdefghijklmnopqrstuvwxyz")

        sanitized = SecureLogger.sanitize_error(error)

        assert "***REDACTED***" in sanitized
        assert "sk-1234567890" not in sanitized

    def test_safe_log_config(self):
        """Test safe_log_config convenience function."""
        config = {
            "OPENAI_API_KEY": "sk-secret123456789012345678901234567890",
            "MODEL_NAME": "gpt-4o"
        }

        log_string = safe_log_config(config)

        # Should be formatted as "key: value" pairs
        assert "OPENAI_API_KEY: sk-secre***" in log_string
        assert "MODEL_NAME: gpt-4o" in log_string
        # Original key should not appear
        assert "sk-secret123456789012345678901234567890" not in log_string

    def test_safe_log_error(self):
        """Test safe_log_error convenience function."""
        error = ValueError("Invalid OPENAI_API_KEY: sk-abc123def456ghi789jkl")

        log_string = safe_log_error(error, include_type=True)

        assert "ValueError:" in log_string
        assert "***REDACTED***" in log_string
        assert "sk-abc123" not in log_string


class TestLoggingIntegration:
    """Test integration of SecureLogger with logging system."""

    def test_logging_config_sanitizes_api_keys(self):
        """Test that logging configuration properly sanitizes API keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            # Setup logging
            logger = setup_logging(log_level="DEBUG", log_dir=log_dir, console_output=False)

            # Simulate logging with sensitive data
            config = {
                "OPENAI_API_KEY": "sk-1234567890abcdefghijklmnopqrstuvwxyz",
                "MODEL_NAME": "gpt-4o"
            }

            # Log using safe_log_config
            safe_config_str = safe_log_config(config)
            logger.info(f"Configuration loaded: {safe_config_str}")

            # Read log file
            log_file = log_dir / "litrx.log"
            assert log_file.exists()

            log_content = log_file.read_text()

            # Verify API key is redacted in log
            assert "sk-12345***" in log_content or "***REDACTED***" in log_content
            # Verify full API key is NOT in log
            assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in log_content

    def test_exception_hook_sanitizes_uncaught_exceptions(self):
        """Test that global exception hook sanitizes uncaught exceptions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            # Setup logging (installs exception hook)
            logger = setup_logging(log_level="DEBUG", log_dir=log_dir, console_output=False)

            # Manually trigger the exception hook
            import sys
            from litrx.logging_config import _secure_exception_hook

            try:
                raise RuntimeError("API key sk-1234567890abcdefghijklmnopqrstuvwxyz is invalid")
            except RuntimeError as e:
                _secure_exception_hook(type(e), e, e.__traceback__)

            # Read log file
            log_file = log_dir / "litrx.log"
            log_content = log_file.read_text()

            # Verify exception is logged with sanitized message
            assert "Uncaught exception" in log_content
            assert "***REDACTED***" in log_content
            # Verify full API key is NOT in log
            assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in log_content


class TestAIClientIntegration:
    """Test AIClient integration with SecureLogger."""

    def test_ai_client_logs_sanitized_config(self, mocker):
        """Test that AIClient logs sanitized configuration."""
        # Mock OpenAI to avoid actual API calls
        mocker.patch("litrx.ai_client.OpenAI")

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            setup_logging(log_level="DEBUG", log_dir=log_dir, console_output=False)

            from litrx.ai_client import AIClient

            config = {
                "AI_SERVICE": "openai",
                "OPENAI_API_KEY": "sk-1234567890abcdefghijklmnopqrstuvwxyz",
                "MODEL_NAME": "gpt-4o"
            }

            # Initialize client (should log sanitized config)
            try:
                client = AIClient(config)
            except Exception:
                pass  # May fail due to mocking, but logs are still written

            # Read log file
            log_file = log_dir / "litrx.log"
            log_content = log_file.read_text()

            # Verify full API key is NOT in log
            assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in log_content
            # Verify sanitized version appears (if logged)
            if "OPENAI_API_KEY" in log_content:
                assert "sk-12345***" in log_content or "***" in log_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
