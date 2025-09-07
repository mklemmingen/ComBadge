"""ComBadge First-Run Setup Wizard

Interactive setup wizard for automatic Ollama installation and model download
with progress tracking and user-friendly interface.
"""

import customtkinter as ctk
from tkinter import messagebox
import threading
import time
from pathlib import Path
from typing import Optional, Callable
import json

from ..intelligence.ollama_installer import OllamaInstaller
from ..intelligence.llm_manager import OllamaServerManager
from ..core.logging_manager import LoggingManager
from .styles.themes import Theme


class SetupWizard(ctk.CTkToplevel):
    """First-run setup wizard for ComBadge."""
    
    def __init__(self, parent=None, on_complete_callback: Optional[Callable] = None):
        """Initialize setup wizard.
        
        Args:
            parent: Parent window
            on_complete_callback: Callback when setup is complete
        """
        super().__init__(parent)
        
        self.logger = LoggingManager.get_logger(__name__)
        self.on_complete_callback = on_complete_callback
        self.setup_complete = False
        self.cancel_requested = False
        
        # Initialize components
        self.installer = OllamaInstaller(progress_callback=self.update_progress)
        self.server_manager = OllamaServerManager()
        
        # Setup state tracking
        self.state_file = Path.home() / ".combadge" / "setup_state.json"
        self.state_file.parent.mkdir(exist_ok=True)
        self.load_state()
        
        # Configure window
        self.title("ComBadge Setup")
        self.geometry("600x500")
        self.resizable(False, False)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Center window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # Create UI
        self.create_widgets()
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Start setup process
        self.after(100, self.check_and_start_setup)
    
    def create_widgets(self):
        """Create wizard UI components."""
        # Header
        header_frame = ctk.CTkFrame(self, height=100)
        header_frame.pack(fill="x", padx=20, pady=(20, 0))
        header_frame.pack_propagate(False)
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="Welcome to ComBadge",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(20, 5))
        
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Setting up AI components for first use",
            font=ctk.CTkFont(size=14)
        )
        subtitle_label.pack()
        
        # Progress frame
        self.progress_frame = ctk.CTkFrame(self)
        self.progress_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Status sections
        self.create_status_section("Ollama Installation", 0)
        self.create_status_section("Service Configuration", 1)
        self.create_status_section("AI Model Download", 2)
        
        # Overall progress
        overall_frame = ctk.CTkFrame(self.progress_frame)
        overall_frame.pack(fill="x", pady=(20, 10))
        
        self.overall_label = ctk.CTkLabel(
            overall_frame,
            text="Preparing setup...",
            font=ctk.CTkFont(size=14)
        )
        self.overall_label.pack(pady=(10, 5))
        
        self.overall_progress = ctk.CTkProgressBar(overall_frame, width=400)
        self.overall_progress.pack(pady=(0, 10))
        self.overall_progress.set(0)
        
        # Action buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.cancel_setup,
            width=100
        )
        self.cancel_button.pack(side="left")
        
        self.continue_button = ctk.CTkButton(
            button_frame,
            text="Continue",
            command=self.continue_setup,
            width=100,
            state="disabled"
        )
        self.continue_button.pack(side="right")
        
        # Info text
        self.info_label = ctk.CTkLabel(
            self,
            text="This one-time setup will download ~8GB of AI model data",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.info_label.pack(pady=(0, 20))
    
    def create_status_section(self, title: str, index: int):
        """Create a status section with icon, title, and progress."""
        section_frame = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        section_frame.pack(fill="x", pady=10)
        
        # Status indicator
        status_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        status_frame.pack(fill="x")
        
        # Status icon (circle that changes color)
        status_icon = ctk.CTkLabel(
            status_frame,
            text="○",
            font=ctk.CTkFont(size=20),
            width=30
        )
        status_icon.pack(side="left", padx=(0, 10))
        
        # Title
        title_label = ctk.CTkLabel(
            status_frame,
            text=title,
            font=ctk.CTkFont(size=16)
        )
        title_label.pack(side="left")
        
        # Status text
        status_text = ctk.CTkLabel(
            status_frame,
            text="Pending",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        status_text.pack(side="right", padx=(10, 0))
        
        # Progress bar (hidden initially)
        progress_bar = ctk.CTkProgressBar(section_frame, width=400, height=10)
        progress_bar.pack(pady=(5, 0))
        progress_bar.pack_forget()  # Hide initially
        
        # Store references
        if index == 0:
            self.ollama_status = (status_icon, title_label, status_text, progress_bar)
        elif index == 1:
            self.service_status = (status_icon, title_label, status_text, progress_bar)
        elif index == 2:
            self.model_status = (status_icon, title_label, status_text, progress_bar)
    
    def update_section_status(self, section_tuple, status: str, progress: Optional[float] = None):
        """Update a section's status display."""
        # Schedule GUI update on main thread
        self.after(0, self._update_section_status_impl, section_tuple, status, progress)
    
    def _update_section_status_impl(self, section_tuple, status: str, progress: Optional[float] = None):
        """Internal implementation of status update - runs on main thread."""
        try:
            icon, title, status_text, progress_bar = section_tuple
            
            # Update status text
            status_text.configure(text=status)
            
            # Update icon based on status
            if "complete" in status.lower():
                icon.configure(text="✓", text_color="green")
            elif "error" in status.lower() or "failed" in status.lower():
                icon.configure(text="✗", text_color="red")
            elif "progress" in status.lower() or "downloading" in status.lower():
                icon.configure(text="◐", text_color="orange")
        except Exception as e:
            self.logger.error(f"Error updating section status: {e}")
        
        # Handle progress bar
        if progress is not None:
            progress_bar.pack(pady=(5, 0))
            progress_bar.set(progress / 100)
        elif "complete" in status.lower():
            progress_bar.pack_forget()
    
    def check_and_start_setup(self):
        """Check what needs to be set up and start the process."""
        # Check current state
        checks = {
            "ollama_installed": self.installer.is_ollama_installed(),
            "service_running": self.server_manager.is_server_running(),
            "model_available": False
        }
        
        # Check for model if service is running
        if checks["service_running"]:
            try:
                models = self.server_manager.get_available_models()
                checks["model_available"] = any("qwen2.5" in m.name for m in models)
            except:
                pass
        
        # Update UI based on checks
        if checks["ollama_installed"]:
            self.update_section_status(self.ollama_status, "Already installed", 100)
            
        if checks["service_running"]:
            self.update_section_status(self.service_status, "Already running", 100)
            
        if checks["model_available"]:
            self.update_section_status(self.model_status, "Already available", 100)
        
        # Determine if setup is needed
        if all(checks.values()):
            self.setup_complete = True
            self.overall_label.configure(text="Setup already complete!")
            self.overall_progress.set(1.0)
            self.continue_button.configure(state="normal", text="Start ComBadge")
            self.cancel_button.configure(text="Close")
        else:
            # Calculate what needs to be done
            steps_needed = []
            if not checks["ollama_installed"]:
                steps_needed.append("install")
            if not checks["service_running"]:
                steps_needed.append("service")
            if not checks["model_available"]:
                steps_needed.append("model")
            
            # Estimate size/time
            total_size = 0
            if "install" in steps_needed:
                total_size += 150  # MB for Ollama
            if "model" in steps_needed:
                total_size += 8000  # MB for model
                
            time_estimate = total_size / 10  # Assume 10MB/s
            
            self.info_label.configure(
                text=f"Setup will download ~{total_size/1000:.1f}GB "
                f"(estimated {int(time_estimate/60)} minutes at 10MB/s)"
            )
            
            # Auto-start setup after a brief delay
            self.after(2000, lambda: self.start_setup_thread(steps_needed))
    
    def start_setup_thread(self, steps_needed: list):
        """Start setup in background thread."""
        self.cancel_button.configure(state="normal")
        
        def run_setup():
            try:
                total_steps = len(steps_needed)
                current_step = 0
                
                # Install Ollama if needed
                if "install" in steps_needed:
                    self.update_section_status(self.ollama_status, "Downloading installer...")
                    success, msg = self.installer.download_ollama()
                    
                    if not success:
                        self.show_error(f"Download failed: {msg}")
                        return
                        
                    self.update_section_status(self.ollama_status, "Installing...")
                    success, msg = self.installer.install_ollama(msg)
                    
                    if not success:
                        self.show_error(f"Installation failed: {msg}")
                        return
                        
                    self.update_section_status(self.ollama_status, "Installation complete", 100)
                    current_step += 1
                    self.update_overall_progress(current_step / total_steps)
                
                # Start service if needed
                if "service" in steps_needed:
                    self.update_section_status(self.service_status, "Starting service...")
                    success, msg = self.installer.setup_ollama_service()
                    
                    if not success:
                        self.show_error(f"Service start failed: {msg}")
                        return
                        
                    self.update_section_status(self.service_status, "Service running", 100)
                    current_step += 1
                    self.update_overall_progress(current_step / total_steps)
                
                # Download model if needed
                if "model" in steps_needed:
                    self.update_section_status(self.model_status, "Preparing download...")
                    
                    # Special progress callback for model download
                    def model_progress(status, percent):
                        self.after(0, lambda: self.update_section_status(
                            self.model_status, 
                            status, 
                            percent
                        ))
                    
                    self.installer.progress_callback = model_progress
                    success, msg = self.installer.download_model("qwen2.5:14b")
                    
                    if not success:
                        self.show_error(f"Model download failed: {msg}")
                        return
                        
                    self.update_section_status(self.model_status, "Model ready", 100)
                    current_step += 1
                    self.update_overall_progress(current_step / total_steps)
                
                # Setup complete
                self.setup_complete = True
                self.save_state()
                
                self.after(0, self.on_setup_complete)
                
            except Exception as e:
                self.logger.error(f"Setup failed: {e}")
                self.show_error(f"Setup failed: {str(e)}")
        
        # Start thread
        self.setup_thread = threading.Thread(target=run_setup, daemon=True)
        self.setup_thread.start()
    
    def update_progress(self, status: str, percent: float):
        """Progress callback for installer."""
        # This is called from background thread
        self.after(0, lambda: self.overall_label.configure(text=status))
    
    def update_overall_progress(self, fraction: float):
        """Update overall progress bar."""
        self.after(0, lambda: self.overall_progress.set(fraction))
    
    def on_setup_complete(self):
        """Handle successful setup completion."""
        self.overall_label.configure(text="Setup complete! Ready to use ComBadge.")
        self.overall_progress.set(1.0)
        self.continue_button.configure(state="normal", text="Start ComBadge")
        self.cancel_button.configure(text="Close")
        
        # Show completion message
        messagebox.showinfo(
            "Setup Complete",
            "ComBadge setup is complete!\n\n"
            "The AI model is ready and you can now start using ComBadge."
        )
    
    def show_error(self, message: str):
        """Show error message to user."""
        self.after(0, lambda: messagebox.showerror("Setup Error", message))
        self.after(0, lambda: self.cancel_button.configure(state="normal"))
        self.after(0, lambda: self.continue_button.configure(state="disabled"))
    
    def cancel_setup(self):
        """Cancel setup process."""
        if self.setup_complete:
            self.on_close()
            return
            
        if hasattr(self, 'setup_thread') and self.setup_thread.is_alive():
            response = messagebox.askyesno(
                "Cancel Setup",
                "Setup is in progress. Are you sure you want to cancel?\n\n"
                "You can resume setup next time you start ComBadge."
            )
            
            if response:
                self.cancel_requested = True
                self.installer.cancel_operation()
                self.save_state()
                self.destroy()
        else:
            self.destroy()
    
    def continue_setup(self):
        """Continue/complete setup."""
        if self.setup_complete:
            self.save_state()
            if self.on_complete_callback:
                self.on_complete_callback()
            self.destroy()
    
    def load_state(self):
        """Load setup state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
            else:
                self.state = {
                    "setup_started": False,
                    "setup_complete": False,
                    "ollama_installed": False,
                    "model_downloaded": False,
                    "last_attempt": None
                }
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            self.state = {}
    
    def save_state(self):
        """Save setup state to file."""
        try:
            self.state["setup_complete"] = self.setup_complete
            self.state["last_attempt"] = time.time()
            
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
    
    def on_close(self):
        """Handle window close."""
        if hasattr(self, 'setup_thread') and self.setup_thread.is_alive():
            self.cancel_setup()
        else:
            self.destroy()


def check_and_run_setup(parent=None, callback=None) -> bool:
    """Check if setup is needed and run wizard if necessary.
    
    Args:
        parent: Parent window
        callback: Callback when setup completes
        
    Returns:
        True if setup is complete or not needed
    """
    # Quick check if everything is already set up
    installer = OllamaInstaller()
    server_manager = OllamaServerManager()
    
    # Check all requirements
    if installer.is_ollama_installed() and server_manager.is_server_running():
        try:
            models = server_manager.get_available_models()
            if any("qwen2.5" in m.name for m in models):
                # Everything is ready
                return True
        except:
            pass
    
    # Setup needed - show wizard
    wizard = SetupWizard(parent, callback)
    wizard.wait_window()  # Wait for wizard to close
    
    # Check if setup completed
    return wizard.setup_complete