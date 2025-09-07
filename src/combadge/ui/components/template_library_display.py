"""Template Library Display Component

Visual component for displaying available templates to the user,
organized by category with metadata and usage statistics.
"""

import customtkinter as ctk
from customtkinter import CTkFont
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from ...processors.templates.template_manager import TemplateMetadata, TemplateManager


@dataclass
class TemplateDisplayInfo:
    """Information for displaying a template."""
    metadata: TemplateMetadata
    usage_count: int = 0
    success_rate: float = 1.0
    example_commands: List[str] = None


class TemplateCard(ctk.CTkFrame):
    """Individual template card displaying template information."""
    
    def __init__(self, parent, template_info: TemplateDisplayInfo, on_select: Optional[Callable[[str], None]] = None):
        super().__init__(parent)
        
        self.template_info = template_info
        self.on_select = on_select
        self.selected = False
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup template card UI."""
        self.grid_columnconfigure(0, weight=1)
        
        # Header with name and category
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame.grid_columnconfigure(0, weight=1)
        
        # Template name
        name_label = ctk.CTkLabel(
            header_frame,
            text=self.template_info.metadata.name.replace('_', ' ').title(),
            font=CTkFont(size=14, weight="bold")
        )
        name_label.grid(row=0, column=0, sticky="w")
        
        # Category badge
        category_label = ctk.CTkLabel(
            header_frame,
            text=self.template_info.metadata.category.upper(),
            font=CTkFont(size=10),
            corner_radius=10,
            fg_color=self._get_category_color(),
            width=80,
            height=20
        )
        category_label.grid(row=0, column=1, sticky="e")
        
        # Description
        if self.template_info.metadata.description:
            desc_label = ctk.CTkLabel(
                self,
                text=self.template_info.metadata.description,
                font=CTkFont(size=11),
                wraplength=300,
                justify="left"
            )
            desc_label.grid(row=1, column=0, sticky="ew", padx=10, pady=2)
        
        # Required entities
        if self.template_info.metadata.required_entities:
            entities_frame = ctk.CTkFrame(self, fg_color="transparent")
            entities_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=2)
            entities_frame.grid_columnconfigure(0, weight=1)
            
            entities_label = ctk.CTkLabel(
                entities_frame,
                text="Required: " + ", ".join(self.template_info.metadata.required_entities),
                font=CTkFont(size=10),
                text_color="gray"
            )
            entities_label.grid(row=0, column=0, sticky="w")
        
        # Usage statistics
        if self.template_info.usage_count > 0:
            stats_frame = ctk.CTkFrame(self, fg_color="transparent")
            stats_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=2)
            
            stats_text = f"Used {self.template_info.usage_count} times • {self.template_info.success_rate:.0%} success rate"
            stats_label = ctk.CTkLabel(
                stats_frame,
                text=stats_text,
                font=CTkFont(size=9),
                text_color="gray"
            )
            stats_label.pack(side="left")
        
        # Select button
        self.select_button = ctk.CTkButton(
            self,
            text="Select Template",
            height=25,
            font=CTkFont(size=11),
            command=self._handle_select,
            fg_color="gray",
            hover_color="darkgray"
        )
        self.select_button.grid(row=4, column=0, sticky="ew", padx=10, pady=(5, 10))
        
        # Click handler for entire card
        self.bind("<Button-1>", lambda e: self._handle_select())
        
    def _get_category_color(self) -> str:
        """Get color for category badge."""
        colors = {
            "reservations": "#4CAF50",
            "maintenance": "#FF9800", 
            "parking": "#2196F3",
            "vehicle_operations": "#9C27B0",
            "default": "#757575"
        }
        return colors.get(self.template_info.metadata.category, colors["default"])
        
    def _handle_select(self):
        """Handle template selection."""
        if self.on_select:
            self.on_select(self.template_info.metadata.name)
        
        # Update visual selection state
        self.set_selected(True)
        
    def set_selected(self, selected: bool):
        """Set visual selection state."""
        self.selected = selected
        if selected:
            self.configure(border_width=2, border_color="#4CAF50")
            self.select_button.configure(
                text="Selected",
                fg_color="#4CAF50",
                hover_color="#45a049"
            )
        else:
            self.configure(border_width=0)
            self.select_button.configure(
                text="Select Template",
                fg_color="gray", 
                hover_color="darkgray"
            )


class TemplateLibraryDisplay(ctk.CTkFrame):
    """Main template library display showing all available templates."""
    
    def __init__(self, parent, template_manager: TemplateManager, on_template_select: Optional[Callable[[str], None]] = None):
        super().__init__(parent)
        
        self.template_manager = template_manager
        self.on_template_select = on_template_select
        self.template_cards: Dict[str, TemplateCard] = {}
        self.selected_template: Optional[str] = None
        
        self._setup_ui()
        self._load_templates()
        
    def _setup_ui(self):
        """Setup main UI structure."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(self, height=50)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.grid_propagate(False)
        header_frame.grid_columnconfigure(0, weight=1)
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="Available Templates",
            font=CTkFont(size=18, weight="bold")
        )
        title_label.grid(row=0, column=0, pady=15)
        
        # Refresh button
        refresh_button = ctk.CTkButton(
            header_frame,
            text="↻ Refresh",
            width=80,
            height=25,
            font=CTkFont(size=11),
            command=self._refresh_templates
        )
        refresh_button.grid(row=0, column=1, padx=10, pady=15)
        
        # Scrollable content area
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
    def _load_templates(self):
        """Load and display all templates."""
        templates_by_category = self.template_manager.get_templates_by_category()
        
        if not templates_by_category:
            # Show empty state
            empty_label = ctk.CTkLabel(
                self.scroll_frame,
                text="No templates found.\nPlease check your templates directory.",
                font=CTkFont(size=14),
                text_color="gray"
            )
            empty_label.grid(row=0, column=0, pady=50)
            return
        
        row = 0
        for category, templates in templates_by_category.items():
            # Category header
            category_label = ctk.CTkLabel(
                self.scroll_frame,
                text=category.replace('_', ' ').title(),
                font=CTkFont(size=16, weight="bold")
            )
            category_label.grid(row=row, column=0, sticky="w", padx=10, pady=(20, 10))
            row += 1
            
            # Templates in category
            for template_metadata in templates:
                # Get usage statistics
                stats = self.template_manager.get_template_stats(template_metadata.name)
                usage_count = stats.total_uses if stats else 0
                success_rate = stats.successful_uses / max(1, stats.total_uses) if stats else 1.0
                
                template_info = TemplateDisplayInfo(
                    metadata=template_metadata,
                    usage_count=usage_count,
                    success_rate=success_rate
                )
                
                # Create template card
                card = TemplateCard(
                    self.scroll_frame,
                    template_info,
                    on_select=self._handle_template_select
                )
                card.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
                
                self.template_cards[template_metadata.name] = card
                row += 1
    
    def _refresh_templates(self):
        """Refresh template display."""
        # Clear existing cards
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        self.template_cards.clear()
        self.selected_template = None
        
        # Reload templates
        self.template_manager.load_templates(force_reload=True)
        self._load_templates()
        
    def _handle_template_select(self, template_name: str):
        """Handle template selection."""
        # Update selection state
        if self.selected_template and self.selected_template in self.template_cards:
            self.template_cards[self.selected_template].set_selected(False)
        
        self.selected_template = template_name
        if template_name in self.template_cards:
            self.template_cards[template_name].set_selected(True)
        
        # Notify parent
        if self.on_template_select:
            self.on_template_select(template_name)
    
    def get_selected_template(self) -> Optional[str]:
        """Get the currently selected template name."""
        return self.selected_template
    
    def select_template(self, template_name: str):
        """Programmatically select a template."""
        if template_name in self.template_cards:
            self._handle_template_select(template_name)
    
    def highlight_template(self, template_name: str, highlight: bool = True):
        """Highlight a specific template (e.g., AI recommendation)."""
        if template_name in self.template_cards:
            card = self.template_cards[template_name]
            if highlight:
                card.configure(border_width=2, border_color="#FFC107")
            else:
                card.configure(border_width=0)