"""Configuration utilities for LitRelevanceAI with Pydantic validation.

This module provides robust configuration management with:
- Type validation using Pydantic models
- Cascading configuration from multiple sources (defaults, files, env, keyring)
- Helpful error messages for configuration issues
- Backward compatibility with existing code
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

try:
    from .key_manager import get_key_manager, KEY_OPENAI, KEY_SILICONFLOW
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False


# ---------------------------------------------------------------------------
# Pydantic Configuration Models
# ---------------------------------------------------------------------------

class AIConfig(BaseModel):
    """AI service configuration with validation.

    Validates configuration values and provides helpful error messages
    for common configuration mistakes.
    """

    AI_SERVICE: Literal["openai", "gemini", "siliconflow"] = Field(
        default="openai",
        description="AI service provider"
    )
    MODEL_NAME: str = Field(
        default="gpt-4o",
        description="Model identifier"
    )
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Google Gemini API key"
    )
    SILICONFLOW_API_KEY: Optional[str] = Field(
        default=None,
        description="SiliconFlow API key"
    )
    API_BASE: Optional[str] = Field(
        default=None,
        description="Custom API base URL (optional)"
    )
    TEMPERATURE: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0-2.0)"
    )
    VERBOSITY: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="GPT-5 verbosity level"
    )
    REASONING_EFFORT: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="GPT-5 reasoning effort level"
    )
    ENABLE_CACHE: bool = Field(
        default=True,
        description="Enable result caching"
    )
    ENABLE_VERIFICATION: bool = Field(
        default=True,
        description="Enable abstract screening verification"
    )
    LANGUAGE: Literal["en", "zh"] = Field(
        default="en",
        description="UI language"
    )

    # Allow extra fields for backward compatibility
    model_config = {
        "extra": "allow",
        "validate_assignment": True,
    }

    @field_validator('OPENAI_API_KEY', 'GEMINI_API_KEY', 'SILICONFLOW_API_KEY')
    @classmethod
    def validate_api_key_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate API key format (basic check)."""
        if v and len(v.strip()) < 10:
            raise ValueError("API key appears to be too short (minimum 10 characters)")
        return v.strip() if v else None

    @model_validator(mode='after')
    def validate_service_has_key(self) -> 'AIConfig':
        """Ensure the selected AI service has a corresponding API key.

        Validation is skipped in test/development environments when LITRX_ENV
        is set to 'test' or 'dev'.
        """
        import os
        import logging

        # 允许测试/开发环境跳过 API 密钥验证
        env_mode = os.getenv('LITRX_ENV', '').lower()
        if env_mode in ['test', 'dev', 'development']:
            # 记录跳过验证（用于调试）
            logger = logging.getLogger(__name__)
            logger.debug(f"Skipping API key validation in {env_mode} environment")
            return self

        # 生产环境：严格验证
        service_to_key = {
            'openai': ('OPENAI_API_KEY', self.OPENAI_API_KEY),
            'gemini': ('GEMINI_API_KEY', self.GEMINI_API_KEY),
            'siliconflow': ('SILICONFLOW_API_KEY', self.SILICONFLOW_API_KEY),
        }

        key_name, key_value = service_to_key.get(self.AI_SERVICE, (None, None))

        if not key_value:
            # Provide helpful error message
            raise ValueError(
                f"AI service '{self.AI_SERVICE}' requires {key_name}, but it is not set. "
                f"Please set it in one of the following ways:\n"
                f"  1. Environment variable: export {key_name}=your-key\n"
                f"  2. .env file: {key_name}=your-key\n"
                f"  3. Config file (~/.litrx_gui.yaml or configs/config.yaml)\n"
                f"  4. System keyring (recommended for security)\n\n"
                f"For testing/development, set: export LITRX_ENV=test"
            )

        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.model_dump(exclude_none=False)


# ---------------------------------------------------------------------------
# Configuration Loader
# ---------------------------------------------------------------------------

class ConfigLoader:
    """Cascading configuration loader with validation.

    Loads configuration from multiple sources in priority order:
    1. Environment variables (highest priority)
    2. Secure keyring storage
    3. User config file (~/.litrx_gui.yaml)
    4. Project config file (configs/config.yaml)
    5. Default values (lowest priority)
    """

    def __init__(self):
        self._config_sources = []

    def load(
        self,
        config_path: Optional[str] = None,
        env_path: str = ".env",
        skip_validation: bool = False
    ) -> AIConfig:
        """Load and validate configuration.

        Args:
            config_path: Path to config file (YAML/JSON)
            env_path: Path to .env file
            skip_validation: Skip API key validation (useful for testing)

        Returns:
            Validated AIConfig instance

        Raises:
            ValueError: If configuration is invalid
        """
        # Load .env file first
        load_env_file(env_path)

        # Build config dictionary from all sources
        config_dict = self._merge_sources(config_path)

        # Create validated config
        try:
            if skip_validation:
                # Temporarily disable validation for testing
                return AIConfig.model_construct(**config_dict)
            else:
                return AIConfig(**config_dict)
        except Exception as e:
            raise ValueError(
                f"Configuration validation failed: {e}\n"
                f"Please check your configuration files and environment variables."
            )

    def _merge_sources(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Merge configuration from all sources in priority order."""
        config = {}

        # 1. Start with defaults (lowest priority)
        config.update(self._load_defaults())

        # 2. Load project config if exists
        project_config = Path("configs/config.yaml")
        if project_config.exists():
            config.update(self._load_yaml(str(project_config)))

        # 3. Load user config if exists
        user_config = Path.home() / ".litrx_gui.yaml"
        if user_config.exists():
            config.update(self._load_yaml(str(user_config)))

        # 4. Load specified config file
        if config_path:
            config.update(self._load_file(config_path))

        # 5. Load from environment variables (higher priority)
        config.update(self._load_env())

        # 6. Load from keyring (highest priority for API keys)
        if KEYRING_AVAILABLE:
            config.update(self._load_keyring())

        return config

    def _load_defaults(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            "AI_SERVICE": "openai",
            "MODEL_NAME": "gpt-4o",
            "OPENAI_API_KEY": None,
            "GEMINI_API_KEY": None,
            "SILICONFLOW_API_KEY": None,
            "API_BASE": None,
            "TEMPERATURE": 0.3,
            "VERBOSITY": "medium",
            "REASONING_EFFORT": "medium",
            "ENABLE_CACHE": True,
            "ENABLE_VERIFICATION": True,
            "LANGUAGE": "en",
        }

    def _load_yaml(self, path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            if yaml is None:
                return {}

            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _load_file(self, path: str) -> Dict[str, Any]:
        """Load configuration from JSON or YAML file."""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return {}

            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in {'.yaml', '.yml'}:
                    if yaml is None:
                        raise RuntimeError("pyyaml is required to read YAML files")
                    data = yaml.safe_load(f) or {}
                else:
                    data = json.load(f)

                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _load_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}

        env_keys = [
            'AI_SERVICE', 'MODEL_NAME', 'OPENAI_API_KEY', 'GEMINI_API_KEY',
            'SILICONFLOW_API_KEY', 'API_BASE', 'TEMPERATURE', 'VERBOSITY',
            'REASONING_EFFORT', 'ENABLE_CACHE', 'ENABLE_VERIFICATION', 'LANGUAGE'
        ]

        for key in env_keys:
            value = os.environ.get(key)
            if value:
                # Type conversion for specific keys
                if key == 'TEMPERATURE':
                    try:
                        config[key] = float(value)
                    except ValueError:
                        pass
                elif key in ['ENABLE_CACHE', 'ENABLE_VERIFICATION']:
                    config[key] = value.lower() in ('true', '1', 'yes')
                else:
                    config[key] = value

        return config

    def _load_keyring(self) -> Dict[str, Any]:
        """Load API keys from secure keyring storage."""
        config = {}

        try:
            key_manager = get_key_manager()

            openai_key = key_manager.get_key(KEY_OPENAI)
            if openai_key:
                config['OPENAI_API_KEY'] = openai_key

            siliconflow_key = key_manager.get_key(KEY_SILICONFLOW)
            if siliconflow_key:
                config['SILICONFLOW_API_KEY'] = siliconflow_key
        except Exception:
            pass

        return config


# ---------------------------------------------------------------------------
# Backward-Compatible Functions
# ---------------------------------------------------------------------------

# Global loader instance
_config_loader = ConfigLoader()

# Legacy DEFAULT_CONFIG for backward compatibility
DEFAULT_CONFIG: Dict[str, Any] = {
    "AI_SERVICE": "openai",
    "MODEL_NAME": "gpt-4o",
    "OPENAI_API_KEY": "",
    "GEMINI_API_KEY": "",
    "SILICONFLOW_API_KEY": "",
    "API_BASE": "",
    "TEMPERATURE": 0.3,
    "VERBOSITY": "medium",
    "REASONING_EFFORT": "medium",
    "ENABLE_CACHE": True,
    "ENABLE_VERIFICATION": True,
    "LANGUAGE": "en",
}


def load_env_file(env_path: str = ".env") -> None:
    """Load environment variables from a .env file if present.

    Args:
        env_path: Path to .env file (default: ".env")
    """
    path = Path(env_path)
    if not path.exists():
        return

    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def load_config(
    path: Optional[str],
    default: Optional[Dict[str, Any]] = None,
    skip_validation: bool = True
) -> Dict[str, Any]:
    """Load configuration from file and merge with defaults.

    This function maintains backward compatibility while using Pydantic
    validation internally. By default, validation is skipped to maintain
    backward compatibility.

    Args:
        path: Path to config file (YAML/JSON)
        default: Default configuration dictionary (ignored, kept for compatibility)
        skip_validation: Skip API key validation (default: True for backward compatibility)

    Returns:
        Configuration dictionary
    """
    try:
        config = _config_loader.load(path, skip_validation=skip_validation)
        return config.to_dict()
    except ValueError:
        # If validation fails, fall back to unvalidated config for backward compatibility
        # but still load from all sources
        config_dict = _config_loader._merge_sources(path)
        return {**DEFAULT_CONFIG, **config_dict}


def get_validated_config(
    path: Optional[str] = None,
    env_path: str = ".env"
) -> AIConfig:
    """Get validated configuration object.

    This is the recommended way to load configuration in new code.

    Args:
        path: Path to config file
        env_path: Path to .env file

    Returns:
        Validated AIConfig instance

    Raises:
        ValueError: If configuration is invalid
    """
    return _config_loader.load(path, env_path)
