"""Request Validators for Fleet Templates

Comprehensive validation system for generated API requests with schema validation,
business rule checks, and data consistency verification.
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ...core.logging_manager import LoggingManager
from .template_manager import TemplateManager, TemplateMetadata
from .json_generator import GenerationResult


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationType(Enum):
    """Types of validation checks."""
    SCHEMA = "schema"
    BUSINESS_RULE = "business_rule"
    DATA_CONSISTENCY = "data_consistency"
    FORMAT = "format"
    CONSTRAINT = "constraint"
    SECURITY = "security"


@dataclass
class ValidationIssue:
    """Individual validation issue."""
    field_path: str
    issue_type: ValidationType
    severity: ValidationSeverity
    message: str
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    suggestion: Optional[str] = None
    rule_name: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation process."""
    is_valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    template_id: str = ""
    validation_timestamp: Optional[datetime] = None
    processing_time: float = 0.0
    warnings_count: int = 0
    errors_count: int = 0
    critical_count: int = 0
    validated_fields: Set[str] = field(default_factory=set)
    business_rules_applied: List[str] = field(default_factory=list)


@dataclass
class ValidationOptions:
    """Options for validation process."""
    strict_mode: bool = False
    validate_business_rules: bool = True
    validate_data_consistency: bool = True
    validate_format: bool = True
    validate_constraints: bool = True
    validate_security: bool = True
    allow_partial_validation: bool = True
    max_issues_per_field: int = 5
    fail_on_warnings: bool = False
    custom_rules: Dict[str, Any] = field(default_factory=dict)


class BusinessRule:
    """Base class for business validation rules."""
    
    def __init__(self, name: str, description: str, severity: ValidationSeverity = ValidationSeverity.ERROR):
        self.name = name
        self.description = description
        self.severity = severity
    
    def validate(self, data: Dict[str, Any], context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate data against this business rule.
        
        Args:
            data: Data to validate
            context: Validation context
            
        Returns:
            List of validation issues
        """
        raise NotImplementedError("Subclasses must implement validate method")


class TemplateValidator:
    """Comprehensive validator for template-generated API requests."""
    
    def __init__(self, template_manager: TemplateManager):
        """Initialize template validator.
        
        Args:
            template_manager: Template manager instance
        """
        self.template_manager = template_manager
        self.logger = LoggingManager.get_logger(__name__)
        
        # Initialize business rules
        self.business_rules = self._initialize_business_rules()
        
        # Default validation options
        self.default_options = ValidationOptions()
        
        # Schema validators for different data types
        self.type_validators = self._build_type_validators()
        
        # Format validators
        self.format_validators = self._build_format_validators()
        
        # Constraint validators
        self.constraint_validators = self._build_constraint_validators()
    
    def _initialize_business_rules(self) -> List[BusinessRule]:
        """Initialize business validation rules.
        
        Returns:
            List of business rules
        """
        return [
            VehicleIDValidationRule(),
            DateTimeConsistencyRule(),
            MaintenanceSchedulingRule(),
            ReservationConflictRule(),
            ParkingAvailabilityRule(),
            UserAuthorizationRule(),
            ResourceConstraintRule(),
            LocationValidationRule()
        ]
    
    def _build_type_validators(self) -> Dict[str, callable]:
        """Build type validation functions.
        
        Returns:
            Dictionary mapping types to validator functions
        """
        return {
            'string': self._validate_string,
            'number': self._validate_number,
            'integer': self._validate_integer,
            'boolean': self._validate_boolean,
            'array': self._validate_array,
            'object': self._validate_object,
            'null': self._validate_null
        }
    
    def _build_format_validators(self) -> Dict[str, callable]:
        """Build format validation functions.
        
        Returns:
            Dictionary mapping formats to validator functions
        """
        return {
            'date': self._validate_date_format,
            'datetime': self._validate_datetime_format,
            'time': self._validate_time_format,
            'email': self._validate_email_format,
            'phone': self._validate_phone_format,
            'uuid': self._validate_uuid_format,
            'url': self._validate_url_format,
            'vin': self._validate_vin_format
        }
    
    def _build_constraint_validators(self) -> Dict[str, callable]:
        """Build constraint validation functions.
        
        Returns:
            Dictionary mapping constraints to validator functions
        """
        return {
            'min_length': self._validate_min_length,
            'max_length': self._validate_max_length,
            'min': self._validate_minimum,
            'max': self._validate_maximum,
            'pattern': self._validate_pattern,
            'allowed_values': self._validate_allowed_values,
            'unique': self._validate_uniqueness
        }
    
    def validate_generation_result(
        self,
        generation_result: GenerationResult,
        options: Optional[ValidationOptions] = None
    ) -> ValidationResult:
        """Validate a generation result.
        
        Args:
            generation_result: Generation result to validate
            options: Validation options
            
        Returns:
            Validation result
        """
        if not options:
            options = self.default_options
        
        start_time = datetime.now()
        
        validation_result = ValidationResult(
            template_id=generation_result.template_id,
            validation_timestamp=start_time
        )
        
        try:
            # Get template metadata and validation rules
            metadata = self.template_manager.get_template_metadata(generation_result.template_id)
            template_data = self.template_manager.get_template(generation_result.template_id)
            
            if not metadata or not template_data:
                validation_result.issues.append(ValidationIssue(
                    field_path="template",
                    issue_type=ValidationType.SCHEMA,
                    severity=ValidationSeverity.CRITICAL,
                    message="Template metadata or data not found"
                ))
                validation_result.is_valid = False
                return validation_result
            
            validation_rules = template_data.get('validation_rules', {})
            
            # Perform different types of validation
            if options.validate_format:
                self._validate_schema(
                    generation_result.generated_json, 
                    validation_rules, 
                    metadata, 
                    validation_result, 
                    options
                )
            
            if options.validate_business_rules:
                self._validate_business_rules(
                    generation_result.generated_json, 
                    metadata, 
                    validation_result, 
                    options
                )
            
            if options.validate_data_consistency:
                self._validate_data_consistency(
                    generation_result.generated_json, 
                    metadata, 
                    validation_result, 
                    options
                )
            
            if options.validate_constraints:
                self._validate_constraints(
                    generation_result.generated_json, 
                    validation_rules, 
                    validation_result, 
                    options
                )
            
            if options.validate_security:
                self._validate_security(
                    generation_result.generated_json, 
                    metadata, 
                    validation_result, 
                    options
                )
            
            # Count issues by severity
            self._count_issues_by_severity(validation_result)
            
            # Determine overall validity
            validation_result.is_valid = self._determine_validity(validation_result, options)
            
            self.logger.debug(
                f"Validation complete for {generation_result.template_id}: "
                f"{'valid' if validation_result.is_valid else 'invalid'}, "
                f"{len(validation_result.issues)} issues found"
            )
            
        except Exception as e:
            self.logger.error(f"Validation failed for {generation_result.template_id}: {e}")
            validation_result.issues.append(ValidationIssue(
                field_path="validation",
                issue_type=ValidationType.SCHEMA,
                severity=ValidationSeverity.CRITICAL,
                message=f"Validation process failed: {str(e)}"
            ))
            validation_result.is_valid = False
        
        # Calculate processing time
        validation_result.processing_time = (datetime.now() - start_time).total_seconds()
        
        return validation_result
    
    def _validate_schema(
        self,
        data: Dict[str, Any],
        validation_rules: Dict[str, Any],
        metadata: TemplateMetadata,
        result: ValidationResult,
        options: ValidationOptions
    ):
        """Validate data against schema rules.
        
        Args:
            data: Data to validate
            validation_rules: Schema validation rules
            metadata: Template metadata
            result: Validation result to update
            options: Validation options
        """
        self._validate_data_recursive(data, validation_rules, "", result, options)
    
    def _validate_data_recursive(
        self,
        data: Any,
        validation_rules: Dict[str, Any],
        path_prefix: str,
        result: ValidationResult,
        options: ValidationOptions
    ):
        """Recursively validate data structure.
        
        Args:
            data: Data to validate
            validation_rules: Validation rules
            path_prefix: Current path prefix
            result: Validation result to update
            options: Validation options
        """
        if isinstance(data, dict):
            for key, value in data.items():
                field_path = f"{path_prefix}.{key}" if path_prefix else key
                result.validated_fields.add(field_path)
                
                # Check if validation rule exists for this field
                if key in validation_rules:
                    rule = validation_rules[key]
                    self._validate_field(field_path, value, rule, result, options)
                
                # Recursively validate nested structures
                if isinstance(value, (dict, list)):
                    self._validate_data_recursive(value, validation_rules, field_path, result, options)
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                field_path = f"{path_prefix}[{i}]"
                self._validate_data_recursive(item, validation_rules, field_path, result, options)
    
    def _validate_field(
        self,
        field_path: str,
        value: Any,
        rule: Dict[str, Any],
        result: ValidationResult,
        options: ValidationOptions
    ):
        """Validate individual field against its rule.
        
        Args:
            field_path: Path to the field
            value: Field value
            rule: Validation rule
            result: Validation result to update
            options: Validation options
        """
        issues_for_field = []
        
        # Required field validation
        if rule.get('required', False) and (value is None or value == ''):
            issues_for_field.append(ValidationIssue(
                field_path=field_path,
                issue_type=ValidationType.SCHEMA,
                severity=ValidationSeverity.ERROR,
                message=f"Required field '{field_path}' is missing or empty",
                actual_value=value
            ))
        
        # Skip further validation if field is null and not required
        if value is None and not rule.get('required', False):
            return
        
        # Type validation
        expected_type = rule.get('type')
        if expected_type and expected_type in self.type_validators:
            type_issues = self.type_validators[expected_type](field_path, value, rule)
            issues_for_field.extend(type_issues)
        
        # Format validation
        format_name = rule.get('format')
        if format_name and format_name in self.format_validators:
            format_issues = self.format_validators[format_name](field_path, value, rule)
            issues_for_field.extend(format_issues)
        
        # Constraint validation
        for constraint_name, constraint_validator in self.constraint_validators.items():
            if constraint_name in rule:
                constraint_issues = constraint_validator(field_path, value, rule[constraint_name], rule)
                issues_for_field.extend(constraint_issues)
        
        # Limit issues per field if specified
        if options.max_issues_per_field > 0:
            issues_for_field = issues_for_field[:options.max_issues_per_field]
        
        result.issues.extend(issues_for_field)
    
    def _validate_business_rules(
        self,
        data: Dict[str, Any],
        metadata: TemplateMetadata,
        result: ValidationResult,
        options: ValidationOptions
    ):
        """Validate data against business rules.
        
        Args:
            data: Data to validate
            metadata: Template metadata
            result: Validation result to update
            options: Validation options
        """
        context = {
            'template_id': metadata.name,
            'category': metadata.category,
            'api_endpoint': metadata.api_endpoint,
            'http_method': metadata.http_method
        }
        
        for rule in self.business_rules:
            try:
                rule_issues = rule.validate(data, context)
                result.issues.extend(rule_issues)
                result.business_rules_applied.append(rule.name)
            except Exception as e:
                self.logger.warning(f"Business rule '{rule.name}' validation failed: {e}")
                result.issues.append(ValidationIssue(
                    field_path="business_rule",
                    issue_type=ValidationType.BUSINESS_RULE,
                    severity=ValidationSeverity.WARNING,
                    message=f"Business rule '{rule.name}' validation failed: {str(e)}",
                    rule_name=rule.name
                ))
    
    def _validate_data_consistency(
        self,
        data: Dict[str, Any],
        metadata: TemplateMetadata,
        result: ValidationResult,
        options: ValidationOptions
    ):
        """Validate data consistency across fields.
        
        Args:
            data: Data to validate
            metadata: Template metadata
            result: Validation result to update
            options: Validation options
        """
        # Date/time consistency checks
        self._check_datetime_consistency(data, result)
        
        # ID field consistency
        self._check_id_consistency(data, result)
        
        # Cross-field validation
        self._check_cross_field_consistency(data, metadata, result)
    
    def _validate_constraints(
        self,
        data: Dict[str, Any],
        validation_rules: Dict[str, Any],
        result: ValidationResult,
        options: ValidationOptions
    ):
        """Validate additional constraints.
        
        Args:
            data: Data to validate
            validation_rules: Validation rules
            result: Validation result to update
            options: Validation options
        """
        # This is handled in _validate_field method
        pass
    
    def _validate_security(
        self,
        data: Dict[str, Any],
        metadata: TemplateMetadata,
        result: ValidationResult,
        options: ValidationOptions
    ):
        """Validate security aspects of the data.
        
        Args:
            data: Data to validate
            metadata: Template metadata
            result: Validation result to update
            options: Validation options
        """
        data_str = json.dumps(data, default=str).lower()
        
        # Check for potential sensitive information
        sensitive_patterns = [
            (r'password', "Potential password field detected"),
            (r'secret', "Potential secret field detected"),
            (r'token', "Potential token field detected"),
            (r'key.*\s*:\s*["\'][^"\']{20,}["\']', "Potential API key detected"),
            (r'ssn|social.*security', "Potential SSN detected"),
            (r'credit.*card|cc.*number', "Potential credit card information detected")
        ]
        
        for pattern, message in sensitive_patterns:
            if re.search(pattern, data_str):
                result.issues.append(ValidationIssue(
                    field_path="security",
                    issue_type=ValidationType.SECURITY,
                    severity=ValidationSeverity.WARNING,
                    message=message,
                    suggestion="Review for sensitive information exposure"
                ))
        
        # Check for injection patterns
        injection_patterns = [
            (r'<script', "Potential script injection"),
            (r'javascript:', "Potential JavaScript injection"),
            (r'on\w+\s*=', "Potential event handler injection"),
            (r'union.*select', "Potential SQL injection"),
            (r'drop.*table', "Potential SQL injection")
        ]
        
        for pattern, message in injection_patterns:
            if re.search(pattern, data_str, re.IGNORECASE):
                result.issues.append(ValidationIssue(
                    field_path="security",
                    issue_type=ValidationType.SECURITY,
                    severity=ValidationSeverity.ERROR,
                    message=message,
                    suggestion="Sanitize input data"
                ))
    
    # Type validators
    def _validate_string(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate string type."""
        issues = []
        if not isinstance(value, str):
            issues.append(ValidationIssue(
                field_path=field_path,
                issue_type=ValidationType.FORMAT,
                severity=ValidationSeverity.ERROR,
                message=f"Expected string, got {type(value).__name__}",
                expected_value="string",
                actual_value=type(value).__name__
            ))
        return issues
    
    def _validate_number(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate number type."""
        issues = []
        if not isinstance(value, (int, float)):
            issues.append(ValidationIssue(
                field_path=field_path,
                issue_type=ValidationType.FORMAT,
                severity=ValidationSeverity.ERROR,
                message=f"Expected number, got {type(value).__name__}",
                expected_value="number",
                actual_value=type(value).__name__
            ))
        return issues
    
    def _validate_integer(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate integer type."""
        issues = []
        if not isinstance(value, int):
            issues.append(ValidationIssue(
                field_path=field_path,
                issue_type=ValidationType.FORMAT,
                severity=ValidationSeverity.ERROR,
                message=f"Expected integer, got {type(value).__name__}",
                expected_value="integer",
                actual_value=type(value).__name__
            ))
        return issues
    
    def _validate_boolean(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate boolean type."""
        issues = []
        if not isinstance(value, bool):
            issues.append(ValidationIssue(
                field_path=field_path,
                issue_type=ValidationType.FORMAT,
                severity=ValidationSeverity.ERROR,
                message=f"Expected boolean, got {type(value).__name__}",
                expected_value="boolean",
                actual_value=type(value).__name__
            ))
        return issues
    
    def _validate_array(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate array type."""
        issues = []
        if not isinstance(value, list):
            issues.append(ValidationIssue(
                field_path=field_path,
                issue_type=ValidationType.FORMAT,
                severity=ValidationSeverity.ERROR,
                message=f"Expected array, got {type(value).__name__}",
                expected_value="array",
                actual_value=type(value).__name__
            ))
        return issues
    
    def _validate_object(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate object type."""
        issues = []
        if not isinstance(value, dict):
            issues.append(ValidationIssue(
                field_path=field_path,
                issue_type=ValidationType.FORMAT,
                severity=ValidationSeverity.ERROR,
                message=f"Expected object, got {type(value).__name__}",
                expected_value="object",
                actual_value=type(value).__name__
            ))
        return issues
    
    def _validate_null(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate null type."""
        issues = []
        if value is not None:
            issues.append(ValidationIssue(
                field_path=field_path,
                issue_type=ValidationType.FORMAT,
                severity=ValidationSeverity.ERROR,
                message=f"Expected null, got {type(value).__name__}",
                expected_value="null",
                actual_value=type(value).__name__
            ))
        return issues
    
    # Format validators
    def _validate_date_format(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate date format."""
        issues = []
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                issues.append(ValidationIssue(
                    field_path=field_path,
                    issue_type=ValidationType.FORMAT,
                    severity=ValidationSeverity.ERROR,
                    message="Invalid date format",
                    suggestion="Use ISO date format (YYYY-MM-DD)"
                ))
        return issues
    
    def _validate_datetime_format(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate datetime format."""
        issues = []
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                issues.append(ValidationIssue(
                    field_path=field_path,
                    issue_type=ValidationType.FORMAT,
                    severity=ValidationSeverity.ERROR,
                    message="Invalid datetime format",
                    suggestion="Use ISO datetime format (YYYY-MM-DDTHH:MM:SS)"
                ))
        return issues
    
    def _validate_time_format(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate time format."""
        issues = []
        if isinstance(value, str):
            if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', value):
                issues.append(ValidationIssue(
                    field_path=field_path,
                    issue_type=ValidationType.FORMAT,
                    severity=ValidationSeverity.ERROR,
                    message="Invalid time format",
                    suggestion="Use HH:MM format"
                ))
        return issues
    
    def _validate_email_format(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate email format."""
        issues = []
        if isinstance(value, str):
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                issues.append(ValidationIssue(
                    field_path=field_path,
                    issue_type=ValidationType.FORMAT,
                    severity=ValidationSeverity.ERROR,
                    message="Invalid email format"
                ))
        return issues
    
    def _validate_phone_format(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate phone format."""
        issues = []
        if isinstance(value, str):
            # Remove non-digit characters for validation
            digits = re.sub(r'\D', '', value)
            if len(digits) < 10 or len(digits) > 15:
                issues.append(ValidationIssue(
                    field_path=field_path,
                    issue_type=ValidationType.FORMAT,
                    severity=ValidationSeverity.ERROR,
                    message="Invalid phone number format"
                ))
        return issues
    
    def _validate_uuid_format(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate UUID format."""
        issues = []
        if isinstance(value, str):
            try:
                uuid.UUID(value)
            except ValueError:
                issues.append(ValidationIssue(
                    field_path=field_path,
                    issue_type=ValidationType.FORMAT,
                    severity=ValidationSeverity.ERROR,
                    message="Invalid UUID format"
                ))
        return issues
    
    def _validate_url_format(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate URL format."""
        issues = []
        if isinstance(value, str):
            url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
            if not re.match(url_pattern, value, re.IGNORECASE):
                issues.append(ValidationIssue(
                    field_path=field_path,
                    issue_type=ValidationType.FORMAT,
                    severity=ValidationSeverity.ERROR,
                    message="Invalid URL format"
                ))
        return issues
    
    def _validate_vin_format(self, field_path: str, value: Any, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate VIN format."""
        issues = []
        if isinstance(value, str):
            if len(value) != 17 or not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', value):
                issues.append(ValidationIssue(
                    field_path=field_path,
                    issue_type=ValidationType.FORMAT,
                    severity=ValidationSeverity.ERROR,
                    message="Invalid VIN format",
                    suggestion="VIN must be 17 characters, excluding I, O, Q"
                ))
        return issues
    
    # Constraint validators
    def _validate_min_length(self, field_path: str, value: Any, constraint: int, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate minimum length constraint."""
        issues = []
        if hasattr(value, '__len__') and len(value) < constraint:
            issues.append(ValidationIssue(
                field_path=field_path,
                issue_type=ValidationType.CONSTRAINT,
                severity=ValidationSeverity.ERROR,
                message=f"Length {len(value)} is below minimum {constraint}",
                expected_value=f">= {constraint}",
                actual_value=len(value)
            ))
        return issues
    
    def _validate_max_length(self, field_path: str, value: Any, constraint: int, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate maximum length constraint."""
        issues = []
        if hasattr(value, '__len__') and len(value) > constraint:
            issues.append(ValidationIssue(
                field_path=field_path,
                issue_type=ValidationType.CONSTRAINT,
                severity=ValidationSeverity.ERROR,
                message=f"Length {len(value)} exceeds maximum {constraint}",
                expected_value=f"<= {constraint}",
                actual_value=len(value)
            ))
        return issues
    
    def _validate_minimum(self, field_path: str, value: Any, constraint: Union[int, float], rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate minimum value constraint."""
        issues = []
        if isinstance(value, (int, float)) and value < constraint:
            issues.append(ValidationIssue(
                field_path=field_path,
                issue_type=ValidationType.CONSTRAINT,
                severity=ValidationSeverity.ERROR,
                message=f"Value {value} is below minimum {constraint}",
                expected_value=f">= {constraint}",
                actual_value=value
            ))
        return issues
    
    def _validate_maximum(self, field_path: str, value: Any, constraint: Union[int, float], rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate maximum value constraint."""
        issues = []
        if isinstance(value, (int, float)) and value > constraint:
            issues.append(ValidationIssue(
                field_path=field_path,
                issue_type=ValidationType.CONSTRAINT,
                severity=ValidationSeverity.ERROR,
                message=f"Value {value} exceeds maximum {constraint}",
                expected_value=f"<= {constraint}",
                actual_value=value
            ))
        return issues
    
    def _validate_pattern(self, field_path: str, value: Any, constraint: str, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate regex pattern constraint."""
        issues = []
        if isinstance(value, str) and not re.match(constraint, value):
            issues.append(ValidationIssue(
                field_path=field_path,
                issue_type=ValidationType.CONSTRAINT,
                severity=ValidationSeverity.ERROR,
                message=f"Value does not match required pattern",
                expected_value=f"Pattern: {constraint}",
                actual_value=value
            ))
        return issues
    
    def _validate_allowed_values(self, field_path: str, value: Any, constraint: List[Any], rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate allowed values constraint."""
        issues = []
        if value not in constraint:
            issues.append(ValidationIssue(
                field_path=field_path,
                issue_type=ValidationType.CONSTRAINT,
                severity=ValidationSeverity.ERROR,
                message=f"Value not in allowed list",
                expected_value=f"One of: {', '.join(map(str, constraint))}",
                actual_value=value
            ))
        return issues
    
    def _validate_uniqueness(self, field_path: str, value: Any, constraint: bool, rule: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate uniqueness constraint."""
        # This would require external context/database checks
        # For now, just return empty list
        return []
    
    # Consistency checks
    def _check_datetime_consistency(self, data: Dict[str, Any], result: ValidationResult):
        """Check datetime field consistency."""
        datetime_fields = self._extract_datetime_fields(data)
        
        for field_name, dt_value in datetime_fields.items():
            try:
                dt = datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
                
                # Check if date is in reasonable range
                now = datetime.now(timezone.utc)
                if dt < now - timedelta(days=365*10):  # 10 years ago
                    result.issues.append(ValidationIssue(
                        field_path=field_name,
                        issue_type=ValidationType.DATA_CONSISTENCY,
                        severity=ValidationSeverity.WARNING,
                        message="Date is unusually far in the past",
                        actual_value=dt_value
                    ))
                elif dt > now + timedelta(days=365*5):  # 5 years future
                    result.issues.append(ValidationIssue(
                        field_path=field_name,
                        issue_type=ValidationType.DATA_CONSISTENCY,
                        severity=ValidationSeverity.WARNING,
                        message="Date is unusually far in the future",
                        actual_value=dt_value
                    ))
            except Exception:
                pass  # Invalid datetime format already caught by format validation
    
    def _check_id_consistency(self, data: Dict[str, Any], result: ValidationResult):
        """Check ID field consistency."""
        id_fields = self._extract_id_fields(data)
        
        for field_name, id_value in id_fields.items():
            if isinstance(id_value, str):
                if len(id_value) == 0:
                    result.issues.append(ValidationIssue(
                        field_path=field_name,
                        issue_type=ValidationType.DATA_CONSISTENCY,
                        severity=ValidationSeverity.ERROR,
                        message="ID field is empty",
                        actual_value=id_value
                    ))
                elif len(id_value) > 100:  # Arbitrary reasonable limit
                    result.issues.append(ValidationIssue(
                        field_path=field_name,
                        issue_type=ValidationType.DATA_CONSISTENCY,
                        severity=ValidationSeverity.WARNING,
                        message="ID field is unusually long",
                        actual_value=f"Length: {len(id_value)}"
                    ))
    
    def _check_cross_field_consistency(self, data: Dict[str, Any], metadata: TemplateMetadata, result: ValidationResult):
        """Check consistency across related fields."""
        # Check start/end datetime consistency
        start_fields = self._extract_fields_with_pattern(data, r'start.*time|.*start')
        end_fields = self._extract_fields_with_pattern(data, r'end.*time|.*end')
        
        for start_field, start_value in start_fields.items():
            for end_field, end_value in end_fields.items():
                try:
                    start_dt = datetime.fromisoformat(start_value.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_value.replace('Z', '+00:00'))
                    
                    if start_dt >= end_dt:
                        result.issues.append(ValidationIssue(
                            field_path=f"{start_field}, {end_field}",
                            issue_type=ValidationType.DATA_CONSISTENCY,
                            severity=ValidationSeverity.ERROR,
                            message="Start time must be before end time",
                            actual_value=f"Start: {start_value}, End: {end_value}"
                        ))
                except Exception:
                    pass  # Invalid datetime formats
    
    # Helper methods
    def _extract_datetime_fields(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Extract datetime fields from data."""
        datetime_fields = {}
        self._extract_fields_recursive(data, datetime_fields, lambda k, v: 
            isinstance(v, str) and ('time' in k.lower() or 'date' in k.lower()) and 
            re.match(r'\d{4}-\d{2}-\d{2}', v))
        return datetime_fields
    
    def _extract_id_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract ID fields from data."""
        id_fields = {}
        self._extract_fields_recursive(data, id_fields, lambda k, v: 'id' in k.lower())
        return id_fields
    
    def _extract_fields_with_pattern(self, data: Dict[str, Any], pattern: str) -> Dict[str, Any]:
        """Extract fields matching a pattern."""
        matching_fields = {}
        self._extract_fields_recursive(data, matching_fields, lambda k, v: 
            re.search(pattern, k.lower()) is not None)
        return matching_fields
    
    def _extract_fields_recursive(self, data: Any, result: Dict[str, Any], condition: callable, path: str = ""):
        """Recursively extract fields matching a condition."""
        if isinstance(data, dict):
            for key, value in data.items():
                field_path = f"{path}.{key}" if path else key
                if condition(key, value):
                    result[field_path] = value
                self._extract_fields_recursive(value, result, condition, field_path)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                item_path = f"{path}[{i}]" if path else f"[{i}]"
                self._extract_fields_recursive(item, result, condition, item_path)
    
    def _count_issues_by_severity(self, result: ValidationResult):
        """Count issues by severity level."""
        severity_counts = {
            ValidationSeverity.INFO: 0,
            ValidationSeverity.WARNING: 0,
            ValidationSeverity.ERROR: 0,
            ValidationSeverity.CRITICAL: 0
        }
        
        for issue in result.issues:
            severity_counts[issue.severity] += 1
        
        result.warnings_count = severity_counts[ValidationSeverity.WARNING]
        result.errors_count = severity_counts[ValidationSeverity.ERROR]
        result.critical_count = severity_counts[ValidationSeverity.CRITICAL]
    
    def _determine_validity(self, result: ValidationResult, options: ValidationOptions) -> bool:
        """Determine overall validity based on issues and options."""
        if result.critical_count > 0:
            return False
        if result.errors_count > 0 and options.strict_mode:
            return False
        if result.warnings_count > 0 and options.fail_on_warnings:
            return False
        return True
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Get summary of validation results.
        
        Args:
            results: List of validation results
            
        Returns:
            Summary information
        """
        if not results:
            return {"total_validations": 0}
        
        valid_count = sum(1 for r in results if r.is_valid)
        total_issues = sum(len(r.issues) for r in results)
        total_warnings = sum(r.warnings_count for r in results)
        total_errors = sum(r.errors_count for r in results)
        total_critical = sum(r.critical_count for r in results)
        total_time = sum(r.processing_time for r in results)
        
        return {
            "total_validations": len(results),
            "valid_count": valid_count,
            "invalid_count": len(results) - valid_count,
            "success_rate": valid_count / len(results),
            "total_issues": total_issues,
            "total_warnings": total_warnings,
            "total_errors": total_errors,
            "total_critical": total_critical,
            "total_processing_time": total_time,
            "average_processing_time": total_time / len(results),
            "templates_validated": [r.template_id for r in results]
        }


# Business Rules Implementation
class VehicleIDValidationRule(BusinessRule):
    """Validates vehicle ID format and consistency."""
    
    def __init__(self):
        super().__init__(
            name="vehicle_id_validation",
            description="Validates vehicle ID format and consistency",
            severity=ValidationSeverity.ERROR
        )
    
    def validate(self, data: Dict[str, Any], context: Dict[str, Any]) -> List[ValidationIssue]:
        issues = []
        vehicle_id = self._extract_vehicle_id(data)
        
        if vehicle_id:
            # Check format
            if not re.match(r'^[A-Z0-9-]{3,15}$', vehicle_id):
                issues.append(ValidationIssue(
                    field_path="vehicle_id",
                    issue_type=ValidationType.BUSINESS_RULE,
                    severity=self.severity,
                    message="Vehicle ID must be 3-15 characters, alphanumeric with hyphens",
                    rule_name=self.name
                ))
        
        return issues
    
    def _extract_vehicle_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract vehicle ID from data structure."""
        vehicle_id_fields = ['vehicle_id', 'vehicleId', 'unit_id', 'asset_id']
        for field in vehicle_id_fields:
            if field in data and data[field]:
                return str(data[field])
        return None


class DateTimeConsistencyRule(BusinessRule):
    """Validates datetime field consistency."""
    
    def __init__(self):
        super().__init__(
            name="datetime_consistency",
            description="Validates datetime field relationships",
            severity=ValidationSeverity.ERROR
        )
    
    def validate(self, data: Dict[str, Any], context: Dict[str, Any]) -> List[ValidationIssue]:
        issues = []
        
        # Check reservation datetime consistency
        if 'reservation_details' in data:
            reservation = data['reservation_details']
            start_time = reservation.get('start_time')
            end_time = reservation.get('end_time')
            
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    
                    if start_dt >= end_dt:
                        issues.append(ValidationIssue(
                            field_path="reservation_details.start_time",
                            issue_type=ValidationType.BUSINESS_RULE,
                            severity=self.severity,
                            message="Reservation start time must be before end time",
                            rule_name=self.name
                        ))
                    
                    # Check if reservation is too far in the future
                    now = datetime.now(timezone.utc)
                    if start_dt > now + timedelta(days=365):
                        issues.append(ValidationIssue(
                            field_path="reservation_details.start_time",
                            issue_type=ValidationType.BUSINESS_RULE,
                            severity=ValidationSeverity.WARNING,
                            message="Reservation is more than 1 year in the future",
                            rule_name=self.name
                        ))
                except ValueError:
                    pass  # Invalid datetime formats handled by format validation
        
        return issues


class MaintenanceSchedulingRule(BusinessRule):
    """Validates maintenance scheduling logic."""
    
    def __init__(self):
        super().__init__(
            name="maintenance_scheduling",
            description="Validates maintenance scheduling constraints",
            severity=ValidationSeverity.WARNING
        )
    
    def validate(self, data: Dict[str, Any], context: Dict[str, Any]) -> List[ValidationIssue]:
        issues = []
        
        if context.get('category') == 'maintenance':
            # Check maintenance scheduling
            if 'scheduling' in data:
                scheduling = data['scheduling']
                requested_date = scheduling.get('requested_date')
                requested_time = scheduling.get('requested_time')
                
                if requested_date and requested_time:
                    try:
                        # Combine date and time
                        datetime_str = f"{requested_date}T{requested_time}"
                        scheduled_dt = datetime.fromisoformat(datetime_str)
                        
                        # Check if scheduled during business hours
                        if scheduled_dt.hour < 7 or scheduled_dt.hour > 18:
                            issues.append(ValidationIssue(
                                field_path="scheduling.requested_time",
                                issue_type=ValidationType.BUSINESS_RULE,
                                severity=self.severity,
                                message="Maintenance scheduled outside business hours (7 AM - 6 PM)",
                                rule_name=self.name
                            ))
                        
                        # Check if scheduled on weekend
                        if scheduled_dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
                            issues.append(ValidationIssue(
                                field_path="scheduling.requested_date",
                                issue_type=ValidationType.BUSINESS_RULE,
                                severity=self.severity,
                                message="Maintenance scheduled on weekend",
                                rule_name=self.name
                            ))
                    except ValueError:
                        pass  # Invalid datetime format
        
        return issues


class ReservationConflictRule(BusinessRule):
    """Validates reservation conflicts."""
    
    def __init__(self):
        super().__init__(
            name="reservation_conflict",
            description="Validates reservation conflicts",
            severity=ValidationSeverity.WARNING
        )
    
    def validate(self, data: Dict[str, Any], context: Dict[str, Any]) -> List[ValidationIssue]:
        # This would require external database checks
        # For now, return empty list
        return []


class ParkingAvailabilityRule(BusinessRule):
    """Validates parking space availability."""
    
    def __init__(self):
        super().__init__(
            name="parking_availability",
            description="Validates parking space availability",
            severity=ValidationSeverity.WARNING
        )
    
    def validate(self, data: Dict[str, Any], context: Dict[str, Any]) -> List[ValidationIssue]:
        # This would require external parking system checks
        # For now, return empty list
        return []


class UserAuthorizationRule(BusinessRule):
    """Validates user authorization."""
    
    def __init__(self):
        super().__init__(
            name="user_authorization",
            description="Validates user authorization for operations",
            severity=ValidationSeverity.WARNING
        )
    
    def validate(self, data: Dict[str, Any], context: Dict[str, Any]) -> List[ValidationIssue]:
        # This would require external user permission checks
        # For now, return empty list
        return []


class ResourceConstraintRule(BusinessRule):
    """Validates resource constraints."""
    
    def __init__(self):
        super().__init__(
            name="resource_constraint",
            description="Validates resource availability constraints",
            severity=ValidationSeverity.WARNING
        )
    
    def validate(self, data: Dict[str, Any], context: Dict[str, Any]) -> List[ValidationIssue]:
        # This would require external resource availability checks
        # For now, return empty list
        return []


class LocationValidationRule(BusinessRule):
    """Validates location information."""
    
    def __init__(self):
        super().__init__(
            name="location_validation",
            description="Validates location information",
            severity=ValidationSeverity.WARNING
        )
    
    def validate(self, data: Dict[str, Any], context: Dict[str, Any]) -> List[ValidationIssue]:
        issues = []
        
        # Check if location fields are consistent
        location_fields = self._extract_location_fields(data)
        
        for field_name, location_value in location_fields.items():
            if isinstance(location_value, str):
                if len(location_value) < 2:
                    issues.append(ValidationIssue(
                        field_path=field_name,
                        issue_type=ValidationType.BUSINESS_RULE,
                        severity=self.severity,
                        message="Location name is too short",
                        rule_name=self.name
                    ))
                elif len(location_value) > 100:
                    issues.append(ValidationIssue(
                        field_path=field_name,
                        issue_type=ValidationType.BUSINESS_RULE,
                        severity=self.severity,
                        message="Location name is unusually long",
                        rule_name=self.name
                    ))
        
        return issues
    
    def _extract_location_fields(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Extract location fields from data."""
        location_fields = {}
        self._extract_location_recursive(data, location_fields)
        return location_fields
    
    def _extract_location_recursive(self, data: Any, result: Dict[str, str], path: str = ""):
        """Recursively extract location fields."""
        if isinstance(data, dict):
            for key, value in data.items():
                field_path = f"{path}.{key}" if path else key
                if 'location' in key.lower() or 'address' in key.lower() or 'site' in key.lower():
                    if isinstance(value, str):
                        result[field_path] = value
                self._extract_location_recursive(value, result, field_path)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                item_path = f"{path}[{i}]" if path else f"[{i}]"
                self._extract_location_recursive(item, result, item_path)