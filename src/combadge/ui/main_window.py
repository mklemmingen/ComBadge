"""ComBadge Main Window

Main application window with responsive design.
"""

import tkinter as tk
import webbrowser
from typing import Optional, Callable

import customtkinter as ctk

from .styles.themes import Theme
from .components.input_panel import InputPanel
from .components.status_indicators import StatusIndicators
from .components.reasoning_display import ReasoningDisplay
from .utils.event_handlers import EventHandler


class MainWindow(ctk.CTk):
    """Main application window for ComBadge."""
    
    def __init__(self):
        """Initialize main window with layout."""
        super().__init__()
        
        # Initialize theme and event handler
        self.theme = Theme()
        self.event_handler = EventHandler(self)
        
        # Window configuration
        self._setup_window()
        self._create_layout()
        self._setup_keyboard_shortcuts()
        
        # Component references
        self.input_panel: Optional[InputPanel] = None
        self.status_indicators: Optional[StatusIndicators] = None
        self.reasoning_display: Optional[ReasoningDisplay] = None
        
        # Callbacks
        self.on_submit: Optional[Callable[[str], None]] = None
        self.on_clear: Optional[Callable[[], None]] = None
        self.on_regenerate: Optional[Callable[[], None]] = None
        
    def _setup_window(self):
        """Configure main window properties."""
        self.title("ComBadge - Fleet Management Assistant")
        self.geometry("1200x800")
        self.minsize(800, 600)
        
        # Setting window icon and properties
        self.configure(fg_color=self.theme.colors.primary_bg)
        
        # Center window on screen
        self._center_window()
        
        # Configure grid weights for responsive design
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Main content area
        
    def _center_window(self):
        """Center window on screen."""
        self.update_idletasks()
        width = 1200
        height = 800
        
        # Getting screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Calculating position
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        
        self.geometry(f"{width}x{height}+{x}+{y}")
        
    def _create_layout(self):
        """Create main window layout structure."""
        # Header
        self._create_header()
        
        # Main content area
        self._create_main_content()
        
        # Footer
        self._create_footer()
        
    def _create_header(self):
        """Create header with title and branding."""
        header_frame = ctk.CTkFrame(
            self,
            height=80,
            corner_radius=0,
            **self.theme.create_frame_style(elevated=True)
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_propagate(False)
        header_frame.grid_columnconfigure(1, weight=1)
        
        # ComBadge logo/title
        title_label = ctk.CTkLabel(
            header_frame,
            text="ComBadge",
            font=self.theme.get_title_font(),
            text_color=self.theme.colors.mercedes_blue
        )
        title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Fleet Management Natural Language Processor",
            font=self.theme.get_body_font(),
            text_color=self.theme.colors.text_secondary
        )
        subtitle_label.grid(row=0, column=1, padx=10, pady=20, sticky="w")
        
        # Status indicator in header
        self.header_status = ctk.CTkLabel(
            header_frame,
            text="Ready",
            font=self.theme.get_small_font(),
            text_color=self.theme.colors.success
        )
        self.header_status.grid(row=0, column=2, padx=20, pady=20, sticky="e")
        
    def _create_main_content(self):
        """Create main content area with input and reasoning panels."""
        # Main container
        main_container = ctk.CTkFrame(
            self,
            **self.theme.create_frame_style(elevated=False)
        )
        main_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        main_container.grid_columnconfigure(0, weight=2)  # Input side
        main_container.grid_columnconfigure(1, weight=1)  # Reasoning side
        main_container.grid_rowconfigure(0, weight=1)
        
        # Left panel - Input and status
        left_panel = ctk.CTkFrame(
            main_container,
            **self.theme.create_frame_style(elevated=True)
        )
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(0, weight=1)  # Input panel
        left_panel.grid_rowconfigure(1, weight=0)  # Status panel
        
        # Input panel
        self.input_panel = InputPanel(left_panel, self.theme)
        self.input_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Status indicators
        self.status_indicators = StatusIndicators(left_panel, self.theme)
        self.status_indicators.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Right panel - Chain of Thought reasoning
        right_panel = ctk.CTkFrame(
            main_container,
            **self.theme.create_frame_style(elevated=True)
        )
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(0, weight=1)
        
        # Reasoning display
        self.reasoning_display = ReasoningDisplay(right_panel, self.theme)
        self.reasoning_display.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Connect event handlers
        self._connect_event_handlers()
        
    def _create_footer(self):
        """Create footer with developer attribution and shortcuts."""
        footer_frame = ctk.CTkFrame(
            self,
            height=30,
            corner_radius=0,
            **self.theme.create_frame_style(elevated=False)
        )
        footer_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        footer_frame.grid_propagate(False)
        footer_frame.grid_columnconfigure(1, weight=1)
        
        # Keyboard shortcuts info
        shortcuts_label = ctk.CTkLabel(
            footer_frame,
            text="Ctrl+Enter: Submit • Ctrl+L: Clear • Ctrl+R: Regenerate",
            font=self.theme.get_small_font(),
            text_color=self.theme.colors.text_muted
        )
        shortcuts_label.grid(row=0, column=0, padx=15, pady=5, sticky="w")
        
        # Developer attribution
        developer_link = ctk.CTkLabel(
            footer_frame,
            text="developed by Martin Lauterbach (mklemmingen)",
            font=self.theme.get_small_font(),
            text_color=self.theme.colors.text_muted
        )
        developer_link.grid(row=0, column=2, padx=15, pady=5, sticky="e")
        
        # Making developer attribution clickable
        developer_link.bind("<Button-1>", self._open_developer_github)
        developer_link.bind("<Enter>", lambda e: developer_link.configure(
            text_color=self.theme.colors.mercedes_blue,
            cursor="hand2"
        ))
        developer_link.bind("<Leave>", lambda e: developer_link.configure(
            text_color=self.theme.colors.text_muted,
            cursor="arrow"
        ))
        
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for the application."""
        # Ctrl+Enter: Submit
        self.bind("<Control-Return>", self._handle_submit_shortcut)
        
        # Ctrl+L: Clear
        self.bind("<Control-l>", self._handle_clear_shortcut)
        self.bind("<Control-L>", self._handle_clear_shortcut)
        
        # Ctrl+R: Regenerate
        self.bind("<Control-r>", self._handle_regenerate_shortcut)
        self.bind("<Control-R>", self._handle_regenerate_shortcut)
        
        # Focus management
        self.focus_set()
        
    def _connect_event_handlers(self):
        """Connect component event handlers."""
        if self.input_panel:
            self.input_panel.on_submit = self._handle_submit
            self.input_panel.on_clear = self._handle_clear
            
    def _handle_submit(self, text: str):
        """Handle submit action from input panel."""
        if self.on_submit and text.strip():
            self.on_submit(text)
            self.update_status("Processing...", "processing")
            
    def _handle_clear(self):
        """Handle clear action."""
        if self.on_clear:
            self.on_clear()
        self.update_status("Ready", "idle")
        if self.reasoning_display:
            self.reasoning_display.clear()
            
    def _handle_regenerate(self):
        """Handle regenerate action."""
        if self.on_regenerate:
            self.on_regenerate()
            self.update_status("Regenerating...", "processing")
            
    def _handle_submit_shortcut(self, event):
        """Handle Ctrl+Enter shortcut."""
        if self.input_panel:
            text = self.input_panel.get_text()
            self._handle_submit(text)
            
    def _handle_clear_shortcut(self, event):
        """Handle Ctrl+L shortcut."""
        if self.input_panel:
            self.input_panel.clear_text()
        self._handle_clear()
        
    def _handle_regenerate_shortcut(self, event):
        """Handle Ctrl+R shortcut."""
        self._handle_regenerate()
        
    def _open_developer_github(self, event):
        """Open developer GitHub profile."""
        webbrowser.open("https://github.com/mklemmingen")
        
    def update_status(self, message: str, status: str = "idle"):
        """Update status indicators and header.
        
        Args:
            message: Status message to display
            status: Status type (idle, processing, success, warning, error)
        """
        # Update header status
        color = self.theme.get_status_color(status)
        self.header_status.configure(text=message, text_color=color)
        
        # Update status indicators
        if self.status_indicators:
            self.status_indicators.update_status(message, status)
            
    def update_progress(self, progress: float, message: str = ""):
        """Update progress indicators.
        
        Args:
            progress: Progress value between 0.0 and 1.0
            message: Optional progress message
        """
        if self.status_indicators:
            self.status_indicators.update_progress(progress, message)
            
    def add_reasoning_step(self, step: str, content: str):
        """Add reasoning step to Chain of Thought display.
        
        Args:
            step: Step title/name
            content: Step content/explanation
        """
        if self.reasoning_display:
            self.reasoning_display.add_step(step, content)
            
    def clear_reasoning(self):
        """Clear Chain of Thought reasoning display."""
        if self.reasoning_display:
            self.reasoning_display.clear()
            
    def set_callbacks(self, 
                     on_submit: Optional[Callable[[str], None]] = None,
                     on_clear: Optional[Callable[[], None]] = None,
                     on_regenerate: Optional[Callable[[], None]] = None):
        """Set callback functions for UI events.
        
        Args:
            on_submit: Function to call when text is submitted
            on_clear: Function to call when clear is requested
            on_regenerate: Function to call when regenerate is requested
        """
        self.on_submit = on_submit
        self.on_clear = on_clear
        self.on_regenerate = on_regenerate
        
    def get_input_text(self) -> str:
        """Get current input text.
        
        Returns:
            Current input text
        """
        return self.input_panel.get_text() if self.input_panel else ""
        
    def set_input_text(self, text: str):
        """Set input text.
        
        Args:
            text: Text to set in input field
        """
        if self.input_panel:
            self.input_panel.set_text(text)
            
    def focus_input(self):
        """Focus the input text area."""
        if self.input_panel:
            self.input_panel.focus_input()