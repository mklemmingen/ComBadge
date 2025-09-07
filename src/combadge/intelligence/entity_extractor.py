"""Entity Extractor for Fleet Management

Extracts structured entities from natural language text including vehicle identifiers,
temporal information, locations, and person names with confidence scoring.
"""

import re
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json

from ..core.logging_manager import LoggingManager


class EntityType(Enum):
    """Types of entities that can be extracted."""
    VEHICLE_ID = "vehicle_id"
    VIN = "vin"
    LICENSE_PLATE = "license_plate"
    PERSON_NAME = "person_name"
    LOCATION = "location"
    BUILDING = "building"
    PARKING_SPOT = "parking_spot"
    DATE = "date"
    TIME = "time"
    DURATION = "duration"
    EMAIL = "email"
    PHONE = "phone"
    DEPARTMENT = "department"
    ROLE = "role"
    UNKNOWN = "unknown"


@dataclass
class EntityMatch:
    """Represents an extracted entity with metadata."""
    entity_type: EntityType
    value: str
    confidence: float
    start_pos: int
    end_pos: int
    original_text: str
    normalized_value: Optional[str] = None
    validation_status: str = "unknown"
    extraction_method: str = "pattern"
    context_clues: List[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    """Complete entity extraction result."""
    entities: List[EntityMatch] = field(default_factory=list)
    entity_groups: Dict[EntityType, List[EntityMatch]] = field(default_factory=dict)
    extraction_confidence: float = 0.0
    processing_notes: List[str] = field(default_factory=list)
    text_processed: str = ""
    unrecognized_patterns: List[str] = field(default_factory=list)


class EntityExtractor:
    """Advanced entity extractor for fleet management data."""
    
    def __init__(self):
        """Initialize entity extractor with patterns and processors."""
        self.logger = LoggingManager.get_logger(__name__)
        
        # Build extraction patterns
        self.entity_patterns = self._build_entity_patterns()
        self.context_patterns = self._build_context_patterns()
        self.validation_patterns = self._build_validation_patterns()
        
        # Initialize processors
        self.temporal_processor = TemporalProcessor()
        self.location_processor = LocationProcessor()
        self.person_processor = PersonProcessor()
        
        # Extraction settings
        self.min_confidence_threshold = 0.3
        self.context_window = 20  # Characters before/after for context
        
    def _build_entity_patterns(self) -> Dict[EntityType, List[Dict[str, Any]]]:
        """Build regex patterns for entity extraction.
        
        Returns:
            Dictionary mapping entity types to pattern configurations
        """
        return {
            EntityType.VIN: [
                {
                    "pattern": r'\b[A-HJ-NPR-Z0-9]{17}\b',
                    "confidence": 0.9,
                    "description": "Standard 17-character VIN"
                },
                {
                    "pattern": r'\bVIN:?\s*([A-HJ-NPR-Z0-9]{17})\b',
                    "confidence": 0.95,
                    "group": 1,
                    "description": "VIN with label"
                }
            ],
            
            EntityType.VEHICLE_ID: [
                {
                    "pattern": r'\b[A-Z]{2,4}-\d{3,5}\b',
                    "confidence": 0.8,
                    "description": "Fleet ID format (ABC-1234)"
                },
                {
                    "pattern": r'\b(?:vehicle|car|truck|van)\s+(?:ID|#|number):?\s*([A-Z0-9-]{3,10})\b',
                    "confidence": 0.85,
                    "group": 1,
                    "description": "Vehicle ID with label"
                },
                {
                    "pattern": r'\bunit\s+([A-Z0-9-]{3,8})\b',
                    "confidence": 0.7,
                    "group": 1,
                    "description": "Unit number format"
                }
            ],
            
            EntityType.LICENSE_PLATE: [
                {
                    "pattern": r'\b[A-Z]{2,3}\s*\d{2,4}[A-Z]?\b',
                    "confidence": 0.7,
                    "description": "Standard license plate format"
                },
                {
                    "pattern": r'\b\d{3}\s*[A-Z]{3}\b',
                    "confidence": 0.75,
                    "description": "Numeric-alpha plate format"
                },
                {
                    "pattern": r'\bplate:?\s*([A-Z0-9\s-]{3,8})\b',
                    "confidence": 0.85,
                    "group": 1,
                    "description": "License plate with label"
                }
            ],
            
            EntityType.EMAIL: [
                {
                    "pattern": r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
                    "confidence": 0.95,
                    "description": "Standard email format"
                }
            ],
            
            EntityType.PHONE: [
                {
                    "pattern": r'\b\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b',
                    "confidence": 0.8,
                    "description": "US phone number format",
                    "formatter": lambda m: f"({m.group(1)}) {m.group(2)}-{m.group(3)}"
                },
                {
                    "pattern": r'\b\d{3}-\d{3}-\d{4}\b',
                    "confidence": 0.9,
                    "description": "Formatted phone number"
                }
            ],
            
            EntityType.BUILDING: [
                {
                    "pattern": r'\bbuilding\s+([A-Z0-9]+)\b',
                    "confidence": 0.85,
                    "group": 1,
                    "description": "Building with identifier"
                },
                {
                    "pattern": r'\b([A-Z])\s+building\b',
                    "confidence": 0.8,
                    "group": 1,
                    "description": "Building with prefix identifier"
                }
            ],
            
            EntityType.PARKING_SPOT: [
                {
                    "pattern": r'\b(?:lot|parking)\s+(\d+|[A-Z]\d*)\b',
                    "confidence": 0.8,
                    "group": 1,
                    "description": "Parking lot number"
                },
                {
                    "pattern": r'\b(?:spot|space)\s+([A-Z]?\d+[A-Z]?)\b',
                    "confidence": 0.85,
                    "group": 1,
                    "description": "Parking spot identifier"
                },
                {
                    "pattern": r'\bfloor\s+(\d+)\b',
                    "confidence": 0.7,
                    "group": 1,
                    "description": "Floor number"
                }
            ],
            
            EntityType.DEPARTMENT: [
                {
                    "pattern": r'\b(IT|HR|Finance|Operations|Marketing|Sales|Legal|Maintenance|Security)\b',
                    "confidence": 0.8,
                    "description": "Common department names"
                }
            ],
            
            EntityType.ROLE: [
                {
                    "pattern": r'\b(manager|director|supervisor|technician|driver|operator|admin|analyst)\b',
                    "confidence": 0.7,
                    "description": "Common job roles"
                }
            ],
            
            EntityType.DATE: [
                {
                    "pattern": r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
                    "confidence": 0.8,
                    "description": "MM/DD/YYYY or MM/DD/YY format"
                },
                {
                    "pattern": r'\b\d{4}-\d{1,2}-\d{1,2}\b',
                    "confidence": 0.9,
                    "description": "ISO date format YYYY-MM-DD"
                },
                {
                    "pattern": r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{2,4}\b',
                    "confidence": 0.85,
                    "description": "Month DD, YYYY format"
                }
            ],
            
            EntityType.TIME: [
                {
                    "pattern": r'\b\d{1,2}:\d{2}\s*(?:am|pm)?\b',
                    "confidence": 0.8,
                    "description": "HH:MM format with optional am/pm"
                },
                {
                    "pattern": r'\b\d{1,2}\s*(?:am|pm)\b',
                    "confidence": 0.75,
                    "description": "Hour with am/pm"
                },
                {
                    "pattern": r'\b\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}\s*(?:am|pm)?\b',
                    "confidence": 0.85,
                    "description": "Time range HH:MM-HH:MM"
                }
            ]
        }
    
    def _build_context_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Build context patterns that help identify entities.
        
        Returns:
            Dictionary of context patterns with metadata
        """
        return {
            # Vehicle context
            r'\b(?:vehicle|car|truck|van|automobile)\b': {
                "boosts": [EntityType.VEHICLE_ID, EntityType.VIN, EntityType.LICENSE_PLATE],
                "confidence_boost": 0.1
            },
            
            # Time context
            r'\b(?:schedule|appointment|meeting|reservation|book|time|date)\b': {
                "boosts": [EntityType.DATE, EntityType.TIME],
                "confidence_boost": 0.1
            },
            
            # Location context
            r'\b(?:location|address|building|parking|lot|space|floor|level)\b': {
                "boosts": [EntityType.LOCATION, EntityType.BUILDING, EntityType.PARKING_SPOT],
                "confidence_boost": 0.1
            },
            
            # Person context
            r'\b(?:from|to|contact|person|name|driver|manager|client|customer)\b': {
                "boosts": [EntityType.PERSON_NAME, EntityType.EMAIL, EntityType.PHONE],
                "confidence_boost": 0.1
            },
            
            # Maintenance context
            r'\b(?:maintenance|service|repair|inspection|oil|brake|tire)\b': {
                "boosts": [EntityType.VEHICLE_ID, EntityType.VIN, EntityType.DATE, EntityType.TIME],
                "confidence_boost": 0.05
            }
        }
    
    def _build_validation_patterns(self) -> Dict[EntityType, List[Dict[str, Any]]]:
        """Build validation patterns for extracted entities.
        
        Returns:
            Dictionary of validation patterns
        """
        return {
            EntityType.EMAIL: [
                {
                    "pattern": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                    "description": "Valid email format"
                }
            ],
            
            EntityType.VIN: [
                {
                    "pattern": r'^[A-HJ-NPR-Z0-9]{17}$',
                    "description": "17-character VIN without I, O, Q"
                }
            ],
            
            EntityType.PHONE: [
                {
                    "pattern": r'^\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$',
                    "description": "Valid US phone number format"
                }
            ]
        }
    
    def extract(self, text: str) -> ExtractionResult:
        """Extract all entities from text with confidence scoring.
        
        Args:
            text: Input text to process
            
        Returns:
            Complete extraction result with entities and metadata
        """
        self.logger.debug(f"Starting entity extraction for text: {text[:100]}...")
        
        # Preprocess text
        processed_text = self._preprocess_text(text)
        
        # Extract entities using patterns
        entities = self._extract_with_patterns(processed_text)
        
        # Apply contextual improvements
        entities = self._apply_context_improvements(processed_text, entities)
        
        # Validate and normalize entities
        entities = self._validate_and_normalize(entities)
        
        # Group entities by type
        entity_groups = self._group_entities(entities)
        
        # Calculate overall extraction confidence
        extraction_confidence = self._calculate_extraction_confidence(entities)
        
        # Generate processing notes
        processing_notes = self._generate_processing_notes(processed_text, entities)
        
        # Find unrecognized patterns
        unrecognized_patterns = self._find_unrecognized_patterns(processed_text, entities)
        
        result = ExtractionResult(
            entities=entities,
            entity_groups=entity_groups,
            extraction_confidence=extraction_confidence,
            processing_notes=processing_notes,
            text_processed=processed_text,
            unrecognized_patterns=unrecognized_patterns
        )
        
        self.logger.info(
            f"Entity extraction complete: {len(entities)} entities found "
            f"(confidence: {extraction_confidence:.2f})"
        )
        
        return result
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better entity extraction.
        
        Args:
            text: Raw input text
            
        Returns:
            Preprocessed text
        """
        # Normalize whitespace
        processed = re.sub(r'\s+', ' ', text)
        
        # Normalize common separators
        processed = re.sub(r'[–—]', '-', processed)  # En dash, em dash to hyphen
        processed = re.sub(r'[''‚]', "'", processed)  # Smart quotes to apostrophe
        processed = re.sub(r'[""„]', '"', processed)  # Smart quotes to regular quotes
        
        # Clean up common formatting issues
        processed = re.sub(r'\b(\w+)\s*:\s*(\w+)\b', r'\1: \2', processed)  # Fix spacing around colons
        
        return processed.strip()
    
    def _extract_with_patterns(self, text: str) -> List[EntityMatch]:
        """Extract entities using regex patterns.
        
        Args:
            text: Preprocessed text
            
        Returns:
            List of entity matches
        """
        entities = []
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern_config in patterns:
                pattern = pattern_config["pattern"]
                confidence = pattern_config["confidence"]
                group = pattern_config.get("group", 0)
                description = pattern_config.get("description", "")
                formatter = pattern_config.get("formatter")
                
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    # Extract value from specified group or full match
                    if group > 0 and group <= len(match.groups()):
                        value = match.group(group)
                        start_pos = match.start(group)
                        end_pos = match.end(group)
                    else:
                        value = match.group(0)
                        start_pos = match.start()
                        end_pos = match.end()
                    
                    # Apply formatter if provided
                    if formatter:
                        try:
                            formatted_value = formatter(match)
                            if formatted_value:
                                value = formatted_value
                        except Exception as e:
                            self.logger.warning(f"Formatter error for {pattern}: {e}")
                    
                    # Get context around the match
                    context_start = max(0, start_pos - self.context_window)
                    context_end = min(len(text), end_pos + self.context_window)
                    context = text[context_start:context_end].strip()
                    
                    entity = EntityMatch(
                        entity_type=entity_type,
                        value=value.strip(),
                        confidence=confidence,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        original_text=match.group(0),
                        extraction_method=f"pattern: {description}",
                        context_clues=[context]
                    )
                    
                    entities.append(entity)
        
        return entities
    
    def _apply_context_improvements(self, text: str, entities: List[EntityMatch]) -> List[EntityMatch]:
        """Apply context-based confidence improvements.
        
        Args:
            text: Processed text
            entities: Initial entity matches
            
        Returns:
            Entities with improved confidence scores
        """
        improved_entities = []
        
        for entity in entities:
            improved_entity = entity
            
            # Check context patterns
            for context_pattern, config in self.context_patterns.items():
                if entity.entity_type in config["boosts"]:
                    # Check if context pattern appears near the entity
                    context_window = text[
                        max(0, entity.start_pos - 50):
                        min(len(text), entity.end_pos + 50)
                    ]
                    
                    if re.search(context_pattern, context_window, re.IGNORECASE):
                        boost = config["confidence_boost"]
                        improved_entity.confidence = min(1.0, entity.confidence + boost)
                        improved_entity.context_clues.append(f"Context boost: {context_pattern}")
            
            improved_entities.append(improved_entity)
        
        return improved_entities
    
    def _validate_and_normalize(self, entities: List[EntityMatch]) -> List[EntityMatch]:
        """Validate and normalize extracted entities.
        
        Args:
            entities: Raw entity matches
            
        Returns:
            Validated and normalized entities
        """
        validated_entities = []
        
        for entity in entities:
            validated_entity = entity
            
            # Apply entity-specific validation
            if entity.entity_type in self.validation_patterns:
                validation_passed = False
                
                for validation_config in self.validation_patterns[entity.entity_type]:
                    pattern = validation_config["pattern"]
                    description = validation_config["description"]
                    
                    if re.match(pattern, entity.value):
                        validation_passed = True
                        validated_entity.validation_status = f"passed: {description}"
                        break
                
                if not validation_passed:
                    validated_entity.validation_status = "failed: format validation"
                    validated_entity.confidence *= 0.7  # Reduce confidence for failed validation
            
            # Apply entity-specific normalization
            normalized_value = self._normalize_entity_value(entity.entity_type, entity.value)
            if normalized_value != entity.value:
                validated_entity.normalized_value = normalized_value
            
            # Only include entities above minimum confidence threshold
            if validated_entity.confidence >= self.min_confidence_threshold:
                validated_entities.append(validated_entity)
        
        return validated_entities
    
    def _normalize_entity_value(self, entity_type: EntityType, value: str) -> str:
        """Normalize entity value based on type.
        
        Args:
            entity_type: Type of entity
            value: Raw value
            
        Returns:
            Normalized value
        """
        if entity_type == EntityType.EMAIL:
            return value.lower()
        
        elif entity_type == EntityType.VIN:
            return value.upper().replace(' ', '')
        
        elif entity_type == EntityType.LICENSE_PLATE:
            return re.sub(r'\s+', ' ', value.upper().strip())
        
        elif entity_type == EntityType.VEHICLE_ID:
            return value.upper()
        
        elif entity_type == EntityType.PERSON_NAME:
            return value.title()
        
        elif entity_type == EntityType.PHONE:
            # Normalize phone number to (XXX) XXX-XXXX format
            digits = re.sub(r'\D', '', value)
            if len(digits) == 10:
                return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        
        return value
    
    def _group_entities(self, entities: List[EntityMatch]) -> Dict[EntityType, List[EntityMatch]]:
        """Group entities by type.
        
        Args:
            entities: List of entity matches
            
        Returns:
            Dictionary grouping entities by type
        """
        groups = {}
        
        for entity in entities:
            if entity.entity_type not in groups:
                groups[entity.entity_type] = []
            groups[entity.entity_type].append(entity)
        
        # Sort entities within each group by confidence
        for entity_type in groups:
            groups[entity_type].sort(key=lambda x: x.confidence, reverse=True)
        
        return groups
    
    def _calculate_extraction_confidence(self, entities: List[EntityMatch]) -> float:
        """Calculate overall extraction confidence.
        
        Args:
            entities: List of extracted entities
            
        Returns:
            Overall confidence score
        """
        if not entities:
            return 0.0
        
        # Weight confidence by entity type importance
        type_weights = {
            EntityType.VIN: 1.0,
            EntityType.VEHICLE_ID: 0.9,
            EntityType.EMAIL: 0.8,
            EntityType.DATE: 0.7,
            EntityType.TIME: 0.7,
            EntityType.PERSON_NAME: 0.6,
            EntityType.LOCATION: 0.6,
            EntityType.LICENSE_PLATE: 0.8,
            EntityType.PHONE: 0.5,
            EntityType.BUILDING: 0.4,
            EntityType.PARKING_SPOT: 0.4,
            EntityType.DEPARTMENT: 0.3,
            EntityType.ROLE: 0.3
        }
        
        total_weighted_confidence = 0.0
        total_weight = 0.0
        
        for entity in entities:
            weight = type_weights.get(entity.entity_type, 0.5)
            total_weighted_confidence += entity.confidence * weight
            total_weight += weight
        
        return total_weighted_confidence / total_weight if total_weight > 0 else 0.0
    
    def _generate_processing_notes(self, text: str, entities: List[EntityMatch]) -> List[str]:
        """Generate processing notes about extraction.
        
        Args:
            text: Processed text
            entities: Extracted entities
            
        Returns:
            List of processing notes
        """
        notes = []
        
        # Text length analysis
        word_count = len(text.split())
        if word_count < 5:
            notes.append("Short input text - limited extraction possible")
        elif word_count > 100:
            notes.append("Long input text - may contain multiple entities")
        
        # Entity distribution analysis
        entity_counts = {}
        for entity in entities:
            entity_type = entity.entity_type.value
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
        
        if len(entity_counts) == 0:
            notes.append("No entities extracted - input may not contain fleet-relevant information")
        elif len(entity_counts) == 1:
            entity_type = list(entity_counts.keys())[0]
            notes.append(f"Single entity type detected: {entity_type}")
        else:
            notes.append(f"Multiple entity types detected: {', '.join(entity_counts.keys())}")
        
        # Confidence analysis
        if entities:
            avg_confidence = sum(e.confidence for e in entities) / len(entities)
            if avg_confidence < 0.5:
                notes.append("Low average confidence - extraction may be unreliable")
            elif avg_confidence > 0.9:
                notes.append("High average confidence - reliable extraction")
        
        # Validation analysis
        validation_failures = [e for e in entities if e.validation_status.startswith("failed")]
        if validation_failures:
            notes.append(f"{len(validation_failures)} entities failed validation")
        
        return notes
    
    def _find_unrecognized_patterns(self, text: str, entities: List[EntityMatch]) -> List[str]:
        """Find potential entity patterns that weren't recognized.
        
        Args:
            text: Processed text
            entities: Extracted entities
            
        Returns:
            List of potentially unrecognized patterns
        """
        unrecognized = []
        
        # Common patterns that might be entities
        potential_patterns = [
            r'\b[A-Z]{3,6}\d{2,6}\b',  # Alphanumeric codes
            r'\b\d{3,6}-\d{3,6}\b',    # Numeric codes with dash
            r'\b[A-Z]+\s+\d+[A-Z]?\b', # Alpha followed by numbers
            r'\b#\d{3,8}\b',           # Hash followed by numbers
        ]
        
        # Find patterns not covered by existing extractions
        covered_spans = [(e.start_pos, e.end_pos) for e in entities]
        
        for pattern in potential_patterns:
            for match in re.finditer(pattern, text):
                start, end = match.span()
                
                # Check if this span overlaps with any extracted entity
                overlaps = any(
                    (start < e_end and end > e_start) 
                    for e_start, e_end in covered_spans
                )
                
                if not overlaps:
                    unrecognized.append(match.group(0))
        
        return list(set(unrecognized))  # Remove duplicates
    
    def extract_by_type(self, text: str, entity_type: EntityType) -> List[EntityMatch]:
        """Extract entities of a specific type only.
        
        Args:
            text: Input text
            entity_type: Specific entity type to extract
            
        Returns:
            List of entities of the specified type
        """
        full_result = self.extract(text)
        return full_result.entity_groups.get(entity_type, [])
    
    def get_best_entities(self, result: ExtractionResult, limit: int = 5) -> List[EntityMatch]:
        """Get the best entities from extraction result.
        
        Args:
            result: Extraction result
            limit: Maximum number of entities to return
            
        Returns:
            List of highest confidence entities
        """
        sorted_entities = sorted(result.entities, key=lambda x: x.confidence, reverse=True)
        return sorted_entities[:limit]
    
    def export_entities_json(self, result: ExtractionResult) -> str:
        """Export entities to JSON format.
        
        Args:
            result: Extraction result
            
        Returns:
            JSON string representation
        """
        export_data = {
            "extraction_confidence": result.extraction_confidence,
            "total_entities": len(result.entities),
            "entities": [
                {
                    "type": entity.entity_type.value,
                    "value": entity.value,
                    "normalized_value": entity.normalized_value,
                    "confidence": entity.confidence,
                    "position": {"start": entity.start_pos, "end": entity.end_pos},
                    "validation_status": entity.validation_status,
                    "extraction_method": entity.extraction_method
                }
                for entity in result.entities
            ],
            "entity_counts": {
                entity_type.value: len(entities)
                for entity_type, entities in result.entity_groups.items()
            },
            "processing_notes": result.processing_notes,
            "unrecognized_patterns": result.unrecognized_patterns
        }
        
        return json.dumps(export_data, indent=2)


class TemporalProcessor:
    """Specialized processor for temporal entities."""
    
    def __init__(self):
        self.logger = LoggingManager.get_logger(__name__)
    
    def process_temporal_expression(self, text: str) -> Optional[datetime]:
        """Process natural language temporal expressions."""
        # Placeholder for temporal processing
        return None


class LocationProcessor:
    """Specialized processor for location entities."""
    
    def __init__(self):
        self.logger = LoggingManager.get_logger(__name__)
    
    def process_location(self, text: str) -> Optional[Dict[str, str]]:
        """Process location information."""
        # Placeholder for location processing
        return None


class PersonProcessor:
    """Specialized processor for person name entities."""
    
    def __init__(self):
        self.logger = LoggingManager.get_logger(__name__)
    
    def process_person_name(self, text: str) -> Optional[Dict[str, str]]:
        """Process person name information."""
        # Placeholder for person name processing
        return None