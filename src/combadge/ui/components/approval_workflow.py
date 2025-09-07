"""
Approval Workflow Interface for ComBadge Fleet Management

Main interface for reviewing and approving AI-generated API requests.
Provides clear display of AI interpretation, extracted entities, and proposed actions.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import customtkinter as ctk
from customtkinter import CTkFont

from .request_preview import RequestPreview
from .edit_interface import EditInterface


class ApprovalAction(Enum):
    """Available approval actions"""
    APPROVE = "approve"
    EDIT_APPROVE = "edit_approve" 
    REGENERATE = "regenerate"
    REJECT = "reject"


@dataclass
class ApprovalDecision:
    """Represents an approval decision with metadata"""
    action: ApprovalAction
    timestamp: datetime
    user_id: str
    original_request: Dict[str, Any]
    modified_request: Optional[Dict[str, Any]] = None
    feedback: Optional[str] = None
    confidence_override: Optional[float] = None
    approval_notes: Optional[str] = None


@dataclass
class AIInterpretation:
    """AI's interpretation of the natural language request"""
    original_text: str
    intent: str
    intent_confidence: float
    entities: Dict[str, Any]
    summary: str
    proposed_action: str
    generated_request: Dict[str, Any]
    overall_confidence: float
    warnings: List[str] = None


class ConfidenceIndicator(ctk.CTkFrame):
    """Visual confidence indicator with color coding"""
    
    def __init__(self, parent, confidence: float, label: str = ""):
        super().__init__(parent)
        
        self.confidence = confidence
        self.label_text = label
        
        self._setup_ui()
        self._update_display()
    
    def _setup_ui(self):
        """Setup the confidence indicator UI"""
        self.grid_columnconfigure(0, weight=1)
        
        # Label
        if self.label_text:
            self.label = ctk.CTkLabel(
                self,
                text=self.label_text,
                font=CTkFont(size=12, weight="bold")
            )
            self.label.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        
        # Confidence bar
        self.progress_frame = ctk.CTkFrame(self, height=20)
        self.progress_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        self.progress_frame.grid_propagate(False)
        
        # Confidence text
        self.confidence_label = ctk.CTkLabel(
            self,
            text=f"{self.confidence:.0%}",
            font=CTkFont(size=10)
        )
        self.confidence_label.grid(row=2, column=0, padx=5, pady=2)
    
    def _update_display(self):
        """Update the visual display based on confidence level"""
        # Color coding based on confidence
        if self.confidence >= 0.9:
            color = "#4CAF50"  # Green - High confidence
        elif self.confidence >= 0.75:
            color = "#8BC34A"  # Light green - Good confidence
        elif self.confidence >= 0.6:
            color = "#FFC107"  # Amber - Medium confidence
        elif self.confidence >= 0.4:
            color = "#FF9800"  # Orange - Low confidence
        else:
            color = "#F44336"  # Red - Very low confidence
        
        # Update progress frame color
        self.progress_frame.configure(fg_color=color)
        
        # Create progress bar effect
        progress_width = int(200 * self.confidence)
        self.progress_bar = ctk.CTkFrame(
            self.progress_frame,
            width=progress_width,
            height=16,
            fg_color=color
        )
        self.progress_bar.place(x=2, y=2)
        
        # Update text color for readability
        text_color = "white" if self.confidence < 0.5 else "black"
        self.confidence_label.configure(text_color=text_color)
    
    def update_confidence(self, confidence: float):
        """Update the confidence value and display"""
        self.confidence = confidence
        self.confidence_label.configure(text=f"{confidence:.0%}")
        self._update_display()


class EntityDisplay(ctk.CTkFrame):
    """Display extracted entities with confidence indicators"""
    
    def __init__(self, parent, entities: Dict[str, Any]):
        super().__init__(parent)
        
        self.entities = entities
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the entity display UI"""
        self.grid_columnconfigure(1, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            self,
            text="Extracted Entities",
            font=CTkFont(size=16, weight="bold")
        )
        title.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 5))
        
        row = 1
        for entity_type, entity_data in self.entities.items():
            # Entity type label
            type_label = ctk.CTkLabel(
                self,
                text=f"{entity_type.replace('_', ' ').title()}:",
                font=CTkFont(size=12, weight="bold")
            )
            type_label.grid(row=row, column=0, sticky="w", padx=10, pady=2)
            
            # Entity value
            if isinstance(entity_data, dict):
                value = entity_data.get('value', str(entity_data))
                confidence = entity_data.get('confidence', 1.0)
            else:
                value = str(entity_data)
                confidence = 1.0
            
            value_label = ctk.CTkLabel(
                self,
                text=str(value),
                font=CTkFont(size=12)
            )
            value_label.grid(row=row, column=1, sticky="w", padx=10, pady=2)
            
            # Confidence indicator (small)
            confidence_frame = ctk.CTkFrame(self, width=60, height=20)
            confidence_frame.grid(row=row, column=2, sticky="e", padx=10, pady=2)
            confidence_frame.grid_propagate(False)
            
            confidence_label = ctk.CTkLabel(
                confidence_frame,
                text=f"{confidence:.0%}",
                font=CTkFont(size=10)
            )
            confidence_label.pack(expand=True)
            
            # Color code the confidence frame
            if confidence >= 0.9:
                confidence_frame.configure(fg_color="#4CAF50")
            elif confidence >= 0.75:
                confidence_frame.configure(fg_color="#8BC34A")
            elif confidence >= 0.6:
                confidence_frame.configure(fg_color="#FFC107")
            else:
                confidence_frame.configure(fg_color="#FF9800")
            
            row += 1


class ApprovalWorkflow(ctk.CTkFrame):
    """
    Main approval workflow interface for AI-generated API requests.
    
    Provides comprehensive review capabilities with:
    - AI interpretation display
    - Entity extraction visualization
    - Request preview and editing
    - Approval actions with feedback
    - Audit logging
    """
    
    def __init__(
        self,
        parent,
        on_approve: Optional[Callable[[ApprovalDecision], None]] = None,
        on_reject: Optional[Callable[[ApprovalDecision], None]] = None,
        on_regenerate: Optional[Callable[[str], None]] = None,
        user_id: str = "unknown"
    ):
        super().__init__(parent)
        
        self.on_approve = on_approve
        self.on_reject = on_reject
        self.on_regenerate = on_regenerate
        self.user_id = user_id
        
        self.current_interpretation: Optional[AIInterpretation] = None
        self.edit_interface: Optional[EditInterface] = None
        self.request_preview: Optional[RequestPreview] = None
        
        # Approval history for audit
        self.approval_history: List[ApprovalDecision] = []
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        self._setup_ui()
        self._setup_keyboard_shortcuts()
    
    def _setup_ui(self):
        """Setup the main approval workflow UI"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Make content area expandable
        
        # Header with title
        self.header_frame = ctk.CTkFrame(self, height=60)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.header_frame.grid_propagate(False)
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="Request Approval Review",
            font=CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, pady=15)
        
        # Main content area with scrolling
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Initially show placeholder
        self._show_placeholder()
    
    def _show_placeholder(self):
        """Show placeholder when no request is loaded"""
        self.placeholder_label = ctk.CTkLabel(
            self.scroll_frame,
            text="No request loaded for review.\nPlease generate a request to begin the approval process.",
            font=CTkFont(size=16),
            text_color="gray"
        )
        self.placeholder_label.grid(row=0, column=0, pady=50)
    
    def _clear_content(self):
        """Clear the current content"""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for quick actions"""
        self.bind_all("<Control-a>", lambda e: self._handle_approve())
        self.bind_all("<Control-e>", lambda e: self._handle_edit_approve())
        self.bind_all("<Control-r>", lambda e: self._handle_regenerate())
        self.bind_all("<Control-j>", lambda e: self._handle_reject())
        self.bind_all("<Escape>", lambda e: self._handle_cancel())
    
    def load_interpretation(self, interpretation: AIInterpretation):
        """Load an AI interpretation for review"""
        self.current_interpretation = interpretation
        self._clear_content()
        self._create_approval_interface()
        
        self.logger.info(f"Loaded interpretation for review: {interpretation.intent}")
    
    def _create_approval_interface(self):
        """Create the complete approval interface"""
        if not self.current_interpretation:
            return
        
        interp = self.current_interpretation
        row = 0
        
        # 1. Intent Summary Section
        self._create_intent_summary(row)
        row += 1
        
        # 2. Extracted Entities Section
        self._create_entities_section(row)
        row += 1
        
        # 3. Confidence Indicators Section
        self._create_confidence_section(row)
        row += 1
        
        # 4. Proposed Action Section
        self._create_proposed_action_section(row)
        row += 1
        
        # 5. API Request Preview Section
        self._create_request_preview_section(row)
        row += 1
        
        # 6. Warnings Section (if any)
        if interp.warnings:
            self._create_warnings_section(row)
            row += 1
        
        # 7. Action Buttons Section
        self._create_action_buttons_section(row)
        row += 1
        
        # 8. Approval History Section
        if self.approval_history:
            self._create_history_section(row)
    
    def _create_intent_summary(self, row: int):
        """Create intent summary section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        section_frame.grid_columnconfigure(0, weight=1)
        
        # Section title
        title = ctk.CTkLabel(
            section_frame,
            text="AI Interpretation",
            font=CTkFont(size=18, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        # Original text
        orig_label = ctk.CTkLabel(
            section_frame,
            text="Original Request:",
            font=CTkFont(size=12, weight="bold")
        )
        orig_label.grid(row=1, column=0, sticky="w", padx=15, pady=(10, 2))
        
        orig_text = ctk.CTkTextbox(
            section_frame,
            height=60,
            font=CTkFont(size=12),
            wrap="word"
        )
        orig_text.grid(row=2, column=0, sticky="ew", padx=15, pady=2)
        orig_text.insert("0.0", self.current_interpretation.original_text)
        orig_text.configure(state="disabled")
        
        # AI Summary
        summary_label = ctk.CTkLabel(
            section_frame,
            text="AI Understanding:",
            font=CTkFont(size=12, weight="bold")
        )
        summary_label.grid(row=3, column=0, sticky="w", padx=15, pady=(10, 2))
        
        summary_text = ctk.CTkLabel(
            section_frame,
            text=self.current_interpretation.summary,
            font=CTkFont(size=12),
            wraplength=600,
            justify="left"
        )
        summary_text.grid(row=4, column=0, sticky="w", padx=15, pady=(2, 15))
    
    def _create_entities_section(self, row: int):
        """Create extracted entities section"""
        entities_frame = EntityDisplay(self.scroll_frame, self.current_interpretation.entities)
        entities_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
    
    def _create_confidence_section(self, row: int):
        """Create confidence indicators section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        section_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Section title
        title = ctk.CTkLabel(
            section_frame,
            text="Confidence Assessment",
            font=CTkFont(size=16, weight="bold")
        )
        title.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(15, 10))
        
        # Overall confidence
        overall_indicator = ConfidenceIndicator(
            section_frame,
            self.current_interpretation.overall_confidence,
            "Overall Confidence"
        )
        overall_indicator.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        
        # Intent confidence
        intent_indicator = ConfidenceIndicator(
            section_frame,
            self.current_interpretation.intent_confidence,
            "Intent Classification"
        )
        intent_indicator.grid(row=1, column=1, sticky="ew", padx=15, pady=5)
        
        # Confidence explanation
        if self.current_interpretation.overall_confidence < 0.8:
            warning_label = ctk.CTkLabel(
                section_frame,
                text="⚠️ Low confidence detected. Please review carefully before approving.",
                font=CTkFont(size=12),
                text_color="#FF9800"
            )
            warning_label.grid(row=2, column=0, columnspan=2, padx=15, pady=(5, 15))
    
    def _create_proposed_action_section(self, row: int):
        """Create proposed action section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        section_frame.grid_columnconfigure(0, weight=1)
        
        # Section title
        title = ctk.CTkLabel(
            section_frame,
            text="Proposed Action",
            font=CTkFont(size=16, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        # Action description
        action_text = ctk.CTkLabel(
            section_frame,
            text=self.current_interpretation.proposed_action,
            font=CTkFont(size=14),
            wraplength=600,
            justify="left"
        )
        action_text.grid(row=1, column=0, sticky="w", padx=15, pady=(5, 15))
    
    def _create_request_preview_section(self, row: int):
        """Create API request preview section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        section_frame.grid_columnconfigure(0, weight=1)
        
        # Create request preview component
        self.request_preview = RequestPreview(
            section_frame,
            self.current_interpretation.generated_request
        )
        self.request_preview.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
    
    def _create_warnings_section(self, row: int):
        """Create warnings section"""
        section_frame = ctk.CTkFrame(self.scroll_frame, fg_color="#FFF3CD")
        section_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        section_frame.grid_columnconfigure(0, weight=1)
        
        # Section title
        title = ctk.CTkLabel(
            section_frame,
            text="⚠️ Warnings",
            font=CTkFont(size=16, weight="bold"),
            text_color="#856404"
        )
        title.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        # Warning list
        for i, warning in enumerate(self.current_interpretation.warnings):
            warning_label = ctk.CTkLabel(
                section_frame,
                text=f"• {warning}",
                font=CTkFont(size=12),
                text_color="#856404",
                justify="left",
                wraplength=600
            )
            warning_label.grid(row=i+1, column=0, sticky="w", padx=25, pady=2)
    
    def _create_action_buttons_section(self, row: int):
        """Create action buttons section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=15)
        section_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # Section title
        title = ctk.CTkLabel(
            section_frame,
            text="Approval Actions",
            font=CTkFont(size=16, weight="bold")
        )
        title.grid(row=0, column=0, columnspan=4, pady=(15, 10))
        
        # Approve button (green)
        self.approve_btn = ctk.CTkButton(
            section_frame,
            text="✓ Approve\n(Ctrl+A)",
            command=self._handle_approve,
            fg_color="#4CAF50",
            hover_color="#45a049",
            height=50,
            font=CTkFont(size=12, weight="bold")
        )
        self.approve_btn.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        # Edit & Approve button (blue)
        self.edit_approve_btn = ctk.CTkButton(
            section_frame,
            text="✎ Edit & Approve\n(Ctrl+E)",
            command=self._handle_edit_approve,
            fg_color="#2196F3",
            hover_color="#1976D2",
            height=50,
            font=CTkFont(size=12, weight="bold")
        )
        self.edit_approve_btn.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        # Regenerate button (yellow)
        self.regenerate_btn = ctk.CTkButton(
            section_frame,
            text="🔄 Regenerate\n(Ctrl+R)",
            command=self._handle_regenerate,
            fg_color="#FFC107",
            hover_color="#FFB300",
            height=50,
            text_color="black",
            font=CTkFont(size=12, weight="bold")
        )
        self.regenerate_btn.grid(row=1, column=2, padx=10, pady=10, sticky="ew")
        
        # Reject button (red)
        self.reject_btn = ctk.CTkButton(
            section_frame,
            text="✗ Reject\n(Ctrl+J)",
            command=self._handle_reject,
            fg_color="#F44336",
            hover_color="#D32F2F",
            height=50,
            font=CTkFont(size=12, weight="bold")
        )
        self.reject_btn.grid(row=1, column=3, padx=10, pady=10, sticky="ew")
        
        # Keyboard shortcuts help
        help_label = ctk.CTkLabel(
            section_frame,
            text="Keyboard shortcuts available • ESC to cancel",
            font=CTkFont(size=10),
            text_color="gray"
        )
        help_label.grid(row=2, column=0, columnspan=4, pady=(0, 15))
    
    def _create_history_section(self, row: int):
        """Create approval history section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        section_frame.grid_columnconfigure(0, weight=1)
        
        # Section title
        title = ctk.CTkLabel(
            section_frame,
            text="Approval History",
            font=CTkFont(size=16, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))
        
        # History list (last 5 entries)
        for i, decision in enumerate(self.approval_history[-5:]):
            history_text = (
                f"{decision.timestamp.strftime('%Y-%m-%d %H:%M')} - "
                f"{decision.action.value.upper()} by {decision.user_id}"
            )
            if decision.feedback:
                history_text += f" - {decision.feedback}"
            
            history_label = ctk.CTkLabel(
                section_frame,
                text=history_text,
                font=CTkFont(size=10),
                justify="left"
            )
            history_label.grid(row=i+1, column=0, sticky="w", padx=25, pady=1)
    
    def _handle_approve(self):
        """Handle approve action"""
        if not self.current_interpretation:
            return
        
        # Show confirmation dialog
        if self._show_confirmation_dialog("Approve Request", 
                                          "Execute this API request immediately?"):
            decision = ApprovalDecision(
                action=ApprovalAction.APPROVE,
                timestamp=datetime.now(),
                user_id=self.user_id,
                original_request=self.current_interpretation.generated_request.copy()
            )
            
            self._record_decision(decision)
            
            if self.on_approve:
                self.on_approve(decision)
    
    def _handle_edit_approve(self):
        """Handle edit and approve action"""
        if not self.current_interpretation:
            return
        
        # Show edit interface
        self._show_edit_interface()
    
    def _handle_regenerate(self):
        """Handle regenerate request action"""
        if not self.current_interpretation:
            return
        
        # Show regeneration dialog
        feedback = self._show_feedback_dialog(
            "Request Regeneration",
            "Provide guidance for improving the AI analysis:"
        )
        
        if feedback is not None:  # User didn't cancel
            decision = ApprovalDecision(
                action=ApprovalAction.REGENERATE,
                timestamp=datetime.now(),
                user_id=self.user_id,
                original_request=self.current_interpretation.generated_request.copy(),
                feedback=feedback
            )
            
            self._record_decision(decision)
            
            if self.on_regenerate:
                self.on_regenerate(feedback)
    
    def _handle_reject(self):
        """Handle reject action"""
        if not self.current_interpretation:
            return
        
        # Show rejection dialog
        feedback = self._show_feedback_dialog(
            "Reject Request",
            "Please provide feedback on why this request is being rejected:",
            required=True
        )
        
        if feedback:
            decision = ApprovalDecision(
                action=ApprovalAction.REJECT,
                timestamp=datetime.now(),
                user_id=self.user_id,
                original_request=self.current_interpretation.generated_request.copy(),
                feedback=feedback
            )
            
            self._record_decision(decision)
            
            if self.on_reject:
                self.on_reject(decision)
    
    def _handle_cancel(self):
        """Handle cancel/escape action"""
        # Clear current interpretation and show placeholder
        self.current_interpretation = None
        self._clear_content()
        self._show_placeholder()
    
    def _show_edit_interface(self):
        """Show the edit interface for modifying the request"""
        if not self.current_interpretation:
            return
        
        # Create edit dialog
        edit_window = ctk.CTkToplevel(self)
        edit_window.title("Edit API Request")
        edit_window.geometry("800x600")
        edit_window.transient(self)
        edit_window.grab_set()
        
        # Create edit interface
        self.edit_interface = EditInterface(
            edit_window,
            self.current_interpretation.generated_request,
            on_save=lambda modified_request: self._handle_edit_save(edit_window, modified_request),
            on_cancel=lambda: edit_window.destroy()
        )
        self.edit_interface.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _handle_edit_save(self, edit_window, modified_request: Dict[str, Any]):
        """Handle saving edited request"""
        decision = ApprovalDecision(
            action=ApprovalAction.EDIT_APPROVE,
            timestamp=datetime.now(),
            user_id=self.user_id,
            original_request=self.current_interpretation.generated_request.copy(),
            modified_request=modified_request.copy()
        )
        
        self._record_decision(decision)
        edit_window.destroy()
        
        # Show confirmation for executing modified request
        if self._show_confirmation_dialog("Execute Modified Request", 
                                          "Execute the modified API request?"):
            if self.on_approve:
                self.on_approve(decision)
    
    def _show_confirmation_dialog(self, title: str, message: str) -> bool:
        """Show confirmation dialog"""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()
        
        result = {"confirmed": False}
        
        # Message
        msg_label = ctk.CTkLabel(dialog, text=message, font=CTkFont(size=14))
        msg_label.pack(pady=20)
        
        # Buttons frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="Confirm",
            command=lambda: [result.update({"confirmed": True}), dialog.destroy()],
            fg_color="#4CAF50"
        )
        confirm_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            fg_color="#757575"
        )
        cancel_btn.pack(side="left", padx=10)
        
        dialog.wait_window()
        return result["confirmed"]
    
    def _show_feedback_dialog(self, title: str, message: str, required: bool = False) -> Optional[str]:
        """Show feedback input dialog"""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("500x300")
        dialog.transient(self)
        dialog.grab_set()
        
        result = {"feedback": None}
        
        # Message
        msg_label = ctk.CTkLabel(dialog, text=message, font=CTkFont(size=14))
        msg_label.pack(pady=20)
        
        # Feedback text area
        feedback_text = ctk.CTkTextbox(dialog, height=100)
        feedback_text.pack(fill="both", expand=True, padx=20, pady=10)
        feedback_text.focus()
        
        # Buttons frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        def save_feedback():
            feedback = feedback_text.get("0.0", "end-1c").strip()
            if required and not feedback:
                # Show error message
                error_label = ctk.CTkLabel(btn_frame, text="Feedback is required", text_color="red")
                error_label.pack(pady=5)
                return
            result["feedback"] = feedback if feedback else ""
            dialog.destroy()
        
        save_btn = ctk.CTkButton(
            btn_frame,
            text="Submit" if required else "Save",
            command=save_feedback,
            fg_color="#4CAF50"
        )
        save_btn.pack(side="left", padx=10)
        
        if not required:
            skip_btn = ctk.CTkButton(
                btn_frame,
                text="Skip",
                command=lambda: [result.update({"feedback": ""}), dialog.destroy()],
                fg_color="#757575"
            )
            skip_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            fg_color="#757575"
        )
        cancel_btn.pack(side="left", padx=10)
        
        dialog.wait_window()
        return result["feedback"]
    
    def _record_decision(self, decision: ApprovalDecision):
        """Record approval decision for audit trail"""
        self.approval_history.append(decision)
        
        # Log the decision
        self.logger.info(
            f"Approval decision recorded: {decision.action.value} by {decision.user_id} "
            f"at {decision.timestamp.isoformat()}"
        )
        
        # Optionally limit history size
        if len(self.approval_history) > 100:
            self.approval_history = self.approval_history[-50:]  # Keep last 50
    
    def export_approval_history(self, filepath: str):
        """Export approval history to JSON file"""
        try:
            history_data = []
            for decision in self.approval_history:
                history_data.append({
                    'action': decision.action.value,
                    'timestamp': decision.timestamp.isoformat(),
                    'user_id': decision.user_id,
                    'original_request': decision.original_request,
                    'modified_request': decision.modified_request,
                    'feedback': decision.feedback,
                    'confidence_override': decision.confidence_override,
                    'approval_notes': decision.approval_notes
                })
            
            with open(filepath, 'w') as f:
                json.dump(history_data, f, indent=2)
            
            self.logger.info(f"Approval history exported to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export approval history: {e}")
            return False
    
    def get_approval_stats(self) -> Dict[str, Any]:
        """Get approval statistics"""
        if not self.approval_history:
            return {}
        
        stats = {
            'total_decisions': len(self.approval_history),
            'approved': len([d for d in self.approval_history if d.action == ApprovalAction.APPROVE]),
            'edited_approved': len([d for d in self.approval_history if d.action == ApprovalAction.EDIT_APPROVE]),
            'rejected': len([d for d in self.approval_history if d.action == ApprovalAction.REJECT]),
            'regenerated': len([d for d in self.approval_history if d.action == ApprovalAction.REGENERATE])
        }
        
        if stats['total_decisions'] > 0:
            stats['approval_rate'] = (stats['approved'] + stats['edited_approved']) / stats['total_decisions']
        
        return stats