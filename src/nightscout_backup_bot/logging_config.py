"""Logging configuration for NightScout Backup Bot."""

import logging
import sys
from typing import Any

from .config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    log_level = logging.DEBUG if not settings.is_production else logging.INFO

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("disnake").setLevel(logging.WARNING)
    logging.getLogger("disnake.http").setLevel(logging.WARNING)
    logging.getLogger("disnake.gateway").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)

    # Application loggers
    logging.getLogger("nightscout_backup_bot").setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module."""
    return logging.getLogger(f"nightscout_backup_bot.{name}")


class StructuredLogger:
    """Structured logger wrapper for consistent logging with context."""

    def __init__(self, name: str) -> None:
        """Initialize structured logger."""
        self.logger = get_logger(name)

    def _format_message(self, message: str, **context: Any) -> str:
        """Format message with context."""
        if not context:
            return message
        context_str = " | ".join(f"{k}={v}" for k, v in context.items())
        return f"{message} | {context_str}"

    def debug(self, message: str, **context: Any) -> None:
        """Log debug message with context."""
        self.logger.debug(self._format_message(message, **context))

    def info(self, message: str, **context: Any) -> None:
        """Log info message with context."""
        self.logger.info(self._format_message(message, **context))

    def warning(self, message: str, **context: Any) -> None:
        """Log warning message with context."""
        self.logger.warning(self._format_message(message, **context))

    def error(self, message: str, **context: Any) -> None:
        """Log error message with context."""
        self.logger.error(self._format_message(message, **context))

    def critical(self, message: str, **context: Any) -> None:
        """Log critical message with context."""
        self.logger.critical(self._format_message(message, **context))

    def exception(self, message: str, **context: Any) -> None:
        """Log exception with context."""
        self.logger.exception(self._format_message(message, **context))
