"""Status Indicators Component

Real-time processing feedback with progress bars and status messages.
"""

import tkinter as tk
from typing import Optional
import threading
import time

import customtkinter as ctk

from ..styles.themes import Theme


class StatusIndicators(ctk.CTkFrame):
    """Status indicators for processing feedback."""
    
    def __init__(self, parent, theme: Theme):
        """Initialize status indicators.
        
        Args:
            parent: Parent widget
            theme: Theme configuration
        """
        super().__init__(parent, **theme.create_frame_style(elevated=False))
        
        self.theme = theme
        self.current_status = "idle"
        self.animation_running = False
        self._animation_thread = None
        
        self._setup_layout()
        
    def _setup_layout(self):
        """Setup status indicators layout."""
        # Configure grid weights
        self.grid_columnconfigure(1, weight=1)
        
        # Status icon/indicator
        self._create_status_icon()
        
        # Status message
        self._create_status_message()
        
        # Progress bar
        self._create_progress_bar()
        
        # Processing time indicator
        self._create_time_indicator()
        
    def _create_status_icon(self):
        """Create animated status icon."""
        self.status_icon = ctk.CTkLabel(
            self,
            text="●",
            font=self.theme.get_header_font(),
            text_color=self.theme.colors.success,
            width=30
        )
        self.status_icon.grid(row=0, column=0, padx=(5, 10), pady=5, sticky="w")
        
    def _create_status_message(self):
        """Create status message label."""
        self.status_message = ctk.CTkLabel(
            self,
            text="Ready",
            font=self.theme.get_body_font(),
            text_color=self.theme.colors.text_primary
        )
        self.status_message.grid(row=0, column=1, padx=0, pady=5, sticky="w")
        
    def _create_progress_bar(self):
        """Create progress bar for processing feedback."""
        # Progress bar container
        progress_frame = ctk.CTkFrame(
            self,
            height=20,
            **self.theme.create_frame_style(elevated=False)
        )
        progress_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=0, pady=(5, 0))
        progress_frame.grid_propagate(False)
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            height=8
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=5, pady=6)
        self.progress_bar.set(0)
        
        # Hide initially
        progress_frame.grid_remove()
        self.progress_frame = progress_frame
        
    def _create_time_indicator(self):
        """Create processing time indicator."""
        self.time_indicator = ctk.CTkLabel(
            self,
            text="",
            font=self.theme.get_small_font(),
            text_color=self.theme.colors.text_muted
        )
        self.time_indicator.grid(row=0, column=2, padx=(10, 5), pady=5, sticky="e")
        
        # Processing start time
        self.processing_start_time = None
        
    def update_status(self, message: str, status: str = "idle"):
        """Update status indicators.
        
        Args:
            message: Status message to display
            status: Status type (idle, processing, success, warning, error)
        """
        self.current_status = status
        
        # Update status message
        self.status_message.configure(text=message)
        
        # Update status icon color and start animation if needed
        self._update_status_icon(status)
        
        # Handle processing-specific updates
        if status == "processing":
            self._start_processing()
        else:
            self._stop_processing()
            
        # Update time indicator
        self._update_time_indicator(status)
        
    def _update_status_icon(self, status: str):
        """Update status icon based on status type.
        
        Args:
            status: Status type
        """
        color = self.theme.get_status_color(status)
        self.status_icon.configure(text_color=color)
        
        # Start pulsing animation for processing status
        if status == "processing":
            self._start_pulse_animation()
        else:
            self._stop_pulse_animation()
            
    def _start_pulse_animation(self):
        """Start pulsing animation for processing status."""
        if not self.animation_running:
            self.animation_running = True
            self._animation_thread = threading.Thread(
                target=self._pulse_animation_loop,
                daemon=True
            )
            self._animation_thread.start()
            
    def _stop_pulse_animation(self):
        """Stop pulsing animation."""
        self.animation_running = False
        
    def _pulse_animation_loop(self):
        """Pulse animation loop running in separate thread."""
        alpha_values = [0.3, 0.5, 0.7, 0.9, 1.0, 0.9, 0.7, 0.5]
        index = 0
        
        while self.animation_running:
            try:
                alpha = alpha_values[index % len(alpha_values)]
                
                # Calculate color with alpha
                base_color = self.theme.colors.processing
                pulsed_color = self._apply_alpha_to_color(base_color, alpha)
                
                # Update icon color on main thread
                self.after_idle(
                    lambda c=pulsed_color: self.status_icon.configure(text_color=c)
                )
                
                index += 1
                time.sleep(0.1)
                
            except Exception:
                break
                
    def _apply_alpha_to_color(self, hex_color: str, alpha: float) -> str:
        """Apply alpha to hex color.
        
        Args:
            hex_color: Hex color string
            alpha: Alpha value (0-1)
            
        Returns:
            Color with applied alpha
        """
        # Simple alpha application by blending with background
        try:
            # Remove '#' if present
            hex_color = hex_color.lstrip('#')
            
            # Convert to RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # Background color (dark gray)
            bg_r, bg_g, bg_b = 43, 43, 43  # #2B2B2B
            
            # Blend with background
            r = int(r * alpha + bg_r * (1 - alpha))
            g = int(g * alpha + bg_g * (1 - alpha))
            b = int(b * alpha + bg_b * (1 - alpha))
            
            return f"#{r:02x}{g:02x}{b:02x}"
            
        except Exception:
            return hex_color
            
    def _start_processing(self):
        """Start processing-specific indicators."""
        # Record start time
        self.processing_start_time = time.time()
        
        # Show progress bar
        self.progress_frame.grid()
        
        # Reset progress
        self.progress_bar.set(0)
        
    def _stop_processing(self):
        """Stop processing-specific indicators."""
        # Hide progress bar
        self.progress_frame.grid_remove()
        
        # Reset processing start time
        self.processing_start_time = None
        
    def _update_time_indicator(self, status: str):
        """Update time indicator based on status.
        
        Args:
            status: Current status
        """
        if status == "processing" and self.processing_start_time:
            # Start time update loop
            self._start_time_update_loop()
        else:
            # Clear time indicator or show completion time
            if status in ["success", "error", "warning"] and self.processing_start_time:
                elapsed = time.time() - self.processing_start_time
                self.time_indicator.configure(text=f"Completed in {elapsed:.1f}s")
            else:
                self.time_indicator.configure(text="")
                
    def _start_time_update_loop(self):
        """Start time update loop for processing."""
        if self.current_status == "processing" and self.processing_start_time:
            elapsed = time.time() - self.processing_start_time
            self.time_indicator.configure(text=f"{elapsed:.1f}s")
            
            # Schedule next update
            self.after(100, self._start_time_update_loop)
            
    def update_progress(self, progress: float, message: str = ""):
        """Update progress bar.
        
        Args:
            progress: Progress value between 0.0 and 1.0
            message: Optional progress message
        """
        # Ensure progress bar is visible
        if self.current_status == "processing":
            self.progress_frame.grid()
            
        # Update progress bar value
        self.progress_bar.set(max(0.0, min(1.0, progress)))
        
        # Update message if provided
        if message:
            self.status_message.configure(text=message)
            
    def show_detailed_status(self, details: str):
        """Show detailed status information in tooltip.
        
        Args:
            details: Detailed status information
        """
        # Create tooltip for detailed information
        self._create_tooltip(self.status_message, details)
        
    def _create_tooltip(self, widget, text: str):
        """Create tooltip for widget.
        
        Args:
            widget: Widget to attach tooltip to
            text: Tooltip text
        """
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.configure(bg=self.theme.colors.surface)
            
            label = tk.Label(
                tooltip,
                text=text,
                bg=self.theme.colors.surface,
                fg=self.theme.colors.text_primary,
                font=self.theme.get_small_font(),
                wraplength=300,
                justify="left"
            )
            label.pack()
            
            # Position tooltip
            x = widget.winfo_rootx() + 25
            y = widget.winfo_rooty() + 25
            tooltip.geometry(f"+{x}+{y}")
            
            # Store tooltip reference
            widget.tooltip = tooltip
            
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
                
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        
    def reset(self):
        """Reset status indicators to initial state."""
        self.update_status("Ready", "idle")
        self.progress_bar.set(0)
        self.progress_frame.grid_remove()
        
    def set_error_details(self, error_message: str):
        """Set error details for display.
        
        Args:
            error_message: Detailed error message
        """
        self.update_status("Error occurred", "error")
        self.show_detailed_status(error_message)