"""
Logging configuration for LitRx Toolkit.
Provides centralized logging setup with file and console handlers.
"""
import logging
import sys
import traceback
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

# Lazy import to avoid circular dependency
_SecureLogger = None


def _get_secure_logger():
    """Lazy import of SecureLogger to avoid circular dependency."""
    global _SecureLogger
    if _SecureLogger is None:
        from .security_utils import SecureLogger
        _SecureLogger = SecureLogger
    return _SecureLogger


def _secure_exception_hook(exc_type, exc_value, exc_traceback):
    """Global exception handler that sanitizes sensitive information before logging.

    This hook is installed by setup_logging() to catch uncaught exceptions
    and ensure API keys or other sensitive data don't leak into logs.

    Args:
        exc_type: Exception type
        exc_value: Exception instance
        exc_traceback: Traceback object
    """
    # Don't log KeyboardInterrupt (user cancelled)
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Get logger and SecureLogger
    logger = logging.getLogger("litrx")
    SecureLogger = _get_secure_logger()

    # Sanitize exception message and traceback to avoid leaking secrets
    safe_message = SecureLogger.sanitize_error(exc_value)
    formatted_tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    safe_traceback = SecureLogger.sanitize_string(formatted_tb)

    logger.critical(
        "Uncaught exception: %s: %s\n%s",
        exc_type.__name__,
        safe_message,
        safe_traceback,
    )

    # Call the default exception hook to ensure normal error handling
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    console_output: bool = True
) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (defaults to ~/.litrx/logs)
        console_output: Whether to output logs to console

    Returns:
        Configured logger instance
    """
    # Allow environment to override log level
    import os as _os
    env_level = _os.getenv("LITRX_LOG_LEVEL")
    if env_level:
        log_level = env_level

    # Create log directory
    if log_dir is None:
        log_dir = Path.home() / ".litrx" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger("litrx")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # File handler with rotation (max 10MB, keep 5 backup files)
    log_file = log_dir / "litrx.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler (optional)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # Install global exception hook for security
    sys.excepthook = _secure_exception_hook

    logger.info(f"Logging configured. Log file: {log_file}")
    logger.debug("Global exception hook installed for sensitive data protection")
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Module name (e.g., __name__)

    Returns:
        Logger instance
    """
    # Ensure parent logger is configured
    parent_logger = logging.getLogger("litrx")
    if not parent_logger.handlers:
        setup_logging()

    return logging.getLogger(f"litrx.{name}")


# Initialize logging on module import
_default_logger = None


def get_default_logger() -> logging.Logger:
    """Get or create the default logger instance."""
    global _default_logger
    if _default_logger is None:
        _default_logger = setup_logging()
    return _default_logger
