"""
Edit Interface Component for ComBadge Approval Workflow

Provides inline editing capabilities for API requests with JSON syntax highlighting,
field validation, real-time error checking, and auto-complete functionality.
"""

import json
import re
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass
from enum import Enum

import customtkinter as ctk
from customtkinter import CTkFont


class ValidationSeverity(Enum):
    """Severity levels for validation errors"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Represents a validation result"""
    field: str
    severity: ValidationSeverity
    message: str
    suggestion: Optional[str] = None


@dataclass
class FieldDefinition:
    """Definition of an editable field"""
    name: str
    label: str
    field_type: type
    required: bool = False
    description: str = ""
    validation_pattern: Optional[str] = None
    options: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class FieldValidator:
    """Validates individual fields based on their definitions"""
    
    # Common validation patterns
    PATTERNS = {
        'vehicle_id': r'^[A-Z]{2,4}[-]?[0-9]{3,6}$',
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'phone': r'^[\+]?[1-9][\d]{0,15}$',
        'date': r'^\d{4}-\d{2}-\d{2}$',
        'datetime': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
        'time': r'^\d{2}:\d{2}(:\d{2})?$',
        'vin': r'^[A-HJ-NPR-Z0-9]{17}$',
        'license_plate': r'^[A-Z0-9-]{2,10}$'
    }
    
    # Field definitions for common fleet management fields
    FIELD_DEFINITIONS = {
        # Vehicle fields
        'vehicle_id': FieldDefinition('vehicle_id', 'Vehicle ID', str, True, 
                                     'Unique vehicle identifier', PATTERNS['vehicle_id']),
        'make': FieldDefinition('make', 'Make', str, True, 'Vehicle manufacturer'),
        'model': FieldDefinition('model', 'Model', str, True, 'Vehicle model'),
        'year': FieldDefinition('year', 'Year', int, True, 'Model year', 
                               min_value=2000, max_value=2025),
        'vin': FieldDefinition('vin', 'VIN', str, False, 
                              'Vehicle Identification Number', PATTERNS['vin']),
        'license_plate': FieldDefinition('license_plate', 'License Plate', str, True,
                                        'Vehicle license plate', PATTERNS['license_plate']),
        
        # User fields
        'user_id': FieldDefinition('user_id', 'User ID', str, True, 'User identifier'),
        'assigned_driver': FieldDefinition('assigned_driver', 'Assigned Driver', str, False,
                                          'Driver assigned to vehicle'),
        
        # Date/time fields
        'requested_date': FieldDefinition('requested_date', 'Requested Date', str, True,
                                         'Date in YYYY-MM-DD format', PATTERNS['date']),
        'start_datetime': FieldDefinition('start_datetime', 'Start Date/Time', str, True,
                                         'Start date and time in ISO format', PATTERNS['datetime']),
        'end_datetime': FieldDefinition('end_datetime', 'End Date/Time', str, False,
                                       'End date and time in ISO format', PATTERNS['datetime']),
        
        # Enum fields
        'maintenance_type': FieldDefinition('maintenance_type', 'Maintenance Type', str, True,
                                           'Type of maintenance service', 
                                           options=['oil_change', 'tire_rotation', 'brake_service',
                                                   'transmission', 'engine', 'electrical', 'inspection']),
        'priority': FieldDefinition('priority', 'Priority', str, False,
                                   'Service priority level',
                                   options=['low', 'normal', 'high', 'urgent', 'emergency']),
        'status': FieldDefinition('status', 'Status', str, False,
                                 'Current status',
                                 options=['active', 'inactive', 'pending', 'completed', 'cancelled']),
        
        # Numeric fields
        'passenger_count': FieldDefinition('passenger_count', 'Passenger Count', int, False,
                                          'Number of passengers', min_value=1, max_value=8),
        'estimated_duration': FieldDefinition('estimated_duration', 'Duration (hours)', float, False,
                                             'Estimated duration in hours', min_value=0.5, max_value=24),
        'mileage': FieldDefinition('mileage', 'Mileage', int, False,
                                  'Vehicle mileage', min_value=0, max_value=999999),
        
        # Text fields
        'description': FieldDefinition('description', 'Description', str, False,
                                      'Detailed description'),
        'purpose': FieldDefinition('purpose', 'Purpose', str, False,
                                  'Purpose or reason'),
        'destination': FieldDefinition('destination', 'Destination', str, False,
                                      'Destination address or location'),
        'notes': FieldDefinition('notes', 'Notes', str, False,
                                'Additional notes or comments')
    }
    
    @classmethod
    def validate_field(cls, field_name: str, value: Any) -> List[ValidationResult]:
        """Validate a single field value"""
        results = []
        
        # Get field definition
        field_def = cls.FIELD_DEFINITIONS.get(field_name)
        if not field_def:
            # Unknown field - just basic validation
            if value is None or (isinstance(value, str) and not value.strip()):
                results.append(ValidationResult(
                    field_name, ValidationSeverity.INFO,
                    f"Unknown field '{field_name}' - no validation rules available"
                ))
            return results
        
        # Check if required field is missing
        if field_def.required and (value is None or (isinstance(value, str) and not value.strip())):
            results.append(ValidationResult(
                field_name, ValidationSeverity.ERROR,
                f"Required field '{field_def.label}' cannot be empty"
            ))
            return results
        
        # Skip validation if value is empty and field is optional
        if value is None or (isinstance(value, str) and not value.strip()):
            return results
        
        # Type validation
        if not isinstance(value, field_def.field_type):
            try:
                # Try to convert
                if field_def.field_type == int:
                    value = int(value)
                elif field_def.field_type == float:
                    value = float(value)
                elif field_def.field_type == str:
                    value = str(value)
                else:
                    results.append(ValidationResult(
                        field_name, ValidationSeverity.ERROR,
                        f"Field '{field_def.label}' must be of type {field_def.field_type.__name__}"
                    ))
                    return results
            except (ValueError, TypeError):
                results.append(ValidationResult(
                    field_name, ValidationSeverity.ERROR,
                    f"Field '{field_def.label}' must be of type {field_def.field_type.__name__}"
                ))
                return results
        
        # Pattern validation
        if field_def.validation_pattern and isinstance(value, str):
            if not re.match(field_def.validation_pattern, value):
                results.append(ValidationResult(
                    field_name, ValidationSeverity.ERROR,
                    f"Field '{field_def.label}' does not match the required format",
                    cls._get_pattern_suggestion(field_name)
                ))
        
        # Options validation
        if field_def.options and value not in field_def.options:
            results.append(ValidationResult(
                field_name, ValidationSeverity.ERROR,
                f"Field '{field_def.label}' must be one of: {', '.join(map(str, field_def.options))}"
            ))
        
        # Numeric range validation
        if isinstance(value, (int, float)):
            if field_def.min_value is not None and value < field_def.min_value:
                results.append(ValidationResult(
                    field_name, ValidationSeverity.ERROR,
                    f"Field '{field_def.label}' must be at least {field_def.min_value}"
                ))
            
            if field_def.max_value is not None and value > field_def.max_value:
                results.append(ValidationResult(
                    field_name, ValidationSeverity.ERROR,
                    f"Field '{field_def.label}' must be at most {field_def.max_value}"
                ))
        
        return results
    
    @classmethod
    def _get_pattern_suggestion(cls, field_name: str) -> str:
        """Get suggestion text for pattern validation failures"""
        suggestions = {
            'vehicle_id': 'Format: ABC123 or ABC-123',
            'email': 'Format: user@domain.com',
            'date': 'Format: YYYY-MM-DD (e.g., 2024-03-15)',
            'datetime': 'Format: YYYY-MM-DDTHH:MM:SS (e.g., 2024-03-15T14:30:00)',
            'time': 'Format: HH:MM (e.g., 14:30)',
            'vin': 'Format: 17 characters, no I, O, or Q',
            'license_plate': 'Format: 2-10 characters, letters and numbers'
        }
        
        for pattern_name, suggestion in suggestions.items():
            if pattern_name in field_name or field_name in pattern_name:
                return suggestion
        
        return 'Please check the format requirements'


class FieldEditor(ctk.CTkFrame):
    """Individual field editor with validation"""
    
    def __init__(
        self,
        parent,
        field_name: str,
        field_value: Any,
        on_change: Callable[[str, Any], None],
        field_def: Optional[FieldDefinition] = None
    ):
        super().__init__(parent)
        
        self.field_name = field_name
        self.field_value = field_value
        self.on_change = on_change
        self.field_def = field_def or FieldValidator.FIELD_DEFINITIONS.get(field_name)
        
        self.validation_results = []
        self.widget = None
        
        self._setup_ui()
        self._validate()
    
    def _setup_ui(self):
        """Setup the field editor UI"""
        self.grid_columnconfigure(1, weight=1)
        
        # Field label
        label_text = self.field_def.label if self.field_def else self.field_name.replace('_', ' ').title()
        if self.field_def and self.field_def.required:
            label_text += " *"
        
        self.label = ctk.CTkLabel(
            self,
            text=label_text,
            font=CTkFont(size=12, weight="bold"),
            width=120
        )
        self.label.grid(row=0, column=0, sticky="nw", padx=5, pady=5)
        
        # Field input widget
        self._create_input_widget()
        
        # Validation feedback
        self.validation_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.validation_frame.grid(row=0, column=2, sticky="nw", padx=5, pady=5)
        
        # Help text
        if self.field_def and self.field_def.description:
            self.help_label = ctk.CTkLabel(
                self,
                text=self.field_def.description,
                font=CTkFont(size=10),
                text_color="gray",
                wraplength=300
            )
            self.help_label.grid(row=1, column=1, sticky="w", padx=5, pady=(0, 5))
    
    def _create_input_widget(self):
        """Create the appropriate input widget based on field type"""
        if not self.field_def:
            # Generic text entry
            self.widget = ctk.CTkEntry(self, width=200)
            self.widget.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
            self.widget.insert(0, str(self.field_value) if self.field_value is not None else "")
            self.widget.bind("<KeyRelease>", self._on_text_change)
            return
        
        if self.field_def.options:
            # Dropdown for fields with predefined options
            self.widget = ctk.CTkComboBox(
                self,
                values=self.field_def.options,
                command=self._on_combobox_change,
                width=200
            )
            self.widget.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
            if self.field_value in self.field_def.options:
                self.widget.set(str(self.field_value))
        
        elif self.field_def.field_type == bool:
            # Checkbox for boolean fields
            self.widget = ctk.CTkCheckBox(
                self,
                text="",
                command=self._on_checkbox_change
            )
            self.widget.grid(row=0, column=1, sticky="w", padx=5, pady=5)
            if self.field_value:
                self.widget.select()
        
        elif self.field_name in ['description', 'notes', 'purpose']:
            # Text area for long text fields
            self.widget = ctk.CTkTextbox(self, height=80, width=200)
            self.widget.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
            self.widget.insert("0.0", str(self.field_value) if self.field_value is not None else "")
            self.widget.bind("<KeyRelease>", self._on_text_change)
        
        else:
            # Regular entry for other fields
            self.widget = ctk.CTkEntry(self, width=200)
            self.widget.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
            self.widget.insert(0, str(self.field_value) if self.field_value is not None else "")
            self.widget.bind("<KeyRelease>", self._on_text_change)
            
            # Add auto-complete for known fields
            self._setup_autocomplete()
    
    def _setup_autocomplete(self):
        """Setup auto-complete functionality"""
        # Auto-complete suggestions for specific fields
        suggestions = {
            'make': ['Toyota', 'Honda', 'Ford', 'Chevrolet', 'Nissan', 'BMW', 'Mercedes', 'Audi'],
            'assigned_driver': [],  # Could be populated from user database
            'destination': []       # Could be populated from common locations
        }
        
        if self.field_name in suggestions and suggestions[self.field_name]:
            # Could implement a dropdown suggestion list here
            pass
    
    def _on_text_change(self, event=None):
        """Handle text input changes"""
        if hasattr(self.widget, 'get'):
            if isinstance(self.widget, ctk.CTkTextbox):
                value = self.widget.get("0.0", "end-1c")
            else:
                value = self.widget.get()
        else:
            return
        
        # Convert value to appropriate type
        converted_value = self._convert_value(value)
        self.field_value = converted_value
        
        # Validate and update
        self._validate()
        self.on_change(self.field_name, converted_value)
    
    def _on_combobox_change(self, value):
        """Handle combobox selection changes"""
        converted_value = self._convert_value(value)
        self.field_value = converted_value
        self._validate()
        self.on_change(self.field_name, converted_value)
    
    def _on_checkbox_change(self):
        """Handle checkbox state changes"""
        value = self.widget.get()
        self.field_value = value
        self._validate()
        self.on_change(self.field_name, value)
    
    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type"""
        if not self.field_def:
            return value
        
        if not value.strip():
            return None
        
        try:
            if self.field_def.field_type == int:
                return int(value)
            elif self.field_def.field_type == float:
                return float(value)
            elif self.field_def.field_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            else:
                return value
        except (ValueError, TypeError):
            return value  # Return original if conversion fails
    
    def _validate(self):
        """Validate the current field value"""
        self.validation_results = FieldValidator.validate_field(self.field_name, self.field_value)
        self._update_validation_display()
    
    def _update_validation_display(self):
        """Update the validation feedback display"""
        # Clear existing validation widgets
        for widget in self.validation_frame.winfo_children():
            widget.destroy()
        
        if not self.validation_results:
            # Show checkmark for valid fields
            valid_label = ctk.CTkLabel(
                self.validation_frame,
                text="✓",
                font=CTkFont(size=14, weight="bold"),
                text_color="#4CAF50"
            )
            valid_label.pack()
            return
        
        # Show validation errors/warnings
        for i, result in enumerate(self.validation_results):
            color = {
                ValidationSeverity.ERROR: "#F44336",
                ValidationSeverity.WARNING: "#FF9800",
                ValidationSeverity.INFO: "#2196F3"
            }[result.severity]
            
            symbol = {
                ValidationSeverity.ERROR: "✗",
                ValidationSeverity.WARNING: "⚠",
                ValidationSeverity.INFO: "ℹ"
            }[result.severity]
            
            error_label = ctk.CTkLabel(
                self.validation_frame,
                text=symbol,
                font=CTkFont(size=12, weight="bold"),
                text_color=color
            )
            error_label.pack()
            
            # Show tooltip with error message on hover
            self._create_tooltip(error_label, result.message)
    
    def _create_tooltip(self, widget, text):
        """Create tooltip for widget"""
        def show_tooltip(event):
            tooltip = ctk.CTkToplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = ctk.CTkLabel(
                tooltip,
                text=text,
                font=CTkFont(size=10),
                wraplength=300
            )
            label.pack()
            
            widget.tooltip = tooltip
        
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
    
    def get_validation_results(self) -> List[ValidationResult]:
        """Get current validation results"""
        return self.validation_results
    
    def has_errors(self) -> bool:
        """Check if field has validation errors"""
        return any(result.severity == ValidationSeverity.ERROR for result in self.validation_results)


class EditInterface(ctk.CTkFrame):
    """
    Complete editing interface for API requests.
    
    Features:
    - Field-by-field editing with validation
    - JSON editor with syntax highlighting
    - Real-time error checking
    - Auto-complete functionality
    - Undo/redo capabilities
    """
    
    def __init__(
        self,
        parent,
        request_data: Dict[str, Any],
        on_save: Callable[[Dict[str, Any]], None],
        on_cancel: Callable[[], None]
    ):
        super().__init__(parent)
        
        self.original_data = request_data.copy()
        self.current_data = request_data.copy()
        self.on_save = on_save
        self.on_cancel = on_cancel
        
        self.field_editors = {}
        self.edit_mode = "fields"  # "fields" or "json"
        self.has_unsaved_changes = False
        
        # Undo/redo functionality
        self.edit_history = [self.current_data.copy()]
        self.history_index = 0
        
        self._setup_ui()
        self._populate_fields()
    
    def _setup_ui(self):
        """Setup the edit interface UI"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header with mode toggle
        self.header_frame = ctk.CTkFrame(self, height=60)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_propagate(False)
        
        # Title
        title_label = ctk.CTkLabel(
            self.header_frame,
            text="Edit API Request",
            font=CTkFont(size=18, weight="bold")
        )
        title_label.grid(row=0, column=0, sticky="w", padx=15, pady=15)
        
        # Mode toggle buttons
        self.mode_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.mode_frame.grid(row=0, column=1, padx=15, pady=15)
        
        self.fields_btn = ctk.CTkButton(
            self.mode_frame,
            text="📝 Field Editor",
            command=self._switch_to_fields_mode,
            height=30,
            font=CTkFont(size=12)
        )
        self.fields_btn.pack(side="left", padx=5)
        
        self.json_btn = ctk.CTkButton(
            self.mode_frame,
            text="🔧 JSON Editor",
            command=self._switch_to_json_mode,
            height=30,
            font=CTkFont(size=12),
            fg_color="#757575"
        )
        self.json_btn.pack(side="left", padx=5)
        
        # Content area
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Action buttons
        self.action_frame = ctk.CTkFrame(self, height=60)
        self.action_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        self.action_frame.grid_columnconfigure((0, 1), weight=1)
        self.action_frame.grid_propagate(False)
        
        self.save_btn = ctk.CTkButton(
            self.action_frame,
            text="💾 Save Changes",
            command=self._save_changes,
            fg_color="#4CAF50",
            height=40,
            font=CTkFont(size=12, weight="bold")
        )
        self.save_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.cancel_btn = ctk.CTkButton(
            self.action_frame,
            text="❌ Cancel",
            command=self.on_cancel,
            fg_color="#757575",
            height=40,
            font=CTkFont(size=12, weight="bold")
        )
        self.cancel_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Undo/Redo buttons
        self.undo_frame = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        self.undo_frame.grid(row=0, column=2, padx=10, pady=10)
        
        self.undo_btn = ctk.CTkButton(
            self.undo_frame,
            text="↶ Undo",
            command=self._undo,
            width=60,
            height=30,
            font=CTkFont(size=10)
        )
        self.undo_btn.pack(side="top", pady=2)
        
        self.redo_btn = ctk.CTkButton(
            self.undo_frame,
            text="↷ Redo",
            command=self._redo,
            width=60,
            height=30,
            font=CTkFont(size=10)
        )
        self.redo_btn.pack(side="top", pady=2)
        
        # Setup keyboard shortcuts
        self.bind_all("<Control-s>", lambda e: self._save_changes())
        self.bind_all("<Control-z>", lambda e: self._undo())
        self.bind_all("<Control-y>", lambda e: self._redo())
    
    def _populate_fields(self):
        """Populate the content area based on current mode"""
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        if self.edit_mode == "fields":
            self._create_fields_editor()
        else:
            self._create_json_editor()
    
    def _create_fields_editor(self):
        """Create the field-by-field editor"""
        # Create scrollable frame
        self.scroll_frame = ctk.CTkScrollableFrame(self.content_frame)
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Extract data fields
        data = self.current_data.get('data', {})
        
        row = 0
        self.field_editors = {}
        
        # Create editor for each field
        for field_name, field_value in data.items():
            field_editor = FieldEditor(
                self.scroll_frame,
                field_name,
                field_value,
                self._on_field_change
            )
            field_editor.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
            
            self.field_editors[field_name] = field_editor
            row += 1
        
        # Add new field button
        add_field_btn = ctk.CTkButton(
            self.scroll_frame,
            text="+ Add Field",
            command=self._add_new_field,
            height=30,
            font=CTkFont(size=11)
        )
        add_field_btn.grid(row=row, column=0, pady=10)
        
        # Validation summary
        self._create_validation_summary(row + 1)
    
    def _create_json_editor(self):
        """Create the JSON editor"""
        # JSON text area
        self.json_text = ctk.CTkTextbox(
            self.content_frame,
            font=CTkFont(family="Courier", size=11),
            wrap="none"
        )
        self.json_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Insert current data as JSON
        try:
            json_str = json.dumps(self.current_data, indent=2)
        except (TypeError, ValueError):
            json_str = str(self.current_data)
        
        self.json_text.insert("0.0", json_str)
        
        # Apply syntax highlighting
        from .request_preview import SyntaxHighlighter
        SyntaxHighlighter.highlight_json(self.json_text, json_str)
        
        # Bind change events
        self.json_text.bind("<KeyRelease>", self._on_json_change)
        
        # JSON validation status
        self.json_validation_frame = ctk.CTkFrame(self.content_frame)
        self.json_validation_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        self._validate_json()
    
    def _create_validation_summary(self, row: int):
        """Create validation summary section"""
        validation_frame = ctk.CTkFrame(self.scroll_frame)
        validation_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=10)
        validation_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            validation_frame,
            text="Validation Summary",
            font=CTkFont(size=14, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        
        # Get all validation results
        all_results = []
        for field_editor in self.field_editors.values():
            all_results.extend(field_editor.get_validation_results())
        
        if not all_results:
            # All valid
            valid_label = ctk.CTkLabel(
                validation_frame,
                text="✓ All fields are valid",
                font=CTkFont(size=12),
                text_color="#4CAF50"
            )
            valid_label.grid(row=1, column=0, sticky="w", padx=15, pady=5)
        else:
            # Show errors and warnings
            errors = [r for r in all_results if r.severity == ValidationSeverity.ERROR]
            warnings = [r for r in all_results if r.severity == ValidationSeverity.WARNING]
            
            if errors:
                error_label = ctk.CTkLabel(
                    validation_frame,
                    text=f"✗ {len(errors)} error(s) found",
                    font=CTkFont(size=12),
                    text_color="#F44336"
                )
                error_label.grid(row=1, column=0, sticky="w", padx=15, pady=2)
                
                # Disable save button if there are errors
                self.save_btn.configure(state="disabled")
            else:
                # Enable save button if no errors
                self.save_btn.configure(state="normal")
            
            if warnings:
                warning_label = ctk.CTkLabel(
                    validation_frame,
                    text=f"⚠ {len(warnings)} warning(s)",
                    font=CTkFont(size=12),
                    text_color="#FF9800"
                )
                warning_label.grid(row=2, column=0, sticky="w", padx=15, pady=2)
    
    def _switch_to_fields_mode(self):
        """Switch to field editing mode"""
        if self.edit_mode == "json":
            # Save JSON changes first
            self._parse_json_changes()
        
        self.edit_mode = "fields"
        self.fields_btn.configure(fg_color="#2196F3")
        self.json_btn.configure(fg_color="#757575")
        self._populate_fields()
    
    def _switch_to_json_mode(self):
        """Switch to JSON editing mode"""
        self.edit_mode = "json"
        self.fields_btn.configure(fg_color="#757575")
        self.json_btn.configure(fg_color="#2196F3")
        self._populate_fields()
    
    def _on_field_change(self, field_name: str, value: Any):
        """Handle field value changes"""
        # Update current data
        if 'data' not in self.current_data:
            self.current_data['data'] = {}
        
        self.current_data['data'][field_name] = value
        self.has_unsaved_changes = True
        
        # Add to edit history
        self._add_to_history()
        
        # Update validation summary
        self.after_idle(lambda: self._update_validation_summary())
    
    def _on_json_change(self, event=None):
        """Handle JSON text changes"""
        self.has_unsaved_changes = True
        self.after_idle(lambda: self._validate_json())
    
    def _validate_json(self):
        """Validate JSON syntax"""
        json_text = self.json_text.get("0.0", "end-1c")
        
        # Clear existing validation
        for widget in self.json_validation_frame.winfo_children():
            widget.destroy()
        
        try:
            parsed_json = json.loads(json_text)
            # JSON is valid
            valid_label = ctk.CTkLabel(
                self.json_validation_frame,
                text="✓ Valid JSON",
                font=CTkFont(size=12),
                text_color="#4CAF50"
            )
            valid_label.pack(padx=10, pady=5)
            
            # Enable save button
            self.save_btn.configure(state="normal")
            
        except json.JSONDecodeError as e:
            # JSON is invalid
            error_label = ctk.CTkLabel(
                self.json_validation_frame,
                text=f"✗ JSON Error: {str(e)}",
                font=CTkFont(size=12),
                text_color="#F44336"
            )
            error_label.pack(padx=10, pady=5)
            
            # Disable save button
            self.save_btn.configure(state="disabled")
    
    def _parse_json_changes(self):
        """Parse changes from JSON editor"""
        json_text = self.json_text.get("0.0", "end-1c")
        try:
            self.current_data = json.loads(json_text)
            self._add_to_history()
        except json.JSONDecodeError:
            # Invalid JSON - don't update
            pass
    
    def _add_new_field(self):
        """Add a new field to the request"""
        # Show dialog to get field name and type
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New Field")
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()
        
        result = {"field_name": None, "field_value": None}
        
        # Field name entry
        name_label = ctk.CTkLabel(dialog, text="Field Name:")
        name_label.pack(pady=5)
        
        name_entry = ctk.CTkEntry(dialog)
        name_entry.pack(pady=5)
        name_entry.focus()
        
        # Initial value entry
        value_label = ctk.CTkLabel(dialog, text="Initial Value:")
        value_label.pack(pady=5)
        
        value_entry = ctk.CTkEntry(dialog)
        value_entry.pack(pady=5)
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        def add_field():
            field_name = name_entry.get().strip()
            field_value = value_entry.get().strip()
            
            if field_name:
                result["field_name"] = field_name
                result["field_value"] = field_value if field_value else ""
            dialog.destroy()
        
        add_btn = ctk.CTkButton(btn_frame, text="Add", command=add_field)
        add_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side="left", padx=5)
        
        dialog.wait_window()
        
        # Add the field if user provided a name
        if result["field_name"]:
            self._on_field_change(result["field_name"], result["field_value"])
            self._populate_fields()  # Refresh the field editor
    
    def _update_validation_summary(self):
        """Update the validation summary"""
        if self.edit_mode == "fields":
            # Re-create the validation summary
            # Find the validation summary and update it
            self._create_validation_summary(len(self.field_editors))
    
    def _add_to_history(self):
        """Add current state to edit history"""
        # Remove any future history if we're not at the end
        self.edit_history = self.edit_history[:self.history_index + 1]
        
        # Add new state
        self.edit_history.append(self.current_data.copy())
        self.history_index = len(self.edit_history) - 1
        
        # Limit history size
        if len(self.edit_history) > 50:
            self.edit_history = self.edit_history[-25:]  # Keep last 25
            self.history_index = len(self.edit_history) - 1
        
        self._update_undo_redo_buttons()
    
    def _undo(self):
        """Undo last change"""
        if self.history_index > 0:
            self.history_index -= 1
            self.current_data = self.edit_history[self.history_index].copy()
            self._populate_fields()
            self._update_undo_redo_buttons()
    
    def _redo(self):
        """Redo last undone change"""
        if self.history_index < len(self.edit_history) - 1:
            self.history_index += 1
            self.current_data = self.edit_history[self.history_index].copy()
            self._populate_fields()
            self._update_undo_redo_buttons()
    
    def _update_undo_redo_buttons(self):
        """Update undo/redo button states"""
        self.undo_btn.configure(state="normal" if self.history_index > 0 else "disabled")
        self.redo_btn.configure(state="normal" if self.history_index < len(self.edit_history) - 1 else "disabled")
    
    def _save_changes(self):
        """Save changes and call the save callback"""
        if self.edit_mode == "json":
            self._parse_json_changes()
        
        # Final validation
        if self._has_validation_errors():
            # Show error dialog
            error_dialog = ctk.CTkToplevel(self)
            error_dialog.title("Validation Errors")
            error_dialog.geometry("400x200")
            error_dialog.transient(self)
            error_dialog.grab_set()
            
            label = ctk.CTkLabel(
                error_dialog,
                text="Please fix validation errors before saving.",
                font=CTkFont(size=14)
            )
            label.pack(pady=20)
            
            ok_btn = ctk.CTkButton(error_dialog, text="OK", command=error_dialog.destroy)
            ok_btn.pack(pady=10)
            
            return
        
        # Save the changes
        self.on_save(self.current_data)
    
    def _has_validation_errors(self) -> bool:
        """Check if there are any validation errors"""
        if self.edit_mode == "fields":
            return any(editor.has_errors() for editor in self.field_editors.values())
        else:
            # Check JSON validity
            try:
                json.loads(self.json_text.get("0.0", "end-1c"))
                return False
            except json.JSONDecodeError:
                return True