"""Unit tests for custom exception hierarchy.

Tests for litrx/exceptions.py to ensure all custom exceptions
behave correctly and provide helpful error messages.
"""

import pytest
from litrx.exceptions import (
    LitRxError,
    ConfigurationError,
    APIKeyMissingError,
    APIRequestError,
    FileProcessingError,
    ValidationError,
    APIError,
)


class TestExceptionHierarchy:
    """Test the exception inheritance structure."""

    def test_base_exception(self):
        """Test that LitRxError is the base exception."""
        error = LitRxError("test message")
        assert str(error) == "test message"
        assert isinstance(error, Exception)

    def test_configuration_error_inheritance(self):
        """Test ConfigurationError inherits from LitRxError."""
        error = ConfigurationError("config error")
        assert isinstance(error, LitRxError)
        assert isinstance(error, Exception)

    def test_api_key_missing_error_inheritance(self):
        """Test APIKeyMissingError inherits from ConfigurationError."""
        error = APIKeyMissingError("openai")
        assert isinstance(error, ConfigurationError)
        assert isinstance(error, LitRxError)

    def test_api_request_error_inheritance(self):
        """Test APIRequestError inherits from LitRxError."""
        error = APIRequestError("request failed")
        assert isinstance(error, LitRxError)

    def test_file_processing_error_inheritance(self):
        """Test FileProcessingError inherits from LitRxError."""
        error = FileProcessingError("file error")
        assert isinstance(error, LitRxError)

    def test_validation_error_inheritance(self):
        """Test ValidationError inherits from LitRxError."""
        error = ValidationError("validation failed")
        assert isinstance(error, LitRxError)


class TestConfigurationError:
    """Test ConfigurationError functionality."""

    def test_basic_error_message(self):
        """Test basic error message without help text."""
        error = ConfigurationError("Missing API key")
        assert str(error) == "Missing API key"

    def test_error_with_help_text_stored(self):
        """Test that help_text is stored as an attribute."""
        error = ConfigurationError(
            "Missing API key",
            help_text="Please set OPENAI_API_KEY in your .env file"
        )
        assert str(error) == "Missing API key"
        assert error.help_text == "Please set OPENAI_API_KEY in your .env file"

    def test_help_text_attribute_none(self):
        """Test that help_text defaults to None."""
        error = ConfigurationError("Error occurred")
        assert error.help_text is None


class TestAPIKeyMissingError:
    """Test APIKeyMissingError functionality."""

    def test_openai_service_message(self):
        """Test error message for OpenAI service."""
        error = APIKeyMissingError("openai")
        error_str = str(error)
        assert "openai" in error_str.lower() or "OpenAI" in error_str

    def test_siliconflow_service_message(self):
        """Test error message for SiliconFlow service."""
        error = APIKeyMissingError("siliconflow")
        error_str = str(error)
        assert "siliconflow" in error_str.lower() or "SiliconFlow" in error_str

    def test_includes_helpful_instructions(self):
        """Test that error includes setup instructions."""
        error = APIKeyMissingError("openai")
        error_str = str(error)
        # Should mention .env or configuration
        assert ".env" in error_str or "配置" in error_str or "config" in error_str.lower()


class TestFileProcessingError:
    """Test FileProcessingError functionality."""

    def test_basic_file_error(self):
        """Test basic file processing error."""
        error = FileProcessingError("File not found: test.csv")
        assert "test.csv" in str(error)

    def test_file_error_with_help_text_stored(self):
        """Test that file error stores help_text as attribute."""
        error = FileProcessingError(
            "Cannot read file",
            help_text="Check file permissions"
        )
        assert str(error) == "Cannot read file"
        assert error.help_text == "Check file permissions"


class TestAPIRequestError:
    """Test APIRequestError functionality."""

    def test_basic_api_error(self):
        """Test basic API request error."""
        error = APIRequestError("API request failed")
        assert "API request failed" in str(error)

    def test_api_error_with_status_code(self):
        """Test API error can include status codes."""
        error = APIRequestError("Request failed with status 429")
        error_str = str(error)
        assert "429" in error_str
        assert "failed" in error_str.lower()


class TestValidationError:
    """Test ValidationError functionality."""

    def test_basic_validation_error(self):
        """Test basic validation error."""
        error = ValidationError("Invalid input format")
        assert "Invalid input format" in str(error)

    def test_validation_error_with_details(self):
        """Test validation error with details."""
        error = ValidationError("Field 'name' is required")
        error_str = str(error)
        assert "name" in error_str
        assert "required" in error_str.lower()


class TestCompatibilityAliases:
    """Test that compatibility aliases work correctly."""

    def test_api_error_exists(self):
        """Test that APIError exists as a separate class."""
        # APIError is a separate class, not an alias
        error = APIError("test")
        assert isinstance(error, LitRxError)
        assert str(error) == "test"

    def test_validation_error_exists(self):
        """Test that ValidationError exists."""
        error = ValidationError("validation failed")
        assert isinstance(error, LitRxError)
        assert str(error) == "validation failed"


class TestExceptionChaining:
    """Test that exceptions can be properly chained."""

    def test_exception_from_clause(self):
        """Test using 'from' clause for exception chaining."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise ConfigurationError("Configuration failed") from e
        except ConfigurationError as config_error:
            assert config_error.__cause__ is not None
            assert isinstance(config_error.__cause__, ValueError)
            assert "Original error" in str(config_error.__cause__)

    def test_chained_context_preserved(self):
        """Test that exception context is preserved in chains."""
        try:
            try:
                1 / 0
            except ZeroDivisionError as e:
                raise FileProcessingError("Math error in file processing") from e
        except FileProcessingError as file_error:
            # Original exception should be accessible
            assert file_error.__cause__ is not None
            assert isinstance(file_error.__cause__, ZeroDivisionError)


class TestExceptionPracticalUsage:
    """Test exceptions in realistic usage scenarios."""

    def test_raise_and_catch_configuration_error(self):
        """Test raising and catching ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("Test config error")

        assert "Test config error" in str(exc_info.value)

    def test_raise_and_catch_with_help_text(self):
        """Test raising error with help text."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError(
                "Missing required field",
                help_text="Add field to config.yaml"
            )

        error = exc_info.value
        assert "Missing required field" in str(error)
        assert error.help_text == "Add field to config.yaml"

    def test_multiple_exception_types(self):
        """Test that different exception types can be distinguished."""
        def raise_config_error():
            raise ConfigurationError("Config error")

        def raise_file_error():
            raise FileProcessingError("File error")

        with pytest.raises(ConfigurationError):
            raise_config_error()

        with pytest.raises(FileProcessingError):
            raise_file_error()

        # They should be different types
        try:
            raise_config_error()
        except ConfigurationError:
            pass  # Correct
        except FileProcessingError:
            pytest.fail("Should not catch FileProcessingError")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
