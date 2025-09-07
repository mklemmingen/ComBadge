"""Global Error Handling for ComBadge

Centralized error handling, logging, and user notification system.
"""

import logging
import sys
import traceback
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type

import customtkinter as ctk


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComBadgeError(Exception):
    """Base exception class for ComBadge application."""
    
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        self.message = message
        self.severity = severity
        super().__init__(self.message)


class ConfigurationError(ComBadgeError):
    """Error raised when configuration is invalid."""
    pass


class LLMError(ComBadgeError):
    """Error raised when LLM processing fails."""
    pass


class APIError(ComBadgeError):
    """Error raised when API operations fail."""
    pass


class DatabaseError(ComBadgeError):
    """Error raised when database operations fail."""
    pass


class ErrorHandler:
    """Global error handler for the application."""
    
    def __init__(self):
        """Initialize error handler."""
        self.logger = logging.getLogger(__name__)
        self.error_callbacks: Dict[Type[Exception], Callable] = {}
        self.setup_exception_handlers()
        
    def setup_exception_handlers(self):
        """Set up global exception handlers."""
        sys.excepthook = self._handle_unhandled_exception
        
    def register_error_callback(self, exception_type: Type[Exception], 
                              callback: Callable[[Exception], None]):
        """Register a callback for specific exception types.
        
        Args:
            exception_type: The exception type to handle
            callback: Function to call when this exception occurs
        """
        self.error_callbacks[exception_type] = callback
        
    def handle_error(self, error: Exception, context: Optional[str] = None) -> bool:
        """Handle an error with appropriate logging and user notification.
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            
        Returns:
            True if error was handled successfully, False otherwise
        """
        try:
            severity = self._get_error_severity(error)
            error_message = self._format_error_message(error, context)
            
            # Logging the error
            self._log_error(error, error_message, severity)
            
            # Notifying user if appropriate
            if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                self._show_user_error_dialog(error, error_message, severity)
                
            # Calling registered callbacks
            error_type = type(error)
            if error_type in self.error_callbacks:
                self.error_callbacks[error_type](error)
                
            return True
            
        except Exception as handler_error:
            # If error handler itself fails, log to stderr
            print(f"Error handler failed: {handler_error}", file=sys.stderr)
            return False
            
    def handle_critical_error(self, error: Exception, context: Optional[str] = None):
        """Handle critical errors that require application shutdown.
        
        Args:
            error: The critical exception
            context: Additional context about the error
        """
        error_message = f"Critical error occurred: {error}"
        if context:
            error_message = f"{context}: {error_message}"
            
        self.logger.critical(error_message, exc_info=True)
        
        # Showing critical error dialog
        self._show_critical_error_dialog(error, error_message)
        
    def _get_error_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity based on exception type.
        
        Args:
            error: The exception to analyze
            
        Returns:
            Appropriate severity level
        """
        if isinstance(error, ComBadgeError):
            return error.severity
            
        # Mapping standard exceptions to severity levels
        severity_map = {
            FileNotFoundError: ErrorSeverity.MEDIUM,
            PermissionError: ErrorSeverity.HIGH,
            ConnectionError: ErrorSeverity.HIGH,
            TimeoutError: ErrorSeverity.MEDIUM,
            MemoryError: ErrorSeverity.CRITICAL,
            KeyboardInterrupt: ErrorSeverity.LOW,
            SystemExit: ErrorSeverity.LOW,
        }
        
        return severity_map.get(type(error), ErrorSeverity.MEDIUM)
        
    def _format_error_message(self, error: Exception, context: Optional[str] = None) -> str:
        """Format error message for logging and display.
        
        Args:
            error: The exception
            context: Additional context
            
        Returns:
            Formatted error message
        """
        message = str(error)
        if context:
            message = f"{context}: {message}"
            
        return message
        
    def _log_error(self, error: Exception, message: str, severity: ErrorSeverity):
        """Log error with appropriate level.
        
        Args:
            error: The exception
            message: Formatted error message
            severity: Error severity
        """
        log_methods = {
            ErrorSeverity.LOW: self.logger.info,
            ErrorSeverity.MEDIUM: self.logger.warning,
            ErrorSeverity.HIGH: self.logger.error,
            ErrorSeverity.CRITICAL: self.logger.critical,
        }
        
        log_method = log_methods[severity]
        log_method(message, exc_info=True)
        
    def _show_user_error_dialog(self, error: Exception, message: str, 
                               severity: ErrorSeverity):
        """Show error dialog to user.
        
        Args:
            error: The exception
            message: Error message
            severity: Error severity
        """
        try:
            # Creating dialog based on severity
            if severity == ErrorSeverity.CRITICAL:
                title = "Critical Error"
                icon = "error"
            else:
                title = "Error"
                icon = "warning"
                
            # Using tkinter messagebox for error display
            import tkinter.messagebox as msgbox
            msgbox.showerror(title, message)
            
        except Exception:
            # If GUI dialog fails, print to stderr
            print(f"Error dialog failed. Original error: {message}", file=sys.stderr)
            
    def _show_critical_error_dialog(self, error: Exception, message: str):
        """Show critical error dialog before shutdown.
        
        Args:
            error: The critical exception
            message: Error message
        """
        try:
            import tkinter.messagebox as msgbox
            msgbox.showerror(
                "Critical Error - Application Will Close",
                f"{message}\n\nThe application will now close."
            )
        except Exception:
            print(f"Critical error dialog failed. Error: {message}", file=sys.stderr)
            
    def _handle_unhandled_exception(self, exc_type, exc_value, exc_traceback):
        """Handle unhandled exceptions.
        
        Args:
            exc_type: Exception type
            exc_value: Exception instance
            exc_traceback: Exception traceback
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow keyboard interrupts to exit normally
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        error_message = ''.join(traceback.format_exception(
            exc_type, exc_value, exc_traceback
        ))
        
        self.logger.critical(f"Unhandled exception: {error_message}")
        
        # Showing critical error dialog for unhandled exceptions
        self._show_critical_error_dialog(
            exc_value, 
            f"An unexpected error occurred: {exc_value}"
        )