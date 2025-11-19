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
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base if api_base else None
        )
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
            Response dictionary in OpenAI format with 'choices' key.
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

            logger.info("AI request completed | usage=%s", getattr(response, 'usage', None))
            return response.model_dump()

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
                    return response.model_dump()
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
