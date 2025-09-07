"""ComBadge Application Core

Main application entry point and orchestration.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from .config_manager import ConfigManager
from .error_handler import ErrorHandler
from .logging_manager import LoggingManager
from ..ui.main_window import MainWindow


class ComBadgeApp:
    """Main application controller for ComBadge."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize ComBadge application.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.error_handler = ErrorHandler()
        self.config_manager = ConfigManager(config_path)
        self.logger = LoggingManager.get_logger(__name__)
        
        self.main_window = None
        self.is_running = False
        
    def run(self):
        """Main application entry point."""
        try:
            self.logger.info("Starting ComBadge application")
            self._initialize_components()
            self._start_main_loop()
        except Exception as e:
            self.error_handler.handle_critical_error(e)
            sys.exit(1)
    
    def _initialize_components(self):
        """Initialize all application components."""
        # Loading configuration
        self.config = self.config_manager.load_config()
        self.logger.info("Configuration loaded successfully")
        
        # Creating main window with professional UI
        self.main_window = MainWindow()
        self.main_window.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Setting up UI callbacks
        self._setup_ui_callbacks()
        
    def _setup_ui_callbacks(self):
        """Setup UI event callbacks."""
        self.main_window.set_callbacks(
            on_submit=self._handle_text_submission,
            on_clear=self._handle_clear_request,
            on_regenerate=self._handle_regenerate_request
        )
        
    def _handle_text_submission(self, text: str):
        """Handle text submission from UI.
        
        Args:
            text: Submitted text content
        """
        self.logger.info(f"Processing submitted text: {text[:50]}...")
        
        # Update UI to show processing
        self.main_window.update_status("Processing natural language input...", "processing")
        self.main_window.clear_reasoning()
        
        # Start reasoning steps
        self.main_window.add_reasoning_step(
            "Input Analysis", 
            f"Analyzing input text:\n\n{text}\n\nLength: {len(text)} characters\nType: {'Email' if '@' in text else 'Command'}"
        )
        
        # Simulate processing steps (placeholder for future LLM integration)
        self._simulate_processing_steps(text)
        
    def _simulate_processing_steps(self, text: str):
        """Simulate processing steps for demonstration.
        
        Args:
            text: Input text to process
        """
        import time
        import threading
        
        def processing_thread():
            try:
                # Step 1: Intent Recognition
                self.main_window.after_idle(
                    lambda: self.main_window.add_reasoning_step(
                        "Intent Recognition",
                        "Identifying intent from natural language input...\n\n"
                        "Detected patterns:\n"
                        "• Fleet management context\n"
                        "• Vehicle identification mentions\n"
                        "• Time-based references"
                    )
                )
                time.sleep(1.5)
                
                # Step 2: Entity Extraction
                self.main_window.after_idle(
                    lambda: self.main_window.add_reasoning_step(
                        "Entity Extraction",
                        "Extracting entities and parameters...\n\n"
                        "Identified entities:\n"
                        "• Vehicle IDs: [pending analysis]\n"
                        "• Dates/Times: [pending analysis]\n"
                        "• Actions: [pending analysis]"
                    )
                )
                time.sleep(1.0)
                
                # Step 3: API Mapping
                self.main_window.after_idle(
                    lambda: self.main_window.add_reasoning_step(
                        "API Mapping",
                        "Mapping to fleet management API endpoints...\n\n"
                        "Suggested API calls:\n"
                        "• GET /vehicles/{id}/status\n"
                        "• POST /reservations\n"
                        "• PUT /maintenance/schedule"
                    )
                )
                time.sleep(1.0)
                
                # Complete processing
                self.main_window.after_idle(
                    lambda: self.main_window.update_status("Processing completed", "success")
                )
                
            except Exception as e:
                self.logger.error(f"Error in processing simulation: {e}")
                self.main_window.after_idle(
                    lambda: self.main_window.update_status("Processing failed", "error")
                )
                
        # Start processing in background thread
        thread = threading.Thread(target=processing_thread, daemon=True)
        thread.start()
        
    def _handle_clear_request(self):
        """Handle clear request from UI."""
        self.logger.info("Clearing UI content")
        
    def _handle_regenerate_request(self):
        """Handle regenerate request from UI."""
        self.logger.info("Regenerating last result")
        
        # Get current input and reprocess
        current_text = self.main_window.get_input_text()
        if current_text.strip():
            self._handle_text_submission(current_text)
        
    def _start_main_loop(self):
        """Start the main application event loop."""
        self.is_running = True
        self.logger.info("Starting main event loop")
        self.main_window.mainloop()
        
    def _on_closing(self):
        """Handle application closing."""
        self.logger.info("Shutting down ComBadge application")
        self.is_running = False
        
        # Cleanup resources
        self._cleanup()
        
        if self.main_window:
            self.main_window.destroy()
            
    def _cleanup(self):
        """Clean up application resources."""
        # Clean up event handlers
        if self.main_window and hasattr(self.main_window, 'event_handler'):
            self.main_window.event_handler.cleanup()