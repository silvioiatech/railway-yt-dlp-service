"""
Structured logging utility for the application.

Provides consistent logging configuration and helper functions.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Color codes for terminal output
class LogColors:
    """ANSI color codes for log levels."""
    RESET = "\033[0m"
    DEBUG = "\033[36m"  # Cyan
    INFO = "\033[32m"   # Green
    WARNING = "\033[33m"  # Yellow
    ERROR = "\033[31m"  # Red
    CRITICAL = "\033[35m"  # Magenta


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for terminal output."""

    FORMATS = {
        logging.DEBUG: f"{LogColors.DEBUG}%(levelname)s{LogColors.RESET} - %(name)s - %(message)s [%(filename)s:%(lineno)d]",
        logging.INFO: f"{LogColors.INFO}%(levelname)s{LogColors.RESET} - %(name)s - %(message)s",
        logging.WARNING: f"{LogColors.WARNING}%(levelname)s{LogColors.RESET} - %(name)s - %(message)s [%(filename)s:%(lineno)d]",
        logging.ERROR: f"{LogColors.ERROR}%(levelname)s{LogColors.RESET} - %(name)s - %(message)s [%(filename)s:%(lineno)d]",
        logging.CRITICAL: f"{LogColors.CRITICAL}%(levelname)s{LogColors.RESET} - %(name)s - %(message)s [%(filename)s:%(lineno)d]",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with color."""
        log_fmt = self.FORMATS.get(record.levelno, "%(levelname)s - %(message)s")
        formatter = logging.Formatter(
            fmt=f"%(asctime)s - {log_fmt}",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        return formatter.format(record)


def configure_logging(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    use_colors: bool = True
) -> None:
    """
    Configure application-wide logging.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (None for stdout only)
        use_colors: Use colored output for terminal logs
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if use_colors and sys.stdout.isatty():
        console_handler.setFormatter(ColoredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s - %(levelname)s - %(name)s - %(message)s [%(filename)s:%(lineno)d]",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )

    root_logger.addHandler(console_handler)

    # File handler if log directory specified
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s - %(levelname)s - %(name)s - %(message)s [%(filename)s:%(lineno)d]",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        root_logger.addHandler(file_handler)

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
