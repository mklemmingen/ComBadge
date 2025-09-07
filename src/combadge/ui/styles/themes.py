"""Theme System

Dark theme with modern styling and clean typography.
"""

from dataclasses import dataclass
from typing import Dict, Tuple
import customtkinter as ctk


@dataclass
class ThemeColors:
    """Dark color palette."""
    
    # Primary colors
    primary_bg: str = "#2B2B2B"           # Dark gray background
    secondary_bg: str = "#3A3A3A"         # Lighter gray for panels
    surface: str = "#404040"              # Surface elements
    
    # Accent colors
    accent_blue: str = "#00ADEF"          # Primary accent blue
    silver: str = "#C0C0C0"              # Silver accents
    platinum: str = "#E5E4E2"            # Light platinum
    
    # Text colors
    text_primary: str = "#FFFFFF"         # Primary white text
    text_secondary: str = "#CCCCCC"       # Secondary gray text
    text_muted: str = "#888888"          # Muted text
    
    # Status colors
    success: str = "#00C851"             # Green for success
    warning: str = "#FFB347"             # Orange for warnings
    error: str = "#FF3547"               # Red for errors
    processing: str = "#00ADEF"          # Blue for processing
    
    # Interactive colors
    button_hover: str = "#0088CC"        # Button hover state
    button_active: str = "#0066AA"       # Button active state
    border: str = "#555555"              # Border color
    border_focus: str = "#00ADEF"        # Focused element border


class Theme:
    """Theme configuration."""
    
    def __init__(self):
        """Initialize theme."""
        self.colors = ThemeColors()
        self._setup_customtkinter_theme()
        
    def _setup_customtkinter_theme(self):
        """Configure CustomTkinter with theme."""
        # Setting appearance mode
        ctk.set_appearance_mode("dark")
        
        # Creating custom color theme
        self._create_custom_theme()
        
    def _create_custom_theme(self):
        """Create custom color theme for CustomTkinter."""
        theme_config = {
            "CTk": {
                "fg_color": [self.colors.primary_bg, self.colors.primary_bg]
            },
            "CTkToplevel": {
                "fg_color": [self.colors.primary_bg, self.colors.primary_bg]
            },
            "CTkFrame": {
                "corner_radius": 8,
                "border_width": 1,
                "fg_color": [self.colors.secondary_bg, self.colors.secondary_bg],
                "border_color": [self.colors.border, self.colors.border]
            },
            "CTkButton": {
                "corner_radius": 6,
                "border_width": 0,
                "fg_color": [self.colors.accent_blue, self.colors.accent_blue],
                "hover_color": [self.colors.button_hover, self.colors.button_hover],
                "text_color": [self.colors.text_primary, self.colors.text_primary],
                "font": ("Segoe UI", 12)
            },
            "CTkLabel": {
                "corner_radius": 0,
                "fg_color": "transparent",
                "text_color": [self.colors.text_primary, self.colors.text_primary],
                "font": ("Segoe UI", 12)
            },
            "CTkEntry": {
                "corner_radius": 6,
                "border_width": 2,
                "fg_color": [self.colors.surface, self.colors.surface],
                "border_color": [self.colors.border, self.colors.border],
                "text_color": [self.colors.text_primary, self.colors.text_primary],
                "placeholder_text_color": [self.colors.text_muted, self.colors.text_muted],
                "font": ("Segoe UI", 12)
            },
            "CTkTextbox": {
                "corner_radius": 6,
                "border_width": 2,
                "fg_color": [self.colors.surface, self.colors.surface],
                "border_color": [self.colors.border, self.colors.border],
                "text_color": [self.colors.text_primary, self.colors.text_primary],
                "font": ("Segoe UI", 12)
            },
            "CTkScrollableFrame": {
                "corner_radius": 6,
                "border_width": 1,
                "fg_color": [self.colors.secondary_bg, self.colors.secondary_bg],
                "border_color": [self.colors.border, self.colors.border]
            },
            "CTkProgressBar": {
                "corner_radius": 10,
                "border_width": 0,
                "fg_color": [self.colors.surface, self.colors.surface],
                "progress_color": [self.colors.accent_blue, self.colors.accent_blue]
            }
        }
        
        # Setting the custom theme
        # Note: Custom theme configuration would be applied here
        
    def get_font(self, size: int = 12, weight: str = "normal") -> Tuple[str, int, str]:
        """Get font configuration.
        
        Args:
            size: Font size
            weight: Font weight (normal, bold)
            
        Returns:
            Font tuple for CustomTkinter
        """
        return ("Segoe UI", size, weight)
        
    def get_title_font(self) -> Tuple[str, int, str]:
        """Get title font configuration."""
        return self.get_font(18, "bold")
        
    def get_header_font(self) -> Tuple[str, int, str]:
        """Get header font configuration."""
        return self.get_font(14, "bold")
        
    def get_body_font(self) -> Tuple[str, int, str]:
        """Get body font configuration."""
        return self.get_font(12, "normal")
        
    def get_small_font(self) -> Tuple[str, int, str]:
        """Get small font configuration."""
        return self.get_font(10, "normal")
        
    def get_status_color(self, status: str) -> str:
        """Get color for status indicators.
        
        Args:
            status: Status type (idle, processing, success, warning, error)
            
        Returns:
            Color hex code
        """
        status_colors = {
            "idle": self.colors.text_muted,
            "processing": self.colors.processing,
            "success": self.colors.success,
            "warning": self.colors.warning,
            "error": self.colors.error
        }
        return status_colors.get(status, self.colors.text_primary)
        
    def create_button_style(self, variant: str = "primary") -> Dict[str, str]:
        """Create button style configuration.
        
        Args:
            variant: Button variant (primary, secondary, danger)
            
        Returns:
            Style configuration dictionary
        """
        base_style = {
            "corner_radius": 6,
            "border_width": 0,
            "font": self.get_body_font()
        }
        
        variants = {
            "primary": {
                "fg_color": self.colors.accent_blue,
                "hover_color": self.colors.button_hover,
                "text_color": self.colors.text_primary
            },
            "secondary": {
                "fg_color": self.colors.surface,
                "hover_color": self.colors.border,
                "text_color": self.colors.text_primary,
                "border_width": 1,
                "border_color": self.colors.border
            },
            "danger": {
                "fg_color": self.colors.error,
                "hover_color": "#CC2936",
                "text_color": self.colors.text_primary
            }
        }
        
        style = base_style.copy()
        style.update(variants.get(variant, variants["primary"]))
        return style
        
    def create_frame_style(self, elevated: bool = False) -> Dict[str, str]:
        """Create frame style configuration.
        
        Args:
            elevated: Whether frame should appear elevated
            
        Returns:
            Style configuration dictionary
        """
        style = {
            "corner_radius": 8,
            "border_width": 1 if elevated else 0,
            "fg_color": self.colors.secondary_bg if elevated else self.colors.primary_bg,
        }
        if elevated:
            style["border_color"] = self.colors.border
        return style
        
    def create_input_style(self, focused: bool = False) -> Dict[str, str]:
        """Create input field style configuration.
        
        Args:
            focused: Whether input is focused
            
        Returns:
            Style configuration dictionary
        """
        return {
            "corner_radius": 6,
            "border_width": 2,
            "fg_color": self.colors.surface,
            "border_color": self.colors.border_focus if focused else self.colors.border,
            "text_color": self.colors.text_primary,
            "font": self.get_body_font()
        }