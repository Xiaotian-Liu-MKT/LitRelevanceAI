"""Configuration factory for module-specific defaults and loading.

This module provides a centralized way to create and load configurations for different
analysis modules, avoiding scattered DEFAULT_CONFIG overrides and duplicate loading
logic throughout the codebase.
"""

from typing import Dict, Any, Tuple, Optional
from pathlib import Path
import json
import yaml

from .constants import DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_WORKERS
from .config import load_config as base_load_config, DEFAULT_CONFIG
from .resources import resource_path
from .logging_config import get_logger

logger = get_logger(__name__)


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

    # Configuration loading methods (eliminates code duplication)

    @staticmethod
    def load_config_with_questions(
        config_path: Optional[str] = None,
        questions_path: Optional[str] = None,
        module: str = "csv"
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Load configuration and questions for a specific module.

        Args:
            config_path: Path to configuration file (optional)
            questions_path: Path to questions template (optional)
            module: Module name ("csv", "abstract", "pdf")

        Returns:
            Tuple of (config_dict, questions_dict)
        """
        # Load base configuration
        default_cfg = resource_path("configs", "config.yaml")
        config = base_load_config(str(config_path or default_cfg), DEFAULT_CONFIG)

        # Load questions
        q_path = questions_path or resource_path("configs", "questions", f"{module}.yaml")

        try:
            if Path(q_path).exists():
                with open(q_path, 'r', encoding='utf-8') as f:
                    questions = yaml.safe_load(f) or {}
                logger.debug(f"Loaded {module} questions from {q_path}")
            else:
                logger.warning(f"Questions file not found: {q_path}, using empty dict")
                questions = {}
        except Exception as e:
            logger.warning(f"Failed to load questions from {q_path}: {e}")
            questions = {}

        return config, questions

    @staticmethod
    def load_mode_questions(mode: str) -> Dict[str, Any]:
        """Load screening mode questions.

        Args:
            mode: Mode name to load

        Returns:
            Dictionary containing mode questions and criteria
        """
        # Try YAML format first
        yaml_path = resource_path("configs", "abstract", f"{mode}.yaml")

        if yaml_path.exists():
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    questions = yaml.safe_load(f)
                    logger.debug(f"Loaded mode '{mode}' from YAML: {yaml_path}")
                    return questions or {}
            except Exception as e:
                logger.warning(f"Failed to load mode from YAML {yaml_path}: {e}")

        # Fallback to legacy JSON format
        legacy_path = resource_path("questions_config.json")

        if legacy_path.exists():
            try:
                with open(legacy_path, 'r', encoding='utf-8') as f:
                    all_modes = json.load(f)

                if mode in all_modes:
                    logger.debug(f"Loaded mode '{mode}' from legacy JSON: {legacy_path}")
                    return all_modes[mode]
                else:
                    logger.warning(f"Mode '{mode}' not found in {legacy_path}")
            except Exception as e:
                logger.warning(f"Failed to load from legacy JSON {legacy_path}: {e}")

        # Return empty structure if nothing found
        logger.warning(f"No questions found for mode '{mode}', using empty structure")
        return {"open_questions": [], "yes_no_questions": []}

    @staticmethod
    def load_matrix_dimensions(dimensions_file: Optional[str] = None) -> Dict[str, Any]:
        """Load matrix dimensions configuration.

        Args:
            dimensions_file: Path to dimensions YAML file (optional)

        Returns:
            Dictionary containing dimensions configuration
        """
        dim_path = dimensions_file or resource_path("configs", "matrix", "default.yaml")

        try:
            if Path(dim_path).exists():
                with open(dim_path, 'r', encoding='utf-8') as f:
                    dimensions = yaml.safe_load(f) or {}
                logger.debug(f"Loaded matrix dimensions from {dim_path}")
                return dimensions
            else:
                logger.warning(f"Dimensions file not found: {dim_path}, using default structure")
                return {"dimensions": []}
        except Exception as e:
            logger.warning(f"Failed to load dimensions from {dim_path}: {e}")
            return {"dimensions": []}
