"""Event Handlers for ComBadge UI

Centralized event handling and UI interaction management.
"""

import tkinter as tk
from typing import Callable, Optional, Dict, Any
import threading
import queue

from ..styles.themes import Theme


class EventHandler:
    """Centralized event handler for ComBadge UI interactions."""
    
    def __init__(self, main_window):
        """Initialize event handler.
        
        Args:
            main_window: Main window instance
        """
        self.main_window = main_window
        self.callbacks: Dict[str, Callable] = {}
        self.event_queue = queue.Queue()
        self.processing_events = False
        
        self._setup_event_processing()
        
    def _setup_event_processing(self):
        """Setup event processing system."""
        # Start event processing thread
        self.processing_thread = threading.Thread(
            target=self._process_events,
            daemon=True
        )
        self.processing_thread.start()
        self.processing_events = True
        
    def _process_events(self):
        """Process events from queue in separate thread."""
        while self.processing_events:
            try:
                event_data = self.event_queue.get(timeout=1.0)
                if event_data:
                    self._handle_queued_event(event_data)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing event: {e}")
                
    def _handle_queued_event(self, event_data: Dict[str, Any]):
        """Handle event from queue.
        
        Args:
            event_data: Event data dictionary
        """
        event_type = event_data.get('type')
        callback = self.callbacks.get(event_type)
        
        if callback:
            try:
                # Execute callback on main thread
                args = event_data.get('args', ())
                kwargs = event_data.get('kwargs', {})
                
                self.main_window.after_idle(
                    lambda: callback(*args, **kwargs)
                )
            except Exception as e:
                print(f"Error in event callback: {e}")
                
    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for event type.
        
        Args:
            event_type: Type of event
            callback: Function to call
        """
        self.callbacks[event_type] = callback
        
    def emit_event(self, event_type: str, *args, **kwargs):
        """Emit event to be processed.
        
        Args:
            event_type: Type of event to emit
            *args: Event arguments
            **kwargs: Event keyword arguments
        """
        event_data = {
            'type': event_type,
            'args': args,
            'kwargs': kwargs
        }
        self.event_queue.put(event_data)
        
    def handle_window_close(self):
        """Handle main window close event."""
        self.processing_events = False
        
        # Clean up resources
        try:
            # Stop processing thread
            if hasattr(self, 'processing_thread'):
                self.processing_thread.join(timeout=1.0)
        except Exception:
            pass
            
    def setup_drag_and_drop(self, widget, callback: Callable[[str], None]):
        """Setup drag and drop functionality for widget.
        
        Args:
            widget: Widget to enable drag and drop on
            callback: Function to call with dropped file path
        """
        def on_drop(event):
            # Handle file drop
            files = event.data.split()
            if files:
                callback(files[0])
                
        # Enable drag and drop (platform-specific implementation)
        try:
            widget.drop_target_register('DND_Files')
            widget.dnd_bind('<<Drop>>', on_drop)
        except Exception:
            # Fallback or skip if drag-drop not available
            pass
            
    def setup_keyboard_navigation(self, widgets: list):
        """Setup keyboard navigation between widgets.
        
        Args:
            widgets: List of widgets for navigation
        """
        for i, widget in enumerate(widgets):
            # Tab navigation
            widget.bind('<Tab>', lambda e, idx=i: self._focus_next_widget(widgets, idx))
            widget.bind('<Shift-Tab>', lambda e, idx=i: self._focus_prev_widget(widgets, idx))
            
    def _focus_next_widget(self, widgets: list, current_index: int):
        """Focus next widget in list.
        
        Args:
            widgets: List of widgets
            current_index: Current widget index
        """
        next_index = (current_index + 1) % len(widgets)
        widgets[next_index].focus_set()
        return "break"  # Prevent default tab behavior
        
    def _focus_prev_widget(self, widgets: list, current_index: int):
        """Focus previous widget in list.
        
        Args:
            widgets: List of widgets
            current_index: Current widget index
        """
        prev_index = (current_index - 1) % len(widgets)
        widgets[prev_index].focus_set()
        return "break"  # Prevent default tab behavior
        
    def setup_context_menu(self, widget, menu_items: list):
        """Setup context menu for widget.
        
        Args:
            widget: Widget to attach menu to
            menu_items: List of menu item dictionaries
        """
        context_menu = tk.Menu(widget, tearoff=0)
        
        for item in menu_items:
            if item.get('separator'):
                context_menu.add_separator()
            else:
                context_menu.add_command(
                    label=item['label'],
                    command=item['command']
                )
                
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
                
        widget.bind("<Button-3>", show_context_menu)  # Right click
        
    def setup_hover_effects(self, widget, hover_style: Dict[str, Any], 
                          normal_style: Dict[str, Any]):
        """Setup hover effects for widget.
        
        Args:
            widget: Widget to add hover effects to
            hover_style: Style to apply on hover
            normal_style: Normal style to restore
        """
        def on_enter(event):
            widget.configure(**hover_style)
            
        def on_leave(event):
            widget.configure(**normal_style)
            
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        
    def setup_tooltip(self, widget, text: str):
        """Setup tooltip for widget.
        
        Args:
            widget: Widget to add tooltip to
            text: Tooltip text
        """
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.configure(bg="#2B2B2B")
            
            label = tk.Label(
                tooltip,
                text=text,
                bg="#2B2B2B",
                fg="#FFFFFF",
                font=("Segoe UI", 9),
                wraplength=300,
                justify="left"
            )
            label.pack()
            
            # Position tooltip
            x = event.x_root + 10
            y = event.y_root + 10
            tooltip.geometry(f"+{x}+{y}")
            
            # Auto-hide after 3 seconds
            tooltip.after(3000, tooltip.destroy)
            
            # Store reference
            widget.tooltip = tooltip
            
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
                
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
        
    def handle_text_selection(self, text_widget):
        """Handle text selection in text widget.
        
        Args:
            text_widget: Text widget to handle selection for
        """
        def on_select(event):
            try:
                selection = text_widget.selection_get()
                if selection:
                    self.emit_event('text_selected', selection, text_widget)
            except tk.TclError:
                # No selection
                pass
                
        text_widget.bind("<<Selection>>", on_select)
        
    def setup_auto_save(self, callback: Callable, interval_ms: int = 30000):
        """Setup auto-save functionality.
        
        Args:
            callback: Function to call for auto-save
            interval_ms: Save interval in milliseconds
        """
        def auto_save():
            try:
                callback()
            except Exception as e:
                print(f"Auto-save error: {e}")
            finally:
                # Schedule next auto-save
                self.main_window.after(interval_ms, auto_save)
                
        # Start auto-save timer
        self.main_window.after(interval_ms, auto_save)
        
    def handle_resize_events(self, callback: Callable[[int, int], None]):
        """Handle window resize events.
        
        Args:
            callback: Function to call with new width/height
        """
        def on_resize(event):
            if event.widget == self.main_window:
                width = event.width
                height = event.height
                callback(width, height)
                
        self.main_window.bind("<Configure>", on_resize)
        
    def setup_undo_redo(self, text_widget):
        """Setup undo/redo functionality for text widget.
        
        Args:
            text_widget: Text widget to add undo/redo to
        """
        # Enable undo
        text_widget.configure(undo=True, maxundo=50)
        
        # Bind shortcuts
        text_widget.bind("<Control-z>", lambda e: text_widget.edit_undo())
        text_widget.bind("<Control-y>", lambda e: text_widget.edit_redo())
        text_widget.bind("<Control-Z>", lambda e: text_widget.edit_redo())  # Shift+Ctrl+Z
        
    def validate_input(self, input_text: str, validation_rules: Dict[str, Any]) -> bool:
        """Validate input text against rules.
        
        Args:
            input_text: Text to validate
            validation_rules: Validation rules dictionary
            
        Returns:
            True if valid, False otherwise
        """
        # Check minimum length
        min_length = validation_rules.get('min_length', 0)
        if len(input_text) < min_length:
            return False
            
        # Check maximum length
        max_length = validation_rules.get('max_length', float('inf'))
        if len(input_text) > max_length:
            return False
            
        # Check required patterns
        patterns = validation_rules.get('patterns', [])
        for pattern in patterns:
            import re
            if not re.search(pattern, input_text):
                return False
                
        return True
        
    def show_confirmation_dialog(self, title: str, message: str, 
                               callback: Callable[[bool], None]):
        """Show confirmation dialog.
        
        Args:
            title: Dialog title
            message: Dialog message
            callback: Function to call with result (True/False)
        """
        import tkinter.messagebox as msgbox
        
        result = msgbox.askyesno(title, message)
        callback(result)
        
    def show_error_dialog(self, title: str, message: str):
        """Show error dialog.
        
        Args:
            title: Dialog title
            message: Error message
        """
        import tkinter.messagebox as msgbox
        msgbox.showerror(title, message)
        
    def show_info_dialog(self, title: str, message: str):
        """Show information dialog.
        
        Args:
            title: Dialog title
            message: Information message
        """
        import tkinter.messagebox as msgbox
        msgbox.showinfo(title, message)
        
    def cleanup(self):
        """Clean up event handler resources."""
        self.processing_events = False
        
        # Clear callbacks
        self.callbacks.clear()
        
        # Clean up queue
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
            except queue.Empty:
                break