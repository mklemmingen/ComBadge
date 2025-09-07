"""Confidence Calculator for NLP Processing

Advanced confidence scoring system that combines multiple signals from intent
classification, entity extraction, and context analysis to provide reliable
confidence scores for fleet management operations.
"""

import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from statistics import mean, stdev

from ..core.logging_manager import LoggingManager
from .intent_classifier import ClassificationResult, IntentMatch, APIIntent
from .entity_extractor import ExtractionResult, EntityMatch, EntityType


class ConfidenceLevel(Enum):
    """Confidence level categories."""
    VERY_HIGH = "very_high"    # 0.9-1.0
    HIGH = "high"              # 0.75-0.89
    MEDIUM = "medium"          # 0.5-0.74
    LOW = "low"                # 0.25-0.49
    VERY_LOW = "very_low"      # 0.0-0.24


class ConfidenceFactor(Enum):
    """Factors that influence confidence calculation."""
    INTENT_CLARITY = "intent_clarity"
    ENTITY_COMPLETENESS = "entity_completeness"
    ENTITY_VALIDATION = "entity_validation"
    CONTEXT_CONSISTENCY = "context_consistency"
    TEXT_QUALITY = "text_quality"
    PATTERN_STRENGTH = "pattern_strength"
    CROSS_VALIDATION = "cross_validation"
    TEMPORAL_CONSISTENCY = "temporal_consistency"


@dataclass
class ConfidenceFactorScore:
    """Score for an individual confidence factor."""
    factor: ConfidenceFactor
    score: float
    weight: float
    evidence: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class ConfidenceCalculation:
    """Complete confidence calculation with breakdown."""
    overall_confidence: float
    confidence_level: ConfidenceLevel
    factor_scores: List[ConfidenceFactorScore] = field(default_factory=list)
    weighted_score: float = 0.0
    normalization_factor: float = 1.0
    calculation_method: str = "weighted_average"
    reliability_indicators: Dict[str, Any] = field(default_factory=dict)
    risk_factors: List[str] = field(default_factory=list)
    confidence_interval: Tuple[float, float] = (0.0, 1.0)


class ConfidenceCalculator:
    """Advanced confidence calculator for fleet management NLP processing."""
    
    def __init__(self):
        """Initialize confidence calculator with weights and thresholds."""
        self.logger = LoggingManager.get_logger(__name__)
        
        # Factor weights (must sum to 1.0)
        self.factor_weights = {
            ConfidenceFactor.INTENT_CLARITY: 0.25,
            ConfidenceFactor.ENTITY_COMPLETENESS: 0.20,
            ConfidenceFactor.ENTITY_VALIDATION: 0.15,
            ConfidenceFactor.CONTEXT_CONSISTENCY: 0.15,
            ConfidenceFactor.TEXT_QUALITY: 0.10,
            ConfidenceFactor.PATTERN_STRENGTH: 0.10,
            ConfidenceFactor.CROSS_VALIDATION: 0.03,
            ConfidenceFactor.TEMPORAL_CONSISTENCY: 0.02
        }
        
        # Confidence level thresholds
        self.confidence_thresholds = {
            ConfidenceLevel.VERY_HIGH: 0.9,
            ConfidenceLevel.HIGH: 0.75,
            ConfidenceLevel.MEDIUM: 0.5,
            ConfidenceLevel.LOW: 0.25,
            ConfidenceLevel.VERY_LOW: 0.0
        }
        
        # Risk factor patterns
        self.risk_factors = self._build_risk_factors()
        
        # Entity importance weights
        self.entity_importance = self._build_entity_importance()
        
    def _build_risk_factors(self) -> Dict[str, Dict[str, Any]]:
        """Build risk factors that reduce confidence.
        
        Returns:
            Dictionary of risk factors with penalties
        """
        return {
            "ambiguous_intent": {
                "penalty": 0.2,
                "description": "Multiple competing intents with similar confidence"
            },
            "incomplete_entities": {
                "penalty": 0.15,
                "description": "Missing critical entities for the identified intent"
            },
            "validation_failures": {
                "penalty": 0.3,
                "description": "Key entities failed format validation"
            },
            "temporal_conflicts": {
                "penalty": 0.25,
                "description": "Conflicting or impossible temporal references"
            },
            "low_text_quality": {
                "penalty": 0.1,
                "description": "Poor text quality or formatting issues"
            },
            "context_mismatch": {
                "penalty": 0.2,
                "description": "Intent and entities don't match contextual clues"
            },
            "weak_patterns": {
                "penalty": 0.15,
                "description": "Extraction based on weak or uncertain patterns"
            }
        }
    
    def _build_entity_importance(self) -> Dict[EntityType, float]:
        """Build entity importance weights for different intents.
        
        Returns:
            Dictionary mapping entity types to importance scores
        """
        return {
            EntityType.VIN: 1.0,
            EntityType.VEHICLE_ID: 0.95,
            EntityType.LICENSE_PLATE: 0.8,
            EntityType.DATE: 0.75,
            EntityType.TIME: 0.7,
            EntityType.PERSON_NAME: 0.6,
            EntityType.EMAIL: 0.65,
            EntityType.LOCATION: 0.5,
            EntityType.BUILDING: 0.4,
            EntityType.PARKING_SPOT: 0.4,
            EntityType.PHONE: 0.3,
            EntityType.DEPARTMENT: 0.2,
            EntityType.ROLE: 0.2
        }
    
    def calculate_confidence(
        self,
        text: str,
        intent_result: ClassificationResult,
        entity_result: ExtractionResult
    ) -> ConfidenceCalculation:
        """Calculate overall confidence from intent and entity results.
        
        Args:
            text: Original input text
            intent_result: Intent classification result
            entity_result: Entity extraction result
            
        Returns:
            Complete confidence calculation
        """
        self.logger.debug("Starting confidence calculation")
        
        # Calculate individual factor scores
        factor_scores = []
        
        # Intent clarity factor
        intent_score = self._calculate_intent_clarity(intent_result)
        factor_scores.append(intent_score)
        
        # Entity completeness factor
        completeness_score = self._calculate_entity_completeness(intent_result, entity_result)
        factor_scores.append(completeness_score)
        
        # Entity validation factor
        validation_score = self._calculate_entity_validation(entity_result)
        factor_scores.append(validation_score)
        
        # Context consistency factor
        context_score = self._calculate_context_consistency(text, intent_result, entity_result)
        factor_scores.append(context_score)
        
        # Text quality factor
        quality_score = self._calculate_text_quality(text)
        factor_scores.append(quality_score)
        
        # Pattern strength factor
        pattern_score = self._calculate_pattern_strength(entity_result)
        factor_scores.append(pattern_score)
        
        # Cross validation factor
        cross_validation_score = self._calculate_cross_validation(intent_result, entity_result)
        factor_scores.append(cross_validation_score)
        
        # Temporal consistency factor
        temporal_score = self._calculate_temporal_consistency(entity_result)
        factor_scores.append(temporal_score)
        
        # Calculate weighted score
        weighted_score = sum(
            score.score * self.factor_weights[score.factor]
            for score in factor_scores
        )
        
        # Apply risk factor penalties
        risk_factors, penalty = self._assess_risk_factors(text, intent_result, entity_result)
        final_score = max(0.0, weighted_score - penalty)
        
        # Calculate confidence interval
        confidence_interval = self._calculate_confidence_interval(factor_scores, final_score)
        
        # Determine confidence level
        confidence_level = self._determine_confidence_level(final_score)
        
        # Generate reliability indicators
        reliability_indicators = self._generate_reliability_indicators(
            factor_scores, intent_result, entity_result
        )
        
        calculation = ConfidenceCalculation(
            overall_confidence=final_score,
            confidence_level=confidence_level,
            factor_scores=factor_scores,
            weighted_score=weighted_score,
            risk_factors=risk_factors,
            confidence_interval=confidence_interval,
            reliability_indicators=reliability_indicators
        )
        
        self.logger.info(
            f"Confidence calculation complete: {final_score:.3f} ({confidence_level.value})"
        )
        
        return calculation
    
    def _calculate_intent_clarity(self, intent_result: ClassificationResult) -> ConfidenceFactorScore:
        """Calculate intent clarity factor score.
        
        Args:
            intent_result: Intent classification result
            
        Returns:
            Intent clarity factor score
        """
        evidence = []
        notes = []
        
        primary_confidence = intent_result.primary_intent.confidence
        evidence.append(f"Primary intent confidence: {primary_confidence:.2f}")
        
        # Base score from primary intent confidence
        base_score = primary_confidence
        
        # Penalty for competing intents
        if intent_result.secondary_intents:
            secondary_confidence = max(intent.confidence for intent in intent_result.secondary_intents)
            competition_penalty = secondary_confidence * 0.5
            base_score = max(0.0, base_score - competition_penalty)
            
            evidence.append(f"Secondary intent penalty: {competition_penalty:.2f}")
            notes.append(f"Competing intent detected: {intent_result.secondary_intents[0].intent.value}")
        
        # Bonus for strong pattern matches
        pattern_count = len(intent_result.primary_intent.patterns_matched)
        if pattern_count > 1:
            pattern_bonus = min(0.1, pattern_count * 0.05)
            base_score = min(1.0, base_score + pattern_bonus)
            evidence.append(f"Pattern bonus: {pattern_bonus:.2f}")
        
        # Penalty for unknown intent
        if intent_result.primary_intent.intent == APIIntent.UNKNOWN:
            base_score *= 0.3
            notes.append("Unknown intent significantly reduces clarity")
        
        return ConfidenceFactorScore(
            factor=ConfidenceFactor.INTENT_CLARITY,
            score=base_score,
            weight=self.factor_weights[ConfidenceFactor.INTENT_CLARITY],
            evidence=evidence,
            notes=notes
        )
    
    def _calculate_entity_completeness(
        self,
        intent_result: ClassificationResult,
        entity_result: ExtractionResult
    ) -> ConfidenceFactorScore:
        """Calculate entity completeness factor score.
        
        Args:
            intent_result: Intent classification result
            entity_result: Entity extraction result
            
        Returns:
            Entity completeness factor score
        """
        evidence = []
        notes = []
        
        # Define required entities for each intent
        required_entities = {
            APIIntent.CREATE_RESOURCE: [EntityType.VIN, EntityType.VEHICLE_ID],
            APIIntent.SCHEDULE_TASK: [EntityType.VEHICLE_ID, EntityType.DATE],
            APIIntent.MAKE_RESERVATION: [EntityType.VEHICLE_ID, EntityType.DATE, EntityType.PERSON_NAME],
            APIIntent.ASSIGN_RESOURCE: [EntityType.VEHICLE_ID, EntityType.LOCATION],
            APIIntent.UPDATE_STATUS: [EntityType.VEHICLE_ID],
            APIIntent.QUERY_INFORMATION: [EntityType.VEHICLE_ID],
            APIIntent.TRANSFER_RESOURCE: [EntityType.VEHICLE_ID, EntityType.LOCATION],
            APIIntent.CANCEL_OPERATION: [EntityType.VEHICLE_ID]
        }
        
        intent = intent_result.primary_intent.intent
        required_for_intent = required_entities.get(intent, [])
        
        if not required_for_intent:
            # No specific requirements
            base_score = 0.8
            notes.append("No specific entity requirements for this intent")
        else:
            # Check how many required entities are present
            found_entities = set(entity.entity_type for entity in entity_result.entities)
            missing_entities = [ent for ent in required_for_intent if ent not in found_entities]
            
            completeness_ratio = 1.0 - (len(missing_entities) / len(required_for_intent))
            base_score = completeness_ratio
            
            evidence.append(f"Required entities: {len(required_for_intent)}")
            evidence.append(f"Found entities: {len(required_for_intent) - len(missing_entities)}")
            evidence.append(f"Completeness ratio: {completeness_ratio:.2f}")
            
            if missing_entities:
                missing_names = [ent.value for ent in missing_entities]
                notes.append(f"Missing entities: {', '.join(missing_names)}")
        
        # Bonus for extra relevant entities
        total_entities = len(entity_result.entities)
        if total_entities > len(required_for_intent):
            extra_bonus = min(0.1, (total_entities - len(required_for_intent)) * 0.02)
            base_score = min(1.0, base_score + extra_bonus)
            evidence.append(f"Extra entities bonus: {extra_bonus:.2f}")
        
        return ConfidenceFactorScore(
            factor=ConfidenceFactor.ENTITY_COMPLETENESS,
            score=base_score,
            weight=self.factor_weights[ConfidenceFactor.ENTITY_COMPLETENESS],
            evidence=evidence,
            notes=notes
        )
    
    def _calculate_entity_validation(self, entity_result: ExtractionResult) -> ConfidenceFactorScore:
        """Calculate entity validation factor score.
        
        Args:
            entity_result: Entity extraction result
            
        Returns:
            Entity validation factor score
        """
        evidence = []
        notes = []
        
        if not entity_result.entities:
            base_score = 0.5  # Neutral score if no entities
            notes.append("No entities to validate")
        else:
            # Count validated vs failed entities
            validated_entities = [
                e for e in entity_result.entities 
                if e.validation_status and not e.validation_status.startswith("failed")
            ]
            failed_entities = [
                e for e in entity_result.entities 
                if e.validation_status and e.validation_status.startswith("failed")
            ]
            
            total_entities = len(entity_result.entities)
            validation_rate = len(validated_entities) / total_entities if total_entities > 0 else 0.0
            
            # Weight by entity importance
            weighted_validation = sum(
                self.entity_importance.get(entity.entity_type, 0.5)
                for entity in validated_entities
            )
            weighted_total = sum(
                self.entity_importance.get(entity.entity_type, 0.5)
                for entity in entity_result.entities
            )
            
            if weighted_total > 0:
                base_score = weighted_validation / weighted_total
            else:
                base_score = validation_rate
            
            evidence.append(f"Validated entities: {len(validated_entities)}/{total_entities}")
            evidence.append(f"Validation rate: {validation_rate:.2f}")
            evidence.append(f"Weighted validation score: {base_score:.2f}")
            
            if failed_entities:
                failed_types = [e.entity_type.value for e in failed_entities]
                notes.append(f"Failed validation: {', '.join(failed_types)}")
        
        return ConfidenceFactorScore(
            factor=ConfidenceFactor.ENTITY_VALIDATION,
            score=base_score,
            weight=self.factor_weights[ConfidenceFactor.ENTITY_VALIDATION],
            evidence=evidence,
            notes=notes
        )
    
    def _calculate_context_consistency(
        self,
        text: str,
        intent_result: ClassificationResult,
        entity_result: ExtractionResult
    ) -> ConfidenceFactorScore:
        """Calculate context consistency factor score.
        
        Args:
            text: Original input text
            intent_result: Intent classification result
            entity_result: Entity extraction result
            
        Returns:
            Context consistency factor score
        """
        evidence = []
        notes = []
        
        # Check if entities support the identified intent
        intent = intent_result.primary_intent.intent
        entity_types = set(entity.entity_type for entity in entity_result.entities)
        
        # Define expected entity combinations for each intent
        expected_combinations = {
            APIIntent.SCHEDULE_TASK: {EntityType.VEHICLE_ID, EntityType.DATE, EntityType.TIME},
            APIIntent.MAKE_RESERVATION: {EntityType.VEHICLE_ID, EntityType.DATE, EntityType.PERSON_NAME},
            APIIntent.ASSIGN_RESOURCE: {EntityType.VEHICLE_ID, EntityType.LOCATION, EntityType.PARKING_SPOT},
            APIIntent.UPDATE_STATUS: {EntityType.VEHICLE_ID},
            APIIntent.TRANSFER_RESOURCE: {EntityType.VEHICLE_ID, EntityType.LOCATION}
        }
        
        expected = expected_combinations.get(intent, set())
        if expected:
            consistency_score = len(entity_types.intersection(expected)) / len(expected)
            evidence.append(f"Entity-intent consistency: {consistency_score:.2f}")
        else:
            consistency_score = 0.7  # Neutral score for intents without specific expectations
            notes.append("No specific entity expectations for this intent")
        
        # Check for contextual keywords that support entities
        text_lower = text.lower()
        context_keywords = {
            EntityType.DATE: ["schedule", "book", "appointment", "meeting", "date"],
            EntityType.VEHICLE_ID: ["vehicle", "car", "truck", "van", "unit"],
            EntityType.LOCATION: ["building", "parking", "lot", "move", "location"],
            EntityType.PERSON_NAME: ["for", "contact", "driver", "manager", "client"]
        }
        
        context_support = 0.0
        supported_entities = 0
        
        for entity in entity_result.entities:
            keywords = context_keywords.get(entity.entity_type, [])
            if any(keyword in text_lower for keyword in keywords):
                context_support += 1.0
                supported_entities += 1
        
        if entity_result.entities:
            context_ratio = context_support / len(entity_result.entities)
            evidence.append(f"Context support ratio: {context_ratio:.2f}")
        else:
            context_ratio = 0.5
        
        # Combine scores
        base_score = (consistency_score * 0.6) + (context_ratio * 0.4)
        
        return ConfidenceFactorScore(
            factor=ConfidenceFactor.CONTEXT_CONSISTENCY,
            score=base_score,
            weight=self.factor_weights[ConfidenceFactor.CONTEXT_CONSISTENCY],
            evidence=evidence,
            notes=notes
        )
    
    def _calculate_text_quality(self, text: str) -> ConfidenceFactorScore:
        """Calculate text quality factor score.
        
        Args:
            text: Input text
            
        Returns:
            Text quality factor score
        """
        evidence = []
        notes = []
        
        # Length analysis
        word_count = len(text.split())
        char_count = len(text)
        
        # Length score (optimal range: 10-100 words)
        if word_count < 3:
            length_score = 0.3
            notes.append("Very short text may lack context")
        elif word_count < 10:
            length_score = 0.6
            notes.append("Short text may be incomplete")
        elif word_count <= 100:
            length_score = 1.0
        else:
            length_score = max(0.7, 1.0 - ((word_count - 100) * 0.01))
            notes.append("Long text may contain multiple requests")
        
        evidence.append(f"Word count: {word_count}")
        evidence.append(f"Length score: {length_score:.2f}")
        
        # Character quality analysis
        special_char_ratio = sum(1 for c in text if not c.isalnum() and c != ' ') / char_count
        if special_char_ratio > 0.3:
            char_quality = 0.6
            notes.append("High ratio of special characters")
        else:
            char_quality = 1.0
        
        # Capitalization patterns (mixed case is good)
        upper_ratio = sum(1 for c in text if c.isupper()) / char_count
        if 0.1 <= upper_ratio <= 0.3:
            caps_score = 1.0
        elif upper_ratio < 0.05:
            caps_score = 0.7
            notes.append("All lowercase text")
        elif upper_ratio > 0.8:
            caps_score = 0.6
            notes.append("All uppercase text")
        else:
            caps_score = 0.8
        
        # Repeated patterns (may indicate poor quality)
        words = text.lower().split()
        unique_words = set(words)
        repetition_score = len(unique_words) / len(words) if words else 1.0
        
        evidence.append(f"Repetition score: {repetition_score:.2f}")
        
        # Combined quality score
        base_score = (length_score * 0.4) + (char_quality * 0.3) + (caps_score * 0.2) + (repetition_score * 0.1)
        
        return ConfidenceFactorScore(
            factor=ConfidenceFactor.TEXT_QUALITY,
            score=base_score,
            weight=self.factor_weights[ConfidenceFactor.TEXT_QUALITY],
            evidence=evidence,
            notes=notes
        )
    
    def _calculate_pattern_strength(self, entity_result: ExtractionResult) -> ConfidenceFactorScore:
        """Calculate pattern strength factor score.
        
        Args:
            entity_result: Entity extraction result
            
        Returns:
            Pattern strength factor score
        """
        evidence = []
        notes = []
        
        if not entity_result.entities:
            base_score = 0.5
            notes.append("No entities to analyze patterns")
        else:
            # Analyze extraction methods
            pattern_entities = [e for e in entity_result.entities if "pattern" in e.extraction_method]
            high_confidence_entities = [e for e in entity_result.entities if e.confidence > 0.8]
            
            pattern_ratio = len(pattern_entities) / len(entity_result.entities)
            confidence_ratio = len(high_confidence_entities) / len(entity_result.entities)
            
            # Average entity confidence
            avg_confidence = mean(e.confidence for e in entity_result.entities)
            
            evidence.append(f"Pattern-based extractions: {len(pattern_entities)}/{len(entity_result.entities)}")
            evidence.append(f"High confidence entities: {len(high_confidence_entities)}")
            evidence.append(f"Average entity confidence: {avg_confidence:.2f}")
            
            base_score = (pattern_ratio * 0.4) + (confidence_ratio * 0.4) + (avg_confidence * 0.2)
        
        return ConfidenceFactorScore(
            factor=ConfidenceFactor.PATTERN_STRENGTH,
            score=base_score,
            weight=self.factor_weights[ConfidenceFactor.PATTERN_STRENGTH],
            evidence=evidence,
            notes=notes
        )
    
    def _calculate_cross_validation(
        self,
        intent_result: ClassificationResult,
        entity_result: ExtractionResult
    ) -> ConfidenceFactorScore:
        """Calculate cross validation factor score.
        
        Args:
            intent_result: Intent classification result
            entity_result: Entity extraction result
            
        Returns:
            Cross validation factor score
        """
        evidence = []
        notes = []
        
        # Cross-check intent keywords against entity context
        intent_keywords = set(intent_result.primary_intent.keywords_matched)
        
        # Check if entities have context that supports intent keywords
        entity_contexts = []
        for entity in entity_result.entities:
            entity_contexts.extend(entity.context_clues)
        
        entity_context_text = " ".join(entity_contexts).lower()
        
        supported_keywords = sum(
            1 for keyword in intent_keywords
            if keyword.lower() in entity_context_text
        )
        
        if intent_keywords:
            cross_validation_score = supported_keywords / len(intent_keywords)
            evidence.append(f"Cross-validated keywords: {supported_keywords}/{len(intent_keywords)}")
        else:
            cross_validation_score = 0.5
            notes.append("No intent keywords to cross-validate")
        
        base_score = cross_validation_score
        
        return ConfidenceFactorScore(
            factor=ConfidenceFactor.CROSS_VALIDATION,
            score=base_score,
            weight=self.factor_weights[ConfidenceFactor.CROSS_VALIDATION],
            evidence=evidence,
            notes=notes
        )
    
    def _calculate_temporal_consistency(self, entity_result: ExtractionResult) -> ConfidenceFactorScore:
        """Calculate temporal consistency factor score.
        
        Args:
            entity_result: Entity extraction result
            
        Returns:
            Temporal consistency factor score
        """
        evidence = []
        notes = []
        
        # Find temporal entities
        date_entities = [e for e in entity_result.entities if e.entity_type == EntityType.DATE]
        time_entities = [e for e in entity_result.entities if e.entity_type == EntityType.TIME]
        
        if not (date_entities or time_entities):
            base_score = 0.8  # Neutral score if no temporal entities
            notes.append("No temporal entities to validate")
        else:
            # Basic consistency checks (placeholder for more complex temporal logic)
            consistency_issues = 0
            total_checks = 0
            
            # Check for multiple conflicting dates
            if len(date_entities) > 1:
                total_checks += 1
                # Placeholder: would implement date conflict detection
                notes.append(f"Multiple dates detected: {len(date_entities)}")
            
            # Check for multiple conflicting times
            if len(time_entities) > 1:
                total_checks += 1
                # Placeholder: would implement time conflict detection
                notes.append(f"Multiple times detected: {len(time_entities)}")
            
            if total_checks > 0:
                base_score = 1.0 - (consistency_issues / total_checks)
            else:
                base_score = 1.0
            
            evidence.append(f"Temporal entities: {len(date_entities)} dates, {len(time_entities)} times")
        
        return ConfidenceFactorScore(
            factor=ConfidenceFactor.TEMPORAL_CONSISTENCY,
            score=base_score,
            weight=self.factor_weights[ConfidenceFactor.TEMPORAL_CONSISTENCY],
            evidence=evidence,
            notes=notes
        )
    
    def _assess_risk_factors(
        self,
        text: str,
        intent_result: ClassificationResult,
        entity_result: ExtractionResult
    ) -> Tuple[List[str], float]:
        """Assess risk factors that reduce overall confidence.
        
        Args:
            text: Input text
            intent_result: Intent classification result
            entity_result: Entity extraction result
            
        Returns:
            Tuple of (risk_factors, total_penalty)
        """
        risk_factors = []
        total_penalty = 0.0
        
        # Ambiguous intent
        if len(intent_result.secondary_intents) > 0:
            highest_secondary = max(intent_result.secondary_intents, key=lambda x: x.confidence)
            if highest_secondary.confidence > 0.6:
                risk_factors.append("ambiguous_intent")
                total_penalty += self.risk_factors["ambiguous_intent"]["penalty"]
        
        # Validation failures
        failed_validations = [
            e for e in entity_result.entities 
            if e.validation_status and e.validation_status.startswith("failed")
        ]
        if failed_validations:
            risk_factors.append("validation_failures")
            total_penalty += self.risk_factors["validation_failures"]["penalty"]
        
        # Low text quality
        word_count = len(text.split())
        if word_count < 3:
            risk_factors.append("low_text_quality")
            total_penalty += self.risk_factors["low_text_quality"]["penalty"]
        
        # Weak patterns
        low_confidence_entities = [e for e in entity_result.entities if e.confidence < 0.5]
        if len(low_confidence_entities) > len(entity_result.entities) / 2:
            risk_factors.append("weak_patterns")
            total_penalty += self.risk_factors["weak_patterns"]["penalty"]
        
        return risk_factors, total_penalty
    
    def _calculate_confidence_interval(
        self,
        factor_scores: List[ConfidenceFactorScore],
        final_score: float
    ) -> Tuple[float, float]:
        """Calculate confidence interval for the final score.
        
        Args:
            factor_scores: List of factor scores
            final_score: Final calculated score
            
        Returns:
            Confidence interval (lower_bound, upper_bound)
        """
        if len(factor_scores) < 2:
            # Not enough data for meaningful interval
            return (max(0.0, final_score - 0.1), min(1.0, final_score + 0.1))
        
        scores = [fs.score for fs in factor_scores]
        score_stdev = stdev(scores) if len(scores) > 1 else 0.1
        
        # Simple confidence interval (±1 standard deviation)
        lower_bound = max(0.0, final_score - score_stdev)
        upper_bound = min(1.0, final_score + score_stdev)
        
        return (lower_bound, upper_bound)
    
    def _determine_confidence_level(self, score: float) -> ConfidenceLevel:
        """Determine confidence level from score.
        
        Args:
            score: Confidence score
            
        Returns:
            Confidence level category
        """
        if score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 0.75:
            return ConfidenceLevel.HIGH
        elif score >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.25:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def _generate_reliability_indicators(
        self,
        factor_scores: List[ConfidenceFactorScore],
        intent_result: ClassificationResult,
        entity_result: ExtractionResult
    ) -> Dict[str, Any]:
        """Generate reliability indicators for the calculation.
        
        Args:
            factor_scores: List of factor scores
            intent_result: Intent classification result
            entity_result: Entity extraction result
            
        Returns:
            Dictionary of reliability indicators
        """
        scores = [fs.score for fs in factor_scores]
        
        return {
            "score_variance": stdev(scores) if len(scores) > 1 else 0.0,
            "score_range": max(scores) - min(scores) if scores else 0.0,
            "consistent_factors": len([s for s in scores if 0.6 <= s <= 0.9]),
            "outlier_factors": len([s for s in scores if s < 0.3 or s > 0.95]),
            "intent_evidence_strength": len(intent_result.primary_intent.evidence),
            "entity_evidence_strength": sum(len(e.context_clues) for e in entity_result.entities),
            "calculation_stability": "high" if stdev(scores) < 0.2 else "medium" if stdev(scores) < 0.4 else "low"
        }
    
    def export_calculation_details(self, calculation: ConfidenceCalculation) -> Dict[str, Any]:
        """Export detailed calculation breakdown.
        
        Args:
            calculation: Confidence calculation result
            
        Returns:
            Detailed calculation data
        """
        return {
            "overall_confidence": calculation.overall_confidence,
            "confidence_level": calculation.confidence_level.value,
            "weighted_score": calculation.weighted_score,
            "factor_breakdown": [
                {
                    "factor": fs.factor.value,
                    "score": fs.score,
                    "weight": fs.weight,
                    "weighted_contribution": fs.score * fs.weight,
                    "evidence": fs.evidence,
                    "notes": fs.notes
                }
                for fs in calculation.factor_scores
            ],
            "risk_factors": calculation.risk_factors,
            "confidence_interval": {
                "lower": calculation.confidence_interval[0],
                "upper": calculation.confidence_interval[1],
                "range": calculation.confidence_interval[1] - calculation.confidence_interval[0]
            },
            "reliability_indicators": calculation.reliability_indicators
        }