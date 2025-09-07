"""
API Request Preview Component for ComBadge Approval Workflow

Displays generated API requests in both human-readable and technical formats
with collapsible JSON view and syntax highlighting.
"""

import json
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import customtkinter as ctk
from customtkinter import CTkFont


@dataclass
class RequestField:
    """Represents a field in the API request"""
    name: str
    value: Any
    field_type: str
    description: str = ""
    required: bool = False


class SyntaxHighlighter:
    """Simple JSON syntax highlighter for text widgets"""
    
    # Color scheme for JSON elements
    COLORS = {
        'string': '#008000',      # Green
        'number': '#0000FF',      # Blue  
        'boolean': '#800080',     # Purple
        'null': '#808080',        # Gray
        'key': '#800000',         # Dark red
        'punctuation': '#000000', # Black
        'brace': '#FF0000'        # Red
    }
    
    @classmethod
    def highlight_json(cls, text_widget, json_text: str):
        """Apply syntax highlighting to JSON text in a text widget"""
        try:
            # Clear existing tags
            for tag in text_widget.tag_names():
                if tag.startswith('syntax_'):
                    text_widget.tag_delete(tag)
            
            # Patterns for JSON elements
            patterns = [
                (r'"[^"]*":', 'key'),           # Keys
                (r'"[^"]*"', 'string'),         # String values
                (r'\b\d+\.?\d*\b', 'number'),   # Numbers
                (r'\b(true|false)\b', 'boolean'), # Booleans
                (r'\bnull\b', 'null'),          # Null
                (r'[{}[\]]', 'brace'),          # Braces and brackets
                (r'[,:;]', 'punctuation')       # Punctuation
            ]
            
            # Apply highlighting
            for pattern, tag in patterns:
                matches = re.finditer(pattern, json_text)
                for match in matches:
                    start_idx = f"1.0+{match.start()}c"
                    end_idx = f"1.0+{match.end()}c"
                    
                    tag_name = f"syntax_{tag}"
                    text_widget.tag_add(tag_name, start_idx, end_idx)
                    
                    if tag in cls.COLORS:
                        text_widget.tag_config(tag_name, foreground=cls.COLORS[tag])
                        
        except Exception as e:
            # If highlighting fails, just display plain text
            pass


class HumanReadableFormatter:
    """Formats API requests in human-readable format"""
    
    FIELD_LABELS = {
        # Vehicle fields
        'vehicle_id': 'Vehicle ID',
        'make': 'Make',
        'model': 'Model',
        'year': 'Year',
        'vin': 'VIN',
        'license_plate': 'License Plate',
        'assigned_driver': 'Assigned Driver',
        'assigned_department': 'Department',
        
        # Maintenance fields
        'maintenance_type': 'Service Type',
        'requested_date': 'Requested Date',
        'priority': 'Priority',
        'technician': 'Technician',
        'estimated_duration': 'Estimated Duration',
        
        # Reservation fields
        'user_id': 'Reserved By',
        'start_datetime': 'Start Time',
        'end_datetime': 'End Time',
        'purpose': 'Purpose',
        'destination': 'Destination',
        'passenger_count': 'Passengers',
        
        # Common fields
        'description': 'Description',
        'notes': 'Notes',
        'status': 'Status'
    }
    
    @classmethod
    def format_request(cls, request_data: Dict[str, Any]) -> str:
        """Format request data in human-readable format"""
        if not request_data:
            return "No request data available"
        
        formatted_lines = []
        
        # Extract endpoint info
        method = request_data.get('method', 'POST')
        endpoint = request_data.get('endpoint', '/api/unknown')
        
        formatted_lines.append(f"API Operation: {method} {endpoint}")
        formatted_lines.append("-" * 40)
        
        # Format request body
        data = request_data.get('data', {})
        if isinstance(data, dict):
            for key, value in data.items():
                label = cls.FIELD_LABELS.get(key, key.replace('_', ' ').title())
                formatted_value = cls._format_value(value)
                formatted_lines.append(f"{label}: {formatted_value}")
        
        # Format parameters
        params = request_data.get('params', {})
        if params:
            formatted_lines.append("\nQuery Parameters:")
            formatted_lines.append("-" * 20)
            for key, value in params.items():
                label = key.replace('_', ' ').title()
                formatted_lines.append(f"{label}: {value}")
        
        return "\n".join(formatted_lines)
    
    @classmethod
    def _format_value(cls, value: Any) -> str:
        """Format individual values for display"""
        if isinstance(value, bool):
            return "Yes" if value else "No"
        elif isinstance(value, list):
            if len(value) <= 3:
                return ", ".join(str(item) for item in value)
            else:
                return f"{', '.join(str(item) for item in value[:3])}... (+{len(value)-3} more)"
        elif isinstance(value, dict):
            return f"{{...}} ({len(value)} fields)"
        elif value is None:
            return "Not specified"
        else:
            return str(value)


class RequestPreview(ctk.CTkFrame):
    """
    API Request Preview Component
    
    Displays API requests in multiple formats:
    - Human-readable summary
    - Collapsible JSON view with syntax highlighting
    - Field-by-field breakdown
    - Request validation status
    """
    
    def __init__(self, parent, request_data: Dict[str, Any]):
        super().__init__(parent)
        
        self.request_data = request_data
        self.show_json = False
        
        self._setup_ui()
        self._populate_content()
    
    def _setup_ui(self):
        """Setup the request preview UI"""
        self.grid_columnconfigure(0, weight=1)
        
        # Header section
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="API Request Preview",
            font=CTkFont(size=18, weight="bold")
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        
        # View toggle buttons
        self.button_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.button_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        self.readable_btn = ctk.CTkButton(
            self.button_frame,
            text="📄 Human Readable",
            command=self._show_readable_view,
            height=30,
            font=CTkFont(size=12)
        )
        self.readable_btn.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        
        self.json_btn = ctk.CTkButton(
            self.button_frame,
            text="🔧 Technical (JSON)",
            command=self._show_json_view,
            height=30,
            font=CTkFont(size=12),
            fg_color="#757575"
        )
        self.json_btn.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        
        # Content area
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Make the content area expandable
        self.grid_rowconfigure(1, weight=1)
    
    def _populate_content(self):
        """Populate content based on current view mode"""
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        if self.show_json:
            self._create_json_view()
        else:
            self._create_readable_view()
    
    def _create_readable_view(self):
        """Create human-readable view"""
        # Format the request in human-readable form
        formatted_text = HumanReadableFormatter.format_request(self.request_data)
        
        # Create scrollable text area
        self.readable_text = ctk.CTkTextbox(
            self.content_frame,
            height=300,
            font=CTkFont(size=12),
            wrap="word"
        )
        self.readable_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Insert formatted text
        self.readable_text.insert("0.0", formatted_text)
        self.readable_text.configure(state="disabled")
        
        # Add validation status
        self._add_validation_status()
    
    def _create_json_view(self):
        """Create JSON view with syntax highlighting"""
        # Create JSON text area
        self.json_text = ctk.CTkTextbox(
            self.content_frame,
            height=300,
            font=CTkFont(family="Courier", size=11),
            wrap="none"
        )
        self.json_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 5))
        
        # Format JSON with proper indentation
        try:
            json_str = json.dumps(self.request_data, indent=2, sort_keys=True)
        except (TypeError, ValueError):
            json_str = str(self.request_data)
        
        # Insert JSON text
        self.json_text.insert("0.0", json_str)
        
        # Apply syntax highlighting
        SyntaxHighlighter.highlight_json(self.json_text, json_str)
        
        # Make read-only
        self.json_text.configure(state="disabled")
        
        # Add copy button
        self.copy_btn = ctk.CTkButton(
            self.content_frame,
            text="📋 Copy JSON",
            command=self._copy_json,
            height=30,
            width=100,
            font=CTkFont(size=11)
        )
        self.copy_btn.grid(row=1, column=0, sticky="e", padx=10, pady=5)
    
    def _add_validation_status(self):
        """Add validation status to readable view"""
        validation_frame = ctk.CTkFrame(self.content_frame)
        validation_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        validation_frame.grid_columnconfigure(1, weight=1)
        
        # Validation status
        validation_status = self._validate_request()
        
        status_label = ctk.CTkLabel(
            validation_frame,
            text="Validation Status:",
            font=CTkFont(size=12, weight="bold")
        )
        status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        status_color = "#4CAF50" if validation_status['valid'] else "#F44336"
        status_text = "✓ Valid" if validation_status['valid'] else "✗ Issues Found"
        
        status_value = ctk.CTkLabel(
            validation_frame,
            text=status_text,
            font=CTkFont(size=12, weight="bold"),
            text_color=status_color
        )
        status_value.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Show validation issues if any
        if not validation_status['valid'] and validation_status['errors']:
            issues_frame = ctk.CTkFrame(validation_frame, fg_color="#FFEBEE")
            issues_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
            
            issues_label = ctk.CTkLabel(
                issues_frame,
                text="Issues:",
                font=CTkFont(size=11, weight="bold"),
                text_color="#C62828"
            )
            issues_label.grid(row=0, column=0, sticky="nw", padx=5, pady=5)
            
            issues_text = "\n".join(f"• {error}" for error in validation_status['errors'])
            issues_content = ctk.CTkLabel(
                issues_frame,
                text=issues_text,
                font=CTkFont(size=11),
                text_color="#C62828",
                justify="left"
            )
            issues_content.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 5))
    
    def _validate_request(self) -> Dict[str, Any]:
        """Validate the API request"""
        errors = []
        
        if not self.request_data:
            errors.append("No request data provided")
        else:
            # Check for required fields based on request type
            data = self.request_data.get('data', {})
            
            # Basic validation rules
            if not data:
                errors.append("Request body is empty")
            
            # Check for common required fields
            common_required = []
            endpoint = self.request_data.get('endpoint', '')
            
            if 'vehicles' in endpoint and self.request_data.get('method') == 'POST':
                common_required = ['make', 'model', 'year']
            elif 'maintenance' in endpoint and self.request_data.get('method') == 'POST':
                common_required = ['vehicle_id', 'maintenance_type']
            elif 'reservations' in endpoint and self.request_data.get('method') == 'POST':
                common_required = ['vehicle_id', 'user_id', 'start_datetime']
            
            for field in common_required:
                if field not in data or not data[field]:
                    errors.append(f"Required field '{field}' is missing or empty")
            
            # Validate data types
            self._validate_field_types(data, errors)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _validate_field_types(self, data: Dict[str, Any], errors: List[str]):
        """Validate field data types"""
        # Date field validation
        date_fields = ['requested_date', 'start_datetime', 'end_datetime', 'start_date', 'end_date']
        for field in date_fields:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    # Check if it looks like a date
                    if not re.match(r'\d{4}-\d{2}-\d{2}', value):
                        errors.append(f"Field '{field}' should be a valid date format (YYYY-MM-DD)")
        
        # Numeric field validation
        numeric_fields = ['year', 'passenger_count', 'estimated_duration', 'mileage']
        for field in numeric_fields:
            if field in data:
                value = data[field]
                if not isinstance(value, (int, float)):
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        errors.append(f"Field '{field}' should be a number")
        
        # Boolean field validation
        boolean_fields = ['requires_approval', 'emergency', 'recurring']
        for field in boolean_fields:
            if field in data:
                value = data[field]
                if not isinstance(value, bool):
                    errors.append(f"Field '{field}' should be true or false")
    
    def _show_readable_view(self):
        """Switch to human-readable view"""
        self.show_json = False
        self._update_button_states()
        self._populate_content()
    
    def _show_json_view(self):
        """Switch to JSON view"""
        self.show_json = True
        self._update_button_states()
        self._populate_content()
    
    def _update_button_states(self):
        """Update button appearance based on current view"""
        if self.show_json:
            self.readable_btn.configure(fg_color="#757575")
            self.json_btn.configure(fg_color="#2196F3")
        else:
            self.readable_btn.configure(fg_color="#2196F3")
            self.json_btn.configure(fg_color="#757575")
    
    def _copy_json(self):
        """Copy JSON to clipboard"""
        try:
            # Get JSON text
            json_str = json.dumps(self.request_data, indent=2)
            
            # Copy to clipboard
            self.clipboard_clear()
            self.clipboard_append(json_str)
            
            # Show confirmation
            self.copy_btn.configure(text="✓ Copied!", fg_color="#4CAF50")
            self.after(2000, lambda: self.copy_btn.configure(text="📋 Copy JSON", fg_color="#2196F3"))
            
        except Exception as e:
            # Show error
            self.copy_btn.configure(text="Error", fg_color="#F44336")
            self.after(2000, lambda: self.copy_btn.configure(text="📋 Copy JSON", fg_color="#2196F3"))
    
    def update_request(self, request_data: Dict[str, Any]):
        """Update the displayed request data"""
        self.request_data = request_data
        self._populate_content()
    
    def get_request_summary(self) -> str:
        """Get a brief summary of the request"""
        if not self.request_data:
            return "No request data"
        
        method = self.request_data.get('method', 'POST')
        endpoint = self.request_data.get('endpoint', '/api/unknown')
        
        # Extract key information from data
        data = self.request_data.get('data', {})
        summary_parts = [f"{method} {endpoint}"]
        
        # Add key identifiers
        key_fields = ['vehicle_id', 'user_id', 'appointment_id', 'reservation_id']
        for field in key_fields:
            if field in data:
                summary_parts.append(f"{field}: {data[field]}")
        
        return " | ".join(summary_parts)
    
    def export_request(self, filepath: str, format: str = 'json') -> bool:
        """Export request to file"""
        try:
            if format.lower() == 'json':
                with open(filepath, 'w') as f:
                    json.dump(self.request_data, f, indent=2)
            elif format.lower() == 'txt':
                with open(filepath, 'w') as f:
                    f.write(HumanReadableFormatter.format_request(self.request_data))
            else:
                return False
            
            return True
            
        except Exception as e:
            return False