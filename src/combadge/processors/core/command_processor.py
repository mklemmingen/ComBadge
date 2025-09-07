"""Command Processor for Fleet Management Direct Commands

Intelligent command parsing that handles direct user commands, imperative statements,
parameter extraction, and command sequence processing for fleet management operations.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ...core.logging_manager import LoggingManager


class CommandType(Enum):
    """Types of direct commands."""
    SCHEDULE = "schedule"          # Schedule maintenance, inspections
    ASSIGN = "assign"             # Assign drivers, routes, vehicles
    UPDATE = "update"             # Update status, information
    REQUEST = "request"           # Request reports, information
    CREATE = "create"             # Create new records
    CANCEL = "cancel"             # Cancel operations
    MOVE = "move"                 # Move vehicles, relocate
    SET = "set"                   # Set parameters, configurations
    UNKNOWN = "unknown"


class CommandPriority(Enum):
    """Command priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class CommandStatus(Enum):
    """Command processing status."""
    PARSED = "parsed"
    VALIDATED = "validated"
    ERROR = "error"
    INCOMPLETE = "incomplete"


@dataclass
class CommandParameter:
    """Individual command parameter."""
    name: str
    value: str
    parameter_type: str
    confidence: float = 0.0
    validation_notes: List[str] = field(default_factory=list)


@dataclass
class CommandSequence:
    """Information about command sequences."""
    sequence_count: int = 1
    sequence_index: int = 0
    is_sequential: bool = False
    dependencies: List[str] = field(default_factory=list)
    coordination_required: bool = False


@dataclass
class CommandParseResult:
    """Complete command parsing result."""
    command_type: CommandType
    action_verb: str
    primary_object: Optional[str] = None
    parameters: List[CommandParameter] = field(default_factory=list)
    command_sequence: Optional[CommandSequence] = None
    priority: CommandPriority = CommandPriority.MEDIUM
    status: CommandStatus = CommandStatus.PARSED
    parsing_confidence: float = 0.0
    parsing_notes: List[str] = field(default_factory=list)
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    raw_command: str = ""


class CommandProcessor:
    """Advanced command parser for fleet management direct commands."""
    
    def __init__(self):
        """Initialize command processor with patterns and configurations."""
        self.logger = LoggingManager.get_logger(__name__)
        
        # Command type detection patterns
        self.command_patterns = self._build_command_patterns()
        
        # Action verb patterns
        self.verb_patterns = self._build_verb_patterns()
        
        # Parameter extraction patterns
        self.parameter_patterns = self._build_parameter_patterns()
        
        # Priority detection patterns
        self.priority_patterns = self._build_priority_patterns()
        
        # Sequence detection patterns
        self.sequence_patterns = self._build_sequence_patterns()
        
        # Object identification patterns
        self.object_patterns = self._build_object_patterns()
        
    def _build_command_patterns(self) -> Dict[CommandType, List[str]]:
        """Build patterns to detect command types.
        
        Returns:
            Dictionary mapping command types to detection patterns
        """
        return {
            CommandType.SCHEDULE: [
                r"schedule\s+(?:maintenance|inspection|service|repair)",
                r"book\s+(?:maintenance|service)",
                r"plan\s+(?:maintenance|inspection)",
                r"arrange\s+(?:maintenance|service)",
                r"set up\s+(?:maintenance|inspection)",
                r"(?:maintenance|service|inspection)\s+(?:for|on)"
            ],
            
            CommandType.ASSIGN: [
                r"assign\s+(?:driver|vehicle|route)",
                r"allocate\s+(?:driver|vehicle)",
                r"designate\s+(?:driver|vehicle)",
                r"give\s+(?:driver|vehicle)",
                r"put\s+(?:driver)\s+(?:in|on)",
                r"route\s+(?:vehicle|driver)\s+to"
            ],
            
            CommandType.UPDATE: [
                r"update\s+(?:status|information|record)",
                r"change\s+(?:status|information)",
                r"modify\s+(?:record|status)",
                r"set\s+status\s+to",
                r"mark\s+(?:as|vehicle|driver)",
                r"record\s+(?:maintenance|repair|issue)"
            ],
            
            CommandType.REQUEST: [
                r"(?:get|fetch|retrieve|show|display)\s+(?:report|information|status)",
                r"(?:generate|create|produce)\s+report",
                r"(?:list|show)\s+(?:all|vehicles|drivers)",
                r"what\s+(?:is|are)\s+(?:the|status)",
                r"how\s+(?:many|much)",
                r"when\s+(?:is|was|will)"
            ],
            
            CommandType.CREATE: [
                r"(?:create|add|register)\s+(?:new|vehicle|driver)",
                r"(?:add|insert)\s+(?:record|entry)",
                r"register\s+(?:vehicle|driver|equipment)",
                r"set up\s+(?:new|vehicle|driver)",
                r"establish\s+(?:record|account)",
                r"initialize\s+(?:vehicle|system)"
            ],
            
            CommandType.CANCEL: [
                r"cancel\s+(?:maintenance|service|appointment)",
                r"(?:abort|stop|halt)\s+(?:operation|maintenance)",
                r"postpone\s+(?:maintenance|service)",
                r"reschedule\s+(?:maintenance|service)",
                r"remove\s+(?:appointment|schedule)",
                r"delete\s+(?:appointment|booking)"
            ],
            
            CommandType.MOVE: [
                r"(?:move|relocate|transfer)\s+vehicle",
                r"send\s+vehicle\s+to",
                r"dispatch\s+vehicle",
                r"route\s+vehicle\s+to",
                r"deliver\s+vehicle\s+to",
                r"transport\s+vehicle"
            ],
            
            CommandType.SET: [
                r"set\s+(?:parameter|configuration|limit)",
                r"configure\s+(?:system|vehicle|driver)",
                r"adjust\s+(?:settings|parameters)",
                r"define\s+(?:limit|rule|parameter)",
                r"establish\s+(?:limit|rule)",
                r"specify\s+(?:value|parameter)"
            ]
        }
    
    def _build_verb_patterns(self) -> Dict[str, List[str]]:
        """Build patterns for action verb extraction.
        
        Returns:
            Dictionary mapping verb categories to patterns
        """
        return {
            "action": [
                r"\b(schedule|book|plan|arrange|set up|assign|allocate|designate|give|put|route|update|change|modify|set|mark|record)\b",
                r"\b(get|fetch|retrieve|show|display|generate|create|produce|list|add|register|insert|establish|initialize)\b",
                r"\b(cancel|abort|stop|halt|postpone|reschedule|remove|delete|move|relocate|transfer|send|dispatch)\b",
                r"\b(deliver|transport|configure|adjust|define|specify)\b"
            ],
            "modal": [
                r"\b(should|must|need|want|would like|please|can you|could you)\b",
                r"\b(have to|ought to|supposed to)\b"
            ]
        }
    
    def _build_parameter_patterns(self) -> Dict[str, str]:
        """Build regex patterns for parameter extraction.
        
        Returns:
            Dictionary mapping parameter types to patterns
        """
        return {
            "vehicle_id": r"(?:vehicle|VIN|vin)\s*(?:id|number|#)?\s*[:=]?\s*([A-Z0-9]{17}|[A-Z]{2,3}-?\d{3,4}|[A-Z0-9-]{5,15})",
            "driver_id": r"(?:driver|employee)\s*(?:id|number|#)?\s*[:=]?\s*([A-Z0-9-]{3,15})",
            "license_plate": r"(?:license|plate|registration)\s*(?:number|#)?\s*[:=]?\s*([A-Z0-9-]{2,10})",
            "datetime": r"(?:on|at|by|for|next|this|tomorrow|yesterday)\s+([A-Za-z]+day|tomorrow|today|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]+|\d{1,2}:\d{2}(?:\s*[APap][Mm])?)",
            "location": r"(?:at|to|from|in|near)\s+([A-Za-z\s,.-]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln|way|place|pl|court|ct|circle|cir|depot|garage|station))",
            "maintenance_type": r"(?:maintenance|service|inspection|repair)\s+(?:type|category)?\s*[:=]?\s*(oil change|brake|tire|engine|transmission|electrical|routine|safety|emergency)",
            "priority": r"(?:priority|urgency|importance)\s*[:=]?\s*(low|medium|high|urgent|critical|asap|immediately)",
            "status": r"(?:status|state|condition)\s*[:=]?\s*(active|inactive|available|unavailable|maintenance|repair|out of service|in service)",
            "duration": r"(?:for|duration|lasting)\s+(\d+\s*(?:hour|hr|minute|min|day|week|month)s?)",
            "cost": r"(?:cost|price|amount|budget)\s*[:=]?\s*\$?(\d+(?:\.\d{2})?)",
            "mileage": r"(?:mileage|miles|odometer)\s*[:=]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:miles|mi|km)?",
            "fuel": r"(?:fuel|gas|diesel)\s+(?:level|amount|type)\s*[:=]?\s*(\d+%?|full|empty|half|quarter|unleaded|diesel|premium)"
        }
    
    def _build_priority_patterns(self) -> Dict[CommandPriority, List[str]]:
        """Build patterns to detect command priority.
        
        Returns:
            Dictionary mapping priorities to detection patterns
        """
        return {
            CommandPriority.LOW: [
                r"\b(?:low|routine|standard|normal|regular|whenever)\b",
                r"\b(?:when convenient|no rush|take your time)\b"
            ],
            
            CommandPriority.MEDIUM: [
                r"\b(?:medium|average|typical|soon|shortly)\b",
                r"\b(?:within.*week|next week|this week)\b"
            ],
            
            CommandPriority.HIGH: [
                r"\b(?:high|important|priority|urgent|quickly|fast)\b",
                r"\b(?:today|tomorrow|this afternoon|by.*end of day)\b"
            ],
            
            CommandPriority.URGENT: [
                r"\b(?:urgent|critical|emergency|asap|immediately|right away)\b",
                r"\b(?:now|right now|urgent|critical|breakdown|emergency)\b"
            ]
        }
    
    def _build_sequence_patterns(self) -> List[Dict[str, Any]]:
        """Build patterns to detect command sequences.
        
        Returns:
            List of sequence detection patterns
        """
        return [
            {
                "pattern": r"\b(?:then|after|next|following|subsequently)\b",
                "type": "sequential",
                "confidence": 0.8
            },
            {
                "pattern": r"\b(?:and|also|additionally|plus|as well)\b",
                "type": "parallel",
                "confidence": 0.6
            },
            {
                "pattern": r"\b(?:first|second|third|finally|lastly)\b",
                "type": "ordered",
                "confidence": 0.9
            },
            {
                "pattern": r"\b(?:before|prior to|after completing)\b",
                "type": "dependent",
                "confidence": 0.85
            },
            {
                "pattern": r"\b(?:simultaneously|at the same time|concurrently)\b",
                "type": "concurrent",
                "confidence": 0.9
            }
        ]
    
    def _build_object_patterns(self) -> Dict[str, str]:
        """Build patterns for primary object identification.
        
        Returns:
            Dictionary mapping object types to patterns
        """
        return {
            "vehicle": r"\b(?:vehicle|car|truck|van|bus|trailer|fleet)\s+(?:[A-Z0-9-]{3,17})\b",
            "driver": r"\b(?:driver|operator|employee)\s+(?:[A-Z][a-z]+\s+[A-Z][a-z]+|[A-Z0-9-]{3,15})\b",
            "maintenance": r"\b(?:maintenance|service|inspection|repair|oil change|brake service)\b",
            "route": r"\b(?:route|trip|delivery|pickup)\s+(?:[A-Z0-9-]{3,15})\b",
            "location": r"\b(?:location|depot|garage|station|address)\s+(?:[A-Za-z\s,.-]+)\b",
            "schedule": r"\b(?:schedule|appointment|booking|reservation)\b"
        }
    
    def parse_command(self, command_text: str) -> CommandParseResult:
        """Parse command text and extract structured information.
        
        Args:
            command_text: Raw command text content
            
        Returns:
            Complete command parsing result
        """
        self.logger.debug("Starting command parsing")
        
        # Clean and normalize command text
        normalized_command = self._normalize_command(command_text)
        
        # Detect command type
        command_type = self._detect_command_type(normalized_command)
        
        # Extract action verb
        action_verb = self._extract_action_verb(normalized_command)
        
        # Extract primary object
        primary_object = self._extract_primary_object(normalized_command)
        
        # Extract parameters
        parameters = self._extract_parameters(normalized_command)
        
        # Detect priority
        priority = self._detect_priority(normalized_command)
        
        # Analyze command sequence
        command_sequence = self._analyze_command_sequence(normalized_command)
        
        # Validate command structure
        status = self._validate_command_structure(
            command_type, action_verb, primary_object, parameters
        )
        
        # Calculate parsing confidence
        parsing_confidence = self._calculate_parsing_confidence(
            command_type, action_verb, primary_object, parameters, status
        )
        
        # Generate parsing notes
        parsing_notes = self._generate_parsing_notes(
            command_text, normalized_command, command_type, action_verb, parameters
        )
        
        # Create extraction metadata
        extraction_metadata = self._create_extraction_metadata(
            command_text, normalized_command, parameters
        )
        
        result = CommandParseResult(
            command_type=command_type,
            action_verb=action_verb,
            primary_object=primary_object,
            parameters=parameters,
            command_sequence=command_sequence,
            priority=priority,
            status=status,
            parsing_confidence=parsing_confidence,
            parsing_notes=parsing_notes,
            extraction_metadata=extraction_metadata,
            raw_command=command_text
        )
        
        self.logger.info(
            f"Command parsing complete: type={command_type.value}, "
            f"verb={action_verb}, confidence={parsing_confidence:.2f}"
        )
        
        return result
    
    def _normalize_command(self, command_text: str) -> str:
        """Normalize command text for processing.
        
        Args:
            command_text: Raw command text
            
        Returns:
            Normalized command text
        """
        # Convert to lowercase for pattern matching
        normalized = command_text.lower()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Handle common abbreviations
        abbreviations = {
            "vin#": "vin number",
            "emp#": "employee id",
            "veh": "vehicle",
            "maint": "maintenance",
            "svc": "service",
            "asap": "immediately",
            "&": "and"
        }
        
        for abbrev, expansion in abbreviations.items():
            normalized = normalized.replace(abbrev, expansion)
        
        return normalized
    
    def _detect_command_type(self, command_text: str) -> CommandType:
        """Detect command type from content patterns.
        
        Args:
            command_text: Normalized command text
            
        Returns:
            Detected command type
        """
        type_scores = {}
        
        # Check each command type's patterns
        for cmd_type, patterns in self.command_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, command_text, re.IGNORECASE):
                    score += 1
            type_scores[cmd_type] = score
        
        # Return type with highest score
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            if type_scores[best_type] > 0:
                return best_type
        
        return CommandType.UNKNOWN
    
    def _extract_action_verb(self, command_text: str) -> str:
        """Extract primary action verb from command.
        
        Args:
            command_text: Normalized command text
            
        Returns:
            Primary action verb
        """
        # Check action patterns
        for category, patterns in self.verb_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, command_text, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        # Fall back to first verb-like word
        words = command_text.split()
        for word in words:
            if re.match(r'\b\w+(?:e|ing|ed)\b', word):
                return word
        
        return "unknown"
    
    def _extract_primary_object(self, command_text: str) -> Optional[str]:
        """Extract primary object being operated on.
        
        Args:
            command_text: Normalized command text
            
        Returns:
            Primary object identifier or None
        """
        # Check object patterns
        for obj_type, pattern in self.object_patterns.items():
            match = re.search(pattern, command_text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        return None
    
    def _extract_parameters(self, command_text: str) -> List[CommandParameter]:
        """Extract command parameters from text.
        
        Args:
            command_text: Normalized command text
            
        Returns:
            List of extracted parameters
        """
        parameters = []
        
        # Extract each parameter type
        for param_type, pattern in self.parameter_patterns.items():
            matches = re.finditer(pattern, command_text, re.IGNORECASE)
            
            for match in matches:
                # Calculate confidence based on pattern strength
                confidence = self._calculate_parameter_confidence(
                    param_type, match.group(1), command_text
                )
                
                # Validate parameter value
                validation_notes = self._validate_parameter_value(
                    param_type, match.group(1)
                )
                
                parameter = CommandParameter(
                    name=param_type,
                    value=match.group(1).strip(),
                    parameter_type=param_type,
                    confidence=confidence,
                    validation_notes=validation_notes
                )
                
                parameters.append(parameter)
        
        return parameters
    
    def _calculate_parameter_confidence(
        self,
        param_type: str,
        value: str,
        context: str
    ) -> float:
        """Calculate confidence score for parameter extraction.
        
        Args:
            param_type: Type of parameter
            value: Extracted parameter value
            context: Full command context
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.5  # Base confidence
        
        # Type-specific confidence adjustments
        if param_type == "vehicle_id":
            if len(value) == 17 and value.isalnum():  # VIN format
                confidence = 0.95
            elif re.match(r'^[A-Z]{2,3}-?\d{3,4}$', value):  # Fleet ID format
                confidence = 0.9
            else:
                confidence = 0.6
        
        elif param_type == "datetime":
            if "tomorrow" in value or "today" in value:
                confidence = 0.9
            elif re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', value):
                confidence = 0.85
            else:
                confidence = 0.7
        
        elif param_type == "priority":
            if value in ["urgent", "critical", "emergency"]:
                confidence = 0.95
            elif value in ["high", "medium", "low"]:
                confidence = 0.9
            else:
                confidence = 0.6
        
        # Context-based adjustments
        if param_type.lower() in context.lower():
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _validate_parameter_value(self, param_type: str, value: str) -> List[str]:
        """Validate parameter value and return validation notes.
        
        Args:
            param_type: Type of parameter
            value: Parameter value to validate
            
        Returns:
            List of validation notes
        """
        notes = []
        
        if param_type == "vehicle_id":
            if len(value) != 17 and not re.match(r'^[A-Z]{2,3}-?\d{3,4}$', value):
                notes.append("Vehicle ID format may be invalid")
        
        elif param_type == "datetime":
            if not re.match(r'(?:tomorrow|today|\d{1,2}[/-]\d{1,2}|\d{1,2}:\d{2})', value):
                notes.append("Date/time format may need clarification")
        
        elif param_type == "cost":
            try:
                float_value = float(value.replace('$', '').replace(',', ''))
                if float_value < 0:
                    notes.append("Negative cost value")
                elif float_value > 50000:
                    notes.append("Very high cost value - please verify")
            except ValueError:
                notes.append("Invalid cost format")
        
        elif param_type == "mileage":
            try:
                mileage = int(value.replace(',', ''))
                if mileage < 0:
                    notes.append("Negative mileage value")
                elif mileage > 1000000:
                    notes.append("Very high mileage - please verify")
            except ValueError:
                notes.append("Invalid mileage format")
        
        return notes
    
    def _detect_priority(self, command_text: str) -> CommandPriority:
        """Detect command priority from content.
        
        Args:
            command_text: Normalized command text
            
        Returns:
            Detected priority level
        """
        priority_scores = {}
        
        # Check each priority's patterns
        for priority, patterns in self.priority_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, command_text, re.IGNORECASE):
                    score += 1
            priority_scores[priority] = score
        
        # Return priority with highest score
        if priority_scores:
            best_priority = max(priority_scores, key=priority_scores.get)
            if priority_scores[best_priority] > 0:
                return best_priority
        
        return CommandPriority.MEDIUM
    
    def _analyze_command_sequence(self, command_text: str) -> Optional[CommandSequence]:
        """Analyze command for sequence indicators.
        
        Args:
            command_text: Normalized command text
            
        Returns:
            Command sequence information or None
        """
        sequence_indicators = []
        
        # Check for sequence patterns
        for seq_config in self.sequence_patterns:
            pattern = seq_config["pattern"]
            seq_type = seq_config["type"]
            confidence = seq_config["confidence"]
            
            matches = re.findall(pattern, command_text, re.IGNORECASE)
            
            if matches:
                sequence_indicators.append({
                    "type": seq_type,
                    "count": len(matches),
                    "confidence": confidence
                })
        
        if not sequence_indicators:
            return None
        
        # Determine sequence characteristics
        is_sequential = any(
            indicator["type"] in ["sequential", "ordered", "dependent"]
            for indicator in sequence_indicators
        )
        
        coordination_required = any(
            indicator["type"] in ["dependent", "concurrent"]
            for indicator in sequence_indicators
        )
        
        # Count command components (rough estimate)
        command_count = len(re.findall(r'\b(?:and|then|also|next)\b', command_text)) + 1
        
        return CommandSequence(
            sequence_count=command_count,
            sequence_index=0,
            is_sequential=is_sequential,
            coordination_required=coordination_required
        )
    
    def _validate_command_structure(
        self,
        command_type: CommandType,
        action_verb: str,
        primary_object: Optional[str],
        parameters: List[CommandParameter]
    ) -> CommandStatus:
        """Validate overall command structure.
        
        Args:
            command_type: Detected command type
            action_verb: Extracted action verb
            primary_object: Primary object
            parameters: Extracted parameters
            
        Returns:
            Command validation status
        """
        if command_type == CommandType.UNKNOWN:
            return CommandStatus.ERROR
        
        if action_verb == "unknown":
            return CommandStatus.INCOMPLETE
        
        # Check for required parameters based on command type
        required_params = self._get_required_parameters(command_type)
        found_param_types = {param.name for param in parameters}
        
        missing_required = required_params - found_param_types
        if missing_required:
            return CommandStatus.INCOMPLETE
        
        # Check parameter validation issues
        for param in parameters:
            if param.validation_notes and any(
                "invalid" in note.lower() or "error" in note.lower()
                for note in param.validation_notes
            ):
                return CommandStatus.ERROR
        
        return CommandStatus.VALIDATED
    
    def _get_required_parameters(self, command_type: CommandType) -> set:
        """Get required parameters for command type.
        
        Args:
            command_type: Command type
            
        Returns:
            Set of required parameter types
        """
        requirements = {
            CommandType.SCHEDULE: {"vehicle_id", "maintenance_type"},
            CommandType.ASSIGN: {"driver_id", "vehicle_id"},
            CommandType.UPDATE: {"vehicle_id", "status"},
            CommandType.MOVE: {"vehicle_id", "location"},
            CommandType.CREATE: {"vehicle_id"},
            CommandType.CANCEL: {"vehicle_id"},
            CommandType.SET: {"vehicle_id"}
        }
        
        return requirements.get(command_type, set())
    
    def _calculate_parsing_confidence(
        self,
        command_type: CommandType,
        action_verb: str,
        primary_object: Optional[str],
        parameters: List[CommandParameter],
        status: CommandStatus
    ) -> float:
        """Calculate overall parsing confidence score.
        
        Args:
            command_type: Detected command type
            action_verb: Extracted action verb
            primary_object: Primary object
            parameters: Extracted parameters
            status: Validation status
            
        Returns:
            Parsing confidence score
        """
        confidence = 0.0
        
        # Command type detection score
        if command_type != CommandType.UNKNOWN:
            confidence += 0.3
        
        # Action verb score
        if action_verb != "unknown":
            confidence += 0.2
        
        # Primary object score
        if primary_object:
            confidence += 0.1
        
        # Parameters score
        if parameters:
            param_confidence = sum(param.confidence for param in parameters) / len(parameters)
            confidence += param_confidence * 0.3
        
        # Validation status score
        if status == CommandStatus.VALIDATED:
            confidence += 0.1
        elif status == CommandStatus.INCOMPLETE:
            confidence += 0.05
        
        return min(1.0, confidence)
    
    def _generate_parsing_notes(
        self,
        original_command: str,
        normalized_command: str,
        command_type: CommandType,
        action_verb: str,
        parameters: List[CommandParameter]
    ) -> List[str]:
        """Generate notes about the parsing process.
        
        Args:
            original_command: Original command text
            normalized_command: Normalized command text
            command_type: Detected command type
            action_verb: Extracted action verb
            parameters: Extracted parameters
            
        Returns:
            List of parsing notes
        """
        notes = []
        
        # Command length analysis
        if len(original_command) < 10:
            notes.append("Very short command - may be incomplete")
        elif len(original_command) > 200:
            notes.append("Very long command - may contain multiple requests")
        
        # Command type analysis
        if command_type == CommandType.UNKNOWN:
            notes.append("Could not determine command type")
        else:
            notes.append(f"Detected command type: {command_type.value}")
        
        # Action verb analysis
        if action_verb == "unknown":
            notes.append("Could not identify clear action verb")
        else:
            notes.append(f"Primary action: {action_verb}")
        
        # Parameter analysis
        if not parameters:
            notes.append("No specific parameters extracted")
        else:
            notes.append(f"Extracted {len(parameters)} parameters")
            
            # Note parameter validation issues
            for param in parameters:
                if param.validation_notes:
                    notes.extend([f"{param.name}: {note}" for note in param.validation_notes])
        
        # Normalization changes
        if original_command.lower() != normalized_command:
            notes.append("Command text was normalized for processing")
        
        return notes
    
    def _create_extraction_metadata(
        self,
        original_command: str,
        normalized_command: str,
        parameters: List[CommandParameter]
    ) -> Dict[str, Any]:
        """Create metadata about the extraction process.
        
        Args:
            original_command: Original command text
            normalized_command: Normalized command text
            parameters: Extracted parameters
            
        Returns:
            Extraction metadata dictionary
        """
        return {
            "original_length": len(original_command),
            "normalized_length": len(normalized_command),
            "parameter_count": len(parameters),
            "parameter_types": list(set(param.name for param in parameters)),
            "has_sequence_indicators": bool(
                re.search(r'\b(?:then|and|also|next|after|before)\b', normalized_command)
            ),
            "has_time_reference": bool(
                re.search(r'\b(?:today|tomorrow|next|this|by|at|on)\b', normalized_command)
            ),
            "has_location_reference": bool(
                re.search(r'\b(?:at|to|from|location|depot|garage)\b', normalized_command)
            ),
            "word_count": len(normalized_command.split()),
            "processing_timestamp": datetime.now().isoformat()
        }