"""
Logging utilities for the multi-cloud CLI tool.
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
import structlog
from rich.console import Console
from rich.logging import RichHandler

from config import config

# Create console for rich output
console = Console()

def setup_logging():
    """Configure structured logging for the application."""
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if config.log_format == "json" else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Setup file handler
    import logging
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.log_level.upper()))
    
    # File handler for JSON logs
    file_handler = logging.FileHandler(
        logs_dir / f"multi_cloud_cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    file_handler.setLevel(logging.DEBUG)
    
    if config.log_format == "json":
        file_formatter = logging.Formatter('%(message)s')
    else:
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    file_handler.setFormatter(file_formatter)
    
    # Rich console handler for pretty terminal output
    console_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=True,
        rich_tracebacks=True
    )
    console_handler.setLevel(getattr(logging, config.log_level.upper()))
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return structlog.get_logger()

def log_operation_start(operation: str, **kwargs):
    """Log the start of an operation with context."""
    logger = structlog.get_logger()
    logger.info(
        "Operation started",
        operation=operation,
        **kwargs
    )

def log_operation_success(operation: str, duration: float = None, **kwargs):
    """Log successful completion of an operation."""
    logger = structlog.get_logger()
    log_data = {
        "operation": operation,
        "status": "success",
        **kwargs
    }
    if duration is not None:
        log_data["duration_seconds"] = duration
    
    logger.info("Operation completed successfully", **log_data)

def log_operation_error(operation: str, error: Exception, **kwargs):
    """Log operation failure with error details."""
    logger = structlog.get_logger()
    logger.error(
        "Operation failed",
        operation=operation,
        error=str(error),
        error_type=type(error).__name__,
        **kwargs
    )

def log_retry_attempt(operation: str, attempt: int, max_attempts: int, error: Exception = None):
    """Log retry attempts."""
    logger = structlog.get_logger()
    logger.warning(
        "Retry attempt",
        operation=operation,
        attempt=attempt,
        max_attempts=max_attempts,
        error=str(error) if error else None
    )
