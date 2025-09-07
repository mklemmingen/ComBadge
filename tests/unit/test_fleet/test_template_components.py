"""
Unit tests for template system components.

Tests JSON generation, template validation, and template management
for the fleet management template processing system.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, mock_open
from typing import Dict, Any, List
import tempfile
import os

from combadge.fleet.templates.json_generator import JSONGenerator
from combadge.fleet.templates.validators import TemplateValidator, ValidationResult
from combadge.fleet.templates.template_manager import TemplateManager
from combadge.api.client import HTTPClient


class TestJSONGenerator:
    """Test suite for JSONGenerator component"""

    @pytest.fixture
    def json_generator(self):
        """Create JSONGenerator instance"""
        return JSONGenerator()

    @pytest.fixture
    def sample_template(self):
        """Sample template for testing"""
        return {
            "template_id": "schedule_maintenance",
            "intent": "maintenance_scheduling",
            "api_request": {
                "method": "POST",
                "endpoint": "/api/maintenance",
                "body": {
                    "vehicle_id": "{{vehicle_id}}",
                    "scheduled_date": "{{date|format_date}}",
                    "maintenance_type": "{{maintenance_type|default:routine}}",
                    "service_center": "{{service_center|default:Main Garage}}",
                    "estimated_cost": "{{cost|optional}}"
                }
            },
            "field_mappings": {
                "vehicle_id": {
                    "type": "string",
                    "required": True,
                    "validation": "vehicle_id_format"
                },
                "date": {
                    "type": "datetime",
                    "required": True,
                    "validation": "future_date"
                },
                "maintenance_type": {
                    "type": "string",
                    "required": False,
                    "default": "routine"
                }
            }
        }

    @pytest.fixture
    def sample_entities(self):
        """Sample entities for template population"""
        return {
            "vehicle_id": "F-123",
            "date": "tomorrow",
            "maintenance_type": "oil_change",
            "service_center": "North Garage"
        }

    @pytest.mark.unit
    def test_generate_basic_json(self, json_generator, sample_template, sample_entities):
        """Test basic JSON generation from template"""
        result = json_generator.generate_json(
            template=sample_template,
            entities=sample_entities,
            intent="maintenance_scheduling",
            confidence=0.90
        )
        
        assert result["success"] is True
        assert result["intent"] == "maintenance_scheduling"
        assert result["confidence"] == 0.90
        
        # Check generated request
        generated_request = result["generated_request"]
        assert generated_request["vehicle_id"] == "F-123"
        assert generated_request["maintenance_type"] == "oil_change"
        assert generated_request["service_center"] == "North Garage"

    @pytest.mark.unit
    def test_template_variable_substitution(self, json_generator):
        """Test template variable substitution"""
        template_content = {
            "vehicle_id": "{{vehicle_id}}",
            "message": "Service {{vehicle_id}} at {{location}}",
            "nested": {
                "date": "{{date}}",
                "cost": "{{cost|default:$150}}"
            }
        }
        
        entities = {
            "vehicle_id": "F-123",
            "location": "Main Garage",
            "date": "2024-03-16"
        }
        
        result = json_generator.substitute_variables(template_content, entities)
        
        assert result["vehicle_id"] == "F-123"
        assert result["message"] == "Service F-123 at Main Garage"
        assert result["nested"]["date"] == "2024-03-16"
        assert result["nested"]["cost"] == "$150"  # Default value used

    @pytest.mark.unit
    def test_template_filters(self, json_generator):
        """Test template filter application"""
        # Test date formatting filter
        date_result = json_generator.apply_filter("2024-03-15", "format_date")
        assert isinstance(date_result, str)
        assert "2024" in date_result
        
        # Test default value filter
        default_result = json_generator.apply_filter(None, "default:routine")
        assert default_result == "routine"
        
        # Test optional filter (removes field if None)
        optional_result = json_generator.apply_filter(None, "optional")
        assert optional_result == json_generator.REMOVE_FIELD
        
        # Test uppercase filter
        upper_result = json_generator.apply_filter("test", "upper")
        assert upper_result == "TEST"

    @pytest.mark.unit
    def test_entity_mapping_with_confidence(self, json_generator, sample_template):
        """Test entity mapping with confidence tracking"""
        entities_with_confidence = {
            "vehicle_id": {"value": "F-123", "confidence": 0.95},
            "date": {"value": "tomorrow", "confidence": 0.80},
            "maintenance_type": {"value": "oil_change", "confidence": 0.70}
        }
        
        result = json_generator.generate_json(
            template=sample_template,
            entities=entities_with_confidence,
            intent="maintenance_scheduling",
            confidence=0.85,
            track_confidence=True
        )
        
        assert result["success"] is True
        assert "field_confidence" in result
        assert result["field_confidence"]["vehicle_id"] == 0.95
        assert result["field_confidence"]["date"] == 0.80

    @pytest.mark.unit
    def test_nested_template_generation(self, json_generator):
        """Test generation with nested template structures"""
        nested_template = {
            "reservation": {
                "vehicle_id": "{{vehicle_id}}",
                "schedule": {
                    "start_time": "{{start_time}}",
                    "end_time": "{{end_time}}",
                    "location": "{{location|default:Main Lot}}"
                },
                "requestor": {
                    "name": "{{user_name}}",
                    "email": "{{user_email}}"
                }
            }
        }
        
        entities = {
            "vehicle_id": "V-456",
            "start_time": "2024-03-15T14:00:00",
            "end_time": "2024-03-15T16:00:00",
            "user_name": "John Doe",
            "user_email": "john.doe@company.com"
        }
        
        result = json_generator.substitute_variables(nested_template, entities)
        
        assert result["reservation"]["vehicle_id"] == "V-456"
        assert result["reservation"]["schedule"]["start_time"] == "2024-03-15T14:00:00"
        assert result["reservation"]["schedule"]["location"] == "Main Lot"  # Default
        assert result["reservation"]["requestor"]["name"] == "John Doe"

    @pytest.mark.unit
    def test_missing_required_entities(self, json_generator, sample_template):
        """Test handling of missing required entities"""
        incomplete_entities = {
            "vehicle_id": "F-123"
            # Missing required 'date' field
        }
        
        result = json_generator.generate_json(
            template=sample_template,
            entities=incomplete_entities,
            intent="maintenance_scheduling",
            confidence=0.90
        )
        
        assert result["success"] is False
        assert "missing_required_fields" in result
        assert "date" in result["missing_required_fields"]

    @pytest.mark.unit
    def test_conditional_field_generation(self, json_generator):
        """Test conditional field generation"""
        conditional_template = {
            "vehicle_id": "{{vehicle_id}}",
            "{{#if urgent}}priority": "high"{{/if}},
            "{{#unless cost}}estimated_cost": "$100"{{/unless}}"
        }
        
        # Test with urgent condition true
        entities_urgent = {
            "vehicle_id": "F-123",
            "urgent": True,
            "cost": 150
        }
        
        result = json_generator.substitute_variables(conditional_template, entities_urgent)
        assert result.get("priority") == "high"
        assert "estimated_cost" not in result  # cost was provided


class TestTemplateValidator:
    """Test suite for TemplateValidator component"""

    @pytest.fixture
    def mock_api_client(self):
        """Mock API client for validation"""
        mock_client = Mock(spec=HTTPClient)
        mock_client.get = AsyncMock()
        return mock_client

    @pytest.fixture
    def template_validator(self, mock_api_client):
        """Create TemplateValidator instance"""
        return TemplateValidator(api_client=mock_api_client)

    @pytest.fixture
    def valid_request(self):
        """Valid API request for testing"""
        return {
            "vehicle_id": "F-123",
            "scheduled_date": "2024-03-16T10:00:00",
            "maintenance_type": "routine",
            "service_center": "Main Garage"
        }

    @pytest.fixture
    def template_schema(self):
        """Template schema for validation"""
        return {
            "required_fields": ["vehicle_id", "scheduled_date"],
            "field_types": {
                "vehicle_id": "string",
                "scheduled_date": "datetime",
                "maintenance_type": "string"
            },
            "business_rules": [
                {
                    "rule_id": "future_date",
                    "field": "scheduled_date",
                    "validation": "must_be_future"
                }
            ]
        }

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_valid_request(self, template_validator, valid_request, template_schema):
        """Test validation of valid request"""
        result = await template_validator.validate_request(
            request=valid_request,
            template={"schema": template_schema}
        )
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_missing_required_fields(self, template_validator, template_schema):
        """Test validation with missing required fields"""
        incomplete_request = {
            "maintenance_type": "routine"
            # Missing required vehicle_id and scheduled_date
        }
        
        result = await template_validator.validate_request(
            request=incomplete_request,
            template={"schema": template_schema}
        )
        
        assert result.is_valid is False
        assert len(result.errors) >= 2  # Missing vehicle_id and scheduled_date
        
        error_message = " ".join(result.errors)
        assert "vehicle_id" in error_message
        assert "scheduled_date" in error_message

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_incorrect_field_types(self, template_validator, template_schema):
        """Test validation with incorrect field types"""
        wrong_types_request = {
            "vehicle_id": 123,  # Should be string
            "scheduled_date": "not-a-date",  # Should be datetime
            "maintenance_type": ["routine"]  # Should be string
        }
        
        result = await template_validator.validate_request(
            request=wrong_types_request,
            template={"schema": template_schema}
        )
        
        assert result.is_valid is False
        assert len(result.errors) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_business_rule_validation(self, template_validator, mock_api_client, template_schema):
        """Test business rule validation"""
        # Setup API client to return validation results
        mock_api_client.get.return_value = {
            "exists": True,
            "valid": True
        }
        
        past_date_request = {
            "vehicle_id": "F-123",
            "scheduled_date": "2024-01-01T10:00:00",  # Past date
            "maintenance_type": "routine"
        }
        
        result = await template_validator.validate_request(
            request=past_date_request,
            template={"schema": template_schema}
        )
        
        # Should fail due to past date business rule
        assert result.is_valid is False
        assert any("future" in error.lower() for error in result.errors)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_vehicle_existence_validation(self, template_validator, mock_api_client):
        """Test vehicle existence validation"""
        # Test with existing vehicle
        mock_api_client.get.return_value = {
            "vehicle": {"id": "F-123", "status": "active"}
        }
        
        result = await template_validator.validate_vehicle_exists("F-123")
        
        assert result.is_valid is True
        
        # Test with non-existent vehicle
        mock_api_client.get.side_effect = Exception("Vehicle not found")
        
        result = await template_validator.validate_vehicle_exists("NONEXISTENT")
        
        assert result.is_valid is False
        assert "not found" in result.error_message.lower()

    @pytest.mark.unit
    def test_data_consistency_validation(self, template_validator):
        """Test data consistency validation"""
        # Test consistent reservation times
        consistent_request = {
            "vehicle_id": "V-456",
            "start_time": "2024-03-15T14:00:00",
            "end_time": "2024-03-15T16:00:00"
        }
        
        result = template_validator.validate_data_consistency(consistent_request)
        
        assert result.is_valid is True
        
        # Test inconsistent times (end before start)
        inconsistent_request = {
            "vehicle_id": "V-456",
            "start_time": "2024-03-15T16:00:00",
            "end_time": "2024-03-15T14:00:00"
        }
        
        result = template_validator.validate_data_consistency(inconsistent_request)
        
        assert result.is_valid is False
        assert "end time" in result.error_message.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_batch_validation(self, template_validator, template_schema):
        """Test batch validation of multiple requests"""
        requests = [
            {"vehicle_id": "F-123", "scheduled_date": "2024-03-16T10:00:00"},
            {"vehicle_id": "V-456", "scheduled_date": "2024-03-17T11:00:00"},
            {"maintenance_type": "routine"}  # Missing required fields
        ]
        
        results = await template_validator.validate_batch(
            requests=requests,
            template={"schema": template_schema}
        )
        
        assert len(results) == 3
        assert results[0].is_valid is True
        assert results[1].is_valid is True
        assert results[2].is_valid is False  # Missing required fields


class TestTemplateManager:
    """Test suite for TemplateManager component"""

    @pytest.fixture
    def template_manager(self):
        """Create TemplateManager instance"""
        return TemplateManager()

    @pytest.fixture
    def sample_templates(self):
        """Sample templates for testing"""
        return {
            "maintenance_scheduling": {
                "schedule_maintenance": {
                    "template_id": "schedule_maintenance",
                    "intent": "maintenance_scheduling",
                    "api_endpoint": "/api/maintenance",
                    "method": "POST",
                    "required_fields": ["vehicle_id", "scheduled_date"],
                    "template": {
                        "vehicle_id": "{{vehicle_id}}",
                        "scheduled_date": "{{date|format_date}}"
                    }
                }
            },
            "vehicle_reservation": {
                "reserve_vehicle": {
                    "template_id": "reserve_vehicle",
                    "intent": "vehicle_reservation",
                    "api_endpoint": "/api/reservations",
                    "method": "POST",
                    "required_fields": ["vehicle_id", "start_time", "end_time"],
                    "template": {
                        "vehicle_id": "{{vehicle_id}}",
                        "start_time": "{{start_time}}",
                        "end_time": "{{end_time}}"
                    }
                }
            }
        }

    @pytest.mark.unit
    def test_load_templates(self, template_manager, sample_templates):
        """Test template loading"""
        # Mock file system operations
        with patch('builtins.open', mock_open(read_data=json.dumps(sample_templates))):
            with patch('os.path.exists', return_value=True):
                template_manager.load_templates("mock_path")
        
        # Verify templates were loaded
        assert len(template_manager.templates) > 0
        assert "maintenance_scheduling" in template_manager.templates

    @pytest.mark.unit
    def test_select_template_by_intent(self, template_manager, sample_templates):
        """Test template selection by intent"""
        template_manager.templates = sample_templates
        
        # Test exact intent match
        selected = template_manager.select_template("maintenance_scheduling")
        
        assert selected is not None
        assert selected["template_id"] == "schedule_maintenance"
        assert selected["intent"] == "maintenance_scheduling"
        
        # Test unknown intent
        unknown = template_manager.select_template("unknown_intent")
        assert unknown is None

    @pytest.mark.unit
    def test_select_best_matching_template(self, template_manager, sample_templates):
        """Test selection of best matching template"""
        template_manager.templates = sample_templates
        
        entities = {
            "vehicle_id": "F-123",
            "start_time": "2024-03-15T14:00:00",
            "end_time": "2024-03-15T16:00:00"
        }
        
        # Should select reservation template based on entities
        selected = template_manager.select_best_template(
            intent="vehicle_reservation",
            entities=entities,
            confidence=0.90
        )
        
        assert selected is not None
        assert selected["template_id"] == "reserve_vehicle"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_request_from_template(self, template_manager, sample_templates):
        """Test API request generation from template"""
        template_manager.templates = sample_templates
        
        template = sample_templates["maintenance_scheduling"]["schedule_maintenance"]
        entities = {
            "vehicle_id": "F-123",
            "date": "2024-03-16T10:00:00"
        }
        
        result = await template_manager.generate_request(
            template=template,
            entities=entities,
            intent="maintenance_scheduling"
        )
        
        assert result["success"] is True
        assert result["method"] == "POST"
        assert result["endpoint"] == "/api/maintenance"
        assert result["body"]["vehicle_id"] == "F-123"

    @pytest.mark.unit
    def test_template_validation_on_load(self, template_manager):
        """Test template validation during loading"""
        invalid_templates = {
            "invalid_intent": {
                "invalid_template": {
                    # Missing required fields like template_id, intent, etc.
                    "some_field": "some_value"
                }
            }
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(invalid_templates))):
            with patch('os.path.exists', return_value=True):
                with pytest.raises(ValueError) as exc_info:
                    template_manager.load_templates("mock_path")
        
        assert "template_id" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_template_inheritance(self, template_manager):
        """Test template inheritance and base templates"""
        base_template = {
            "base_maintenance": {
                "template_id": "base_maintenance",
                "intent": "maintenance_scheduling",
                "api_endpoint": "/api/maintenance",
                "method": "POST",
                "template": {
                    "vehicle_id": "{{vehicle_id}}",
                    "service_center": "{{service_center|default:Main Garage}}"
                }
            }
        }
        
        extended_template = {
            "oil_change": {
                "template_id": "oil_change",
                "extends": "base_maintenance",
                "template": {
                    "maintenance_type": "oil_change",
                    "estimated_duration": "30 minutes"
                }
            }
        }
        
        # Test template inheritance merging
        merged = template_manager.merge_templates(base_template["base_maintenance"], 
                                                 extended_template["oil_change"])
        
        assert merged["template_id"] == "oil_change"
        assert merged["api_endpoint"] == "/api/maintenance"  # Inherited
        assert merged["template"]["maintenance_type"] == "oil_change"  # Extended
        assert merged["template"]["vehicle_id"] == "{{vehicle_id}}"  # Inherited

    @pytest.mark.unit
    def test_template_caching(self, template_manager, sample_templates):
        """Test template caching mechanism"""
        template_manager.templates = sample_templates
        template_manager.enable_caching = True
        
        # First access - should cache
        result1 = template_manager.select_template("maintenance_scheduling")
        assert result1 is not None
        
        # Second access - should use cache
        result2 = template_manager.select_template("maintenance_scheduling")
        assert result2 is not None
        assert result2 == result1  # Should be same object from cache

    @pytest.mark.unit
    def test_template_hot_reload(self, template_manager, sample_templates):
        """Test hot reloading of templates"""
        template_manager.templates = sample_templates
        template_manager.enable_hot_reload = True
        
        # Simulate file modification
        with patch('os.path.getmtime', return_value=time.time() + 100):  # Newer timestamp
            with patch('builtins.open', mock_open(read_data=json.dumps({}))):
                with patch('os.path.exists', return_value=True):
                    # Should detect modification and reload
                    template_manager.check_for_updates()
        
        # Templates should be updated (empty in this mock case)
        assert len(template_manager.templates) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_template_performance(self, template_manager, sample_templates, performance_monitor):
        """Test template processing performance"""
        template_manager.templates = sample_templates
        
        performance_monitor.start()
        
        # Process multiple template selections and generations
        tasks = []
        for i in range(100):
            intent = "maintenance_scheduling" if i % 2 == 0 else "vehicle_reservation"
            tasks.append(template_manager.select_template(intent))
        
        results = await asyncio.gather(*[asyncio.coroutine(lambda x=t: x)() for t in tasks])
        
        metrics = performance_monitor.stop()
        
        # Verify all selections completed
        assert len(results) == 100
        for result in results:
            assert result is not None
        
        # Check performance
        avg_time = metrics['duration'] / len(results) * 1000  # ms per selection
        assert avg_time < 10  # Should be very fast (under 10ms per selection)