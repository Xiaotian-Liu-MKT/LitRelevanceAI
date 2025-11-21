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

        openai_version: tuple[int, ...] = ()
        httpx_version: tuple[int, ...] = ()

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

        try:
            openai_version = AIClient._parse_version(getattr(openai_module, "__version__", ""))
            httpx_version = AIClient._parse_version(getattr(httpx_module, "__version__", ""))
        except Exception as exc:  # pragma: no cover - defensive guard for unexpected module state
            message = (
                "Unable to read dependency versions (openai/httpx). "
                "Reinstall with `pip install -e .` to restore supported packages."
            )
            logger.error(message)
            raise RuntimeError(message) from exc

        if openai_version and openai_version < (1, 14, 0):
            message = (
                f"OpenAI SDK {getattr(openai_module, '__version__', '<unknown>')} is too old. "
                "Install openai>=1.14.0 to continue."
            )
            logger.error(message)
            raise RuntimeError(message)

        # Enforce lower bound while providing a compatibility shim for unexpected upgrades
        if httpx_version and httpx_version < (0, 27, 0):
            message = (
                f"httpx {getattr(httpx_module, '__version__', '<unknown>')} is too old. "
                "Install httpx>=0.27,<0.28 to avoid transport issues."
            )
            logger.error(message)
            raise RuntimeError(message)

        if httpx_version and httpx_version >= (0, 28, 0):
            logger.warning(
                "Detected httpx %s (proxy keyword removed). Applying compatibility shim "
                "so OpenAI SDK calls keep working. Please pin httpx>=0.27,<0.28 to avoid this fallback.",
                getattr(httpx_module, "__version__", "<unknown>"),
            )
            AIClient._ensure_httpx_proxy_shim(httpx_module)

    @staticmethod
    def _ensure_httpx_proxy_shim(httpx_module: Any) -> None:
        """Add a thin shim so httpx>=0.28 accepts the deprecated ``proxies`` kwarg.

        Newer httpx versions removed the ``proxies`` parameter, but OpenAI <1.52
        still passes it. When users have unexpectedly upgraded httpx, we adapt the
        keyword instead of crashing the GUI. The shim is idempotent and only runs
        when required.
        """

        if getattr(httpx_module, "_litrx_proxy_shim_installed", False):
            return

        def _normalize_proxy(kwargs: Dict[str, Any]) -> None:
            if "proxies" not in kwargs:
                return
            proxies = kwargs.pop("proxies")
            if proxies is None:
                return
            if "proxy" in kwargs:
                return
            # httpx>=0.28 expects a single proxy value; choose a sensible default
            if isinstance(proxies, dict):
                if proxies:
                    kwargs["proxy"] = next(iter(proxies.values()))
            else:
                kwargs["proxy"] = proxies

        original_client_init = httpx_module.Client.__init__

        def patched_client_init(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
            _normalize_proxy(kwargs)
            return original_client_init(self, *args, **kwargs)

        httpx_module.Client.__init__ = patched_client_init  # type: ignore[assignment]

        if hasattr(httpx_module, "AsyncClient"):
            original_async_init = httpx_module.AsyncClient.__init__

            def patched_async_init(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
                _normalize_proxy(kwargs)
                return original_async_init(self, *args, **kwargs)

            httpx_module.AsyncClient.__init__ = patched_async_init  # type: ignore[assignment]

        httpx_module._litrx_proxy_shim_installed = True
