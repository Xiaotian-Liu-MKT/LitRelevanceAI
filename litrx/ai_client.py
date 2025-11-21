"""Simple AI client wrapper for OpenAI and SiliconFlow APIs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .config import DEFAULT_CONFIG as BASE_CONFIG, load_config as base_load_config
from .resources import resource_path
from .i18n import t
from .logging_config import get_logger
from .security_utils import SecureLogger, safe_log_config, safe_log_error
from .token_tracker import TokenUsage

logger = get_logger(__name__)


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load AI client configuration.

    Parameters
    ----------
    path:
        Optional path to a YAML/JSON config file. When omitted, the default
        configuration under ``configs/config.yaml`` is used.
    """

    default_path = resource_path("configs", "config.yaml")
    return base_load_config(str(path or default_path), BASE_CONFIG)


class AIClient:
    """Initialize API credentials and send requests through OpenAI SDK."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self._validate_dependencies()

        service = config.get("AI_SERVICE", "openai")
        model = config.get("MODEL_NAME", "gpt-4o")

        # Log sanitized configuration for debugging
        logger.info(f"Initializing AIClient with service={service}, model={model}")
        logger.debug(f"Configuration: {safe_log_config(config)}")

        if service == "openai":
            api_key = config.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error("OpenAI API key not configured")
                raise RuntimeError(t("error_openai_key_missing"))
            api_base = config.get("API_BASE") or os.getenv("API_BASE") or None
            logger.debug(f"OpenAI API base: {api_base if api_base else 'default'}")

        elif service == "siliconflow":
            api_key = config.get("SILICONFLOW_API_KEY") or os.getenv("SILICONFLOW_API_KEY")
            if not api_key:
                logger.error("SiliconFlow API key not configured")
                raise RuntimeError(t("error_siliconflow_key_missing"))
            # SiliconFlow uses OpenAI-compatible API
            api_base = "https://api.siliconflow.cn/v1"
            logger.debug(f"SiliconFlow API base: {api_base}")

        else:
            logger.error(f"Invalid AI service: {service}")
            raise RuntimeError(t("error_invalid_service", service=service))

        self.model = model
        self.service = service
        self.config = config

        # Cache model capability (avoid per-request checks/log spam)
        self.supports_temperature = self._detect_temperature_support(model)
        self._warned_temperature = False

        # Initialize OpenAI client (works for both OpenAI and SiliconFlow)
        try:
            self.client = OpenAI(
                api_key=api_key,
                base_url=api_base if api_base else None
            )
        except TypeError as exc:
            # Provide a clearer message for the common httpx/OpenAI mismatch
            if "proxies" in str(exc):
                guidance = (
                    "Incompatible httpx/OpenAI versions detected (unsupported 'proxies' argument). "
                    "Reinstall with `pip install -e .` to get openai>=1.14.0 and httpx>=0.27,<0.28."
                )
                logger.error(guidance)
                raise RuntimeError(guidance) from exc
            raise
        logger.info("AIClient initialized successfully")

    def request(self, messages: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        """Send a chat completion request and return the response.

        Parameters
        ----------
        messages:
            List of message dictionaries with 'role' and 'content' keys.
        **kwargs:
            Additional parameters to pass to the API (temperature, max_tokens, etc.)

        Returns
        -------
        dict:
            Response dictionary in OpenAI format with 'choices' and 'token_usage' keys.
            The 'token_usage' key contains a TokenUsage object with input/output token counts.
        """
        # Sanitize unsupported params for some models (e.g., GPT-5/o* may not accept temperature)
        sanitized = dict(kwargs)
        if not self.supports_temperature and "temperature" in sanitized:
            if not self._warned_temperature:
                logger.info("Model does not support 'temperature'; removing it from requests")
                self._warned_temperature = True
            sanitized.pop("temperature", None)

        try:
            # Promote visibility so GUI users can see activity at INFO level
            try:
                has_rf = bool(sanitized.get("response_format"))
            except Exception:
                has_rf = False

            # Sanitize messages before logging to avoid leaking sensitive data
            safe_message_preview = SecureLogger.sanitize_string(str(messages[0]["content"][:100]) if messages else "")

            logger.info(
                "Dispatching AI request | model=%s, messages=%d, temperature=%s, response_format=%s",
                self.model,
                len(messages),
                sanitized.get("temperature", "<omitted>"),
                sanitized.get("response_format") if has_rf else "<none>"
            )
            logger.debug(f"First message preview (sanitized): {safe_message_preview}...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                timeout=self.config.get("AI_TIMEOUT_SECONDS", 60),
                **sanitized
            )

            # Parse token usage from response
            usage_dict = getattr(response, 'usage', None)
            token_usage = TokenUsage.from_api_response(usage_dict.model_dump() if usage_dict else None)

            logger.info(
                "AI request completed | %s | API calls: see tracker",
                token_usage.format_summary()
            )

            # Return response dict with token_usage object attached
            result = response.model_dump()
            result['token_usage'] = token_usage
            return result

        except Exception as e:
            # Fallback retry if server rejects temperature specifically
            msg = str(e)
            if "param":
                pass
            if ("temperature" in kwargs) and (
                "Unsupported value" in msg or "unsupported_value" in msg or "param': 'temperature" in msg
            ):
                try:
                    logger.warning("Retrying request without temperature due to model constraints")
                    retry_kwargs = dict(sanitized)
                    retry_kwargs.pop("temperature", None)
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        timeout=self.config.get("AI_TIMEOUT_SECONDS", 60),
                        **retry_kwargs
                    )

                    # Parse token usage for retry response
                    usage_dict = getattr(response, 'usage', None)
                    token_usage = TokenUsage.from_api_response(usage_dict.model_dump() if usage_dict else None)
                    logger.info("Retry request completed | %s", token_usage.format_summary())

                    result = response.model_dump()
                    result['token_usage'] = token_usage
                    return result
                except Exception as e2:
                    # Sanitize error message to prevent API key leakage
                    safe_error = safe_log_error(e2)
                    logger.error(f"AI request failed after retry: {safe_error}", exc_info=True)
                    sanitized_error_msg = SecureLogger.sanitize_error(e2)
                    raise RuntimeError(t("error_ai_request_failed", error=sanitized_error_msg)) from e2

            # Sanitize error message to prevent API key leakage
            safe_error = safe_log_error(e)
            logger.error(f"AI request failed: {safe_error}", exc_info=True)
            sanitized_error_msg = SecureLogger.sanitize_error(e)
            raise RuntimeError(t("error_ai_request_failed", error=sanitized_error_msg)) from e

    @staticmethod
    def _detect_temperature_support(model_name: str) -> bool:
        """Heuristic to determine temperature support for a model name."""
        name = (model_name or "").lower()
        return not (name.startswith("gpt-5") or name.startswith("o1") or name.startswith("o3") or name.startswith("o-"))

    @staticmethod
    def _parse_version(version_str: str) -> tuple[int, ...]:
        """Extract numeric components from a version string."""

        parts: List[int] = []
        for segment in version_str.split("."):
            number = ""
            for char in segment:
                if char.isdigit():
                    number += char
                else:
                    break
            if not number:
                break
            parts.append(int(number))
        return tuple(parts)

    @staticmethod
    def _validate_dependencies() -> None:
        """Validate OpenAI/httpx versions to prevent the 'proxies' TypeError."""

        try:
            import openai as openai_module
            import httpx as httpx_module
        except ImportError as exc:
            message = (
                "Required dependencies are missing. Reinstall with `pip install -e .` "
                "to ensure compatible openai and httpx versions."
            )
            logger.error(message)
            raise RuntimeError(message) from exc

        openai_version = AIClient._parse_version(getattr(openai_module, "__version__", ""))
        httpx_version = AIClient._parse_version(getattr(httpx_module, "__version__", ""))

        if openai_version and openai_version < (1, 14, 0):
            message = (
                f"OpenAI SDK {openai_module.__version__} is too old. "
                "Install openai>=1.14.0 to continue."
            )
            logger.error(message)
            raise RuntimeError(message)

        if httpx_version and httpx_version >= (0, 28, 0):
            message = (
                f"httpx {httpx_module.__version__} is incompatible with older OpenAI SDKs. "
                "Install httpx>=0.27,<0.28 to avoid the 'proxies' error."
            )
            logger.error(message)
            raise RuntimeError(message)
