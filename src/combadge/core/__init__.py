"""Core modules for ComBadge application.

This package contains the fundamental components that power the ComBadge 
natural language processing application.
"""

from .application import ComBadgeApp
from .config_manager import AppConfig, ConfigManager
from .error_handler import (
    ComBadgeError,
    ConfigurationError,
    LLMError,
    APIError,
    DatabaseError,
    ErrorHandler,
    ErrorSeverity
)
from .logging_manager import LoggingManager

__all__ = [
    "ComBadgeApp",
    "AppConfig",
    "ConfigManager",
    "ComBadgeError",
    "ConfigurationError", 
    "LLMError",
    "APIError",
    "DatabaseError",
    "ErrorHandler",
    "ErrorSeverity",
    "LoggingManager"
]