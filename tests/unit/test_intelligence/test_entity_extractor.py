"""
Unit tests for the EntityExtractor component.

Tests entity extraction accuracy, pattern matching,
and validation for the NLP entity extraction system.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
import re
from datetime import datetime, timedelta

from combadge.intelligence.entity_extractor import EntityExtractor
from combadge.intelligence.llm_manager import LLMManager
from tests.fixtures.sample_data import SAMPLE_COMMANDS, SAMPLE_LLM_RESPONSES


class TestEntityExtractor:
    """Test suite for EntityExtractor component"""

    @pytest.fixture
    def llm_manager(self):
        """Mock LLM manager for testing"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.is_available = Mock(return_value=True)
        mock_llm.generate_response = AsyncMock()
        return mock_llm

    @pytest.fixture
    def entity_extractor(self, llm_manager):
        """Create EntityExtractor instance with mocked dependencies"""
        return EntityExtractor(llm_manager=llm_manager)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_vehicle_entities(self, entity_extractor, llm_manager):
        """Test extraction of vehicle-related entities"""
        # Setup mock response
        llm_manager.generate_response.return_value = {
            "entities": {
                "vehicle_id": "F-123",
                "make": "Ford",
                "model": "Transit",
                "license_plate": "FLT-123"
            },
            "confidence": 0.92
        }
        
        text = "Schedule maintenance for Ford Transit F-123 with license plate FLT-123"
        result = await entity_extractor.extract_entities(text, intent="maintenance_scheduling")
        
        assert result["entities"]["vehicle_id"] == "F-123"
        assert result["entities"]["make"] == "Ford"
        assert result["entities"]["model"] == "Transit"
        assert result["entities"]["license_plate"] == "FLT-123"
        assert result["confidence"] == 0.92

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_temporal_entities(self, entity_extractor, llm_manager):
        """Test extraction of date and time entities"""
        llm_manager.generate_response.return_value = {
            "entities": {
                "date": "2024-03-15",
                "time": "10:00 AM",
                "duration": "2 hours",
                "relative_date": "tomorrow"
            },
            "confidence": 0.88
        }
        
        text = "Schedule maintenance tomorrow at 10:00 AM for 2 hours"
        result = await entity_extractor.extract_entities(text, intent="maintenance_scheduling")
        
        entities = result["entities"]
        assert entities["date"] == "2024-03-15"
        assert entities["time"] == "10:00 AM"
        assert entities["duration"] == "2 hours"
        assert entities["relative_date"] == "tomorrow"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_location_entities(self, entity_extractor, llm_manager):
        """Test extraction of location-related entities"""
        llm_manager.generate_response.return_value = {
            "entities": {
                "location": "Building A",
                "parking_spot": "B-12",
                "service_center": "Main Garage",
                "address": "123 Main St"
            },
            "confidence": 0.85
        }
        
        text = "Assign vehicle to Building A parking spot B-12 near Main Garage at 123 Main St"
        result = await entity_extractor.extract_entities(text, intent="parking_management")
        
        entities = result["entities"]
        assert entities["location"] == "Building A"
        assert entities["parking_spot"] == "B-12"
        assert entities["service_center"] == "Main Garage"
        assert entities["address"] == "123 Main St"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_contact_entities(self, entity_extractor, llm_manager):
        """Test extraction of contact information entities"""
        llm_manager.generate_response.return_value = {
            "entities": {
                "email": "john.doe@company.com",
                "phone": "+1-555-123-4567",
                "name": "John Doe",
                "department": "Sales"
            },
            "confidence": 0.90
        }
        
        text = "Reserve vehicle for John Doe from Sales at john.doe@company.com phone +1-555-123-4567"
        result = await entity_extractor.extract_entities(text, intent="vehicle_reservation")
        
        entities = result["entities"]
        assert entities["email"] == "john.doe@company.com"
        assert entities["phone"] == "+1-555-123-4567"
        assert entities["name"] == "John Doe"
        assert entities["department"] == "Sales"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_numeric_entities(self, entity_extractor, llm_manager):
        """Test extraction of numeric values and measurements"""
        llm_manager.generate_response.return_value = {
            "entities": {
                "mileage": "25000",
                "fuel_level": "75%",
                "year": "2023",
                "capacity": "8 passengers",
                "cost": "$150"
            },
            "confidence": 0.87
        }
        
        text = "Vehicle has 25000 miles, 75% fuel, built in 2023, seats 8 passengers, costs $150 to service"
        result = await entity_extractor.extract_entities(text, intent="data_query")
        
        entities = result["entities"]
        assert entities["mileage"] == "25000"
        assert entities["fuel_level"] == "75%"
        assert entities["year"] == "2023"
        assert entities["capacity"] == "8 passengers"
        assert entities["cost"] == "$150"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_with_pattern_validation(self, entity_extractor, llm_manager):
        """Test entity extraction with pattern validation"""
        # Setup extractor with validation patterns
        vehicle_patterns = [r'^[A-Z]-\d{3,4}$', r'^[A-Z]{3}-\d{3}$']
        entity_extractor.set_validation_patterns("vehicle_id", vehicle_patterns)
        
        llm_manager.generate_response.return_value = {
            "entities": {
                "vehicle_id": "F-123",
                "invalid_vehicle_id": "INVALID-FORMAT"
            },
            "confidence": 0.80
        }
        
        text = "Process vehicle F-123 and INVALID-FORMAT"
        result = await entity_extractor.extract_entities(text, validate_patterns=True)
        
        entities = result["entities"]
        assert entities["vehicle_id"] == "F-123"  # Valid format
        assert "invalid_vehicle_id" not in entities  # Invalid format filtered out

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_entities_batch_processing(self, entity_extractor, llm_manager):
        """Test batch processing of multiple texts"""
        texts = [
            "Schedule maintenance for F-123 tomorrow",
            "Reserve V-456 for sales meeting",
            "Add Toyota Camry to fleet"
        ]
        
        expected_entities = [
            {"vehicle_id": "F-123", "date": "tomorrow"},
            {"vehicle_id": "V-456", "purpose": "sales meeting"},
            {"make": "Toyota", "model": "Camry"}
        ]
        
        # Setup sequential responses
        llm_manager.generate_response.side_effect = [
            {"entities": entities, "confidence": 0.9}
            for entities in expected_entities
        ]
        
        results = await entity_extractor.batch_extract(texts)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            expected = expected_entities[i]
            for key, value in expected.items():
                assert result["entities"][key] == value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_entities_with_context(self, entity_extractor, llm_manager):
        """Test entity extraction with contextual information"""
        context = {
            "previous_vehicle": "F-123",
            "current_location": "Building A",
            "user_department": "Fleet Management"
        }
        
        llm_manager.generate_response.return_value = {
            "entities": {
                "vehicle_id": "F-123",  # Resolved from context
                "action": "maintenance",
                "location": "Building A"  # Inherited from context
            },
            "confidence": 0.93
        }
        
        text = "Schedule maintenance for the vehicle"  # Ambiguous reference
        result = await entity_extractor.extract_entities(text, context=context)
        
        entities = result["entities"]
        assert entities["vehicle_id"] == "F-123"  # Resolved from context
        assert entities["location"] == "Building A"  # Inherited from context

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_entities_error_handling(self, entity_extractor, llm_manager):
        """Test error handling during entity extraction"""
        # Test LLM service failure
        llm_manager.generate_response.side_effect = Exception("LLM service unavailable")
        
        with pytest.raises(Exception) as exc_info:
            await entity_extractor.extract_entities("test text")
        
        assert "LLM service unavailable" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_entities_malformed_response(self, entity_extractor, llm_manager):
        """Test handling of malformed LLM response"""
        # Setup malformed response
        llm_manager.generate_response.return_value = {
            "invalid_format": "missing required fields"
        }
        
        result = await entity_extractor.extract_entities("test text")
        
        # Should handle gracefully with empty entities
        assert "entities" in result
        assert "confidence" in result
        assert isinstance(result["entities"], dict)
        assert result["confidence"] < 0.5

    @pytest.mark.unit
    def test_validation_patterns_management(self, entity_extractor):
        """Test management of validation patterns"""
        # Test setting patterns
        patterns = [r'^[A-Z]-\d{3}$', r'^[A-Z]\d{3}$']
        entity_extractor.set_validation_patterns("vehicle_id", patterns)
        
        stored_patterns = entity_extractor.get_validation_patterns("vehicle_id")
        assert stored_patterns == patterns
        
        # Test pattern validation
        assert entity_extractor.validate_entity("vehicle_id", "F-123") == True
        assert entity_extractor.validate_entity("vehicle_id", "F123") == True
        assert entity_extractor.validate_entity("vehicle_id", "INVALID") == False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_entity_confidence_scoring(self, entity_extractor, llm_manager):
        """Test individual entity confidence scoring"""
        llm_manager.generate_response.return_value = {
            "entities": {
                "vehicle_id": "F-123",
                "date": "tomorrow",
                "uncertain_field": "maybe_value"
            },
            "confidence": 0.80,
            "entity_scores": {
                "vehicle_id": 0.95,
                "date": 0.85,
                "uncertain_field": 0.40
            }
        }
        
        text = "Schedule F-123 maybe tomorrow for uncertain_field maybe_value"
        result = await entity_extractor.extract_entities(text, include_scores=True)
        
        assert "entity_scores" in result
        assert result["entity_scores"]["vehicle_id"] == 0.95
        assert result["entity_scores"]["date"] == 0.85
        assert result["entity_scores"]["uncertain_field"] == 0.40

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_sample_commands(self, entity_extractor, llm_manager):
        """Test entity extraction on sample commands"""
        for sample in SAMPLE_COMMANDS[:3]:  # Test first 3 samples
            # Setup mock response based on expected entities
            llm_manager.generate_response.return_value = {
                "entities": sample["expected_entities"],
                "confidence": sample["expected_confidence"]
            }
            
            result = await entity_extractor.extract_entities(
                sample["text"], 
                intent=sample["expected_intent"]
            )
            
            # Verify expected entities are extracted
            for key, expected_value in sample["expected_entities"].items():
                assert result["entities"][key] == expected_value
            
            assert result["confidence"] >= 0.7  # Minimum acceptable confidence

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_entity_extraction_performance(self, entity_extractor, llm_manager, performance_monitor):
        """Test performance benchmarks for entity extraction"""
        llm_manager.generate_response.return_value = {
            "entities": {"vehicle_id": "F-123", "date": "tomorrow"},
            "confidence": 0.88
        }
        
        performance_monitor.start()
        
        # Extract entities from multiple texts
        tasks = [
            entity_extractor.extract_entities(f"Test extraction {i}")
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
        
        metrics = performance_monitor.stop()
        
        # Verify all extractions completed
        assert len(results) == 10
        for result in results:
            assert "entities" in result
            assert "confidence" in result
        
        # Check performance metrics
        avg_response_time = metrics['duration'] / len(results) * 1000  # ms per extraction
        assert avg_response_time < 400  # Should be under 400ms per extraction

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_entity_type_classification(self, entity_extractor, llm_manager):
        """Test classification of entity types"""
        llm_manager.generate_response.return_value = {
            "entities": {
                "vehicle_id": "F-123",
                "email": "user@company.com",
                "date": "2024-03-15",
                "amount": "$150.50"
            },
            "confidence": 0.90,
            "entity_types": {
                "vehicle_id": "identifier",
                "email": "contact",
                "date": "temporal",
                "amount": "monetary"
            }
        }
        
        text = "Reserve F-123 for user@company.com on 2024-03-15 costing $150.50"
        result = await entity_extractor.extract_entities(text, classify_types=True)
        
        assert "entity_types" in result
        assert result["entity_types"]["vehicle_id"] == "identifier"
        assert result["entity_types"]["email"] == "contact"
        assert result["entity_types"]["date"] == "temporal"
        assert result["entity_types"]["amount"] == "monetary"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_nested_entity_extraction(self, entity_extractor, llm_manager):
        """Test extraction of nested and compound entities"""
        llm_manager.generate_response.return_value = {
            "entities": {
                "reservation": {
                    "vehicle_id": "V-456",
                    "start_time": "2024-03-15T14:00:00",
                    "end_time": "2024-03-15T17:00:00",
                    "requestor": {
                        "name": "John Doe",
                        "email": "john.doe@company.com",
                        "department": "Sales"
                    }
                }
            },
            "confidence": 0.87
        }
        
        text = "Reserve vehicle V-456 from 2pm to 5pm on March 15th for John Doe from Sales (john.doe@company.com)"
        result = await entity_extractor.extract_entities(text, extract_nested=True)
        
        reservation = result["entities"]["reservation"]
        assert reservation["vehicle_id"] == "V-456"
        assert reservation["requestor"]["name"] == "John Doe"
        assert reservation["requestor"]["email"] == "john.doe@company.com"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_entity_normalization(self, entity_extractor, llm_manager):
        """Test normalization of extracted entities"""
        llm_manager.generate_response.return_value = {
            "entities": {
                "date": "tomorrow",
                "time": "10am", 
                "vehicle_id": "f-123",  # lowercase
                "email": "JOHN.DOE@COMPANY.COM"  # uppercase
            },
            "confidence": 0.85
        }
        
        text = "Schedule f-123 tomorrow at 10am for JOHN.DOE@COMPANY.COM"
        result = await entity_extractor.extract_entities(text, normalize=True)
        
        entities = result["entities"]
        # Check normalized values
        assert entities["vehicle_id"] == "F-123"  # Normalized to uppercase
        assert entities["email"] == "john.doe@company.com"  # Normalized to lowercase
        # Date and time should be normalized to standard formats
        assert entities["date"] != "tomorrow"  # Should be converted to actual date
        assert ":" in entities["time"]  # Should be in HH:MM format

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_entity_relationship_extraction(self, entity_extractor, llm_manager):
        """Test extraction of relationships between entities"""
        llm_manager.generate_response.return_value = {
            "entities": {
                "vehicle_id": "F-123",
                "driver": "John Doe",
                "location": "Building A"
            },
            "relationships": [
                {"type": "assigned_to", "from": "vehicle_id", "to": "driver"},
                {"type": "located_at", "from": "vehicle_id", "to": "location"}
            ],
            "confidence": 0.92
        }
        
        text = "Vehicle F-123 is assigned to driver John Doe and located at Building A"
        result = await entity_extractor.extract_entities(text, extract_relationships=True)
        
        assert "relationships" in result
        relationships = result["relationships"]
        assert len(relationships) == 2
        assert relationships[0]["type"] == "assigned_to"
        assert relationships[0]["from"] == "vehicle_id"
        assert relationships[0]["to"] == "driver"