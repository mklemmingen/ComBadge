"""Centralized Logging Management for ComBadge

Handles log configuration, formatting, and output management.
"""

import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        """Format log record with colors for console output."""
        log_message = super().format(record)
        return f"{self.COLORS.get(record.levelname, '')}{log_message}{self.COLORS['RESET']}"


class LoggingManager:
    """Centralized logging configuration and management."""
    
    _instance: Optional['LoggingManager'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'LoggingManager':
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize logging manager (only once)."""
        if self._initialized:
            return
            
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        self.loggers: Dict[str, logging.Logger] = {}
        self._setup_root_logger()
        self._initialized = True
        
    def _setup_root_logger(self):
        """Configure the root logger with handlers."""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Clearing existing handlers
        root_logger.handlers.clear()
        
        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler for all logs
        log_file = self.log_dir / f"combadge_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Error file handler for errors only
        error_file = self.log_dir / f"combadge_errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=10
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)
        
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger with the specified name.
        
        Args:
            name: Logger name (typically __name__ of the module)
            
        Returns:
            Configured logger instance
        """
        if name in self.loggers:
            return self.loggers[name]
            
        logger = logging.getLogger(name)
        self.loggers[name] = logger
        return logger
        
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Class method to get logger instance.
        
        Args:
            name: Logger name
            
        Returns:
            Configured logger
        """
        manager = cls()
        return manager._get_logger_instance(name)
        
    def _get_logger_instance(self, name: str) -> logging.Logger:
        """Internal method to get logger instance."""
        if name in self.loggers:
            return self.loggers[name]
            
        logger = logging.getLogger(name)
        self.loggers[name] = logger
        return logger
        
    def set_log_level(self, level: str):
        """Set the logging level for all handlers.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        numeric_level = getattr(logging, level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f'Invalid log level: {level}')
            
        # Updating console handler level
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                handler.setLevel(numeric_level)
                break
                
    def add_custom_handler(self, handler: logging.Handler, level: Optional[str] = None):
        """Add a custom handler to the root logger.
        
        Args:
            handler: The logging handler to add
            level: Optional log level for the handler
        """
        if level:
            numeric_level = getattr(logging, level.upper(), None)
            if isinstance(numeric_level, int):
                handler.setLevel(numeric_level)
                
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        
    def cleanup_old_logs(self, days: int = 30):
        """Clean up log files older than specified days.
        
        Args:
            days: Number of days to keep logs
        """
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        for log_file in self.log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_date:
                try:
                    log_file.unlink()
                    print(f"Removed old log file: {log_file}")
                except OSError as e:
                    print(f"Failed to remove log file {log_file}: {e}")
                    
    def get_log_stats(self) -> Dict[str, int]:
        """Get statistics about log files.
        
        Returns:
            Dictionary with log file statistics
        """
        stats = {
            'total_files': 0,
            'total_size_mb': 0,
            'error_files': 0,
            'debug_files': 0
        }
        
        for log_file in self.log_dir.glob("*.log*"):
            stats['total_files'] += 1
            stats['total_size_mb'] += log_file.stat().st_size / (1024 * 1024)
            
            if 'error' in log_file.name:
                stats['error_files'] += 1
            else:
                stats['debug_files'] += 1
                
        stats['total_size_mb'] = round(stats['total_size_mb'], 2)
        return stats