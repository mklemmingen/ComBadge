"""Input Panel Component

Large auto-expanding text area for email and command input.
"""

import tkinter as tk
from typing import Optional, Callable

import customtkinter as ctk

from ..styles.themes import Theme


class InputPanel(ctk.CTkFrame):
    """Input panel for natural language commands and emails."""
    
    def __init__(self, parent, theme: Theme):
        """Initialize input panel.
        
        Args:
            parent: Parent widget
            theme: Theme configuration
        """
        super().__init__(parent, **theme.create_frame_style(elevated=False))
        
        self.theme = theme
        self.on_submit: Optional[Callable[[str], None]] = None
        self.on_clear: Optional[Callable[[], None]] = None
        
        self._setup_layout()
        self._setup_event_handlers()
        
    def _setup_layout(self):
        """Setup input panel layout."""
        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Text area
        
        # Header with title and clear button
        self._create_header()
        
        # Main text input area
        self._create_text_area()
        
        # Action buttons
        self._create_action_buttons()
        
    def _create_header(self):
        """Create header with title and clear button."""
        header_frame = ctk.CTkFrame(
            self,
            height=40,
            **self.theme.create_frame_style(elevated=False)
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))
        header_frame.grid_propagate(False)
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Title label
        title_label = ctk.CTkLabel(
            header_frame,
            text="Input",
            font=self.theme.get_header_font(),
            text_color=self.theme.colors.text_primary
        )
        title_label.grid(row=0, column=0, padx=0, pady=10, sticky="w")
        
        # Clear button
        self.clear_button = ctk.CTkButton(
            header_frame,
            text="Clear",
            width=60,
            height=25,
            command=self._handle_clear,
            **self.theme.create_button_style("secondary")
        )
        self.clear_button.grid(row=0, column=2, padx=0, pady=10, sticky="e")
        
    def _create_text_area(self):
        """Create main text input area."""
        # Text area with scrolling
        self.text_area = ctk.CTkTextbox(
            self,
            wrap="word",
            **self.theme.create_input_style()
        )
        self.text_area.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        
        # Setting placeholder text
        self._set_placeholder()
        
        # Binding events for placeholder management
        self.text_area.bind("<FocusIn>", self._on_focus_in)
        self.text_area.bind("<FocusOut>", self._on_focus_out)
        self.text_area.bind("<KeyRelease>", self._on_text_change)
        
        # Context menu
        self._create_context_menu()
        
    def _create_action_buttons(self):
        """Create action buttons at bottom."""
        button_frame = ctk.CTkFrame(
            self,
            height=50,
            **self.theme.create_frame_style(elevated=False)
        )
        button_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=(10, 0))
        button_frame.grid_propagate(False)
        button_frame.grid_columnconfigure(0, weight=1)
        
        # Submit button
        self.submit_button = ctk.CTkButton(
            button_frame,
            text="Process Command",
            height=32,
            command=self._handle_submit,
            **self.theme.create_button_style("primary")
        )
        self.submit_button.grid(row=0, column=1, padx=5, pady=10, sticky="e")
        
        # Character count label
        self.char_count_label = ctk.CTkLabel(
            button_frame,
            text="0 characters",
            font=self.theme.get_small_font(),
            text_color=self.theme.colors.text_muted
        )
        self.char_count_label.grid(row=0, column=0, padx=0, pady=10, sticky="w")
        
    def _create_context_menu(self):
        """Create context menu for text area."""
        self.context_menu = tk.Menu(
            self,
            tearoff=0,
            bg=self.theme.colors.surface,
            fg=self.theme.colors.text_primary,
            activebackground=self.theme.colors.accent_blue,
            activeforeground=self.theme.colors.text_primary,
            border=0
        )
        
        self.context_menu.add_command(label="Cut", command=self._cut_text)
        self.context_menu.add_command(label="Copy", command=self._copy_text)
        self.context_menu.add_command(label="Paste", command=self._paste_text)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Select All", command=self._select_all)
        self.context_menu.add_command(label="Clear", command=self._handle_clear)
        
        # Binding right-click to show context menu
        self.text_area.bind("<Button-3>", self._show_context_menu)
        
    def _setup_event_handlers(self):
        """Setup event handlers for input panel."""
        # Ctrl+Enter for submit
        self.text_area.bind("<Control-Return>", lambda e: self._handle_submit())
        
        # Tab handling for better UX
        self.text_area.bind("<Tab>", self._handle_tab)
        
        # Auto-resize handling
        self.bind("<Configure>", self._on_resize)
        
    def _set_placeholder(self):
        """Set placeholder text in text area."""
        placeholder_text = "Paste email or enter your command...\n\nExamples:\n• Reserve resource RES-1234 for tomorrow 2-4pm\n• Schedule task for project items due this week\n• Generate report for usage data last month"
        
        self.text_area.insert("1.0", placeholder_text)
        self.text_area.configure(text_color=self.theme.colors.text_muted)
        self._placeholder_active = True
        
    def _on_focus_in(self, event):
        """Handle focus in event."""
        if self._placeholder_active:
            self.text_area.delete("1.0", "end")
            self.text_area.configure(text_color=self.theme.colors.text_primary)
            self._placeholder_active = False
            
        # Update border color for focus
        self.text_area.configure(
            **self.theme.create_input_style(focused=True)
        )
        
    def _on_focus_out(self, event):
        """Handle focus out event."""
        # Restore placeholder if empty
        if not self.text_area.get("1.0", "end-1c").strip():
            self._set_placeholder()
            
        # Remove focus border
        self.text_area.configure(
            **self.theme.create_input_style(focused=False)
        )
        
    def _on_text_change(self, event):
        """Handle text change event."""
        text = self.get_text()
        char_count = len(text)
        
        # Update character count
        self.char_count_label.configure(
            text=f"{char_count:,} characters"
        )
        
        # Update submit button state
        self._update_submit_button_state(text)
        
    def _update_submit_button_state(self, text: str):
        """Update submit button based on text content.
        
        Args:
            text: Current text content
        """
        has_content = bool(text.strip()) and not self._placeholder_active
        
        if has_content:
            self.submit_button.configure(state="normal")
        else:
            self.submit_button.configure(state="disabled")
            
    def _on_resize(self, event):
        """Handle panel resize."""
        # Auto-adjust minimum height based on content
        pass
        
    def _handle_tab(self, event):
        """Handle tab key press."""
        # Insert 4 spaces instead of tab character
        self.text_area.insert("insert", "    ")
        return "break"  # Prevent default tab behavior
        
    def _handle_submit(self):
        """Handle submit action."""
        text = self.get_text()
        if text.strip() and self.on_submit:
            self.on_submit(text)
            
    def _handle_clear(self):
        """Handle clear action."""
        self.clear_text()
        if self.on_clear:
            self.on_clear()
            
    def _show_context_menu(self, event):
        """Show context menu at cursor position."""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
            
    def _cut_text(self):
        """Cut selected text."""
        try:
            self.text_area.event_generate("<<Cut>>")
        except tk.TclError:
            pass
            
    def _copy_text(self):
        """Copy selected text."""
        try:
            self.text_area.event_generate("<<Copy>>")
        except tk.TclError:
            pass
            
    def _paste_text(self):
        """Paste text from clipboard."""
        try:
            # Clear placeholder before pasting
            if self._placeholder_active:
                self._on_focus_in(None)
            self.text_area.event_generate("<<Paste>>")
        except tk.TclError:
            pass
            
    def _select_all(self):
        """Select all text."""
        self.text_area.tag_add("sel", "1.0", "end")
        
    def get_text(self) -> str:
        """Get current text content.
        
        Returns:
            Current text content (empty if placeholder is active)
        """
        if self._placeholder_active:
            return ""
        return self.text_area.get("1.0", "end-1c")
        
    def set_text(self, text: str):
        """Set text content.
        
        Args:
            text: Text to set
        """
        # Clear existing content
        self.text_area.delete("1.0", "end")
        
        if text.strip():
            # Set actual content
            self.text_area.insert("1.0", text)
            self.text_area.configure(text_color=self.theme.colors.text_primary)
            self._placeholder_active = False
        else:
            # Set placeholder
            self._set_placeholder()
            
        # Update UI state
        self._on_text_change(None)
        
    def clear_text(self):
        """Clear text content."""
        self.text_area.delete("1.0", "end")
        self._set_placeholder()
        self._on_text_change(None)
        
    def focus_input(self):
        """Focus the text input area."""
        self.text_area.focus_set()
        
    def set_readonly(self, readonly: bool):
        """Set text area as readonly.
        
        Args:
            readonly: Whether text area should be readonly
        """
        state = "disabled" if readonly else "normal"
        self.text_area.configure(state=state)
        self.submit_button.configure(state="disabled" if readonly else "normal")
        self.clear_button.configure(state="disabled" if readonly else "normal")
        
    def append_text(self, text: str):
        """Append text to current content.
        
        Args:
            text: Text to append
        """
        if self._placeholder_active:
            self.set_text(text)
        else:
            current_text = self.get_text()
            self.set_text(current_text + text)