"""JSON Generator for Fleet Templates

Populates JSON templates with extracted entities and formats data for API requests
with validation, data transformation, and fallback handling.
"""

import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ...core.logging_manager import LoggingManager
from ...intelligence.intent_classifier import ClassificationResult
from ...intelligence.entity_extractor import ExtractionResult, EntityType, ExtractedEntity
from .template_manager import TemplateManager, TemplateMetadata
from .template_selector import TemplateSelector, SelectionResult, TemplateScore


class ValueTransformType(Enum):
    """Types of value transformations."""
    NONE = "none"
    UPPERCASE = "uppercase"
    LOWERCASE = "lowercase"
    CAPITALIZE = "capitalize"
    FORMAT_DATE = "format_date"
    FORMAT_TIME = "format_time"
    FORMAT_PHONE = "format_phone"
    NORMALIZE_EMAIL = "normalize_email"
    GENERATE_UUID = "generate_uuid"
    CURRENT_TIMESTAMP = "current_timestamp"
    AUTO_INCREMENT = "auto_increment"


class DefaultValueStrategy(Enum):
    """Strategies for handling missing values."""
    NULL = "null"
    EMPTY_STRING = "empty_string"
    DEFAULT_FROM_TEMPLATE = "default_from_template"
    CALCULATED = "calculated"
    PROMPT_USER = "prompt_user"


@dataclass
class ValueMapping:
    """Mapping configuration for entity values."""
    entity_type: EntityType
    template_field: str
    transform: ValueTransformType = ValueTransformType.NONE
    default_strategy: DefaultValueStrategy = DefaultValueStrategy.DEFAULT_FROM_TEMPLATE
    default_value: Optional[Any] = None
    validation_pattern: Optional[str] = None
    required: bool = False


@dataclass
class GenerationResult:
    """Result of JSON generation process."""
    generated_json: Dict[str, Any] = field(default_factory=dict)
    template_id: str = ""
    populated_fields: Set[str] = field(default_factory=set)
    missing_fields: Set[str] = field(default_factory=set)
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    generation_confidence: float = 0.0
    processing_time: float = 0.0
    fallback_values_used: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationOptions:
    """Options for JSON generation."""
    strict_validation: bool = False
    allow_partial_generation: bool = True
    use_fallback_values: bool = True
    transform_values: bool = True
    include_metadata: bool = True
    generate_missing_ids: bool = True
    format_timestamps: bool = True
    preserve_template_structure: bool = True


class JSONGenerator:
    """JSON generator for populating templates with extracted entities."""
    
    def __init__(self, template_manager: TemplateManager):
        """Initialize JSON generator.
        
        Args:
            template_manager: Template manager instance
        """
        self.template_manager = template_manager
        self.logger = LoggingManager.get_logger(__name__)
        
        # Entity type to template field mappings
        self.entity_mappings = self._build_entity_mappings()
        
        # Value transformers
        self.transformers = self._build_value_transformers()
        
        # Auto-increment counters for generated IDs
        self._auto_counters = {}
        
        # Default generation options
        self.default_options = GenerationOptions()
        
    def _build_entity_mappings(self) -> Dict[EntityType, List[ValueMapping]]:
        """Build entity type to template field mappings.
        
        Returns:
            Dictionary mapping entity types to value mappings
        """
        return {
            EntityType.VEHICLE_ID: [
                ValueMapping(EntityType.VEHICLE_ID, "vehicle_id", required=True),
                ValueMapping(EntityType.VEHICLE_ID, "unit_id"),
                ValueMapping(EntityType.VEHICLE_ID, "asset_id")
            ],
            EntityType.VIN: [
                ValueMapping(EntityType.VIN, "vin", ValueTransformType.UPPERCASE),
                ValueMapping(EntityType.VIN, "vehicle_identification_number")
            ],
            EntityType.LICENSE_PLATE: [
                ValueMapping(EntityType.LICENSE_PLATE, "license_plate", ValueTransformType.UPPERCASE),
                ValueMapping(EntityType.LICENSE_PLATE, "plate_number"),
                ValueMapping(EntityType.LICENSE_PLATE, "registration")
            ],
            EntityType.PERSON_NAME: [
                ValueMapping(EntityType.PERSON_NAME, "user", required=True),
                ValueMapping(EntityType.PERSON_NAME, "user_id"),
                ValueMapping(EntityType.PERSON_NAME, "driver"),
                ValueMapping(EntityType.PERSON_NAME, "assigned_to"),
                ValueMapping(EntityType.PERSON_NAME, "requestor"),
                ValueMapping(EntityType.PERSON_NAME, "contact_person")
            ],
            EntityType.DATE: [
                ValueMapping(EntityType.DATE, "date", ValueTransformType.FORMAT_DATE, required=True),
                ValueMapping(EntityType.DATE, "start_date", ValueTransformType.FORMAT_DATE),
                ValueMapping(EntityType.DATE, "end_date", ValueTransformType.FORMAT_DATE),
                ValueMapping(EntityType.DATE, "scheduled_date", ValueTransformType.FORMAT_DATE),
                ValueMapping(EntityType.DATE, "requested_date", ValueTransformType.FORMAT_DATE)
            ],
            EntityType.TIME: [
                ValueMapping(EntityType.TIME, "time", ValueTransformType.FORMAT_TIME),
                ValueMapping(EntityType.TIME, "start_time", ValueTransformType.FORMAT_TIME),
                ValueMapping(EntityType.TIME, "end_time", ValueTransformType.FORMAT_TIME),
                ValueMapping(EntityType.TIME, "requested_time", ValueTransformType.FORMAT_TIME)
            ],
            EntityType.LOCATION: [
                ValueMapping(EntityType.LOCATION, "location", required=True),
                ValueMapping(EntityType.LOCATION, "address"),
                ValueMapping(EntityType.LOCATION, "site"),
                ValueMapping(EntityType.LOCATION, "destination"),
                ValueMapping(EntityType.LOCATION, "pickup_location"),
                ValueMapping(EntityType.LOCATION, "return_location")
            ],
            EntityType.BUILDING: [
                ValueMapping(EntityType.BUILDING, "building"),
                ValueMapping(EntityType.BUILDING, "building_name"),
                ValueMapping(EntityType.BUILDING, "facility")
            ],
            EntityType.PARKING_SPOT: [
                ValueMapping(EntityType.PARKING_SPOT, "parking_spot"),
                ValueMapping(EntityType.PARKING_SPOT, "spot_number"),
                ValueMapping(EntityType.PARKING_SPOT, "space"),
                ValueMapping(EntityType.PARKING_SPOT, "bay")
            ],
            EntityType.EMAIL: [
                ValueMapping(EntityType.EMAIL, "email", ValueTransformType.NORMALIZE_EMAIL),
                ValueMapping(EntityType.EMAIL, "contact_email"),
                ValueMapping(EntityType.EMAIL, "user_email")
            ],
            EntityType.PHONE: [
                ValueMapping(EntityType.PHONE, "phone", ValueTransformType.FORMAT_PHONE),
                ValueMapping(EntityType.PHONE, "contact_phone"),
                ValueMapping(EntityType.PHONE, "telephone")
            ],
            EntityType.DEPARTMENT: [
                ValueMapping(EntityType.DEPARTMENT, "department"),
                ValueMapping(EntityType.DEPARTMENT, "division"),
                ValueMapping(EntityType.DEPARTMENT, "unit")
            ],
            EntityType.ROLE: [
                ValueMapping(EntityType.ROLE, "role"),
                ValueMapping(EntityType.ROLE, "position"),
                ValueMapping(EntityType.ROLE, "title")
            ]
        }
    
    def _build_value_transformers(self) -> Dict[ValueTransformType, callable]:
        """Build value transformation functions.
        
        Returns:
            Dictionary mapping transform types to functions
        """
        return {
            ValueTransformType.NONE: lambda x: x,
            ValueTransformType.UPPERCASE: lambda x: str(x).upper(),
            ValueTransformType.LOWERCASE: lambda x: str(x).lower(),
            ValueTransformType.CAPITALIZE: lambda x: str(x).capitalize(),
            ValueTransformType.FORMAT_DATE: self._format_date,
            ValueTransformType.FORMAT_TIME: self._format_time,
            ValueTransformType.FORMAT_PHONE: self._format_phone,
            ValueTransformType.NORMALIZE_EMAIL: self._normalize_email,
            ValueTransformType.GENERATE_UUID: lambda x: str(uuid.uuid4()),
            ValueTransformType.CURRENT_TIMESTAMP: lambda x: datetime.now(timezone.utc).isoformat(),
            ValueTransformType.AUTO_INCREMENT: self._auto_increment
        }
    
    def generate_json(
        self,
        selection_result: SelectionResult,
        intent_result: ClassificationResult,
        entity_result: ExtractionResult,
        options: Optional[GenerationOptions] = None
    ) -> List[GenerationResult]:
        """Generate JSON from selected templates and extracted entities.
        
        Args:
            selection_result: Template selection result
            intent_result: Intent classification result
            entity_result: Entity extraction result
            options: Generation options
            
        Returns:
            List of generation results for each selected template
        """
        if not options:
            options = self.default_options
        
        start_time = datetime.now()
        results = []
        
        self.logger.debug(f"Generating JSON for {len(selection_result.selected_templates)} templates")
        
        for template_score in selection_result.selected_templates:
            result = self._generate_single_json(
                template_score, intent_result, entity_result, options
            )
            results.append(result)
        
        # Calculate total processing time
        total_time = (datetime.now() - start_time).total_seconds()
        
        self.logger.info(
            f"JSON generation complete: {len(results)} templates processed in {total_time:.3f}s"
        )
        
        return results
    
    def _generate_single_json(
        self,
        template_score: TemplateScore,
        intent_result: ClassificationResult,
        entity_result: ExtractionResult,
        options: GenerationOptions
    ) -> GenerationResult:
        """Generate JSON for a single template.
        
        Args:
            template_score: Template score with template ID
            intent_result: Intent classification result
            entity_result: Entity extraction result
            options: Generation options
            
        Returns:
            Generation result
        """
        start_time = datetime.now()
        
        # Get template data
        template_data = self.template_manager.get_template(template_score.template_id)
        template_metadata = self.template_manager.get_template_metadata(template_score.template_id)
        
        if not template_data or not template_metadata:
            return GenerationResult(
                template_id=template_score.template_id,
                validation_errors=["Template not found"],
                processing_time=(datetime.now() - start_time).total_seconds()
            )
        
        # Initialize result
        result = GenerationResult(template_id=template_score.template_id)
        
        # Get template content
        template_content = template_data['content']
        validation_rules = template_data.get('validation_rules', {})
        
        try:
            # Create entity lookup
            entity_lookup = self._create_entity_lookup(entity_result)
            
            # Process template content
            result.generated_json = self._process_template_content(
                template_content, entity_lookup, template_metadata, options, result
            )
            
            # Validate result if strict validation enabled
            if options.strict_validation:
                self._validate_generated_json(
                    result.generated_json, validation_rules, template_metadata, result
                )
            
            # Calculate generation confidence
            result.generation_confidence = self._calculate_generation_confidence(
                result, template_metadata, entity_result
            )
            
            self.logger.debug(
                f"Generated JSON for {template_score.template_id}: "
                f"{len(result.populated_fields)} populated, "
                f"{len(result.missing_fields)} missing, "
                f"confidence: {result.generation_confidence:.2f}"
            )
            
        except Exception as e:
            self.logger.error(f"Error generating JSON for {template_score.template_id}: {e}")
            result.validation_errors.append(f"Generation failed: {str(e)}")
        
        # Calculate processing time
        result.processing_time = (datetime.now() - start_time).total_seconds()
        
        return result
    
    def _create_entity_lookup(self, entity_result: ExtractionResult) -> Dict[str, List[ExtractedEntity]]:
        """Create entity lookup dictionary by type and field names.
        
        Args:
            entity_result: Entity extraction result
            
        Returns:
            Dictionary mapping field names to entity lists
        """
        entity_lookup = {}
        
        # Group entities by type
        entities_by_type = {}
        for entity in entity_result.entities:
            if entity.entity_type not in entities_by_type:
                entities_by_type[entity.entity_type] = []
            entities_by_type[entity.entity_type].append(entity)
        
        # Create lookup by field names
        for entity_type, entities in entities_by_type.items():
            if entity_type in self.entity_mappings:
                for mapping in self.entity_mappings[entity_type]:
                    field_name = mapping.template_field
                    if field_name not in entity_lookup:
                        entity_lookup[field_name] = []
                    entity_lookup[field_name].extend(entities)
        
        return entity_lookup
    
    def _process_template_content(
        self,
        content: Any,
        entity_lookup: Dict[str, List[ExtractedEntity]],
        metadata: TemplateMetadata,
        options: GenerationOptions,
        result: GenerationResult
    ) -> Any:
        """Process template content recursively.
        
        Args:
            content: Template content (dict, list, or primitive)
            entity_lookup: Entity lookup dictionary
            metadata: Template metadata
            options: Generation options
            result: Result object to update
            
        Returns:
            Processed content
        """
        if isinstance(content, dict):
            processed = {}
            for key, value in content.items():
                processed[key] = self._process_template_content(
                    value, entity_lookup, metadata, options, result
                )
            return processed
        
        elif isinstance(content, list):
            return [
                self._process_template_content(item, entity_lookup, metadata, options, result)
                for item in content
            ]
        
        elif isinstance(content, str):
            return self._process_template_string(
                content, entity_lookup, metadata, options, result
            )
        
        else:
            return content
    
    def _process_template_string(
        self,
        template_string: str,
        entity_lookup: Dict[str, List[ExtractedEntity]],
        metadata: TemplateMetadata,
        options: GenerationOptions,
        result: GenerationResult
    ) -> str:
        """Process template string with variable substitution.
        
        Args:
            template_string: Template string with variables
            entity_lookup: Entity lookup dictionary
            metadata: Template metadata
            options: Generation options
            result: Result object to update
            
        Returns:
            Processed string with variables replaced
        """
        # Pattern to match template variables: {variable_name|default_value}
        pattern = r'\{([^}]+)\}'
        
        def replace_variable(match):
            variable_spec = match.group(1)
            
            # Parse variable name and default value
            if '|' in variable_spec:
                var_name, default_value = variable_spec.split('|', 1)
            else:
                var_name = variable_spec
                default_value = None
            
            var_name = var_name.strip()
            
            # Try to get value from entities
            value = self._get_entity_value(var_name, entity_lookup, result)
            
            if value is not None:
                # Transform value if needed
                transformed_value = self._transform_value(var_name, value, options)
                result.populated_fields.add(var_name)
                return str(transformed_value)
            
            # Handle missing value
            return self._handle_missing_value(
                var_name, default_value, metadata, options, result
            )
        
        return re.sub(pattern, replace_variable, template_string)
    
    def _get_entity_value(
        self,
        field_name: str,
        entity_lookup: Dict[str, List[ExtractedEntity]],
        result: GenerationResult
    ) -> Optional[str]:
        """Get entity value for a field name.
        
        Args:
            field_name: Template field name
            entity_lookup: Entity lookup dictionary
            result: Result object to update
            
        Returns:
            Entity value or None if not found
        """
        # Direct field name match
        if field_name in entity_lookup and entity_lookup[field_name]:
            # Take the highest confidence entity
            best_entity = max(entity_lookup[field_name], key=lambda e: e.confidence)
            return best_entity.value
        
        # Check for partial field name matches
        for lookup_field, entities in entity_lookup.items():
            if lookup_field in field_name or field_name in lookup_field:
                if entities:
                    best_entity = max(entities, key=lambda e: e.confidence)
                    return best_entity.value
        
        return None
    
    def _handle_missing_value(
        self,
        field_name: str,
        default_value: Optional[str],
        metadata: TemplateMetadata,
        options: GenerationOptions,
        result: GenerationResult
    ) -> str:
        """Handle missing value with fallback strategies.
        
        Args:
            field_name: Template field name
            default_value: Default value from template
            metadata: Template metadata
            options: Generation options
            result: Result object to update
            
        Returns:
            Fallback value
        """
        result.missing_fields.add(field_name)
        
        if not options.use_fallback_values:
            if field_name in metadata.required_entities:
                result.validation_errors.append(f"Required field '{field_name}' is missing")
            return f"{{{field_name}}}"  # Return original placeholder
        
        # Use template default value
        if default_value is not None:
            fallback_value = self._process_default_value(default_value, field_name, options)
            result.fallback_values_used[field_name] = fallback_value
            return str(fallback_value)
        
        # Generate fallback based on field name
        fallback_value = self._generate_fallback_value(field_name, metadata, options)
        if fallback_value is not None:
            result.fallback_values_used[field_name] = fallback_value
            return str(fallback_value)
        
        # Last resort - return null or empty based on field requirements
        if field_name in metadata.required_entities:
            result.validation_errors.append(f"Required field '{field_name}' has no fallback value")
            return "null"
        
        return "null"
    
    def _process_default_value(
        self,
        default_value: str,
        field_name: str,
        options: GenerationOptions
    ) -> Any:
        """Process default value from template.
        
        Args:
            default_value: Default value string
            field_name: Field name for context
            options: Generation options
            
        Returns:
            Processed default value
        """
        # Handle special default values
        if default_value == "null":
            return None
        elif default_value == "current_timestamp":
            return datetime.now(timezone.utc).isoformat()
        elif default_value == "auto_generate":
            return self._auto_increment(field_name)
        elif default_value.startswith("[]"):
            return []
        elif default_value.startswith("{}"):
            return {}
        else:
            return default_value
    
    def _generate_fallback_value(
        self,
        field_name: str,
        metadata: TemplateMetadata,
        options: GenerationOptions
    ) -> Optional[Any]:
        """Generate fallback value based on field name patterns.
        
        Args:
            field_name: Template field name
            metadata: Template metadata
            options: Generation options
            
        Returns:
            Generated fallback value or None
        """
        field_lower = field_name.lower()
        
        # ID fields
        if any(suffix in field_lower for suffix in ['_id', 'id']):
            if options.generate_missing_ids:
                return self._auto_increment(field_name)
        
        # Timestamp fields
        if any(keyword in field_lower for keyword in ['timestamp', 'created_at', 'updated_at']):
            if options.format_timestamps:
                return datetime.now(timezone.utc).isoformat()
        
        # Status fields
        if 'status' in field_lower:
            return "pending"
        
        # Boolean fields
        if any(keyword in field_lower for keyword in ['required', 'enabled', 'verified', 'approved']):
            return False
        
        # Numeric fields
        if any(keyword in field_lower for keyword in ['count', 'number', 'amount', 'quantity']):
            return 0
        
        return None
    
    def _transform_value(
        self,
        field_name: str,
        value: str,
        options: GenerationOptions
    ) -> Any:
        """Transform value based on field name and options.
        
        Args:
            field_name: Template field name
            value: Original value
            options: Generation options
            
        Returns:
            Transformed value
        """
        if not options.transform_values:
            return value
        
        field_lower = field_name.lower()
        
        # Determine transformation type
        transform_type = ValueTransformType.NONE
        
        if any(keyword in field_lower for keyword in ['email']):
            transform_type = ValueTransformType.NORMALIZE_EMAIL
        elif any(keyword in field_lower for keyword in ['phone', 'telephone']):
            transform_type = ValueTransformType.FORMAT_PHONE
        elif any(keyword in field_lower for keyword in ['date']):
            transform_type = ValueTransformType.FORMAT_DATE
        elif any(keyword in field_lower for keyword in ['time']) and 'timestamp' not in field_lower:
            transform_type = ValueTransformType.FORMAT_TIME
        elif any(keyword in field_lower for keyword in ['vin', 'license', 'plate']):
            transform_type = ValueTransformType.UPPERCASE
        
        # Apply transformation
        if transform_type in self.transformers:
            try:
                return self.transformers[transform_type](value)
            except Exception as e:
                self.logger.warning(f"Failed to transform value '{value}' for field '{field_name}': {e}")
                return value
        
        return value
    
    def _format_date(self, value: str) -> str:
        """Format date value to ISO format."""
        try:
            # Try parsing common date formats
            date_formats = [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%Y/%m/%d",
                "%m-%d-%Y",
                "%d-%m-%Y",
                "%B %d, %Y",
                "%d %B %Y"
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(value, fmt)
                    return parsed_date.date().isoformat()
                except ValueError:
                    continue
            
            # If no format matches, return original
            return value
            
        except Exception:
            return value
    
    def _format_time(self, value: str) -> str:
        """Format time value to HH:MM format."""
        try:
            # Clean up time string
            time_str = re.sub(r'[^\d:]', '', value)
            
            # Handle various time formats
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) >= 2:
                    hour = int(parts[0]) % 24
                    minute = int(parts[1]) % 60
                    return f"{hour:02d}:{minute:02d}"
            
            # Single number (assume hours)
            elif time_str.isdigit():
                hour = int(time_str) % 24
                return f"{hour:02d}:00"
            
            return value
            
        except Exception:
            return value
    
    def _format_phone(self, value: str) -> str:
        """Format phone number."""
        try:
            # Extract digits only
            digits = re.sub(r'\D', '', value)
            
            if len(digits) == 10:
                return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            elif len(digits) == 11 and digits[0] == '1':
                return f"1-({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
            else:
                return value
                
        except Exception:
            return value
    
    def _normalize_email(self, value: str) -> str:
        """Normalize email address."""
        try:
            return value.lower().strip()
        except Exception:
            return value
    
    def _auto_increment(self, field_name: str) -> str:
        """Generate auto-incrementing value."""
        if field_name not in self._auto_counters:
            self._auto_counters[field_name] = 1
        else:
            self._auto_counters[field_name] += 1
        
        prefix = field_name.upper().replace('_', '')[:3]
        return f"{prefix}{self._auto_counters[field_name]:04d}"
    
    def _validate_generated_json(
        self,
        generated_json: Dict[str, Any],
        validation_rules: Dict[str, Any],
        metadata: TemplateMetadata,
        result: GenerationResult
    ):
        """Validate generated JSON against rules.
        
        Args:
            generated_json: Generated JSON data
            validation_rules: Validation rules from template
            metadata: Template metadata
            result: Result object to update
        """
        json_str = json.dumps(generated_json)
        
        # Check required entities
        for required_entity in metadata.required_entities:
            if f'"{required_entity}"' not in json_str or f'null' in str(generated_json.get(required_entity, 'null')):
                result.validation_errors.append(f"Required entity '{required_entity}' is missing or null")
        
        # Apply validation rules
        for field, rules in validation_rules.items():
            if self._is_field_in_json(field, generated_json):
                field_value = self._extract_field_value(field, generated_json)
                self._validate_field_value(field, field_value, rules, result)
    
    def _is_field_in_json(self, field_name: str, json_data: Dict[str, Any]) -> bool:
        """Check if field exists in JSON data."""
        return field_name in json.dumps(json_data)
    
    def _extract_field_value(self, field_name: str, json_data: Dict[str, Any]) -> Optional[Any]:
        """Extract field value from JSON data."""
        # Simple implementation - could be enhanced for nested field access
        json_str = json.dumps(json_data)
        if f'"{field_name}":' in json_str:
            # Find the value (this is simplified - real implementation would parse properly)
            start = json_str.find(f'"{field_name}":') + len(f'"{field_name}":')
            # This is a simplified extraction
            return "extracted_value"  # Placeholder
        return None
    
    def _validate_field_value(
        self,
        field_name: str,
        value: Any,
        rules: Dict[str, Any],
        result: GenerationResult
    ):
        """Validate field value against rules.
        
        Args:
            field_name: Field name
            value: Field value
            rules: Validation rules for field
            result: Result object to update
        """
        if value is None:
            if rules.get('required', False):
                result.validation_errors.append(f"Required field '{field_name}' is null")
            return
        
        # Type validation
        expected_type = rules.get('type')
        if expected_type and not self._check_type(value, expected_type):
            result.validation_errors.append(
                f"Field '{field_name}' has incorrect type. Expected {expected_type}, got {type(value).__name__}"
            )
        
        # Pattern validation
        pattern = rules.get('pattern')
        if pattern and isinstance(value, str):
            if not re.match(pattern, value):
                result.validation_errors.append(f"Field '{field_name}' does not match pattern {pattern}")
        
        # Range validation
        if isinstance(value, (int, float)):
            if 'min' in rules and value < rules['min']:
                result.validation_errors.append(f"Field '{field_name}' below minimum value {rules['min']}")
            if 'max' in rules and value > rules['max']:
                result.validation_errors.append(f"Field '{field_name}' above maximum value {rules['max']}")
        
        # Allowed values validation
        allowed_values = rules.get('allowed_values')
        if allowed_values and value not in allowed_values:
            result.validation_errors.append(
                f"Field '{field_name}' has invalid value. Must be one of: {', '.join(map(str, allowed_values))}"
            )
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        if expected_type == 'string':
            return isinstance(value, str)
        elif expected_type == 'number':
            return isinstance(value, (int, float))
        elif expected_type == 'integer':
            return isinstance(value, int)
        elif expected_type == 'boolean':
            return isinstance(value, bool)
        elif expected_type == 'array':
            return isinstance(value, list)
        elif expected_type == 'object':
            return isinstance(value, dict)
        return True
    
    def _calculate_generation_confidence(
        self,
        result: GenerationResult,
        metadata: TemplateMetadata,
        entity_result: ExtractionResult
    ) -> float:
        """Calculate generation confidence score.
        
        Args:
            result: Generation result
            metadata: Template metadata
            entity_result: Entity extraction result
            
        Returns:
            Confidence score (0-1)
        """
        total_fields = len(result.populated_fields) + len(result.missing_fields)
        if total_fields == 0:
            return 0.0
        
        # Base score from field coverage
        field_coverage = len(result.populated_fields) / total_fields
        
        # Penalty for validation errors
        error_penalty = min(0.5, len(result.validation_errors) * 0.1)
        
        # Penalty for missing required fields
        required_fields = set(metadata.required_entities)
        missing_required = required_fields.intersection(result.missing_fields)
        required_penalty = len(missing_required) * 0.2
        
        # Bonus for high entity extraction confidence
        avg_entity_confidence = (
            sum(entity.confidence for entity in entity_result.entities) / 
            len(entity_result.entities) if entity_result.entities else 0
        )
        confidence_bonus = (avg_entity_confidence - 0.5) * 0.2
        
        # Calculate final confidence
        confidence = field_coverage - error_penalty - required_penalty + confidence_bonus
        
        return max(0.0, min(1.0, confidence))
    
    def generate_json_from_template_id(
        self,
        template_id: str,
        intent_result: ClassificationResult,
        entity_result: ExtractionResult,
        options: Optional[GenerationOptions] = None
    ) -> GenerationResult:
        """Generate JSON from specific template ID.
        
        Args:
            template_id: Template identifier
            intent_result: Intent classification result
            entity_result: Entity extraction result
            options: Generation options
            
        Returns:
            Generation result
        """
        from .template_selector import TemplateScore
        
        # Create template score for single template
        template_score = TemplateScore(template_id=template_id, total_score=1.0, confidence=1.0)
        
        return self._generate_single_json(template_score, intent_result, entity_result, options or self.default_options)
    
    def get_generation_summary(self, results: List[GenerationResult]) -> Dict[str, Any]:
        """Get summary of generation results.
        
        Args:
            results: List of generation results
            
        Returns:
            Summary information
        """
        if not results:
            return {"total_templates": 0, "successful_generations": 0}
        
        successful = [r for r in results if not r.validation_errors]
        total_time = sum(r.processing_time for r in results)
        avg_confidence = sum(r.generation_confidence for r in results) / len(results)
        
        return {
            "total_templates": len(results),
            "successful_generations": len(successful),
            "success_rate": len(successful) / len(results),
            "total_processing_time": total_time,
            "average_confidence": avg_confidence,
            "total_populated_fields": sum(len(r.populated_fields) for r in results),
            "total_missing_fields": sum(len(r.missing_fields) for r in results),
            "total_validation_errors": sum(len(r.validation_errors) for r in results),
            "templates_processed": [r.template_id for r in results]
        }