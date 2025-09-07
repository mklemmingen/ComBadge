"""Real-time Reasoning Display Component

Advanced Chain of Thought visualization with streaming updates, semantic highlighting,
confidence indicators, and export functionality for transparent AI reasoning.
"""

import tkinter as tk
import threading
import queue
import time
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..styles.themes import Theme
from ...intelligence.chain_of_thought.reasoning_parser import (
    ReasoningParser, 
    ReasoningTrace, 
    ReasoningStep, 
    ReasoningPhase,
    ConfidenceLevel
)
from ...core.logging_manager import LoggingManager


class ConfidenceBadge(ctk.CTkFrame):
    """Confidence indicator badge with color coding."""
    
    def __init__(self, parent, theme: Theme, confidence: float = 0.0):
        """Initialize confidence badge.
        
        Args:
            parent: Parent widget
            theme: Theme configuration
            confidence: Confidence value (0.0-1.0)
        """
        super().__init__(parent, width=80, height=25)
        
        self.theme = theme
        self.confidence = confidence
        
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        
        # Confidence label
        self.confidence_label = ctk.CTkLabel(
            self,
            text=f"{confidence:.0%}",
            font=self.theme.get_small_font(),
            width=80,
            height=25
        )
        self.confidence_label.grid(row=0, column=0, sticky="ew")
        
        self.update_confidence(confidence)
        
    def update_confidence(self, confidence: float):
        """Update confidence display and colors.
        
        Args:
            confidence: New confidence value
        """
        self.confidence = confidence
        self.confidence_label.configure(text=f"{confidence:.0%}")
        
        # Set colors based on confidence level
        if confidence >= 0.8:
            # High confidence - green
            bg_color = "#2D7D32"
            text_color = "#FFFFFF"
        elif confidence >= 0.6:
            # Medium confidence - yellow
            bg_color = "#F57C00"
            text_color = "#FFFFFF"
        elif confidence >= 0.4:
            # Low confidence - orange
            bg_color = "#E65100"
            text_color = "#FFFFFF"
        else:
            # Very low confidence - red
            bg_color = "#C62828"
            text_color = "#FFFFFF"
            
        self.configure(fg_color=bg_color)
        self.confidence_label.configure(text_color=text_color)


class ReasoningStepWidget(ctk.CTkFrame):
    """Widget representing a single reasoning step with semantic highlighting."""
    
    def __init__(self, parent, theme: Theme, step: ReasoningStep, step_number: int):
        """Initialize reasoning step widget.
        
        Args:
            parent: Parent widget
            theme: Theme configuration
            step: Reasoning step data
            step_number: Step number for display
        """
        super().__init__(parent)
        
        self.theme = theme
        self.step = step
        self.step_number = step_number
        self.is_expanded = True
        self.is_processing = False
        
        self.grid_columnconfigure(0, weight=1)
        
        self._setup_header()
        self._setup_content()
        self._apply_phase_styling()
        
    def _setup_header(self):
        """Setup step header with controls."""
        self.header_frame = ctk.CTkFrame(self, height=40)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))
        self.header_frame.grid_propagate(False)
        self.header_frame.grid_columnconfigure(2, weight=1)
        
        # Step number indicator
        self.step_indicator = ctk.CTkLabel(
            self.header_frame,
            text=f"{self.step_number}",
            font=self.theme.get_body_font(),
            width=30,
            height=30
        )
        self.step_indicator.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Step title
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text=self.step.title,
            font=self.theme.get_body_font(),
            text_color=self.theme.colors.text_primary
        )
        self.title_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        # Confidence badge
        self.confidence_badge = ConfidenceBadge(
            self.header_frame, 
            self.theme, 
            self.step.confidence
        )
        self.confidence_badge.grid(row=0, column=3, padx=5, pady=5, sticky="e")
        
        # Timestamp
        timestamp_text = datetime.fromtimestamp(self.step.timestamp).strftime("%H:%M:%S.%f")[:-3]
        self.timestamp_label = ctk.CTkLabel(
            self.header_frame,
            text=timestamp_text,
            font=self.theme.get_small_font(),
            text_color=self.theme.colors.text_muted
        )
        self.timestamp_label.grid(row=0, column=4, padx=5, pady=5, sticky="e")
        
        # Expand/collapse button
        self.expand_button = ctk.CTkButton(
            self.header_frame,
            text="▼",
            width=25,
            height=25,
            font=self.theme.get_small_font(),
            command=self.toggle_content
        )
        self.expand_button.grid(row=0, column=5, padx=5, pady=5, sticky="e")
        
    def _setup_content(self):
        """Setup step content area."""
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Main content text
        self.content_text = ctk.CTkTextbox(
            self.content_frame,
            height=100,
            wrap="word",
            font=self.theme.get_body_font()
        )
        self.content_text.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.content_text.insert("1.0", self.step.content)
        
        # Entities section (if present)
        if self.step.entities:
            self._add_entities_section()
            
        # Findings section (if present)
        if self.step.findings:
            self._add_findings_section()
            
        self.content_text.configure(state="disabled")
        
    def _add_entities_section(self):
        """Add entities display section."""
        entities_label = ctk.CTkLabel(
            self.content_frame,
            text="Extracted Entities:",
            font=self.theme.get_body_font(),
            text_color=self.theme.colors.accent_blue
        )
        entities_label.grid(row=1, column=0, sticky="w", padx=5, pady=(10, 0))
        
        entities_text = ctk.CTkTextbox(
            self.content_frame,
            height=60,
            wrap="word",
            font=self.theme.get_small_font()
        )
        entities_text.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        # Format entities for display
        entities_content = []
        for entity_type, values in self.step.entities.items():
            if isinstance(values, list):
                values_str = ", ".join(str(v) for v in values)
            else:
                values_str = str(values)
            entities_content.append(f"• {entity_type.replace('_', ' ').title()}: {values_str}")
            
        entities_text.insert("1.0", "\n".join(entities_content))
        entities_text.configure(state="disabled")
        
    def _add_findings_section(self):
        """Add findings display section."""
        findings_label = ctk.CTkLabel(
            self.content_frame,
            text="Key Findings:",
            font=self.theme.get_body_font(),
            text_color=self.theme.colors.accent_blue
        )
        findings_label.grid(row=3, column=0, sticky="w", padx=5, pady=(10, 0))
        
        findings_text = ctk.CTkTextbox(
            self.content_frame,
            height=60,
            wrap="word",
            font=self.theme.get_small_font()
        )
        findings_text.grid(row=4, column=0, sticky="ew", padx=5, pady=5)
        
        # Format findings
        findings_content = "\n".join(f"• {finding}" for finding in self.step.findings)
        findings_text.insert("1.0", findings_content)
        findings_text.configure(state="disabled")
        
    def _apply_phase_styling(self):
        """Apply semantic styling based on reasoning phase."""
        phase_colors = {
            ReasoningPhase.ANALYZING_INPUT: "#555555",      # Gray for initial analysis
            ReasoningPhase.IDENTIFYING_INTENT: "#1976D2",   # Blue for active reasoning  
            ReasoningPhase.EXTRACTING_ENTITIES: "#1976D2",  # Blue for active reasoning
            ReasoningPhase.SELECTING_TEMPLATE: "#1976D2",   # Blue for active reasoning
            ReasoningPhase.GENERATING_REQUEST: "#388E3C",   # Green for conclusions
            ReasoningPhase.COMPLETED: "#388E3C",            # Green for completion
            ReasoningPhase.ERROR: "#D32F2F"                 # Red for errors
        }
        
        phase_color = phase_colors.get(self.step.phase, self.theme.colors.border)
        
        # Apply border color to indicate phase
        self.configure(border_color=phase_color, border_width=2)
        self.step_indicator.configure(
            fg_color=phase_color,
            text_color="#FFFFFF"
        )
        
    def toggle_content(self):
        """Toggle content visibility."""
        if self.is_expanded:
            self.content_frame.grid_remove()
            self.expand_button.configure(text="▶")
            self.is_expanded = False
        else:
            self.content_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
            self.expand_button.configure(text="▼")
            self.is_expanded = True
            
    def update_content(self, content: str):
        """Update step content.
        
        Args:
            content: New content text
        """
        self.step.content = content
        
        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", "end")
        self.content_text.insert("1.0", content)
        self.content_text.configure(state="disabled")
        
    def set_processing(self, processing: bool):
        """Set processing animation state.
        
        Args:
            processing: Whether step is currently processing
        """
        self.is_processing = processing
        if processing:
            self._start_processing_animation()
        else:
            self._stop_processing_animation()
            
    def _start_processing_animation(self):
        """Start processing animation."""
        self._animate_processing(0)
        
    def _animate_processing(self, frame: int):
        """Animate processing indicator.
        
        Args:
            frame: Current animation frame
        """
        if not self.is_processing:
            return
            
        # Animate step indicator background
        colors = ["#1976D2", "#2196F3", "#64B5F6", "#2196F3"]
        color = colors[frame % len(colors)]
        self.step_indicator.configure(fg_color=color)
        
        # Schedule next frame
        self.after(500, lambda: self._animate_processing(frame + 1))
        
    def _stop_processing_animation(self):
        """Stop processing animation."""
        self._apply_phase_styling()


class RealtimeReasoningDisplay(ctk.CTkScrollableFrame):
    """Real-time Chain of Thought reasoning display with streaming visualization."""
    
    def __init__(self, parent, theme: Theme):
        """Initialize real-time reasoning display.
        
        Args:
            parent: Parent widget
            theme: Theme configuration
        """
        super().__init__(parent)
        
        self.theme = theme
        self.logger = LoggingManager.get_logger(__name__)
        
        # Reasoning state
        self.reasoning_parser = ReasoningParser()
        self.current_trace: Optional[ReasoningTrace] = None
        self.step_widgets: List[ReasoningStepWidget] = []
        
        # Threading for real-time updates
        self.update_queue: queue.Queue = queue.Queue()
        self.update_thread: Optional[threading.Thread] = None
        self.is_updating = False
        
        # Callbacks
        self.on_reasoning_complete: Optional[Callable[[ReasoningTrace], None]] = None
        self.on_step_added: Optional[Callable[[ReasoningStep], None]] = None
        
        self.grid_columnconfigure(0, weight=1)
        
        self._setup_header()
        self._setup_parser_callbacks()
        self._start_update_processing()
        
    def _setup_header(self):
        """Setup display header with controls."""
        self.header_frame = ctk.CTkFrame(self, height=50)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))
        self.header_frame.grid_propagate(False)
        self.header_frame.grid_columnconfigure(2, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            self.header_frame,
            text="Chain of Thought Reasoning",
            font=self.theme.get_header_font(),
            text_color=self.theme.colors.text_primary
        )
        title_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Status indicator
        self.status_label = ctk.CTkLabel(
            self.header_frame,
            text="Ready",
            font=self.theme.get_small_font(),
            text_color=self.theme.colors.text_muted
        )
        self.status_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # Overall confidence display
        self.overall_confidence = ConfidenceBadge(self.header_frame, self.theme, 0.0)
        self.overall_confidence.grid(row=0, column=3, padx=5, pady=10, sticky="e")
        
        # Control buttons frame
        controls_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        controls_frame.grid(row=0, column=4, padx=5, pady=10, sticky="e")
        
        # Export button
        self.export_button = ctk.CTkButton(
            controls_frame,
            text="Export",
            width=60,
            height=25,
            command=self.export_reasoning,
            font=self.theme.get_small_font()
        )
        self.export_button.grid(row=0, column=0, padx=2)
        
        # Collapse all button
        self.collapse_button = ctk.CTkButton(
            controls_frame,
            text="Collapse",
            width=60,
            height=25,
            command=self.collapse_all,
            font=self.theme.get_small_font()
        )
        self.collapse_button.grid(row=0, column=1, padx=2)
        
        # Clear button
        self.clear_button = ctk.CTkButton(
            controls_frame,
            text="Clear",
            width=60,
            height=25,
            command=self.clear,
            font=self.theme.get_small_font()
        )
        self.clear_button.grid(row=0, column=2, padx=2)
        
    def _setup_parser_callbacks(self):
        """Setup reasoning parser callbacks."""
        self.reasoning_parser.on_step_parsed = self._on_step_parsed
        self.reasoning_parser.on_phase_change = self._on_phase_change
        self.reasoning_parser.on_confidence_update = self._on_confidence_update
        
    def _start_update_processing(self):
        """Start background thread for processing UI updates."""
        self.is_updating = True
        self.update_thread = threading.Thread(
            target=self._process_updates,
            daemon=True,
            name="ReasoningDisplayUpdater"
        )
        self.update_thread.start()
        
    def _process_updates(self):
        """Process queued UI updates in background thread."""
        while self.is_updating:
            try:
                # Process up to 10 updates per cycle
                updates_processed = 0
                while not self.update_queue.empty() and updates_processed < 10:
                    try:
                        update_func = self.update_queue.get_nowait()
                        # Schedule UI update on main thread
                        self.after_idle(update_func)
                        updates_processed += 1
                    except queue.Empty:
                        break
                        
                # Sleep briefly to prevent excessive CPU usage
                time.sleep(0.05)  # 20 FPS update rate
                
            except Exception as e:
                self.logger.error(f"Error processing reasoning display updates: {e}")
                
    def start_reasoning(self, session_id: str):
        """Start a new reasoning session.
        
        Args:
            session_id: Unique session identifier
        """
        self.logger.info(f"Starting reasoning display for session: {session_id}")
        
        # Clear previous reasoning
        self.clear()
        
        # Start parser
        self.current_trace = self.reasoning_parser.start_parsing(session_id)
        
        # Update status
        self._queue_update(lambda: self.status_label.configure(text="Processing..."))
        
    def add_content_chunk(self, content: str):
        """Add streaming content chunk for processing.
        
        Args:
            content: Content chunk from LLM stream
        """
        if not self.current_trace:
            self.logger.warning("No active reasoning session")
            return
            
        # Process chunk in background
        threading.Thread(
            target=self._process_content_chunk,
            args=(content,),
            daemon=True
        ).start()
        
    def add_step(self, title: str, content: str, confidence: float = 0.0, phase: Optional[ReasoningPhase] = None):
        """Add a reasoning step directly.
        
        Args:
            title: Step title
            content: Step content
            confidence: Confidence level (0.0-1.0)
            phase: Reasoning phase (defaults to current phase)
        """
        if not self.current_trace:
            # Start a default session if none exists
            self.start_reasoning("direct_step_session")
            
        if phase is None:
            phase = self.current_trace.current_phase if self.current_trace else ReasoningPhase.ANALYZING_INPUT
            
        # Create step
        step = ReasoningStep(
            phase=phase,
            title=title,
            content=content,
            confidence=confidence,
            is_complete=True
        )
        
        # Add step to trace and notify callbacks
        if self.current_trace:
            self.current_trace.add_step(step)
            
            # Add step widget directly
            self._queue_update(lambda: self._add_step_widget(step))
            
            # Trigger callbacks
            if self.on_step_added:
                try:
                    self.on_step_added(step)
                except Exception as e:
                    self.logger.error(f"Error in step added callback: {e}")
                    
            # Update confidence if needed
            if self.current_trace.overall_confidence > 0:
                self._queue_update(lambda: self.overall_confidence.update_confidence(self.current_trace.overall_confidence))
        
    def _process_content_chunk(self, content: str):
        """Process content chunk in background.
        
        Args:
            content: Content chunk to process
        """
        try:
            new_steps = self.reasoning_parser.add_content_chunk(content)
            # Steps will be added via callbacks
        except Exception as e:
            self.logger.error(f"Error processing content chunk: {e}")
            
    def _on_step_parsed(self, step: ReasoningStep):
        """Handle parsed reasoning step.
        
        Args:
            step: Newly parsed reasoning step
        """
        self._queue_update(lambda: self._add_step_widget(step))
        
        # Notify callback
        if self.on_step_added:
            try:
                self.on_step_added(step)
            except Exception as e:
                self.logger.error(f"Error in step added callback: {e}")
                
    def _on_phase_change(self, phase: ReasoningPhase):
        """Handle reasoning phase change.
        
        Args:
            phase: New reasoning phase
        """
        phase_name = phase.value.replace('_', ' ').title()
        self._queue_update(lambda: self.status_label.configure(text=f"Phase: {phase_name}"))
        
    def _on_confidence_update(self, confidence: float):
        """Handle overall confidence update.
        
        Args:
            confidence: New confidence value
        """
        self._queue_update(lambda: self.overall_confidence.update_confidence(confidence))
        
    def _queue_update(self, update_func: Callable):
        """Queue UI update for main thread processing.
        
        Args:
            update_func: Function to execute on main thread
        """
        try:
            self.update_queue.put_nowait(update_func)
        except queue.Full:
            self.logger.warning("Reasoning display update queue full")
            
    def _add_step_widget(self, step: ReasoningStep):
        """Add step widget to display.
        
        Args:
            step: Reasoning step to add
        """
        step_number = len(self.step_widgets) + 1
        
        step_widget = ReasoningStepWidget(
            self, 
            self.theme, 
            step, 
            step_number
        )
        step_widget.grid(
            row=step_number, 
            column=0, 
            sticky="ew", 
            padx=0, 
            pady=(0, 5)
        )
        
        self.step_widgets.append(step_widget)
        
        # Auto-scroll to latest step
        self._scroll_to_bottom()
        
    def _scroll_to_bottom(self):
        """Scroll to show latest reasoning step."""
        self.after(100, self._update_scroll)
        
    def _update_scroll(self):
        """Update scroll position to bottom."""
        try:
            self.update_idletasks()
            # Scroll to bottom
            self._parent_canvas.yview_moveto(1.0)
        except Exception as e:
            # Handle cases where canvas might not be available
            pass
            
    def complete_reasoning(self):
        """Complete current reasoning session."""
        if not self.current_trace:
            return
            
        # Complete parsing
        completed_trace = self.reasoning_parser.complete_parsing()
        
        if completed_trace:
            # Update status
            duration = completed_trace.get_duration()
            self._queue_update(
                lambda: self.status_label.configure(
                    text=f"Completed ({duration:.1f}s, {len(completed_trace.steps)} steps)"
                )
            )
            
            # Notify callback
            if self.on_reasoning_complete:
                try:
                    self.on_reasoning_complete(completed_trace)
                except Exception as e:
                    self.logger.error(f"Error in reasoning complete callback: {e}")
                    
    def export_reasoning(self):
        """Export reasoning trace to file."""
        if not self.current_trace or not self.current_trace.steps:
            messagebox.showwarning("Export", "No reasoning steps to export.")
            return
            
        # Ask user for file location
        file_path = filedialog.asksaveasfilename(
            title="Export Reasoning Trace",
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
            
        try:
            # Determine format from extension
            if file_path.lower().endswith('.json'):
                content = self.reasoning_parser.export_trace(self.current_trace, "json")
            else:
                content = self.reasoning_parser.export_trace(self.current_trace, "text")
                
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            messagebox.showinfo("Export", f"Reasoning trace exported to:\n{file_path}")
            
        except Exception as e:
            self.logger.error(f"Error exporting reasoning trace: {e}")
            messagebox.showerror("Export Error", f"Failed to export reasoning trace:\n{e}")
            
    def collapse_all(self):
        """Collapse all reasoning steps."""
        for step_widget in self.step_widgets:
            if step_widget.is_expanded:
                step_widget.toggle_content()
                
    def expand_all(self):
        """Expand all reasoning steps."""
        for step_widget in self.step_widgets:
            if not step_widget.is_expanded:
                step_widget.toggle_content()
                
    def clear(self):
        """Clear all reasoning display."""
        # Clear step widgets
        for step_widget in self.step_widgets:
            step_widget.destroy()
            
        self.step_widgets.clear()
        
        # Reset state
        self.current_trace = None
        
        # Reset UI
        self.status_label.configure(text="Ready")
        self.overall_confidence.update_confidence(0.0)
        
    def cleanup(self):
        """Cleanup resources and stop threads."""
        self.logger.info("Cleaning up reasoning display")
        
        # Stop update processing
        self.is_updating = False
        
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)
            
        # Clear display
        self.clear()
        
    def get_current_trace(self) -> Optional[ReasoningTrace]:
        """Get current reasoning trace.
        
        Returns:
            Current reasoning trace or None
        """
        return self.current_trace
        
    def get_step_count(self) -> int:
        """Get number of displayed reasoning steps.
        
        Returns:
            Number of steps
        """
        return len(self.step_widgets)