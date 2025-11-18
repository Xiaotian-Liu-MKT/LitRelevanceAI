"""Configuration factory for module-specific defaults.

This module provides a centralized way to create configurations for different
analysis modules, avoiding scattered DEFAULT_CONFIG overrides throughout the codebase.
"""

from typing import Dict, Any

from .constants import DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_WORKERS


class ConfigFactory:
    """Factory for creating module-specific configurations.

    This class provides static methods to generate configuration dictionaries
    with appropriate defaults for each analysis module, while preserving any
    custom settings from the base configuration.
    """

    @staticmethod
    def for_csv_analyzer(base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create configuration for CSV relevance analyzer.

        Args:
            base_config: Base configuration dictionary

        Returns:
            Merged configuration with CSV analyzer defaults
        """
        return {
            **base_config,
            "MODEL_NAME": base_config.get("MODEL_NAME", DEFAULT_MODEL),
            "TEMPERATURE": base_config.get("TEMPERATURE", DEFAULT_TEMPERATURE),
        }

    @staticmethod
    def for_abstract_screener(base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create configuration for abstract screener.

        Args:
            base_config: Base configuration dictionary

        Returns:
            Merged configuration with abstract screener defaults
        """
        return {
            **base_config,
            "MODEL_NAME": base_config.get("MODEL_NAME", DEFAULT_MODEL),
            "TEMPERATURE": base_config.get("TEMPERATURE", DEFAULT_TEMPERATURE),
            "ENABLE_VERIFICATION": base_config.get("ENABLE_VERIFICATION", True),
            "MAX_WORKERS": base_config.get("MAX_WORKERS", DEFAULT_MAX_WORKERS),
        }

    @staticmethod
    def for_matrix_analyzer(base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create configuration for literature matrix analyzer.

        Args:
            base_config: Base configuration dictionary

        Returns:
            Merged configuration with matrix analyzer defaults
        """
        return {
            **base_config,
            "MODEL_NAME": base_config.get("MODEL_NAME", "gpt-4o"),  # Matrix uses more powerful model
            "TEMPERATURE": base_config.get("TEMPERATURE", 0.2),  # Lower temperature for structured data
        }

    @staticmethod
    def for_pdf_screener(base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create configuration for PDF screener (legacy).

        Args:
            base_config: Base configuration dictionary

        Returns:
            Merged configuration with PDF screener defaults
        """
        return {
            **base_config,
            "MODEL_NAME": base_config.get("MODEL_NAME", DEFAULT_MODEL),
            "TEMPERATURE": base_config.get("TEMPERATURE", DEFAULT_TEMPERATURE),
        }

    @staticmethod
    def merge_custom_settings(
        config: Dict[str, Any],
        custom_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge custom settings into configuration.

        Args:
            config: Base configuration
            custom_settings: Custom settings to override

        Returns:
            Merged configuration
        """
        return {**config, **custom_settings}
