"""ComBadge Application Core

Main application entry point and orchestration.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

# Fix CustomTkinter scaling tracker bug with Python 3.13
import customtkinter as ctk
# Temporarily disable scaling tracker patch to focus on reasoning display issue

from .config_manager import ConfigManager
from .error_handler import ErrorHandler
from .logging_manager import LoggingManager
from ..ui.main_window import MainWindow
from ..ui.setup_wizard import check_and_run_setup
from ..intelligence.llm_manager import OllamaServerManager
from ..intelligence.reasoning_engine import ChainOfThoughtEngine


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
        self.ollama_manager = None
        self.reasoning_engine = None
        self.setup_complete = False
        
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
        
        # Create main window
        self.main_window = MainWindow()
        self.main_window.withdraw()  # Hide until setup is complete
        
        # Wait for window to fully initialize
        self.main_window.update_idletasks()
        
        # Temporarily bypass setup wizard due to threading issues
        self.logger.info("Bypassing setup wizard (temporary fix for threading issues)")
        
        # Proceed directly to initialize components  
        self.setup_complete = True
        self._initialize_ollama()
        
        # Ensure reasoning display is available before showing window
        if self.main_window.reasoning_display:
            self.logger.info("Reasoning display successfully initialized")
        else:
            self.logger.error("Reasoning display failed to initialize")
            
        self.main_window.deiconify()  # Show main window
        
        # Set window protocol after showing
        self.main_window.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Setting up UI callbacks
        self._setup_ui_callbacks()
        
    def _initialize_ollama(self):
        """Initialize Ollama server manager."""
        try:
            self.logger.info("Initializing Ollama server manager...")
            self.ollama_manager = OllamaServerManager(
                model_name=self.config.llm.model
            )
            
            # Set up download progress callback
            self.ollama_manager.on_download_progress = self._on_model_download_progress
            
            # Initialize reasoning engine
            self.logger.info("Initializing reasoning engine...")
            self.reasoning_engine = ChainOfThoughtEngine(
                ollama_manager=self.ollama_manager
            )
            
            # Start server if not already running
            if not self.ollama_manager.is_server_running():
                self.logger.info("Starting Ollama server...")
                if self.ollama_manager.start_server():
                    self.logger.info("Ollama server started successfully")
                else:
                    self.logger.error("Failed to start Ollama server")
                    
        except Exception as e:
            self.logger.error(f"Failed to initialize Ollama: {e}")
            self.error_handler.handle_error(e, "Ollama initialization failed")
        
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
        
        # Process with Ollama LLM integration
        self._simulate_processing_steps(text)
        
    def _simulate_processing_steps(self, text: str):
        """Process user input with actual Ollama Chain of Thought reasoning.
        
        Args:
            text: Input text to process
        """
        import threading
        
        def processing_thread():
            try:
                if not self.reasoning_engine:
                    self.logger.error("Reasoning engine not initialized")
                    self.main_window.after_idle(
                        lambda: self.main_window.update_status("Reasoning engine not available", "error")
                    )
                    return
                
                self.logger.info(f"Starting Ollama processing for input: {text[:50]}...")
                
                # Update status to show model preparation
                self.main_window.after_idle(
                    lambda: self.main_window.update_status("Preparing AI model...", "processing")
                )
                
                # Start reasoning engine if not already started
                if not self.reasoning_engine.start_engine():
                    self.logger.error("Failed to start reasoning engine")
                    self.main_window.after_idle(
                        lambda: self.main_window.update_status("Failed to start reasoning engine", "error")
                    )
                    return
                
                # Update status to show we're connecting to Ollama
                self.main_window.after_idle(
                    lambda: self.main_window.update_status("Checking AI model availability...", "processing")
                )
                
                # Start reasoning session in UI
                self.logger.info("Starting reasoning display session...")
                
                # Process with reasoning engine
                self.logger.info("Sending request to Ollama...")
                request_id = self.reasoning_engine.process_request(
                    user_input=text,
                    context={"source": "ui_input"},
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens,
                    stream=True
                )
                
                # Start reasoning session in UI
                def start_reasoning_safe():
                    if self.main_window and self.main_window.reasoning_display:
                        self.main_window.reasoning_display.start_reasoning(request_id)
                    else:
                        self.logger.error("Reasoning display not available")
                        
                self.main_window.after_idle(start_reasoning_safe)
                
                self.logger.info(f"Ollama processing request {request_id}")
                
                # Update status to show we're processing with Ollama
                self.main_window.after_idle(
                    lambda: self.main_window.update_status("Processing with Ollama LLM...", "processing")
                )
                
                # Set up callback to receive streaming results
                if hasattr(self.reasoning_engine, 'stream_processor'):
                    # Connect stream processor to reasoning display
                    original_on_chunk = getattr(self.reasoning_engine.stream_processor, 'on_chunk_received', None)
                    def chunk_handler(chunk_content):
                        # Forward chunks to reasoning display
                        def add_chunk_safe():
                            if self.main_window and self.main_window.reasoning_display:
                                self.main_window.reasoning_display.add_content_chunk(chunk_content)
                                
                        self.main_window.after_idle(add_chunk_safe)
                        # Call original handler if it exists
                        if original_on_chunk:
                            original_on_chunk(chunk_content)
                    
                    self.reasoning_engine.stream_processor.on_chunk_received = chunk_handler
                    
                    # Set up completion callback
                    original_on_complete = getattr(self.reasoning_engine.stream_processor, 'on_processing_complete', None)
                    def completion_handler(result):
                        # Mark reasoning as complete in UI
                        def complete_reasoning_safe():
                            if self.main_window and self.main_window.reasoning_display:
                                self.main_window.reasoning_display.complete_reasoning()
                                
                        def update_status_safe():
                            if self.main_window:
                                self.main_window.update_status("Processing completed - Check results", "success")
                                
                        self.main_window.after_idle(complete_reasoning_safe)
                        self.main_window.after_idle(update_status_safe)
                        # Call original handler if it exists
                        if original_on_complete:
                            original_on_complete(result)
                    
                    self.reasoning_engine.stream_processor.on_processing_complete = completion_handler
                
            except Exception as e:
                self.logger.error(f"Error processing input with Ollama: {e}")
                self.main_window.after_idle(
                    lambda: self.main_window.update_status(f"Ollama processing failed: {str(e)}", "error")
                )
                
        # Start processing in background thread
        thread = threading.Thread(target=processing_thread, daemon=True)
        thread.start()
    
    def _on_model_download_progress(self, progress):
        """Handle model download progress updates.
        
        Args:
            progress: DownloadProgress object with download status
        """
        # Update UI on main thread
        def update_ui():
            if hasattr(self.main_window, 'update_status'):
                if progress.status == "success":
                    status_msg = "AI model ready! Processing..."
                    self.main_window.update_status(status_msg, "processing")
                elif progress.total > 0:
                    mb_completed = progress.completed / (1024 * 1024)
                    mb_total = progress.total / (1024 * 1024)
                    status_msg = f"Downloading AI model: {mb_completed:.0f}/{mb_total:.0f} MB ({progress.percent:.1f}%)"
                    self.main_window.update_status(status_msg, "processing")
                else:
                    status_msg = f"Downloading AI model... {progress.status}"
                    self.main_window.update_status(status_msg, "processing")
                
        self.main_window.after_idle(update_ui)
        
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