"""Template Selector for Fleet Operations

Intelligent template selection system that matches classified intents to appropriate
templates with scoring, fallback mechanisms, and multi-step operation handling.
"""

from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import re
from datetime import datetime

from ...core.logging_manager import LoggingManager
from ...intelligence.intent_classifier import ClassificationResult, APIIntent
from ...intelligence.entity_extractor import ExtractionResult, EntityType
from .template_manager import TemplateManager, TemplateMetadata


class SelectionStrategy(Enum):
    """Template selection strategies."""
    EXACT_MATCH = "exact_match"
    BEST_FIT = "best_fit"
    MULTI_TEMPLATE = "multi_template"
    FALLBACK = "fallback"
    HYBRID = "hybrid"


class MatchingCriteria(Enum):
    """Criteria for template matching."""
    INTENT_ALIGNMENT = "intent_alignment"
    ENTITY_COVERAGE = "entity_coverage"
    REQUIRED_ENTITIES = "required_entities"
    TEMPLATE_POPULARITY = "template_popularity"
    SUCCESS_RATE = "success_rate"
    API_COMPATIBILITY = "api_compatibility"


@dataclass
class TemplateCriteria:
    """Criteria for template selection."""
    primary_intent: APIIntent
    secondary_intents: List[APIIntent] = field(default_factory=list)
    available_entities: Dict[EntityType, List[str]] = field(default_factory=dict)
    required_entities: Set[str] = field(default_factory=set)
    preferred_categories: List[str] = field(default_factory=list)
    excluded_templates: Set[str] = field(default_factory=set)
    selection_strategy: SelectionStrategy = SelectionStrategy.BEST_FIT
    min_confidence_threshold: float = 0.6
    max_templates: int = 3
    allow_partial_matches: bool = True


@dataclass
class TemplateScore:
    """Scoring information for a template candidate."""
    template_id: str
    total_score: float
    criteria_scores: Dict[MatchingCriteria, float] = field(default_factory=dict)
    matching_entities: Set[str] = field(default_factory=set)
    missing_entities: Set[str] = field(default_factory=set)
    confidence: float = 0.0
    reasoning: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class SelectionResult:
    """Result of template selection process."""
    selected_templates: List[TemplateScore] = field(default_factory=list)
    primary_template: Optional[TemplateScore] = None
    fallback_templates: List[TemplateScore] = field(default_factory=list)
    selection_confidence: float = 0.0
    selection_strategy_used: SelectionStrategy = SelectionStrategy.BEST_FIT
    selection_notes: List[str] = field(default_factory=list)
    multi_step_operations: List[Dict[str, Any]] = field(default_factory=list)
    processing_time: float = 0.0


class TemplateSelector:
    """Intelligent template selector with scoring and fallback mechanisms."""
    
    def __init__(self, template_manager: TemplateManager):
        """Initialize template selector.
        
        Args:
            template_manager: Template manager instance
        """
        self.template_manager = template_manager
        self.logger = LoggingManager.get_logger(__name__)
        
        # Intent to category mapping
        self.intent_category_map = self._build_intent_category_map()
        
        # Scoring weights for different criteria
        self.scoring_weights = {
            MatchingCriteria.INTENT_ALIGNMENT: 0.30,
            MatchingCriteria.ENTITY_COVERAGE: 0.25,
            MatchingCriteria.REQUIRED_ENTITIES: 0.20,
            MatchingCriteria.TEMPLATE_POPULARITY: 0.10,
            MatchingCriteria.SUCCESS_RATE: 0.10,
            MatchingCriteria.API_COMPATIBILITY: 0.05
        }
        
        # Template selection settings
        self.fallback_enabled = True
        self.multi_step_detection = True
        self.partial_match_penalty = 0.3
        
    def _build_intent_category_map(self) -> Dict[APIIntent, List[str]]:
        """Build mapping from intents to template categories.
        
        Returns:
            Dictionary mapping intents to categories
        """
        return {
            APIIntent.CREATE_RESOURCE: ["vehicle_operations"],
            APIIntent.SCHEDULE_TASK: ["maintenance"],
            APIIntent.MAKE_RESERVATION: ["reservations"],
            APIIntent.ASSIGN_RESOURCE: ["parking"],
            APIIntent.UPDATE_STATUS: ["vehicle_operations", "maintenance"],
            APIIntent.QUERY_INFORMATION: ["vehicle_operations", "reservations", "maintenance"],
            APIIntent.TRANSFER_RESOURCE: ["vehicle_operations", "parking"],
            APIIntent.CANCEL_OPERATION: ["reservations", "maintenance"]
        }
    
    def select_templates(
        self,
        intent_result: ClassificationResult,
        entity_result: ExtractionResult,
        criteria: Optional[TemplateCriteria] = None
    ) -> SelectionResult:
        """Select optimal templates based on intent and entities.
        
        Args:
            intent_result: Intent classification result
            entity_result: Entity extraction result
            criteria: Optional selection criteria
            
        Returns:
            Template selection result
        """
        start_time = datetime.now()
        
        self.logger.debug("Starting template selection process")
        
        # Create default criteria if not provided
        if not criteria:
            criteria = self._create_default_criteria(intent_result, entity_result)
        
        # Get candidate templates
        candidate_templates = self._get_candidate_templates(criteria)
        
        if not candidate_templates:
            self.logger.warning("No candidate templates found")
            return SelectionResult(
                selection_notes=["No templates found matching criteria"],
                processing_time=(datetime.now() - start_time).total_seconds()
            )
        
        # Score candidate templates
        scored_templates = self._score_templates(
            candidate_templates, criteria, intent_result, entity_result
        )
        
        # Apply selection strategy
        selection_result = self._apply_selection_strategy(
            scored_templates, criteria, intent_result
        )
        
        # Calculate processing time
        selection_result.processing_time = (datetime.now() - start_time).total_seconds()
        
        self.logger.info(
            f"Template selection complete: {len(selection_result.selected_templates)} templates selected, "
            f"confidence: {selection_result.selection_confidence:.2f}"
        )
        
        return selection_result
    
    def _create_default_criteria(
        self,
        intent_result: ClassificationResult,
        entity_result: ExtractionResult
    ) -> TemplateCriteria:
        """Create default selection criteria from results.
        
        Args:
            intent_result: Intent classification result
            entity_result: Entity extraction result
            
        Returns:
            Default template criteria
        """
        # Extract available entities by type
        available_entities = {}
        for entity in entity_result.entities:
            if entity.entity_type not in available_entities:
                available_entities[entity.entity_type] = []
            available_entities[entity.entity_type].append(entity.value)
        
        # Get preferred categories from primary intent
        preferred_categories = self.intent_category_map.get(
            intent_result.primary_intent.intent, []
        )
        
        # Add categories from secondary intents
        for secondary in intent_result.secondary_intents:
            secondary_categories = self.intent_category_map.get(secondary.intent, [])
            preferred_categories.extend(secondary_categories)
        
        # Remove duplicates while preserving order
        preferred_categories = list(dict.fromkeys(preferred_categories))
        
        # Determine selection strategy
        strategy = SelectionStrategy.BEST_FIT
        if intent_result.is_multi_intent:
            strategy = SelectionStrategy.MULTI_TEMPLATE
        elif intent_result.overall_confidence < 0.6:
            strategy = SelectionStrategy.FALLBACK
        
        return TemplateCriteria(
            primary_intent=intent_result.primary_intent.intent,
            secondary_intents=[si.intent for si in intent_result.secondary_intents],
            available_entities=available_entities,
            preferred_categories=preferred_categories,
            selection_strategy=strategy,
            min_confidence_threshold=0.5,
            max_templates=5 if intent_result.is_multi_intent else 3
        )
    
    def _get_candidate_templates(self, criteria: TemplateCriteria) -> List[str]:
        """Get candidate templates based on criteria.
        
        Args:
            criteria: Selection criteria
            
        Returns:
            List of candidate template IDs
        """
        candidate_templates = set()
        
        # Get templates by preferred categories
        for category in criteria.preferred_categories:
            category_templates = self.template_manager.find_templates_by_category(category)
            candidate_templates.update(category_templates)
        
        # If no candidates from preferred categories, search all categories
        if not candidate_templates:
            all_templates = self.template_manager.registry.templates.keys()
            candidate_templates.update(all_templates)
        
        # Remove excluded templates
        candidate_templates -= criteria.excluded_templates
        
        # Convert to sorted list for consistent ordering
        return sorted(candidate_templates)
    
    def _score_templates(
        self,
        candidate_templates: List[str],
        criteria: TemplateCriteria,
        intent_result: ClassificationResult,
        entity_result: ExtractionResult
    ) -> List[TemplateScore]:
        """Score candidate templates against criteria.
        
        Args:
            candidate_templates: List of candidate template IDs
            criteria: Selection criteria
            intent_result: Intent classification result
            entity_result: Entity extraction result
            
        Returns:
            List of scored templates
        """
        scored_templates = []
        
        for template_id in candidate_templates:
            template_metadata = self.template_manager.get_template_metadata(template_id)
            if not template_metadata:
                continue
            
            score = self._score_single_template(
                template_id, template_metadata, criteria, intent_result, entity_result
            )
            
            # Filter by minimum confidence threshold
            if score.total_score >= criteria.min_confidence_threshold:
                scored_templates.append(score)
        
        # Sort by total score
        scored_templates.sort(key=lambda x: x.total_score, reverse=True)
        
        return scored_templates
    
    def _score_single_template(
        self,
        template_id: str,
        metadata: TemplateMetadata,
        criteria: TemplateCriteria,
        intent_result: ClassificationResult,
        entity_result: ExtractionResult
    ) -> TemplateScore:
        """Score a single template.
        
        Args:
            template_id: Template ID
            metadata: Template metadata
            criteria: Selection criteria
            intent_result: Intent classification result
            entity_result: Entity extraction result
            
        Returns:
            Template score
        """
        score = TemplateScore(template_id=template_id)
        
        # Score intent alignment
        intent_score = self._score_intent_alignment(
            metadata, criteria.primary_intent, criteria.secondary_intents
        )
        score.criteria_scores[MatchingCriteria.INTENT_ALIGNMENT] = intent_score
        
        # Score entity coverage
        entity_score, matching_entities, missing_entities = self._score_entity_coverage(
            metadata, criteria.available_entities
        )
        score.criteria_scores[MatchingCriteria.ENTITY_COVERAGE] = entity_score
        score.matching_entities = matching_entities
        score.missing_entities = missing_entities
        
        # Score required entities
        required_score = self._score_required_entities(metadata, criteria.available_entities)
        score.criteria_scores[MatchingCriteria.REQUIRED_ENTITIES] = required_score
        
        # Score template popularity
        popularity_score = self._score_template_popularity(template_id)
        score.criteria_scores[MatchingCriteria.TEMPLATE_POPULARITY] = popularity_score
        
        # Score success rate
        success_score = self._score_success_rate(template_id)
        score.criteria_scores[MatchingCriteria.SUCCESS_RATE] = success_score
        
        # Score API compatibility (placeholder)
        api_score = self._score_api_compatibility(metadata)
        score.criteria_scores[MatchingCriteria.API_COMPATIBILITY] = api_score
        
        # Calculate total weighted score
        total_score = sum(
            score.criteria_scores[criteria_type] * weight
            for criteria_type, weight in self.scoring_weights.items()
        )
        
        # Apply penalties
        if missing_entities and not criteria.allow_partial_matches:
            total_score *= (1.0 - self.partial_match_penalty)
        
        score.total_score = total_score
        score.confidence = min(1.0, total_score)
        
        # Generate reasoning
        score.reasoning = self._generate_scoring_reasoning(score, metadata)
        
        # Generate warnings
        score.warnings = self._generate_scoring_warnings(score, metadata)
        
        return score
    
    def _score_intent_alignment(
        self,
        metadata: TemplateMetadata,
        primary_intent: APIIntent,
        secondary_intents: List[APIIntent]
    ) -> float:
        """Score how well template aligns with identified intents.
        
        Args:
            metadata: Template metadata
            primary_intent: Primary intent
            secondary_intents: Secondary intents
            
        Returns:
            Intent alignment score (0-1)
        """
        # Map intent to expected template names/categories
        intent_mappings = {
            APIIntent.CREATE_RESOURCE: ["create", "new", "add"],
            APIIntent.SCHEDULE_TASK: ["schedule", "maintenance", "service"],
            APIIntent.MAKE_RESERVATION: ["reserve", "book", "reservation"],
            APIIntent.ASSIGN_RESOURCE: ["assign", "park", "parking"],
            APIIntent.UPDATE_STATUS: ["update", "modify", "change"],
            APIIntent.QUERY_INFORMATION: ["query", "search", "find", "get"],
            APIIntent.TRANSFER_RESOURCE: ["transfer", "move", "relocate"],
            APIIntent.CANCEL_OPERATION: ["cancel", "remove", "delete"]
        }
        
        score = 0.0
        
        # Check primary intent alignment
        primary_keywords = intent_mappings.get(primary_intent, [])
        template_text = f"{metadata.name} {metadata.description} {metadata.category}".lower()
        
        for keyword in primary_keywords:
            if keyword in template_text:
                score += 0.8  # High score for primary intent match
                break
        
        # Check secondary intent alignment
        for secondary_intent in secondary_intents[:2]:  # Limit to top 2 secondary intents
            secondary_keywords = intent_mappings.get(secondary_intent, [])
            for keyword in secondary_keywords:
                if keyword in template_text:
                    score += 0.2  # Lower score for secondary intent match
                    break
        
        return min(1.0, score)
    
    def _score_entity_coverage(
        self,
        metadata: TemplateMetadata,
        available_entities: Dict[EntityType, List[str]]
    ) -> Tuple[float, Set[str], Set[str]]:
        """Score how well available entities cover template requirements.
        
        Args:
            metadata: Template metadata
            available_entities: Available entities by type
            
        Returns:
            Tuple of (coverage_score, matching_entities, missing_entities)
        """
        all_template_entities = set(metadata.required_entities + metadata.optional_entities)
        
        # Map entity types to template entity names
        entity_type_map = {
            EntityType.VEHICLE_ID: ["vehicle_id", "vehicle", "unit_id"],
            EntityType.VIN: ["vin", "vehicle_identification"],
            EntityType.LICENSE_PLATE: ["license_plate", "plate", "registration"],
            EntityType.PERSON_NAME: ["user", "driver", "person", "contact", "assigned_to"],
            EntityType.DATE: ["date", "scheduled_date", "start_date", "end_date"],
            EntityType.TIME: ["time", "start_time", "end_time", "scheduled_time"],
            EntityType.LOCATION: ["location", "address", "site", "building"],
            EntityType.BUILDING: ["building", "location", "site"],
            EntityType.PARKING_SPOT: ["parking_spot", "spot", "space", "bay"],
            EntityType.EMAIL: ["email", "contact_email", "user_email"],
            EntityType.PHONE: ["phone", "contact_phone", "telephone"],
            EntityType.DEPARTMENT: ["department", "division", "unit"],
            EntityType.ROLE: ["role", "position", "title"]
        }
        
        matching_entities = set()
        
        # Check which template entities can be satisfied
        for template_entity in all_template_entities:
            template_entity_lower = template_entity.lower()
            
            for entity_type, values in available_entities.items():
                if values:  # Has values for this entity type
                    mapped_names = entity_type_map.get(entity_type, [])
                    
                    # Direct name match
                    if template_entity_lower in mapped_names:
                        matching_entities.add(template_entity)
                        break
                    
                    # Partial name match
                    for mapped_name in mapped_names:
                        if mapped_name in template_entity_lower or template_entity_lower in mapped_name:
                            matching_entities.add(template_entity)
                            break
        
        missing_entities = all_template_entities - matching_entities
        
        # Calculate coverage score
        if all_template_entities:
            coverage_score = len(matching_entities) / len(all_template_entities)
        else:
            coverage_score = 1.0  # Perfect score if no entities required
        
        return coverage_score, matching_entities, missing_entities
    
    def _score_required_entities(
        self,
        metadata: TemplateMetadata,
        available_entities: Dict[EntityType, List[str]]
    ) -> float:
        """Score coverage of required entities specifically.
        
        Args:
            metadata: Template metadata
            available_entities: Available entities
            
        Returns:
            Required entities coverage score (0-1)
        """
        if not metadata.required_entities:
            return 1.0  # Perfect score if no required entities
        
        _, matching_entities, _ = self._score_entity_coverage(metadata, available_entities)
        
        required_entities_set = set(metadata.required_entities)
        matching_required = required_entities_set.intersection(matching_entities)
        
        return len(matching_required) / len(required_entities_set)
    
    def _score_template_popularity(self, template_id: str) -> float:
        """Score template based on usage popularity.
        
        Args:
            template_id: Template ID
            
        Returns:
            Popularity score (0-1)
        """
        stats = self.template_manager.get_template_stats(template_id)
        if not stats or stats.total_uses == 0:
            return 0.5  # Neutral score for unused templates
        
        # Normalize usage count (log scale to prevent dominance of heavily used templates)
        import math
        normalized_usage = min(1.0, math.log(stats.total_uses + 1) / math.log(100))
        
        return normalized_usage
    
    def _score_success_rate(self, template_id: str) -> float:
        """Score template based on historical success rate.
        
        Args:
            template_id: Template ID
            
        Returns:
            Success rate score (0-1)
        """
        stats = self.template_manager.get_template_stats(template_id)
        if not stats or stats.total_uses == 0:
            return 1.0  # Optimistic score for new templates
        
        success_rate = stats.successful_uses / stats.total_uses
        return success_rate
    
    def _score_api_compatibility(self, metadata: TemplateMetadata) -> float:
        """Score API compatibility (placeholder for future implementation).
        
        Args:
            metadata: Template metadata
            
        Returns:
            API compatibility score (0-1)
        """
        # Placeholder implementation
        if metadata.api_endpoint and metadata.http_method:
            return 1.0
        elif metadata.api_endpoint:
            return 0.8
        else:
            return 0.5
    
    def _generate_scoring_reasoning(self, score: TemplateScore, metadata: TemplateMetadata) -> List[str]:
        """Generate reasoning for template scoring.
        
        Args:
            score: Template score
            metadata: Template metadata
            
        Returns:
            List of reasoning statements
        """
        reasoning = []
        
        # Intent alignment reasoning
        intent_score = score.criteria_scores.get(MatchingCriteria.INTENT_ALIGNMENT, 0)
        if intent_score > 0.7:
            reasoning.append(f"Strong intent alignment with template '{metadata.name}'")
        elif intent_score > 0.4:
            reasoning.append(f"Moderate intent alignment with template '{metadata.name}'")
        else:
            reasoning.append(f"Weak intent alignment with template '{metadata.name}'")
        
        # Entity coverage reasoning
        entity_score = score.criteria_scores.get(MatchingCriteria.ENTITY_COVERAGE, 0)
        if score.matching_entities:
            reasoning.append(f"Covers {len(score.matching_entities)} entities: {', '.join(sorted(score.matching_entities))}")
        
        if score.missing_entities:
            reasoning.append(f"Missing {len(score.missing_entities)} entities: {', '.join(sorted(score.missing_entities))}")
        
        # Success rate reasoning
        success_score = score.criteria_scores.get(MatchingCriteria.SUCCESS_RATE, 0)
        if success_score > 0.9:
            reasoning.append("High historical success rate")
        elif success_score < 0.5:
            reasoning.append("Lower historical success rate")
        
        return reasoning
    
    def _generate_scoring_warnings(self, score: TemplateScore, metadata: TemplateMetadata) -> List[str]:
        """Generate warnings for template scoring.
        
        Args:
            score: Template score
            metadata: Template metadata
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Missing required entities warning
        required_entities = set(metadata.required_entities)
        if score.missing_entities.intersection(required_entities):
            missing_required = score.missing_entities.intersection(required_entities)
            warnings.append(f"Missing required entities: {', '.join(sorted(missing_required))}")
        
        # Low confidence warning
        if score.total_score < 0.5:
            warnings.append("Low overall confidence for this template match")
        
        # No API endpoint warning
        if not metadata.api_endpoint:
            warnings.append("Template has no defined API endpoint")
        
        return warnings
    
    def _apply_selection_strategy(
        self,
        scored_templates: List[TemplateScore],
        criteria: TemplateCriteria,
        intent_result: ClassificationResult
    ) -> SelectionResult:
        """Apply selection strategy to choose final templates.
        
        Args:
            scored_templates: List of scored templates
            criteria: Selection criteria
            intent_result: Intent classification result
            
        Returns:
            Selection result
        """
        result = SelectionResult(selection_strategy_used=criteria.selection_strategy)
        
        if criteria.selection_strategy == SelectionStrategy.EXACT_MATCH:
            result = self._apply_exact_match_strategy(scored_templates, criteria)
        
        elif criteria.selection_strategy == SelectionStrategy.BEST_FIT:
            result = self._apply_best_fit_strategy(scored_templates, criteria)
        
        elif criteria.selection_strategy == SelectionStrategy.MULTI_TEMPLATE:
            result = self._apply_multi_template_strategy(scored_templates, criteria, intent_result)
        
        elif criteria.selection_strategy == SelectionStrategy.FALLBACK:
            result = self._apply_fallback_strategy(scored_templates, criteria)
        
        else:  # HYBRID
            result = self._apply_hybrid_strategy(scored_templates, criteria, intent_result)
        
        # Set primary template
        if result.selected_templates:
            result.primary_template = result.selected_templates[0]
            result.selection_confidence = result.primary_template.confidence
        
        return result
    
    def _apply_exact_match_strategy(self, scored_templates: List[TemplateScore], criteria: TemplateCriteria) -> SelectionResult:
        """Apply exact match selection strategy.
        
        Args:
            scored_templates: Scored templates
            criteria: Selection criteria
            
        Returns:
            Selection result
        """
        result = SelectionResult(selection_strategy_used=SelectionStrategy.EXACT_MATCH)
        
        # Find templates with perfect or near-perfect scores
        for template_score in scored_templates:
            if template_score.total_score >= 0.9 and not template_score.missing_entities:
                result.selected_templates.append(template_score)
                break  # Take only the first exact match
        
        if not result.selected_templates:
            result.selection_notes.append("No exact match found, falling back to best fit")
            return self._apply_best_fit_strategy(scored_templates, criteria)
        
        return result
    
    def _apply_best_fit_strategy(self, scored_templates: List[TemplateScore], criteria: TemplateCriteria) -> SelectionResult:
        """Apply best fit selection strategy.
        
        Args:
            scored_templates: Scored templates
            criteria: Selection criteria
            
        Returns:
            Selection result
        """
        result = SelectionResult(selection_strategy_used=SelectionStrategy.BEST_FIT)
        
        # Take top template(s) up to max_templates
        result.selected_templates = scored_templates[:criteria.max_templates]
        
        if result.selected_templates:
            result.selection_confidence = result.selected_templates[0].total_score
        
        return result
    
    def _apply_multi_template_strategy(
        self,
        scored_templates: List[TemplateScore],
        criteria: TemplateCriteria,
        intent_result: ClassificationResult
    ) -> SelectionResult:
        """Apply multi-template selection strategy for multi-intent operations.
        
        Args:
            scored_templates: Scored templates
            criteria: Selection criteria
            intent_result: Intent classification result
            
        Returns:
            Selection result
        """
        result = SelectionResult(selection_strategy_used=SelectionStrategy.MULTI_TEMPLATE)
        
        # Group templates by intent/category
        template_groups = {}
        
        for template_score in scored_templates:
            metadata = self.template_manager.get_template_metadata(template_score.template_id)
            if metadata:
                category = metadata.category
                if category not in template_groups:
                    template_groups[category] = []
                template_groups[category].append(template_score)
        
        # Select best template from each relevant category
        for intent in [criteria.primary_intent] + criteria.secondary_intents:
            preferred_categories = self.intent_category_map.get(intent, [])
            
            for category in preferred_categories:
                if category in template_groups and template_groups[category]:
                    best_in_category = template_groups[category][0]  # Already sorted by score
                    if best_in_category not in result.selected_templates:
                        result.selected_templates.append(best_in_category)
        
        # Limit to max_templates
        result.selected_templates = result.selected_templates[:criteria.max_templates]
        
        # Create multi-step operation plan
        if len(result.selected_templates) > 1:
            result.multi_step_operations = self._create_multi_step_plan(
                result.selected_templates, intent_result
            )
        
        if result.selected_templates:
            # Calculate average confidence
            avg_confidence = sum(ts.confidence for ts in result.selected_templates) / len(result.selected_templates)
            result.selection_confidence = avg_confidence
        
        return result
    
    def _apply_fallback_strategy(self, scored_templates: List[TemplateScore], criteria: TemplateCriteria) -> SelectionResult:
        """Apply fallback selection strategy for low-confidence situations.
        
        Args:
            scored_templates: Scored templates
            criteria: Selection criteria
            
        Returns:
            Selection result
        """
        result = SelectionResult(selection_strategy_used=SelectionStrategy.FALLBACK)
        
        # Lower the confidence threshold for fallback
        fallback_threshold = criteria.min_confidence_threshold * 0.7
        
        # Include templates above fallback threshold
        for template_score in scored_templates:
            if (template_score.total_score >= fallback_threshold and 
                len(result.selected_templates) < criteria.max_templates):
                result.selected_templates.append(template_score)
        
        # If still no templates, take the best available
        if not result.selected_templates and scored_templates:
            result.selected_templates.append(scored_templates[0])
            result.selection_notes.append("Using best available template despite low confidence")
        
        # Mark additional templates as fallbacks
        remaining_templates = scored_templates[len(result.selected_templates):criteria.max_templates*2]
        result.fallback_templates = remaining_templates
        
        if result.selected_templates:
            result.selection_confidence = result.selected_templates[0].total_score
        
        return result
    
    def _apply_hybrid_strategy(
        self,
        scored_templates: List[TemplateScore],
        criteria: TemplateCriteria,
        intent_result: ClassificationResult
    ) -> SelectionResult:
        """Apply hybrid selection strategy combining multiple approaches.
        
        Args:
            scored_templates: Scored templates
            criteria: Selection criteria
            intent_result: Intent classification result
            
        Returns:
            Selection result
        """
        # Try exact match first
        exact_result = self._apply_exact_match_strategy(scored_templates, criteria)
        if exact_result.selected_templates:
            exact_result.selection_strategy_used = SelectionStrategy.HYBRID
            exact_result.selection_notes.append("Used exact match within hybrid strategy")
            return exact_result
        
        # Try multi-template if multi-intent
        if intent_result.is_multi_intent:
            multi_result = self._apply_multi_template_strategy(scored_templates, criteria, intent_result)
            multi_result.selection_strategy_used = SelectionStrategy.HYBRID
            multi_result.selection_notes.append("Used multi-template within hybrid strategy")
            return multi_result
        
        # Fall back to best fit
        best_fit_result = self._apply_best_fit_strategy(scored_templates, criteria)
        best_fit_result.selection_strategy_used = SelectionStrategy.HYBRID
        best_fit_result.selection_notes.append("Used best fit within hybrid strategy")
        return best_fit_result
    
    def _create_multi_step_plan(
        self,
        selected_templates: List[TemplateScore],
        intent_result: ClassificationResult
    ) -> List[Dict[str, Any]]:
        """Create multi-step operation plan.
        
        Args:
            selected_templates: Selected templates
            intent_result: Intent classification result
            
        Returns:
            List of operation steps
        """
        steps = []
        
        # Define step ordering priorities
        step_priorities = {
            "vehicle_operations": 1,
            "maintenance": 2,
            "reservations": 3,
            "parking": 4
        }
        
        # Sort templates by priority
        prioritized_templates = sorted(
            selected_templates,
            key=lambda ts: step_priorities.get(
                self.template_manager.get_template_metadata(ts.template_id).category, 999
            )
        )
        
        for i, template_score in enumerate(prioritized_templates):
            metadata = self.template_manager.get_template_metadata(template_score.template_id)
            if metadata:
                steps.append({
                    "step_number": i + 1,
                    "template_id": template_score.template_id,
                    "category": metadata.category,
                    "operation": metadata.name,
                    "dependencies": metadata.dependencies,
                    "confidence": template_score.confidence,
                    "required_entities": metadata.required_entities,
                    "api_endpoint": metadata.api_endpoint,
                    "http_method": metadata.http_method
                })
        
        return steps
    
    def select_template_by_name(
        self,
        template_name: str,
        category: Optional[str] = None,
        version: Optional[str] = None
    ) -> Optional[str]:
        """Select template by name, category, and version.
        
        Args:
            template_name: Template name
            category: Optional category filter
            version: Optional specific version
            
        Returns:
            Template ID or None if not found
        """
        matching_templates = self.template_manager.find_templates_by_name(template_name, category)
        
        if not matching_templates:
            return None
        
        if version:
            # Find specific version
            for template_id in matching_templates:
                metadata = self.template_manager.get_template_metadata(template_id)
                if metadata and metadata.version == version:
                    return template_id
            return None
        else:
            # Return latest version
            return matching_templates[0]  # Already sorted by version (latest first)
    
    def get_selection_explanation(self, selection_result: SelectionResult) -> Dict[str, Any]:
        """Get detailed explanation of selection process.
        
        Args:
            selection_result: Selection result to explain
            
        Returns:
            Detailed explanation
        """
        explanation = {
            "strategy_used": selection_result.selection_strategy_used.value,
            "selection_confidence": selection_result.selection_confidence,
            "total_candidates_evaluated": len(selection_result.selected_templates) + len(selection_result.fallback_templates),
            "templates_selected": len(selection_result.selected_templates),
            "processing_time": selection_result.processing_time,
            "selection_notes": selection_result.selection_notes,
            "template_details": []
        }
        
        # Add details for each selected template
        for i, template_score in enumerate(selection_result.selected_templates):
            metadata = self.template_manager.get_template_metadata(template_score.template_id)
            template_detail = {
                "rank": i + 1,
                "template_id": template_score.template_id,
                "template_name": metadata.name if metadata else "Unknown",
                "category": metadata.category if metadata else "Unknown",
                "total_score": template_score.total_score,
                "confidence": template_score.confidence,
                "criteria_scores": template_score.criteria_scores,
                "matching_entities": list(template_score.matching_entities),
                "missing_entities": list(template_score.missing_entities),
                "reasoning": template_score.reasoning,
                "warnings": template_score.warnings
            }
            explanation["template_details"].append(template_detail)
        
        # Add multi-step information if applicable
        if selection_result.multi_step_operations:
            explanation["multi_step_plan"] = {
                "steps_count": len(selection_result.multi_step_operations),
                "steps": selection_result.multi_step_operations
            }
        
        return explanation