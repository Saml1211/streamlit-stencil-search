"""
Logging utilities for the Visio Stencil Explorer application.
Provides consistent logging configuration across the application.
"""

import logging
import os
import sys
from datetime import datetime

# Define log levels
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

# Default format for log messages
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Create logs directory if it doesn't exist
def ensure_log_directory(log_dir="logs"):
    """Ensure the log directory exists"""
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except Exception as e:
            print(f"Error creating log directory: {e}")
            return False
    return True

def setup_logger(name, level="info", log_to_file=True, log_dir="logs", 
                 log_format=DEFAULT_LOG_FORMAT, console_output=True):
    """
    Set up a logger with the specified configuration
    
    Args:
        name (str): Name of the logger
        level (str): Log level (debug, info, warning, error, critical)
        log_to_file (bool): Whether to log to a file
        log_dir (str): Directory to store log files
        log_format (str): Format for log messages
        console_output (bool): Whether to output logs to console
        
    Returns:
        logging.Logger: Configured logger
    """
    # Get the log level
    log_level = LOG_LEVELS.get(level.lower(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Add console handler if requested
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add file handler if requested
    if log_to_file and ensure_log_directory(log_dir):
        # Create a unique log file name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"{name}_{timestamp}.log")
        
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"Failed to create log file handler: {e}")
    
    return logger

class MemoryStreamHandler(logging.Handler):
    """
    Logging handler that retains the last N log records in memory for diagnostics/UI.
    Thread-safe, FIFO buffer.
    """
    def __init__(self, capacity=100, fmt=DEFAULT_LOG_FORMAT):
        super().__init__()
        self.capacity = capacity
        self.buffer = []
        self.formatter = logging.Formatter(fmt)
        self.lock = logging.Lock()

    def emit(self, record):
        with self.lock:
            msg = self.format(record)
            self.buffer.append(msg)
            if len(self.buffer) > self.capacity:
                self.buffer = self.buffer[-self.capacity:]

    def get_latest_logs(self):
        with self.lock:
            return list(self.buffer)

    def clear(self):
        with self.lock:
            self.buffer.clear()

    def set_capacity(self, capacity):
        with self.lock:
            self.capacity = capacity
            if len(self.buffer) > self.capacity:
                self.buffer = self.buffer[-self.capacity:]
def get_logger(name, level=None):
    """
    Get a logger with the specified name
    
    Args:
        name (str): Name of the logger
        level (str, optional): Override the default log level
        
    Returns:
        logging.Logger: Logger instance
    """
    logger = logging.getLogger(name)
    
    # Set level if provided
    if level and level.lower() in LOG_LEVELS:
        logger.setLevel(LOG_LEVELS[level.lower()])
        
    return logger
