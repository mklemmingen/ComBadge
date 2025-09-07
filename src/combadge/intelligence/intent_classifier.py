"""Intent Classifier for Fleet Management Operations

Classifies natural language requests into structured fleet management operation types
with confidence scoring and multi-intent handling capabilities.
"""

import re
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from ..core.logging_manager import LoggingManager


class FleetIntent(Enum):
    """Fleet management operation intent categories."""
    CREATE_VEHICLE = "create_vehicle"
    SCHEDULE_MAINTENANCE = "schedule_maintenance"
    MAKE_RESERVATION = "make_reservation"
    ASSIGN_PARKING = "assign_parking"
    UPDATE_STATUS = "update_status"
    QUERY_INFORMATION = "query_information"
    TRANSFER_VEHICLE = "transfer_vehicle"
    CANCEL_OPERATION = "cancel_operation"
    UNKNOWN = "unknown"


@dataclass
class IntentMatch:
    """Represents a classified intent with confidence and evidence."""
    intent: FleetIntent
    confidence: float
    evidence: List[str] = field(default_factory=list)
    keywords_matched: List[str] = field(default_factory=list)
    patterns_matched: List[str] = field(default_factory=list)
    context_clues: List[str] = field(default_factory=list)


@dataclass
class ClassificationResult:
    """Complete intent classification result with multiple intents."""
    primary_intent: IntentMatch
    secondary_intents: List[IntentMatch] = field(default_factory=list)
    overall_confidence: float = 0.0
    is_multi_intent: bool = False
    text_processed: str = ""
    processing_notes: List[str] = field(default_factory=list)


class IntentClassifier:
    """Intelligent intent classifier for fleet management operations."""
    
    def __init__(self):
        """Initialize intent classifier with patterns and keywords."""
        self.logger = LoggingManager.get_logger(__name__)
        
        # Intent patterns and keywords
        self.intent_patterns = self._build_intent_patterns()
        self.intent_keywords = self._build_intent_keywords()
        self.context_patterns = self._build_context_patterns()
        self.negation_patterns = self._build_negation_patterns()
        
        # Classification thresholds
        self.confidence_threshold = 0.6
        self.multi_intent_threshold = 0.4
        
    def _build_intent_patterns(self) -> Dict[FleetIntent, List[str]]:
        """Build regex patterns for each intent type.
        
        Returns:
            Dictionary mapping intents to regex patterns
        """
        return {
            FleetIntent.CREATE_VEHICLE: [
                r'\b(?:add|create|register|new|setup)\s+(?:vehicle|car|truck|van)',
                r'\b(?:vehicle|car|truck|van)\s+(?:registration|creation|setup)',
                r'\b(?:onboard|enroll)\s+(?:new\s+)?(?:vehicle|car|truck|van)',
                r'\bregister\s+(?:new\s+)?(?:vehicle|car|truck|van)',
            ],
            
            FleetIntent.SCHEDULE_MAINTENANCE: [
                r'\b(?:schedule|book|arrange|plan)\s+(?:maintenance|service|repair|inspection)',
                r'\b(?:maintenance|service|repair|inspection)\s+(?:schedule|booking|appointment)',
                r'\b(?:need|due|time)\s+for\s+(?:maintenance|service|repair|inspection)',
                r'\b(?:oil\s+change|tune.?up|brake|tire|engine)\s+(?:service|maintenance)',
                r'\bservice\s+(?:reminder|due|needed|required)',
                r'\b(?:preventive|routine|scheduled)\s+maintenance',
            ],
            
            FleetIntent.MAKE_RESERVATION: [
                r'\b(?:reserve|book|schedule|allocate)\s+(?:vehicle|car|truck|van)',
                r'\b(?:vehicle|car|truck|van)\s+(?:reservation|booking)',
                r'\b(?:need|require|want)\s+(?:to\s+)?(?:reserve|book)\s+(?:a\s+)?(?:vehicle|car|truck|van)',
                r'\breservation\s+for\s+(?:vehicle|car|truck|van)',
                r'\b(?:client|meeting|trip|appointment)\s+(?:vehicle|car|truck|van)',
                r'\bassign\s+(?:vehicle|car|truck|van)\s+(?:to|for)',
            ],
            
            FleetIntent.ASSIGN_PARKING: [
                r'\b(?:assign|allocate|move|park)\s+(?:to\s+)?(?:parking|lot|space|spot|garage)',
                r'\b(?:parking|lot|space|spot|garage)\s+(?:assignment|allocation)',
                r'\bmove\s+(?:vehicle|car|truck|van)\s+(?:to|from)',
                r'\b(?:relocate|transfer)\s+(?:vehicle|car|truck|van)',
                r'\bparking\s+(?:spot|space|lot)\s+(?:assignment|change)',
                r'\b(?:building|floor|level)\s+(?:\d+|[a-z]+)\s+parking',
            ],
            
            FleetIntent.UPDATE_STATUS: [
                r'\b(?:update|change|modify|edit)\s+(?:status|information|details)',
                r'\bstatus\s+(?:update|change|modification)',
                r'\b(?:mark|set)\s+(?:as\s+)?(?:available|unavailable|in.?use|maintenance|retired)',
                r'\b(?:activate|deactivate|enable|disable)\s+(?:vehicle|car|truck|van)',
                r'\bchange\s+(?:vehicle|car|truck|van)\s+(?:status|state)',
            ],
            
            FleetIntent.QUERY_INFORMATION: [
                r'\b(?:where\s+is|what\s+is|when\s+is|who\s+has|which\s+vehicle)',
                r'\b(?:check|find|search|lookup|show|display)\s+(?:vehicle|car|truck|van|status)',
                r'\b(?:status|location|availability|schedule)\s+(?:of|for)\s+(?:vehicle|car|truck|van)',
                r'\b(?:vehicle|car|truck|van)\s+(?:information|details|status)',
                r'\b(?:available|free)\s+(?:vehicles|cars|trucks|vans)',
                r'\blist\s+(?:all\s+)?(?:vehicles|cars|trucks|vans)',
            ],
            
            FleetIntent.TRANSFER_VEHICLE: [
                r'\btransfer\s+(?:vehicle|car|truck|van)',
                r'\bmove\s+(?:vehicle|car|truck|van)\s+(?:from|to)',
                r'\brelocate\s+(?:vehicle|car|truck|van)',
                r'\b(?:change|switch)\s+(?:vehicle|car|truck|van)\s+(?:location|assignment)',
                r'\bassign\s+(?:vehicle|car|truck|van)\s+(?:to|from)\s+(?:different|new)',
            ],
            
            FleetIntent.CANCEL_OPERATION: [
                r'\b(?:cancel|abort|stop|remove|delete)\s+(?:reservation|booking|maintenance|appointment)',
                r'\b(?:reservation|booking|maintenance|appointment)\s+(?:cancellation|removal)',
                r'\bno\s+longer\s+need',
                r'\b(?:cancel|abort|stop)\s+(?:the\s+)?(?:scheduled|planned)',
                r'\b(?:withdraw|retract)\s+(?:request|reservation)',
            ]
        }
    
    def _build_intent_keywords(self) -> Dict[FleetIntent, Dict[str, float]]:
        """Build keyword weightings for each intent type.
        
        Returns:
            Dictionary mapping intents to keywords with confidence weights
        """
        return {
            FleetIntent.CREATE_VEHICLE: {
                "new": 0.8, "add": 0.9, "create": 0.9, "register": 0.8,
                "setup": 0.7, "onboard": 0.8, "enroll": 0.7, "vehicle": 0.6,
                "car": 0.6, "truck": 0.6, "van": 0.6, "fleet": 0.5
            },
            
            FleetIntent.SCHEDULE_MAINTENANCE: {
                "maintenance": 0.9, "service": 0.8, "repair": 0.8, "inspection": 0.7,
                "schedule": 0.7, "book": 0.6, "oil": 0.6, "brake": 0.6,
                "tire": 0.6, "engine": 0.6, "tune-up": 0.7, "checkup": 0.6,
                "due": 0.8, "overdue": 0.9, "preventive": 0.7, "routine": 0.6
            },
            
            FleetIntent.MAKE_RESERVATION: {
                "reserve": 0.9, "book": 0.8, "reservation": 0.9, "booking": 0.8,
                "allocate": 0.7, "assign": 0.6, "client": 0.6, "meeting": 0.7,
                "trip": 0.7, "appointment": 0.6, "need": 0.5, "require": 0.5
            },
            
            FleetIntent.ASSIGN_PARKING: {
                "parking": 0.9, "park": 0.8, "lot": 0.7, "space": 0.7,
                "spot": 0.7, "garage": 0.7, "move": 0.6, "relocate": 0.8,
                "building": 0.6, "floor": 0.5, "level": 0.5, "assign": 0.7
            },
            
            FleetIntent.UPDATE_STATUS: {
                "update": 0.9, "change": 0.8, "modify": 0.8, "status": 0.9,
                "available": 0.7, "unavailable": 0.8, "in-use": 0.7, "active": 0.6,
                "inactive": 0.7, "retired": 0.8, "enable": 0.7, "disable": 0.7
            },
            
            FleetIntent.QUERY_INFORMATION: {
                "where": 0.8, "what": 0.7, "when": 0.7, "who": 0.7, "which": 0.7,
                "check": 0.8, "find": 0.8, "search": 0.8, "show": 0.7,
                "display": 0.7, "list": 0.8, "available": 0.6, "status": 0.7
            },
            
            FleetIntent.TRANSFER_VEHICLE: {
                "transfer": 0.9, "move": 0.8, "relocate": 0.8, "reassign": 0.8,
                "switch": 0.7, "change": 0.6, "from": 0.5, "to": 0.5
            },
            
            FleetIntent.CANCEL_OPERATION: {
                "cancel": 0.9, "abort": 0.8, "stop": 0.7, "remove": 0.7,
                "delete": 0.8, "withdraw": 0.8, "retract": 0.7, "no": 0.6,
                "longer": 0.6, "cancellation": 0.9
            }
        }
    
    def _build_context_patterns(self) -> Dict[str, float]:
        """Build context clue patterns that boost confidence.
        
        Returns:
            Dictionary mapping context patterns to confidence boosts
        """
        return {
            # Time-based context
            r'\b(?:today|tomorrow|next\s+week|monday|tuesday|wednesday|thursday|friday)\b': 0.2,
            r'\b(?:\d{1,2}:\d{2}|am|pm|\d{1,2}\s*-\s*\d{1,2})\b': 0.15,
            
            # Vehicle identifiers
            r'\b[A-Z]{2,4}-\d{3,4}\b': 0.25,  # Fleet ID pattern
            r'\b[A-HJ-NPR-Z0-9]{17}\b': 0.3,   # VIN pattern
            r'\b[A-Z]{2,3}\s*\d{2,4}\b': 0.2, # License plate pattern
            
            # Location context
            r'\bbuilding\s+[A-Z0-9]\b': 0.15,
            r'\blot\s+\d+\b': 0.1,
            r'\bfloor\s+\d+\b': 0.1,
            
            # Urgency indicators
            r'\b(?:urgent|asap|immediately|priority|rush)\b': 0.1,
            r'\b(?:overdue|late|delayed)\b': 0.15,
            
            # Person/role context
            r'\b(?:client|customer|manager|driver|technician)\b': 0.1,
            
            # Business context
            r'\b(?:meeting|appointment|conference|presentation)\b': 0.1,
        }
    
    def _build_negation_patterns(self) -> List[str]:
        """Build patterns that indicate negation or cancellation.
        
        Returns:
            List of negation patterns
        """
        return [
            r'\b(?:not|don\'t|doesn\'t|won\'t|can\'t|shouldn\'t)\b',
            r'\b(?:no|never|none|nothing|nobody)\b',
            r'\b(?:cancel|abort|stop|remove|delete)\b',
            r'\b(?:undo|reverse|rollback)\b'
        ]
    
    def classify(self, text: str) -> ClassificationResult:
        """Classify intent from natural language text.
        
        Args:
            text: Input text to classify
            
        Returns:
            Complete classification result with confidence scores
        """
        self.logger.debug(f"Classifying intent for text: {text[:100]}...")
        
        # Preprocess text
        processed_text = self._preprocess_text(text)
        
        # Score all intents
        intent_scores = self._score_all_intents(processed_text)
        
        # Find primary intent
        primary_intent = max(intent_scores, key=lambda x: x.confidence)
        
        # Find secondary intents
        secondary_intents = [
            intent for intent in intent_scores 
            if intent != primary_intent 
            and intent.confidence >= self.multi_intent_threshold
        ]
        secondary_intents.sort(key=lambda x: x.confidence, reverse=True)
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(
            primary_intent, secondary_intents
        )
        
        # Determine if multi-intent
        is_multi_intent = len(secondary_intents) > 0
        
        # Generate processing notes
        processing_notes = self._generate_processing_notes(
            processed_text, primary_intent, secondary_intents
        )
        
        result = ClassificationResult(
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            overall_confidence=overall_confidence,
            is_multi_intent=is_multi_intent,
            text_processed=processed_text,
            processing_notes=processing_notes
        )
        
        self.logger.info(
            f"Intent classification complete: {primary_intent.intent.value} "
            f"(confidence: {primary_intent.confidence:.2f})"
        )
        
        return result
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better pattern matching.
        
        Args:
            text: Raw input text
            
        Returns:
            Preprocessed text
        """
        # Convert to lowercase for pattern matching
        processed = text.lower()
        
        # Normalize whitespace
        processed = re.sub(r'\s+', ' ', processed)
        
        # Remove extra punctuation but keep sentence structure
        processed = re.sub(r'[^\w\s\-:.,!?]', ' ', processed)
        
        # Normalize common abbreviations
        abbreviations = {
            r'\bveh\b': 'vehicle',
            r'\bmaint\b': 'maintenance',
            r'\bresv\b': 'reservation',
            r'\bappt\b': 'appointment',
            r'\bsched\b': 'schedule',
            r'\bpkg\b': 'parking',
            r'\basap\b': 'as soon as possible'
        }
        
        for pattern, replacement in abbreviations.items():
            processed = re.sub(pattern, replacement, processed)
        
        return processed.strip()
    
    def _score_all_intents(self, text: str) -> List[IntentMatch]:
        """Score all possible intents for the given text.
        
        Args:
            text: Preprocessed text
            
        Returns:
            List of intent matches with scores
        """
        intent_matches = []
        
        for intent in FleetIntent:
            if intent == FleetIntent.UNKNOWN:
                continue
                
            match = self._score_intent(text, intent)
            intent_matches.append(match)
        
        # Add unknown intent as fallback
        unknown_match = IntentMatch(
            intent=FleetIntent.UNKNOWN,
            confidence=max(0.1, 1.0 - max(m.confidence for m in intent_matches))
        )
        intent_matches.append(unknown_match)
        
        return intent_matches
    
    def _score_intent(self, text: str, intent: FleetIntent) -> IntentMatch:
        """Score a specific intent for the given text.
        
        Args:
            text: Preprocessed text
            intent: Intent to score
            
        Returns:
            Intent match with confidence score
        """
        evidence = []
        keywords_matched = []
        patterns_matched = []
        context_clues = []
        
        base_confidence = 0.0
        
        # Score patterns
        if intent in self.intent_patterns:
            for pattern in self.intent_patterns[intent]:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    patterns_matched.append(pattern)
                    evidence.extend([f"Pattern match: {match}" for match in matches])
                    base_confidence += 0.3  # Each pattern adds 30%
        
        # Score keywords
        if intent in self.intent_keywords:
            for keyword, weight in self.intent_keywords[intent].items():
                if re.search(rf'\b{re.escape(keyword)}\b', text, re.IGNORECASE):
                    keywords_matched.append(keyword)
                    evidence.append(f"Keyword match: {keyword}")
                    base_confidence += weight * 0.1  # Keywords add weighted confidence
        
        # Score context clues
        for pattern, boost in self.context_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                matches = re.findall(pattern, text, re.IGNORECASE)
                context_clues.extend(matches)
                evidence.extend([f"Context clue: {match}" for match in matches])
                base_confidence += boost
        
        # Check for negation (reduces confidence)
        negation_penalty = 0.0
        for negation_pattern in self.negation_patterns:
            if re.search(negation_pattern, text, re.IGNORECASE):
                negation_penalty += 0.2
                evidence.append(f"Negation detected: {negation_pattern}")
        
        # Apply negation penalty
        if negation_penalty > 0 and intent != FleetIntent.CANCEL_OPERATION:
            base_confidence *= (1.0 - min(negation_penalty, 0.8))
        elif negation_penalty > 0 and intent == FleetIntent.CANCEL_OPERATION:
            base_confidence += negation_penalty  # Negation boosts cancel intent
        
        # Normalize confidence to 0-1 range
        final_confidence = min(1.0, max(0.0, base_confidence))
        
        return IntentMatch(
            intent=intent,
            confidence=final_confidence,
            evidence=evidence,
            keywords_matched=keywords_matched,
            patterns_matched=patterns_matched,
            context_clues=context_clues
        )
    
    def _calculate_overall_confidence(
        self, 
        primary_intent: IntentMatch, 
        secondary_intents: List[IntentMatch]
    ) -> float:
        """Calculate overall classification confidence.
        
        Args:
            primary_intent: Primary intent match
            secondary_intents: List of secondary intent matches
            
        Returns:
            Overall confidence score
        """
        if not secondary_intents:
            return primary_intent.confidence
        
        # Reduce confidence if there are competing intents
        competition_penalty = sum(intent.confidence for intent in secondary_intents) * 0.1
        
        return max(0.0, primary_intent.confidence - competition_penalty)
    
    def _generate_processing_notes(
        self,
        text: str,
        primary_intent: IntentMatch,
        secondary_intents: List[IntentMatch]
    ) -> List[str]:
        """Generate notes about the classification process.
        
        Args:
            text: Processed text
            primary_intent: Primary intent match
            secondary_intents: Secondary intent matches
            
        Returns:
            List of processing notes
        """
        notes = []
        
        # Text length note
        word_count = len(text.split())
        if word_count < 3:
            notes.append("Very short input - confidence may be low")
        elif word_count > 50:
            notes.append("Long input - may contain multiple intents")
        
        # Confidence level note
        if primary_intent.confidence < 0.3:
            notes.append("Low confidence classification - input may be ambiguous")
        elif primary_intent.confidence > 0.9:
            notes.append("High confidence classification - clear intent detected")
        
        # Multi-intent note
        if secondary_intents:
            secondary_names = [intent.intent.value for intent in secondary_intents[:2]]
            notes.append(f"Multiple intents detected: also considering {', '.join(secondary_names)}")
        
        # Pattern matching notes
        pattern_count = len(primary_intent.patterns_matched)
        keyword_count = len(primary_intent.keywords_matched)
        
        if pattern_count == 0 and keyword_count > 0:
            notes.append("Classification based on keywords only - no patterns matched")
        elif pattern_count > 0 and keyword_count == 0:
            notes.append("Classification based on patterns only - no keywords matched")
        elif pattern_count == 0 and keyword_count == 0:
            notes.append("Classification based on context clues only")
        
        # Unknown intent note
        if primary_intent.intent == FleetIntent.UNKNOWN:
            notes.append("No clear intent detected - may need human review")
        
        return notes
    
    def get_intent_description(self, intent: FleetIntent) -> str:
        """Get human-readable description of intent.
        
        Args:
            intent: Fleet intent enum
            
        Returns:
            Human-readable description
        """
        descriptions = {
            FleetIntent.CREATE_VEHICLE: "Add a new vehicle to the fleet system",
            FleetIntent.SCHEDULE_MAINTENANCE: "Schedule maintenance, service, or repairs for a vehicle",
            FleetIntent.MAKE_RESERVATION: "Reserve a vehicle for specific use or time period",
            FleetIntent.ASSIGN_PARKING: "Assign parking space or move vehicle to different location",
            FleetIntent.UPDATE_STATUS: "Update vehicle status or information in the system",
            FleetIntent.QUERY_INFORMATION: "Query vehicle information, status, or availability",
            FleetIntent.TRANSFER_VEHICLE: "Transfer vehicle between locations, users, or assignments",
            FleetIntent.CANCEL_OPERATION: "Cancel existing reservation, maintenance, or other operation",
            FleetIntent.UNKNOWN: "Intent could not be determined from the input"
        }
        
        return descriptions.get(intent, "Unknown intent type")
    
    def batch_classify(self, texts: List[str]) -> List[ClassificationResult]:
        """Classify multiple texts in batch.
        
        Args:
            texts: List of texts to classify
            
        Returns:
            List of classification results
        """
        results = []
        
        for i, text in enumerate(texts):
            self.logger.debug(f"Processing batch item {i+1}/{len(texts)}")
            result = self.classify(text)
            results.append(result)
        
        self.logger.info(f"Batch classification complete: {len(texts)} items processed")
        return results
    
    def get_classification_stats(self, results: List[ClassificationResult]) -> Dict[str, any]:
        """Get statistics about classification results.
        
        Args:
            results: List of classification results
            
        Returns:
            Dictionary with classification statistics
        """
        if not results:
            return {"error": "No results provided"}
        
        # Count intents
        intent_counts = defaultdict(int)
        confidence_sum = 0.0
        multi_intent_count = 0
        
        for result in results:
            intent_counts[result.primary_intent.intent.value] += 1
            confidence_sum += result.overall_confidence
            if result.is_multi_intent:
                multi_intent_count += 1
        
        # Calculate statistics
        avg_confidence = confidence_sum / len(results)
        multi_intent_rate = multi_intent_count / len(results)
        
        return {
            "total_classified": len(results),
            "intent_distribution": dict(intent_counts),
            "average_confidence": avg_confidence,
            "multi_intent_rate": multi_intent_rate,
            "most_common_intent": max(intent_counts, key=intent_counts.get),
            "confidence_stats": {
                "high_confidence": len([r for r in results if r.overall_confidence > 0.8]),
                "medium_confidence": len([r for r in results if 0.5 <= r.overall_confidence <= 0.8]),
                "low_confidence": len([r for r in results if r.overall_confidence < 0.5])
            }
        }