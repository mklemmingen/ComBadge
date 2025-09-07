"""
Settings Dialog for ComBadge Configuration Management

User-friendly interface for managing application settings with tabs for different
categories, input validation, preview of changes, and reset functionality.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Callable, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

import customtkinter as ctk
from customtkinter import CTkFont

from ...core.config_manager import ConfigManager, AppConfig, ValidationError


class SettingsCategory(Enum):
    """Settings categories for tab organization"""
    GENERAL = "General"
    LLM = "Language Model"
    API = "API Configuration"
    UI = "User Interface"
    PROCESSING = "Processing"
    SHORTCUTS = "Keyboard Shortcuts"
    LOGGING = "Logging & Audit"
    ADVANCED = "Advanced"


@dataclass
class SettingField:
    """Represents a configuration field in the UI"""
    key: str
    label: str
    description: str
    field_type: type
    category: SettingsCategory
    options: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    sensitive: bool = False
    requires_restart: bool = False


class SettingWidget:
    """Base class for setting input widgets"""
    
    def __init__(self, parent: ctk.CTkFrame, field: SettingField, current_value: Any):
        self.parent = parent
        self.field = field
        self.current_value = current_value
        self.widget = None
        self._create_widget()
    
    def _create_widget(self):
        """Create the appropriate widget based on field type"""
        raise NotImplementedError
    
    def get_value(self) -> Any:
        """Get the current value from the widget"""
        raise NotImplementedError
    
    def set_value(self, value: Any):
        """Set the widget value"""
        raise NotImplementedError
    
    def reset_to_default(self, default_value: Any):
        """Reset widget to default value"""
        self.set_value(default_value)


class StringSettingWidget(SettingWidget):
    """Widget for string settings"""
    
    def _create_widget(self):
        if self.field.options:
            # Dropdown for string options
            self.widget = ctk.CTkComboBox(
                self.parent,
                values=self.field.options,
                width=200
            )
            if self.current_value in self.field.options:
                self.widget.set(self.current_value)
        else:
            # Text entry
            self.widget = ctk.CTkEntry(
                self.parent,
                width=200,
                show="*" if self.field.sensitive else None
            )
            self.widget.insert(0, str(self.current_value or ""))
    
    def get_value(self) -> str:
        if isinstance(self.widget, ctk.CTkComboBox):
            return self.widget.get()
        else:
            return self.widget.get()
    
    def set_value(self, value: Any):
        if isinstance(self.widget, ctk.CTkComboBox):
            if value in self.field.options:
                self.widget.set(str(value))
        else:
            self.widget.delete(0, "end")
            self.widget.insert(0, str(value or ""))


class IntSettingWidget(SettingWidget):
    """Widget for integer settings"""
    
    def _create_widget(self):
        frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        
        # Entry for value
        self.widget = ctk.CTkEntry(frame, width=100)
        self.widget.insert(0, str(self.current_value or 0))
        self.widget.pack(side="left", padx=(0, 5))
        
        # Spinner buttons
        if self.field.min_value is not None and self.field.max_value is not None:
            spinner_frame = ctk.CTkFrame(frame, fg_color="transparent")
            spinner_frame.pack(side="left")
            
            up_btn = ctk.CTkButton(
                spinner_frame,
                text="▲",
                width=20,
                height=15,
                font=CTkFont(size=8),
                command=self._increment
            )
            up_btn.pack()
            
            down_btn = ctk.CTkButton(
                spinner_frame,
                text="▼",
                width=20,
                height=15,
                font=CTkFont(size=8),
                command=self._decrement
            )
            down_btn.pack()
        
        # Range label
        if self.field.min_value is not None or self.field.max_value is not None:
            range_text = f"({self.field.min_value or ''} - {self.field.max_value or ''})"
            range_label = ctk.CTkLabel(frame, text=range_text, font=CTkFont(size=10))
            range_label.pack(side="left", padx=5)
        
        self.container = frame
    
    def _increment(self):
        try:
            value = int(self.widget.get())
            if self.field.max_value is None or value < self.field.max_value:
                self.widget.delete(0, "end")
                self.widget.insert(0, str(value + 1))
        except ValueError:
            pass
    
    def _decrement(self):
        try:
            value = int(self.widget.get())
            if self.field.min_value is None or value > self.field.min_value:
                self.widget.delete(0, "end")
                self.widget.insert(0, str(value - 1))
        except ValueError:
            pass
    
    def get_value(self) -> int:
        try:
            value = int(self.widget.get())
            if self.field.min_value is not None:
                value = max(value, self.field.min_value)
            if self.field.max_value is not None:
                value = min(value, self.field.max_value)
            return value
        except ValueError:
            return self.current_value or 0
    
    def set_value(self, value: Any):
        self.widget.delete(0, "end")
        self.widget.insert(0, str(value or 0))


class FloatSettingWidget(SettingWidget):
    """Widget for float settings"""
    
    def _create_widget(self):
        frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        
        # Slider for float values with defined range
        if self.field.min_value is not None and self.field.max_value is not None:
            self.slider = ctk.CTkSlider(
                frame,
                from_=self.field.min_value,
                to=self.field.max_value,
                width=150,
                command=self._on_slider_change
            )
            self.slider.set(self.current_value or self.field.min_value)
            self.slider.pack(side="left", padx=(0, 10))
        
        # Entry for precise value
        self.widget = ctk.CTkEntry(frame, width=80)
        self.widget.insert(0, f"{self.current_value or 0:.2f}")
        self.widget.pack(side="left")
        
        # Bind entry changes to slider
        if hasattr(self, 'slider'):
            self.widget.bind("<Return>", self._on_entry_change)
        
        self.container = frame
    
    def _on_slider_change(self, value: float):
        self.widget.delete(0, "end")
        self.widget.insert(0, f"{value:.2f}")
    
    def _on_entry_change(self, event):
        try:
            value = float(self.widget.get())
            if self.field.min_value is not None and self.field.max_value is not None:
                value = max(self.field.min_value, min(value, self.field.max_value))
                if hasattr(self, 'slider'):
                    self.slider.set(value)
        except ValueError:
            pass
    
    def get_value(self) -> float:
        try:
            value = float(self.widget.get())
            if self.field.min_value is not None:
                value = max(value, self.field.min_value)
            if self.field.max_value is not None:
                value = min(value, self.field.max_value)
            return value
        except ValueError:
            return self.current_value or 0.0
    
    def set_value(self, value: Any):
        self.widget.delete(0, "end")
        self.widget.insert(0, f"{value or 0:.2f}")
        if hasattr(self, 'slider'):
            self.slider.set(value or self.field.min_value)


class BoolSettingWidget(SettingWidget):
    """Widget for boolean settings"""
    
    def _create_widget(self):
        self.widget = ctk.CTkCheckBox(self.parent, text="")
        if self.current_value:
            self.widget.select()
    
    def get_value(self) -> bool:
        return self.widget.get()
    
    def set_value(self, value: Any):
        if value:
            self.widget.select()
        else:
            self.widget.deselect()


class ListSettingWidget(SettingWidget):
    """Widget for list settings"""
    
    def _create_widget(self):
        self.widget = ctk.CTkEntry(self.parent, width=200)
        # Convert list to comma-separated string
        value_str = ", ".join(str(v) for v in (self.current_value or []))
        self.widget.insert(0, value_str)
    
    def get_value(self) -> List[Any]:
        value_str = self.widget.get()
        if not value_str.strip():
            return []
        
        # Parse comma-separated values
        values = [v.strip() for v in value_str.split(',')]
        
        # Try to convert to appropriate types
        converted = []
        for v in values:
            try:
                # Try int
                converted.append(int(v))
            except ValueError:
                try:
                    # Try float
                    converted.append(float(v))
                except ValueError:
                    # Keep as string
                    converted.append(v)
        
        return converted
    
    def set_value(self, value: Any):
        self.widget.delete(0, "end")
        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value)
            self.widget.insert(0, value_str)


class SettingsCategoryTab(ctk.CTkFrame):
    """Tab content for a settings category"""
    
    def __init__(self, parent, category: SettingsCategory, fields: List[SettingField], config: Dict[str, Any]):
        super().__init__(parent)
        
        self.category = category
        self.fields = fields
        self.config = config
        self.widgets = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the category tab UI"""
        # Create scrollable frame
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text=self.category.value)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.scroll_frame.grid_columnconfigure(1, weight=1)
        
        row = 0
        for field in self.fields:
            # Field label
            label = ctk.CTkLabel(
                self.scroll_frame,
                text=field.label + ("*" if field.requires_restart else ""),
                font=CTkFont(size=12, weight="bold"),
                anchor="w"
            )
            label.grid(row=row, column=0, sticky="w", padx=10, pady=(10, 2))
            
            # Field description
            if field.description:
                desc_label = ctk.CTkLabel(
                    self.scroll_frame,
                    text=field.description,
                    font=CTkFont(size=10),
                    text_color="gray",
                    anchor="w",
                    wraplength=400
                )
                desc_label.grid(row=row+1, column=0, sticky="w", padx=20, pady=(0, 5))
            
            # Create appropriate widget
            current_value = self._get_nested_value(self.config, field.key)
            widget = self._create_field_widget(field, current_value)
            
            if hasattr(widget, 'container'):
                widget.container.grid(row=row, column=1, sticky="w", padx=10, pady=(10, 2))
            else:
                widget.widget.grid(row=row, column=1, sticky="w", padx=10, pady=(10, 2))
            
            self.widgets[field.key] = widget
            
            row += 2 if field.description else 1
            
        # Add note about restart requirements
        if any(f.requires_restart for f in self.fields):
            note_label = ctk.CTkLabel(
                self.scroll_frame,
                text="* Changes to these settings require application restart",
                font=CTkFont(size=10, slant="italic"),
                text_color="orange"
            )
            note_label.grid(row=row, column=0, columnspan=2, pady=10)
    
    def _create_field_widget(self, field: SettingField, current_value: Any) -> SettingWidget:
        """Create appropriate widget based on field type"""
        widget_map = {
            str: StringSettingWidget,
            int: IntSettingWidget,
            float: FloatSettingWidget,
            bool: BoolSettingWidget,
            list: ListSettingWidget
        }
        
        widget_class = widget_map.get(field.field_type, StringSettingWidget)
        return widget_class(self.scroll_frame, field, current_value)
    
    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        parts = key.split('.')
        current = config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def get_values(self) -> Dict[str, Any]:
        """Get all current values from widgets"""
        values = {}
        for key, widget in self.widgets.items():
            values[key] = widget.get_value()
        return values
    
    def reset_to_defaults(self, defaults: Dict[str, Any]):
        """Reset all fields to default values"""
        for key, widget in self.widgets.items():
            default_value = self._get_nested_value(defaults, key)
            if default_value is not None:
                widget.reset_to_default(default_value)


class SettingsDialog(ctk.CTkToplevel):
    """
    Comprehensive settings dialog for ComBadge configuration.
    
    Features:
    - Tabbed interface for different categories
    - Input validation with error messages
    - Preview of changes before applying
    - Reset to defaults functionality
    - Import/Export configuration
    - Hot-reload status indicator
    """
    
    # Define all configuration fields
    SETTING_FIELDS = [
        # General settings
        SettingField("environment", "Environment", "Deployment environment", 
                    str, SettingsCategory.GENERAL, 
                    options=["development", "staging", "production"],
                    requires_restart=True),
        SettingField("debug_mode", "Debug Mode", "Enable debug logging and features", 
                    bool, SettingsCategory.GENERAL),
        SettingField("enable_telemetry", "Enable Telemetry", "Send anonymous usage statistics", 
                    bool, SettingsCategory.GENERAL),
        
        # LLM settings
        SettingField("llm.model", "Model Name", "Language model to use", 
                    str, SettingsCategory.LLM),
        SettingField("llm.temperature", "Temperature", "Model creativity (0=focused, 2=creative)", 
                    float, SettingsCategory.LLM, min_value=0.0, max_value=2.0),
        SettingField("llm.max_tokens", "Max Tokens", "Maximum response length", 
                    int, SettingsCategory.LLM, min_value=100, max_value=4096),
        SettingField("llm.timeout", "Timeout (seconds)", "Request timeout", 
                    int, SettingsCategory.LLM, min_value=10, max_value=300),
        SettingField("llm.streaming", "Enable Streaming", "Stream responses in real-time", 
                    bool, SettingsCategory.LLM),
        SettingField("llm.base_url", "Base URL", "LLM API endpoint", 
                    str, SettingsCategory.LLM),
        
        # API settings
        SettingField("api.base_url", "API Base URL", "Fleet management API endpoint", 
                    str, SettingsCategory.API),
        SettingField("api.timeout", "Timeout (seconds)", "API request timeout", 
                    int, SettingsCategory.API, min_value=5, max_value=300),
        SettingField("api.retry_attempts", "Retry Attempts", "Number of retry attempts on failure", 
                    int, SettingsCategory.API, min_value=0, max_value=10),
        SettingField("api.retry_delay", "Retry Delay (seconds)", "Delay between retries", 
                    float, SettingsCategory.API, min_value=0.5, max_value=30.0),
        SettingField("api.authentication.method", "Auth Method", "Authentication type", 
                    str, SettingsCategory.API, options=["cookie", "token", "oauth", "api_key"]),
        SettingField("api.verify_ssl", "Verify SSL", "Verify SSL certificates", 
                    bool, SettingsCategory.API),
        
        # UI settings
        SettingField("ui.theme", "Theme", "Application theme", 
                    str, SettingsCategory.UI, options=["dark", "light", "auto"]),
        SettingField("ui.window_size", "Window Size", "Default window dimensions [width, height]", 
                    list, SettingsCategory.UI),
        SettingField("ui.font_size", "Font Size", "Base font size", 
                    int, SettingsCategory.UI, min_value=8, max_value=24),
        SettingField("ui.font_family", "Font Family", "UI font", 
                    str, SettingsCategory.UI),
        SettingField("ui.auto_approve_high_confidence", "Auto-Approve High Confidence", 
                    "Automatically approve requests above threshold", bool, SettingsCategory.UI),
        SettingField("ui.confidence_threshold", "Confidence Threshold", 
                    "Minimum confidence for auto-approval", 
                    float, SettingsCategory.UI, min_value=0.0, max_value=1.0),
        SettingField("ui.show_reasoning_steps", "Show Reasoning Steps", 
                    "Display AI reasoning process", bool, SettingsCategory.UI),
        SettingField("ui.enable_sound_notifications", "Sound Notifications", 
                    "Play sounds for events", bool, SettingsCategory.UI),
        
        # Processing settings
        SettingField("processing.confidence_threshold", "Processing Confidence", 
                    "Minimum confidence to process requests", 
                    float, SettingsCategory.PROCESSING, min_value=0.0, max_value=1.0),
        SettingField("processing.max_processing_time", "Max Processing Time", 
                    "Maximum seconds for processing", 
                    int, SettingsCategory.PROCESSING, min_value=10, max_value=300),
        SettingField("processing.enable_caching", "Enable Caching", 
                    "Cache API responses", bool, SettingsCategory.PROCESSING),
        SettingField("processing.cache_ttl", "Cache TTL (seconds)", 
                    "Cache time to live", 
                    int, SettingsCategory.PROCESSING, min_value=60, max_value=86400),
        
        # Keyboard shortcuts
        SettingField("keyboard_shortcuts.approve", "Approve", "Approve request shortcut", 
                    str, SettingsCategory.SHORTCUTS),
        SettingField("keyboard_shortcuts.edit_approve", "Edit & Approve", "Edit and approve shortcut", 
                    str, SettingsCategory.SHORTCUTS),
        SettingField("keyboard_shortcuts.regenerate", "Regenerate", "Regenerate request shortcut", 
                    str, SettingsCategory.SHORTCUTS),
        SettingField("keyboard_shortcuts.reject", "Reject", "Reject request shortcut", 
                    str, SettingsCategory.SHORTCUTS),
        SettingField("keyboard_shortcuts.cancel", "Cancel", "Cancel operation shortcut", 
                    str, SettingsCategory.SHORTCUTS),
        
        # Logging settings
        SettingField("logging.level", "Log Level", "Minimum log level to record", 
                    str, SettingsCategory.LOGGING, 
                    options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
        SettingField("logging.file_path", "Log File Path", "Path to log file", 
                    str, SettingsCategory.LOGGING),
        SettingField("logging.max_file_size", "Max File Size", "Maximum log file size", 
                    str, SettingsCategory.LOGGING),
        SettingField("logging.backup_count", "Backup Count", "Number of log backups to keep", 
                    int, SettingsCategory.LOGGING, min_value=1, max_value=20),
        SettingField("logging.audit_enabled", "Enable Audit Logging", 
                    "Log all configuration changes", bool, SettingsCategory.LOGGING),
        SettingField("logging.log_to_console", "Log to Console", 
                    "Also display logs in console", bool, SettingsCategory.LOGGING),
        
        # Advanced settings
        SettingField("enable_hot_reload", "Hot Reload", 
                    "Automatically reload configuration changes", 
                    bool, SettingsCategory.ADVANCED, requires_restart=True),
        SettingField("enable_auto_backup", "Auto Backup", 
                    "Automatically backup configuration", 
                    bool, SettingsCategory.ADVANCED),
    ]
    
    def __init__(
        self,
        parent,
        config_manager: ConfigManager,
        on_save: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.on_save = on_save
        self.logger = logging.getLogger(__name__)
        
        # Load current configuration
        self.current_config = config_manager.load_config()
        self.original_config = self.current_config.model_dump()
        self.modified_config = self.original_config.copy()
        
        # Setup dialog
        self.title("ComBadge Settings")
        self.geometry("900x700")
        self.transient(parent)
        
        # Initialize UI components
        self.category_tabs = {}
        self.has_changes = False
        
        self._setup_ui()
        self._populate_fields()
        
        # Make dialog modal
        self.grab_set()
    
    def _setup_ui(self):
        """Setup the settings dialog UI"""
        # Main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(self, height=60)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.grid_propagate(False)
        header_frame.grid_columnconfigure(0, weight=1)
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="Application Settings",
            font=CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, pady=15)
        
        # Hot reload indicator
        self._create_status_indicator(header_frame)
        
        # Tab view for categories
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Create tabs for each category
        for category in SettingsCategory:
            tab = self.tabview.add(category.value)
            
            # Get fields for this category
            category_fields = [f for f in self.SETTING_FIELDS if f.category == category]
            
            if category_fields:
                category_tab = SettingsCategoryTab(tab, category, category_fields, self.modified_config)
                category_tab.pack(fill="both", expand=True)
                self.category_tabs[category] = category_tab
        
        # Footer with action buttons
        footer_frame = ctk.CTkFrame(self, height=80)
        footer_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        footer_frame.grid_propagate(False)
        footer_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # Import/Export buttons
        import_btn = ctk.CTkButton(
            footer_frame,
            text="📥 Import",
            command=self._import_config,
            height=35,
            font=CTkFont(size=12)
        )
        import_btn.grid(row=0, column=0, padx=5, pady=10, sticky="ew")
        
        export_btn = ctk.CTkButton(
            footer_frame,
            text="📤 Export",
            command=self._export_config,
            height=35,
            font=CTkFont(size=12)
        )
        export_btn.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        
        # Reset button
        reset_btn = ctk.CTkButton(
            footer_frame,
            text="🔄 Reset to Defaults",
            command=self._reset_to_defaults,
            height=35,
            font=CTkFont(size=12),
            fg_color="#FF5722"
        )
        reset_btn.grid(row=0, column=2, padx=5, pady=10, sticky="ew")
        
        # Spacer
        spacer = ctk.CTkFrame(footer_frame, fg_color="transparent", width=50)
        spacer.grid(row=0, column=3, sticky="ew")
        
        # Apply and Cancel buttons
        self.apply_btn = ctk.CTkButton(
            footer_frame,
            text="✓ Apply",
            command=self._apply_changes,
            height=40,
            font=CTkFont(size=12, weight="bold"),
            fg_color="#4CAF50"
        )
        self.apply_btn.grid(row=0, column=4, padx=5, pady=10, sticky="ew")
        
        cancel_btn = ctk.CTkButton(
            footer_frame,
            text="✗ Cancel",
            command=self.destroy,
            height=40,
            font=CTkFont(size=12, weight="bold"),
            fg_color="#757575"
        )
        cancel_btn.grid(row=0, column=5, padx=5, pady=10, sticky="ew")
        
        # Preview button
        preview_btn = ctk.CTkButton(
            footer_frame,
            text="👁 Preview Changes",
            command=self._preview_changes,
            height=30,
            font=CTkFont(size=11),
            fg_color="#2196F3"
        )
        preview_btn.grid(row=1, column=4, columnspan=2, padx=5, pady=(0, 10), sticky="ew")
        
        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_status_indicator(self, parent):
        """Create hot reload status indicator"""
        status_frame = ctk.CTkFrame(parent, fg_color="transparent")
        status_frame.grid(row=0, column=1, padx=20, pady=15)
        
        # Status dot
        self.status_dot = ctk.CTkLabel(
            status_frame,
            text="●",
            font=CTkFont(size=12),
            text_color="#4CAF50" if self.current_config.enable_hot_reload else "#757575"
        )
        self.status_dot.pack(side="left", padx=(0, 5))
        
        # Status text
        status_text = "Hot Reload Active" if self.current_config.enable_hot_reload else "Hot Reload Inactive"
        self.status_label = ctk.CTkLabel(
            status_frame,
            text=status_text,
            font=CTkFont(size=10)
        )
        self.status_label.pack(side="left")
    
    def _populate_fields(self):
        """Populate all fields with current configuration values"""
        # Fields are populated in SettingsCategoryTab __init__
        pass
    
    def _collect_changes(self) -> Dict[str, Any]:
        """Collect all changes from UI widgets"""
        changes = {}
        
        for category, tab in self.category_tabs.items():
            category_values = tab.get_values()
            
            for key, value in category_values.items():
                # Convert flat key to nested structure
                parts = key.split('.')
                current = changes
                
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                current[parts[-1]] = value
        
        return changes
    
    def _preview_changes(self):
        """Show preview of configuration changes"""
        changes = self._collect_changes()
        
        # Compare with original config
        differences = self._get_differences(self.original_config, changes)
        
        if not differences:
            self._show_info("No Changes", "No configuration changes have been made.")
            return
        
        # Create preview dialog
        preview_dialog = ctk.CTkToplevel(self)
        preview_dialog.title("Configuration Changes Preview")
        preview_dialog.geometry("600x400")
        preview_dialog.transient(self)
        preview_dialog.grab_set()
        
        # Title
        title_label = ctk.CTkLabel(
            preview_dialog,
            text="Configuration Changes",
            font=CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=10)
        
        # Changes text area
        changes_text = ctk.CTkTextbox(preview_dialog, height=300)
        changes_text.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Format changes
        formatted_changes = self._format_differences(differences)
        changes_text.insert("0.0", formatted_changes)
        changes_text.configure(state="disabled")
        
        # Close button
        close_btn = ctk.CTkButton(
            preview_dialog,
            text="Close",
            command=preview_dialog.destroy
        )
        close_btn.pack(pady=10)
    
    def _get_differences(self, original: Dict[str, Any], modified: Dict[str, Any], prefix: str = "") -> List[Tuple[str, Any, Any]]:
        """Get differences between original and modified config"""
        differences = []
        
        all_keys = set(original.keys()) | set(modified.keys())
        
        for key in all_keys:
            current_path = f"{prefix}.{key}" if prefix else key
            
            if key not in original:
                differences.append((current_path, None, modified[key]))
            elif key not in modified:
                differences.append((current_path, original[key], None))
            elif isinstance(original[key], dict) and isinstance(modified[key], dict):
                nested_diff = self._get_differences(original[key], modified[key], current_path)
                differences.extend(nested_diff)
            elif original[key] != modified[key]:
                differences.append((current_path, original[key], modified[key]))
        
        return differences
    
    def _format_differences(self, differences: List[Tuple[str, Any, Any]]) -> str:
        """Format differences for display"""
        lines = []
        
        for path, old_value, new_value in differences:
            if old_value is None:
                lines.append(f"+ {path}: {new_value}")
            elif new_value is None:
                lines.append(f"- {path}: {old_value}")
            else:
                lines.append(f"  {path}: {old_value} → {new_value}")
        
        return "\n".join(lines)
    
    def _apply_changes(self):
        """Apply configuration changes"""
        try:
            # Collect changes
            changes = self._collect_changes()
            
            # Validate changes
            temp_config = self.original_config.copy()
            self.config_manager._deep_merge(temp_config, changes)
            
            errors = self.config_manager.validate_config(temp_config)
            if errors:
                self._show_error("Validation Error", "\n".join(errors))
                return
            
            # Check for changes requiring restart
            restart_required = self._check_restart_required(changes)
            
            if restart_required:
                if not self._confirm_action(
                    "Restart Required",
                    "Some changes require application restart to take effect.\nApply changes anyway?"
                ):
                    return
            
            # Apply changes
            self.config_manager.update_config(changes)
            
            # Call save callback if provided
            if self.on_save:
                self.on_save(changes)
            
            self.logger.info("Configuration changes applied successfully")
            
            if restart_required:
                self._show_info(
                    "Changes Applied",
                    "Configuration changes have been applied.\nPlease restart the application for all changes to take effect."
                )
            else:
                self._show_info("Changes Applied", "Configuration changes have been applied successfully.")
            
            # Close dialog
            self.destroy()
            
        except Exception as e:
            self.logger.error(f"Failed to apply configuration changes: {e}")
            self._show_error("Error", f"Failed to apply changes: {str(e)}")
    
    def _check_restart_required(self, changes: Dict[str, Any]) -> bool:
        """Check if any changes require restart"""
        restart_fields = [f.key for f in self.SETTING_FIELDS if f.requires_restart]
        
        def check_nested(config_dict: Dict[str, Any], prefix: str = "") -> bool:
            for key, value in config_dict.items():
                current_path = f"{prefix}.{key}" if prefix else key
                
                if current_path in restart_fields:
                    # Check if value actually changed
                    original_value = self._get_nested_value(self.original_config, current_path)
                    if original_value != value:
                        return True
                
                if isinstance(value, dict):
                    if check_nested(value, current_path):
                        return True
            
            return False
        
        return check_nested(changes)
    
    def _get_nested_value(self, config: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        parts = path.split('.')
        current = config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def _reset_to_defaults(self):
        """Reset all settings to defaults"""
        if not self._confirm_action(
            "Reset to Defaults",
            "Are you sure you want to reset all settings to defaults?\nThis action cannot be undone."
        ):
            return
        
        try:
            # Get default configuration
            default_config = AppConfig()
            defaults = default_config.model_dump()
            
            # Reset all tabs
            for category, tab in self.category_tabs.items():
                tab.reset_to_defaults(defaults)
            
            self._show_info("Reset Complete", "All settings have been reset to defaults.")
            
        except Exception as e:
            self.logger.error(f"Failed to reset to defaults: {e}")
            self._show_error("Error", f"Failed to reset to defaults: {str(e)}")
    
    def _import_config(self):
        """Import configuration from file"""
        from tkinter import filedialog
        
        file_path = filedialog.askopenfilename(
            title="Import Configuration",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            if self.config_manager.import_config(Path(file_path)):
                # Reload configuration
                self.current_config = self.config_manager.load_config()
                self.original_config = self.current_config.model_dump()
                
                # Refresh UI
                self._refresh_ui()
                
                self._show_info("Import Successful", "Configuration imported successfully.")
            else:
                self._show_error("Import Failed", "Failed to import configuration file.")
                
        except Exception as e:
            self.logger.error(f"Failed to import configuration: {e}")
            self._show_error("Import Error", f"Failed to import configuration: {str(e)}")
    
    def _export_config(self):
        """Export configuration to file"""
        from tkinter import filedialog
        
        file_path = filedialog.asksaveasfilename(
            title="Export Configuration",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            include_sensitive = self._confirm_action(
                "Export Sensitive Data",
                "Include sensitive data (passwords, API keys) in export?"
            )
            
            if self.config_manager.export_config(Path(file_path), include_sensitive):
                self._show_info("Export Successful", f"Configuration exported to:\n{file_path}")
            else:
                self._show_error("Export Failed", "Failed to export configuration.")
                
        except Exception as e:
            self.logger.error(f"Failed to export configuration: {e}")
            self._show_error("Export Error", f"Failed to export configuration: {str(e)}")
    
    def _refresh_ui(self):
        """Refresh UI with current configuration"""
        # Recreate tabs with new config
        for widget in self.tabview.winfo_children():
            widget.destroy()
        
        self.category_tabs.clear()
        self._populate_fields()
    
    def _on_close(self):
        """Handle dialog close event"""
        # Check for unsaved changes
        changes = self._collect_changes()
        differences = self._get_differences(self.original_config, changes)
        
        if differences:
            if self._confirm_action(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to discard them?"
            ):
                self.destroy()
        else:
            self.destroy()
    
    def _confirm_action(self, title: str, message: str) -> bool:
        """Show confirmation dialog"""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()
        
        result = {"confirmed": False}
        
        # Message
        msg_label = ctk.CTkLabel(
            dialog,
            text=message,
            font=CTkFont(size=12),
            wraplength=350
        )
        msg_label.pack(pady=20)
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        yes_btn = ctk.CTkButton(
            btn_frame,
            text="Yes",
            command=lambda: [result.update({"confirmed": True}), dialog.destroy()],
            width=80
        )
        yes_btn.pack(side="left", padx=5)
        
        no_btn = ctk.CTkButton(
            btn_frame,
            text="No",
            command=dialog.destroy,
            width=80
        )
        no_btn.pack(side="left", padx=5)
        
        dialog.wait_window()
        return result["confirmed"]
    
    def _show_info(self, title: str, message: str):
        """Show information dialog"""
        self._show_message(title, message, "info")
    
    def _show_error(self, title: str, message: str):
        """Show error dialog"""
        self._show_message(title, message, "error")
    
    def _show_message(self, title: str, message: str, msg_type: str = "info"):
        """Show message dialog"""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()
        
        # Icon and color based on type
        if msg_type == "error":
            icon = "❌"
            color = "#F44336"
        else:
            icon = "ℹ️"
            color = "#2196F3"
        
        # Icon label
        icon_label = ctk.CTkLabel(
            dialog,
            text=icon,
            font=CTkFont(size=32)
        )
        icon_label.pack(pady=(20, 10))
        
        # Message
        msg_label = ctk.CTkLabel(
            dialog,
            text=message,
            font=CTkFont(size=12),
            wraplength=350
        )
        msg_label.pack(pady=10)
        
        # OK button
        ok_btn = ctk.CTkButton(
            dialog,
            text="OK",
            command=dialog.destroy,
            fg_color=color
        )
        ok_btn.pack(pady=20)