"""
Utility functions for retry logic and resilience.
"""
import time
import functools
from typing import Callable, Any, Type, Tuple
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import structlog

from config import config
from logger import log_retry_attempt

logger = structlog.get_logger()

# Common exceptions that should trigger retries
RETRIABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    # Add cloud-specific exceptions here as needed
)

def with_retry(
    max_attempts: int = None,
    delay: float = None,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = RETRIABLE_EXCEPTIONS
):
    """
    Decorator to add retry logic to functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Exponential backoff factor
        exceptions: Tuple of exception types to retry on
    """
    max_attempts = max_attempts or config.max_retries
    delay = delay or config.retry_delay
    
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=delay, max=60),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, "WARNING")
        )
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

def retry_operation(
    operation: Callable,
    operation_name: str = "operation",
    max_attempts: int = None,
    delay: float = None,
    *args,
    **kwargs
) -> Any:
    """
    Retry an operation with exponential backoff.
    
    Args:
        operation: Function to retry
        operation_name: Name for logging purposes
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries
        *args, **kwargs: Arguments to pass to the operation
    
    Returns:
        Result of the operation
        
    Raises:
        The last exception if all retries fail
    """
    max_attempts = max_attempts or config.max_retries
    delay = delay or config.retry_delay
    
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            result = operation(*args, **kwargs)
            if attempt > 1:
                logger.info(
                    "Operation succeeded after retries",
                    operation=operation_name,
                    attempt=attempt
                )
            return result
            
        except Exception as e:
            last_exception = e
            log_retry_attempt(operation_name, attempt, max_attempts, e)
            
            if attempt == max_attempts:
                logger.error(
                    "Operation failed after all retries",
                    operation=operation_name,
                    attempts=max_attempts,
                    final_error=str(e)
                )
                raise
            
            # Exponential backoff
            sleep_time = delay * (2 ** (attempt - 1))
            time.sleep(min(sleep_time, 60))  # Cap at 60 seconds
    
    # This should never be reached, but just in case
    raise last_exception

class CircuitBreaker:
    """
    Circuit breaker pattern implementation for resilience.
    """
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.
        """
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise ConnectionError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(
                    "Circuit breaker opened",
                    failure_count=self.failure_count,
                    threshold=self.failure_threshold
                )
            
            raise e

def validate_file_path(file_path: str) -> bool:
    """
    Validate that a file path is safe and accessible.
    """
    import os
    from pathlib import Path
    
    try:
        path = Path(file_path)
        # Check if path exists and is a file
        if not path.exists():
            return False
        if not path.is_file():
            return False
        # Check if file is readable
        if not os.access(path, os.R_OK):
            return False
        return True
    except (OSError, ValueError):
        return False

def format_bytes(bytes_count: int) -> str:
    """
    Format bytes into human readable format.
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"

def calculate_transfer_speed(bytes_transferred: int, duration_seconds: float) -> str:
    """
    Calculate and format transfer speed.
    """
    if duration_seconds <= 0:
        return "N/A"
    
    speed_bps = bytes_transferred / duration_seconds
    return f"{format_bytes(int(speed_bps))}/s"
