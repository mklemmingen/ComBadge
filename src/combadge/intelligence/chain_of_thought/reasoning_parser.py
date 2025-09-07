"""Reasoning Parser for Real-time Chain of Thought Display

Parses streaming LLM responses to identify reasoning steps, extract confidence 
indicators, detect decision points, and format content for display visualization.
"""

import json
import re
import time
import threading
import queue
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ...core.logging_manager import LoggingManager


class ReasoningPhase(Enum):
    """Phases of reasoning process."""
    ANALYZING_INPUT = "analyzing_input"
    IDENTIFYING_INTENT = "identifying_intent"
    EXTRACTING_ENTITIES = "extracting_entities"
    SELECTING_TEMPLATE = "selecting_template"
    GENERATING_REQUEST = "generating_request"
    COMPLETED = "completed"
    ERROR = "error"


class ConfidenceLevel(Enum):
    """Confidence level indicators."""
    HIGH = "high"        # 80-100%
    MEDIUM = "medium"    # 60-79%
    LOW = "low"         # 40-59%
    VERY_LOW = "very_low"  # 0-39%


@dataclass
class ReasoningStep:
    """Represents a single step in the reasoning process."""
    phase: ReasoningPhase
    title: str
    content: str
    confidence: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    timestamp: float = field(default_factory=time.time)
    entities: Optional[Dict[str, Any]] = None
    findings: Optional[List[str]] = None
    is_complete: bool = False
    
    def __post_init__(self):
        """Post-initialization to set confidence level."""
        self.confidence_level = self._calculate_confidence_level()
        
    def _calculate_confidence_level(self) -> ConfidenceLevel:
        """Calculate confidence level from numeric confidence."""
        if self.confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.6:
            return ConfidenceLevel.MEDIUM
        elif self.confidence >= 0.4:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


@dataclass
class ReasoningTrace:
    """Complete reasoning trace with all steps."""
    session_id: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    steps: List[ReasoningStep] = field(default_factory=list)
    current_phase: ReasoningPhase = ReasoningPhase.ANALYZING_INPUT
    overall_confidence: float = 0.0
    raw_content: str = ""
    parsed_api_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_step(self, step: ReasoningStep):
        """Add a reasoning step and update current phase."""
        self.steps.append(step)
        self.current_phase = step.phase
        self._update_overall_confidence()
        
    def _update_overall_confidence(self):
        """Update overall confidence based on completed steps."""
        if not self.steps:
            self.overall_confidence = 0.0
            return
            
        completed_steps = [s for s in self.steps if s.is_complete and s.confidence > 0]
        if completed_steps:
            self.overall_confidence = sum(s.confidence for s in completed_steps) / len(completed_steps)
            
    def complete(self):
        """Mark reasoning trace as completed."""
        self.end_time = time.time()
        self.current_phase = ReasoningPhase.COMPLETED
        
    def get_duration(self) -> float:
        """Get total reasoning duration."""
        end = self.end_time or time.time()
        return end - self.start_time


class ReasoningParser:
    """Parser for streaming LLM responses with Chain of Thought reasoning."""
    
    def __init__(self):
        """Initialize reasoning parser."""
        self.logger = LoggingManager.get_logger(__name__)
        
        # Current parsing state
        self.current_trace: Optional[ReasoningTrace] = None
        self.accumulated_content = ""
        self.current_json_buffer = ""
        
        # Phase detection patterns
        self.phase_patterns = {
            ReasoningPhase.ANALYZING_INPUT: [
                r"analyzing?\s+input",
                r"examining\s+the\s+request",
                r"understanding\s+the\s+query",
                r"parsing\s+user\s+input"
            ],
            ReasoningPhase.IDENTIFYING_INTENT: [
                r"identifying?\s+intent",
                r"determining\s+purpose",
                r"recognizing\s+the\s+goal",
                r"intent\s+recognition"
            ],
            ReasoningPhase.EXTRACTING_ENTITIES: [
                r"extracting\s+entities",
                r"finding\s+key\s+information",
                r"identifying\s+parameters",
                r"entity\s+extraction"
            ],
            ReasoningPhase.SELECTING_TEMPLATE: [
                r"selecting\s+template",
                r"choosing\s+API\s+endpoint",
                r"mapping\s+to\s+API",
                r"template\s+selection"
            ],
            ReasoningPhase.GENERATING_REQUEST: [
                r"generating\s+request",
                r"creating\s+API\s+call",
                r"building\s+the\s+request",
                r"request\s+generation"
            ]
        }
        
        # Confidence extraction patterns
        self.confidence_patterns = [
            r"confidence:?\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)%?\s*confidence",
            r"certainty:?\s*(\d+(?:\.\d+)?)",
            r"score:?\s*(\d+(?:\.\d+)?)"
        ]
        
        # Entity patterns
        self.entity_patterns = {
            "resource_ids": r"\b[A-Z]{2,4}-\d{3,4}\b|\b[A-Z]{3,4}\d{3}\b",
            "dates": r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}\/\d{1,2}\/\d{4}\b",
            "times": r"\b\d{1,2}:\d{2}(?::\d{2})?\b|\b\d{1,2}(?:am|pm)\b",
            "emails": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
        }
        
        # Callbacks for real-time updates
        self.on_step_parsed: Optional[Callable[[ReasoningStep], None]] = None
        self.on_phase_change: Optional[Callable[[ReasoningPhase], None]] = None
        self.on_confidence_update: Optional[Callable[[float], None]] = None
        
    def start_parsing(self, session_id: str) -> ReasoningTrace:
        """Start parsing a new reasoning session.
        
        Args:
            session_id: Unique identifier for this reasoning session
            
        Returns:
            New reasoning trace instance
        """
        self.current_trace = ReasoningTrace(session_id=session_id)
        self.accumulated_content = ""
        self.current_json_buffer = ""
        
        self.logger.info(f"Started reasoning parsing session: {session_id}")
        return self.current_trace
        
    def add_content_chunk(self, content: str) -> List[ReasoningStep]:
        """Add a chunk of streaming content and parse for reasoning steps.
        
        Args:
            content: Content chunk from LLM stream
            
        Returns:
            List of newly parsed reasoning steps
        """
        if not self.current_trace:
            self.logger.warning("No active parsing session")
            return []
            
        self.accumulated_content += content
        new_steps = []
        
        # Try to parse JSON structures
        json_steps = self._parse_json_reasoning(content)
        new_steps.extend(json_steps)
        
        # Try to parse text-based reasoning
        text_steps = self._parse_text_reasoning(content)
        new_steps.extend(text_steps)
        
        # Add steps to trace and notify callbacks
        for step in new_steps:
            self.current_trace.add_step(step)
            
            if self.on_step_parsed:
                try:
                    self.on_step_parsed(step)
                except Exception as e:
                    self.logger.error(f"Error in step parsed callback: {e}")
                    
            if self.on_phase_change and step.phase != self.current_trace.current_phase:
                try:
                    self.on_phase_change(step.phase)
                except Exception as e:
                    self.logger.error(f"Error in phase change callback: {e}")
                    
        # Update overall confidence
        if self.on_confidence_update and self.current_trace.overall_confidence > 0:
            try:
                self.on_confidence_update(self.current_trace.overall_confidence)
            except Exception as e:
                self.logger.error(f"Error in confidence update callback: {e}")
                
        return new_steps
        
    def _parse_json_reasoning(self, content: str) -> List[ReasoningStep]:
        """Parse JSON-structured reasoning from content.
        
        Args:
            content: Content chunk to parse
            
        Returns:
            List of parsed reasoning steps
        """
        steps = []
        
        # Add to JSON buffer
        self.current_json_buffer += content
        
        # Try to find complete JSON objects
        json_pattern = r'\{(?:[^{}]|{[^{}]*})*\}'
        matches = re.finditer(json_pattern, self.current_json_buffer)
        
        for match in matches:
            json_str = match.group(0)
            
            try:
                data = json.loads(json_str)
                
                # Check if this looks like Chain of Thought JSON
                if "chain_of_thought" in data:
                    chain_steps = data["chain_of_thought"]
                    
                    for step_data in chain_steps:
                        step = self._create_step_from_json(step_data)
                        if step:
                            steps.append(step)
                            
                # Clear processed JSON from buffer
                self.current_json_buffer = self.current_json_buffer[match.end():]
                
            except json.JSONDecodeError:
                continue
                
        return steps
        
    def _parse_text_reasoning(self, content: str) -> List[ReasoningStep]:
        """Parse text-based reasoning patterns.
        
        Args:
            content: Content chunk to parse
            
        Returns:
            List of parsed reasoning steps
        """
        steps = []
        
        # Detect reasoning phases
        detected_phase = self._detect_phase(content)
        if detected_phase and detected_phase != self.current_trace.current_phase:
            
            # Create step for phase transition
            step = ReasoningStep(
                phase=detected_phase,
                title=self._get_phase_title(detected_phase),
                content=content.strip(),
                confidence=self._extract_confidence(content)
            )
            
            # Extract entities if in appropriate phase
            if detected_phase == ReasoningPhase.EXTRACTING_ENTITIES:
                step.entities = self._extract_entities(content)
                
            steps.append(step)
            
        return steps
        
    def _create_step_from_json(self, step_data: Dict[str, Any]) -> Optional[ReasoningStep]:
        """Create reasoning step from JSON data.
        
        Args:
            step_data: JSON data for the step
            
        Returns:
            ReasoningStep instance or None if invalid
        """
        try:
            step_name = step_data.get("step", "").lower()
            phase = self._map_step_to_phase(step_name)
            
            step = ReasoningStep(
                phase=phase,
                title=step_data.get("step", "Unknown Step"),
                content=step_data.get("reasoning", ""),
                confidence=step_data.get("confidence", 0.0),
                entities=step_data.get("entities"),
                findings=step_data.get("findings"),
                is_complete=True
            )
            
            return step
            
        except Exception as e:
            self.logger.error(f"Error creating step from JSON: {e}")
            return None
            
    def _detect_phase(self, content: str) -> Optional[ReasoningPhase]:
        """Detect reasoning phase from content.
        
        Args:
            content: Content to analyze
            
        Returns:
            Detected phase or None
        """
        content_lower = content.lower()
        
        for phase, patterns in self.phase_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    return phase
                    
        return None
        
    def _map_step_to_phase(self, step_name: str) -> ReasoningPhase:
        """Map step name to reasoning phase.
        
        Args:
            step_name: Name of the step
            
        Returns:
            Corresponding reasoning phase
        """
        step_lower = step_name.lower()
        
        if "input" in step_lower or "analyz" in step_lower:
            return ReasoningPhase.ANALYZING_INPUT
        elif "intent" in step_lower:
            return ReasoningPhase.IDENTIFYING_INTENT
        elif "entit" in step_lower or "extract" in step_lower:
            return ReasoningPhase.EXTRACTING_ENTITIES
        elif "template" in step_lower or "mapping" in step_lower:
            return ReasoningPhase.SELECTING_TEMPLATE
        elif "generat" in step_lower or "request" in step_lower:
            return ReasoningPhase.GENERATING_REQUEST
        else:
            return ReasoningPhase.ANALYZING_INPUT
            
    def _extract_confidence(self, content: str) -> float:
        """Extract confidence value from content.
        
        Args:
            content: Content to search
            
        Returns:
            Confidence value (0.0 to 1.0)
        """
        for pattern in self.confidence_patterns:
            match = re.search(pattern, content.lower())
            if match:
                try:
                    value = float(match.group(1))
                    # Normalize to 0-1 range
                    if value > 1.0:
                        value = value / 100.0
                    return min(1.0, max(0.0, value))
                except (ValueError, IndexError):
                    continue
                    
        return 0.0
        
    def _extract_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract entities from content.
        
        Args:
            content: Content to search
            
        Returns:
            Dictionary of entity types and their values
        """
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                entities[entity_type] = list(set(matches))  # Remove duplicates
                
        return entities
        
    def _get_phase_title(self, phase: ReasoningPhase) -> str:
        """Get display title for reasoning phase.
        
        Args:
            phase: Reasoning phase
            
        Returns:
            Human-readable phase title
        """
        titles = {
            ReasoningPhase.ANALYZING_INPUT: "Analyzing Input",
            ReasoningPhase.IDENTIFYING_INTENT: "Identifying Intent",
            ReasoningPhase.EXTRACTING_ENTITIES: "Extracting Entities",
            ReasoningPhase.SELECTING_TEMPLATE: "Selecting Template",
            ReasoningPhase.GENERATING_REQUEST: "Generating Request",
            ReasoningPhase.COMPLETED: "Completed",
            ReasoningPhase.ERROR: "Error"
        }
        return titles.get(phase, "Unknown Phase")
        
    def complete_parsing(self) -> Optional[ReasoningTrace]:
        """Complete the current parsing session.
        
        Returns:
            Completed reasoning trace or None if no active session
        """
        if not self.current_trace:
            return None
            
        self.current_trace.complete()
        self.current_trace.raw_content = self.accumulated_content
        
        # Try final parse for any remaining content
        if self.accumulated_content:
            self._parse_final_content()
            
        completed_trace = self.current_trace
        self.current_trace = None
        self.accumulated_content = ""
        self.current_json_buffer = ""
        
        self.logger.info(f"Completed reasoning parsing session: {completed_trace.session_id}")
        return completed_trace
        
    def _parse_final_content(self):
        """Perform final parsing of accumulated content."""
        try:
            # Try to parse entire content as JSON
            data = json.loads(self.accumulated_content)
            
            if "summary" in data:
                summary = data["summary"]
                
                # Extract API calls
                if "api_calls" in summary:
                    self.current_trace.parsed_api_calls = summary["api_calls"]
                    
                # Update overall confidence
                if "confidence" in summary:
                    self.current_trace.overall_confidence = summary["confidence"]
                    
        except json.JSONDecodeError:
            # Content is not valid JSON, continue with text parsing
            pass
            
    def export_trace(self, trace: ReasoningTrace, format: str = "text") -> str:
        """Export reasoning trace in specified format.
        
        Args:
            trace: Reasoning trace to export
            format: Export format ("text" or "json")
            
        Returns:
            Formatted trace content
        """
        if format.lower() == "json":
            return self._export_trace_json(trace)
        else:
            return self._export_trace_text(trace)
            
    def _export_trace_text(self, trace: ReasoningTrace) -> str:
        """Export trace as formatted text.
        
        Args:
            trace: Reasoning trace to export
            
        Returns:
            Formatted text representation
        """
        lines = [
            f"ComBadge Reasoning Trace",
            f"Session ID: {trace.session_id}",
            f"Start Time: {datetime.fromtimestamp(trace.start_time)}",
            f"Duration: {trace.get_duration():.2f} seconds",
            f"Overall Confidence: {trace.overall_confidence:.1%}",
            f"Steps: {len(trace.steps)}",
            "",
            "=" * 50,
            ""
        ]
        
        for i, step in enumerate(trace.steps, 1):
            lines.extend([
                f"Step {i}: {step.title}",
                f"Phase: {step.phase.value.replace('_', ' ').title()}",
                f"Confidence: {step.confidence:.1%} ({step.confidence_level.value})",
                f"Timestamp: {datetime.fromtimestamp(step.timestamp)}",
                "",
                step.content,
                ""
            ])
            
            if step.entities:
                lines.append("Entities:")
                for entity_type, values in step.entities.items():
                    lines.append(f"  {entity_type}: {', '.join(values)}")
                lines.append("")
                
            if step.findings:
                lines.append("Findings:")
                for finding in step.findings:
                    lines.append(f"  - {finding}")
                lines.append("")
                
            lines.append("-" * 30)
            lines.append("")
            
        if trace.parsed_api_calls:
            lines.extend([
                "Generated API Calls:",
                "",
                json.dumps(trace.parsed_api_calls, indent=2)
            ])
            
        return "\n".join(lines)
        
    def _export_trace_json(self, trace: ReasoningTrace) -> str:
        """Export trace as JSON.
        
        Args:
            trace: Reasoning trace to export
            
        Returns:
            JSON representation
        """
        trace_data = {
            "session_id": trace.session_id,
            "start_time": trace.start_time,
            "end_time": trace.end_time,
            "duration": trace.get_duration(),
            "current_phase": trace.current_phase.value,
            "overall_confidence": trace.overall_confidence,
            "steps": [
                {
                    "phase": step.phase.value,
                    "title": step.title,
                    "content": step.content,
                    "confidence": step.confidence,
                    "confidence_level": step.confidence_level.value,
                    "timestamp": step.timestamp,
                    "entities": step.entities,
                    "findings": step.findings,
                    "is_complete": step.is_complete
                }
                for step in trace.steps
            ],
            "api_calls": trace.parsed_api_calls,
            "raw_content": trace.raw_content
        }
        
        return json.dumps(trace_data, indent=2)
        
    def get_phase_summary(self, trace: ReasoningTrace) -> Dict[str, Any]:
        """Get summary of reasoning phases.
        
        Args:
            trace: Reasoning trace to summarize
            
        Returns:
            Phase summary statistics
        """
        phase_stats = {}
        
        for phase in ReasoningPhase:
            phase_steps = [s for s in trace.steps if s.phase == phase]
            if phase_steps:
                phase_stats[phase.value] = {
                    "count": len(phase_steps),
                    "avg_confidence": sum(s.confidence for s in phase_steps) / len(phase_steps),
                    "duration": max(s.timestamp for s in phase_steps) - min(s.timestamp for s in phase_steps)
                }
                
        return phase_stats