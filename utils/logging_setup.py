"""
Logging Setup for AutoScraper
Configures file and console logging with rotation
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from config import LOGGING


# Live log buffer for UI
LOG_BUFFER = []
LOG_BUFFER_MAX = 100


class BufferHandler(logging.Handler):
    """Custom handler to store logs in memory for live viewing"""
    
    def emit(self, record):
        log_entry = {
            'timestamp': record.created,
            'level': record.levelname,
            'message': self.format(record)
        }
        LOG_BUFFER.append(log_entry)
        
        # Keep buffer limited
        while len(LOG_BUFFER) > LOG_BUFFER_MAX:
            LOG_BUFFER.pop(0)


def setup_logging():
    """
    Setup file and console logging based on config.
    
    Creates:
    - Rotating file handler (logs/autoscraper.log)
    - Console handler (stdout)
    - Buffer handler (for UI live view)
    """
    if not LOGGING.get('enabled', True):
        return
    
    # Create logs directory
    log_file = LOGGING.get('file', 'logs/autoscraper.log')
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Setup rotating file handler
    log_level = getattr(logging, LOGGING.get('level', 'INFO').upper(), logging.INFO)
    max_bytes = LOGGING.get('max_size_mb', 10) * 1024 * 1024
    backup_count = LOGGING.get('backup_count', 5)
    
    # File handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    
    # Buffer handler for UI
    buffer_handler = BufferHandler()
    buffer_handler.setFormatter(logging.Formatter('%(message)s'))
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(buffer_handler)
    
    logging.info("🚀 AutoScraper started - Logging initialized")


def get_recent_logs(count=50):
    """
    Get recent log entries for UI display.
    
    Args:
        count: Number of recent logs to return
        
    Returns:
        list: Recent log entries
    """
    return LOG_BUFFER[-count:]


def clear_log_buffer():
    """Clear the log buffer."""
    global LOG_BUFFER
    LOG_BUFFER = []
