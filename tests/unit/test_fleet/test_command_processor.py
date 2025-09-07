"""
Unit tests for the CommandProcessor component.

Tests command processing, validation, and execution flow
for the fleet management command processing system.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta

from combadge.fleet.processors.command_processor import CommandProcessor, ProcessingResult
from combadge.intelligence.intent_classifier import IntentClassifier
from combadge.intelligence.entity_extractor import EntityExtractor
from combadge.intelligence.reasoning_engine import ReasoningEngine
from combadge.fleet.templates.template_manager import TemplateManager
from combadge.fleet.templates.validators import TemplateValidator
from tests.fixtures.sample_data import SAMPLE_COMMANDS


@dataclass
class MockProcessingContext:
    """Mock processing context for testing"""
    user_id: str = "test_user"
    session_id: str = "test_session"
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class TestCommandProcessor:
    """Test suite for CommandProcessor component"""

    @pytest.fixture
    def mock_intent_classifier(self):
        """Mock intent classifier"""
        mock = Mock(spec=IntentClassifier)
        mock.classify_intent = AsyncMock()
        return mock

    @pytest.fixture
    def mock_entity_extractor(self):
        """Mock entity extractor"""
        mock = Mock(spec=EntityExtractor)
        mock.extract_entities = AsyncMock()
        return mock

    @pytest.fixture
    def mock_reasoning_engine(self):
        """Mock reasoning engine"""
        mock = Mock(spec=ReasoningEngine)
        mock.reason_about_interpretation = AsyncMock()
        return mock

    @pytest.fixture
    def mock_template_manager(self):
        """Mock template manager"""
        mock = Mock(spec=TemplateManager)
        mock.select_template = Mock()
        mock.generate_request = AsyncMock()
        return mock

    @pytest.fixture
    def mock_validator(self):
        """Mock template validator"""
        mock = Mock(spec=TemplateValidator)
        mock.validate_request = AsyncMock()
        return mock

    @pytest.fixture
    def command_processor(self, mock_intent_classifier, mock_entity_extractor, 
                         mock_reasoning_engine, mock_template_manager, mock_validator):
        """Create CommandProcessor with mocked dependencies"""
        return CommandProcessor(
            intent_classifier=mock_intent_classifier,
            entity_extractor=mock_entity_extractor,
            reasoning_engine=mock_reasoning_engine,
            template_manager=mock_template_manager,
            validator=mock_validator
        )

    @pytest.fixture
    def processing_context(self):
        """Sample processing context"""
        return MockProcessingContext()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_successful_command_processing(self, command_processor, processing_context,
                                               mock_intent_classifier, mock_entity_extractor,
                                               mock_reasoning_engine, mock_template_manager, 
                                               mock_validator):
        """Test successful end-to-end command processing"""
        # Setup mock responses
        mock_intent_classifier.classify_intent.return_value = {
            "intent": "vehicle_operations",
            "confidence": 0.95
        }
        
        mock_entity_extractor.extract_entities.return_value = {
            "entities": {"vehicle_id": "F-123", "action": "maintenance"},
            "confidence": 0.90
        }
        
        mock_reasoning_result = Mock()
        mock_reasoning_result.recommendation = "proceed"
        mock_reasoning_result.confidence = 0.92
        mock_reasoning_result.risk_level = "low"
        mock_reasoning_engine.reason_about_interpretation.return_value = mock_reasoning_result
        
        mock_template_manager.select_template.return_value = {
            "template_id": "schedule_maintenance",
            "api_endpoint": "/api/maintenance",
            "method": "POST"
        }
        
        mock_template_manager.generate_request.return_value = {
            "vehicle_id": "F-123",
            "maintenance_type": "routine",
            "scheduled_date": "2024-03-16"
        }
        
        mock_validator.validate_request.return_value = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Process command
        command = "Schedule maintenance for vehicle F-123"
        result = await command_processor.process_command(command, processing_context)
        
        # Verify successful processing
        assert result.success is True
        assert result.intent == "vehicle_operations"
        assert result.confidence >= 0.85
        assert result.entities["vehicle_id"] == "F-123"
        assert result.api_request["vehicle_id"] == "F-123"
        assert result.recommendation == "proceed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_low_confidence_processing(self, command_processor, processing_context,
                                           mock_intent_classifier, mock_entity_extractor,
                                           mock_reasoning_engine):
        """Test processing of low confidence interpretations"""
        # Setup low confidence responses
        mock_intent_classifier.classify_intent.return_value = {
            "intent": "unknown",
            "confidence": 0.30
        }
        
        mock_entity_extractor.extract_entities.return_value = {
            "entities": {},
            "confidence": 0.25
        }
        
        mock_reasoning_result = Mock()
        mock_reasoning_result.recommendation = "request_clarification"
        mock_reasoning_result.confidence = 0.20
        mock_reasoning_result.clarification_questions = ["What specific vehicle do you mean?"]
        mock_reasoning_engine.reason_about_interpretation.return_value = mock_reasoning_result
        
        # Process ambiguous command
        command = "Do something with that vehicle"
        result = await command_processor.process_command(command, processing_context)
        
        # Verify low confidence handling
        assert result.success is False
        assert result.confidence < 0.5
        assert result.recommendation == "request_clarification"
        assert len(result.clarification_questions) > 0
        assert result.needs_clarification is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_high_risk_command_processing(self, command_processor, processing_context,
                                              mock_intent_classifier, mock_entity_extractor,
                                              mock_reasoning_engine, mock_template_manager):
        """Test processing of high-risk commands"""
        # Setup high-risk scenario
        mock_intent_classifier.classify_intent.return_value = {
            "intent": "vehicle_operations",
            "confidence": 0.85
        }
        
        mock_entity_extractor.extract_entities.return_value = {
            "entities": {"action": "delete", "target": "all_vehicles"},
            "confidence": 0.80
        }
        
        mock_reasoning_result = Mock()
        mock_reasoning_result.recommendation = "require_approval"
        mock_reasoning_result.confidence = 0.40  # Lower confidence due to risk
        mock_reasoning_result.risk_level = "high"
        mock_reasoning_result.concerns = ["destructive_operation", "bulk_action"]
        mock_reasoning_engine.reason_about_interpretation.return_value = mock_reasoning_result
        
        # Process high-risk command
        command = "Delete all vehicles from the fleet"
        result = await command_processor.process_command(command, processing_context)
        
        # Verify high-risk handling
        assert result.risk_level == "high"
        assert result.recommendation == "require_approval"
        assert "destructive_operation" in result.risk_factors
        assert result.requires_approval is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validation_failure_processing(self, command_processor, processing_context,
                                                mock_intent_classifier, mock_entity_extractor,
                                                mock_reasoning_engine, mock_template_manager,
                                                mock_validator):
        """Test processing when validation fails"""
        # Setup normal classification and extraction
        mock_intent_classifier.classify_intent.return_value = {
            "intent": "vehicle_reservation",
            "confidence": 0.90
        }
        
        mock_entity_extractor.extract_entities.return_value = {
            "entities": {
                "vehicle_id": "F-123",
                "start_time": "2024-03-15T14:00:00",
                "end_time": "2024-03-15T10:00:00"  # End before start!
            },
            "confidence": 0.85
        }
        
        mock_reasoning_result = Mock()
        mock_reasoning_result.recommendation = "proceed"
        mock_reasoning_result.confidence = 0.88
        mock_reasoning_engine.reason_about_interpretation.return_value = mock_reasoning_result
        
        mock_template_manager.select_template.return_value = {
            "template_id": "reserve_vehicle",
            "api_endpoint": "/api/reservations"
        }
        
        mock_template_manager.generate_request.return_value = {
            "vehicle_id": "F-123",
            "start_time": "2024-03-15T14:00:00",
            "end_time": "2024-03-15T10:00:00"
        }
        
        # Setup validation failure
        mock_validator.validate_request.return_value = {
            "is_valid": False,
            "errors": ["End time cannot be before start time"],
            "warnings": []
        }
        
        # Process command
        command = "Reserve F-123 from 2pm to 10am"
        result = await command_processor.process_command(command, processing_context)
        
        # Verify validation failure handling
        assert result.success is False
        assert result.is_valid is False
        assert "End time cannot be before start time" in result.validation_errors
        assert result.recommendation in ["reject", "request_correction"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_template_generation_failure(self, command_processor, processing_context,
                                             mock_intent_classifier, mock_entity_extractor,
                                             mock_reasoning_engine, mock_template_manager):
        """Test handling when template generation fails"""
        # Setup successful classification
        mock_intent_classifier.classify_intent.return_value = {
            "intent": "vehicle_operations",
            "confidence": 0.90
        }
        
        mock_entity_extractor.extract_entities.return_value = {
            "entities": {"vehicle_id": "F-123"},
            "confidence": 0.85
        }
        
        mock_reasoning_result = Mock()
        mock_reasoning_result.recommendation = "proceed"
        mock_reasoning_result.confidence = 0.88
        mock_reasoning_engine.reason_about_interpretation.return_value = mock_reasoning_result
        
        # Template selection fails
        mock_template_manager.select_template.return_value = None
        
        # Process command
        command = "Perform unknown operation on F-123"
        result = await command_processor.process_command(command, processing_context)
        
        # Verify template failure handling
        assert result.success is False
        assert result.error_type == "template_not_found"
        assert "template" in result.error_message.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_batch_command_processing(self, command_processor, processing_context,
                                          mock_intent_classifier, mock_entity_extractor,
                                          mock_reasoning_engine, mock_template_manager,
                                          mock_validator):
        """Test batch processing of multiple commands"""
        commands = [
            "Schedule maintenance for F-123",
            "Reserve vehicle V-456",
            "Add Toyota Camry to fleet"
        ]
        
        # Setup mock responses for each command
        mock_intent_classifier.classify_intent.side_effect = [
            {"intent": "maintenance_scheduling", "confidence": 0.95},
            {"intent": "vehicle_reservation", "confidence": 0.90},
            {"intent": "vehicle_operations", "confidence": 0.85}
        ]
        
        mock_entity_extractor.extract_entities.side_effect = [
            {"entities": {"vehicle_id": "F-123"}, "confidence": 0.90},
            {"entities": {"vehicle_id": "V-456"}, "confidence": 0.85},
            {"entities": {"make": "Toyota", "model": "Camry"}, "confidence": 0.80}
        ]
        
        # Setup reasoning results
        mock_reasoning_result = Mock()
        mock_reasoning_result.recommendation = "proceed"
        mock_reasoning_result.confidence = 0.90
        mock_reasoning_result.risk_level = "low"
        mock_reasoning_engine.reason_about_interpretation.return_value = mock_reasoning_result
        
        # Setup template responses
        mock_template_manager.select_template.side_effect = [
            {"template_id": "schedule_maintenance"},
            {"template_id": "reserve_vehicle"},
            {"template_id": "create_vehicle"}
        ]
        
        mock_template_manager.generate_request.side_effect = [
            {"vehicle_id": "F-123", "type": "maintenance"},
            {"vehicle_id": "V-456", "type": "reservation"},
            {"make": "Toyota", "model": "Camry"}
        ]
        
        mock_validator.validate_request.return_value = {
            "is_valid": True, "errors": [], "warnings": []
        }
        
        # Process commands in batch
        results = await command_processor.process_batch(commands, processing_context)
        
        # Verify all commands processed
        assert len(results) == 3
        for result in results:
            assert result.success is True
            assert result.confidence >= 0.8

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_context_aware_processing(self, command_processor, mock_intent_classifier,
                                          mock_entity_extractor, mock_reasoning_engine,
                                          mock_template_manager, mock_validator):
        """Test context-aware command processing"""
        # Enhanced processing context
        context = MockProcessingContext(
            user_id="fleet_manager",
            session_id="session_001"
        )
        context.conversation_history = [
            {"role": "user", "message": "I need to work on vehicle F-123"},
            {"role": "assistant", "message": "What would you like to do with F-123?"}
        ]
        context.current_vehicle = "F-123"
        context.user_permissions = ["maintenance", "reservations"]
        
        # Setup mocks to use context
        mock_intent_classifier.classify_intent.return_value = {
            "intent": "maintenance_scheduling",
            "confidence": 0.95
        }
        
        mock_entity_extractor.extract_entities.return_value = {
            "entities": {
                "vehicle_id": "F-123",  # Resolved from context
                "action": "schedule"
            },
            "confidence": 0.92
        }
        
        mock_reasoning_result = Mock()
        mock_reasoning_result.recommendation = "proceed"
        mock_reasoning_result.confidence = 0.90
        mock_reasoning_result.context_factors = ["vehicle_in_context", "user_authorized"]
        mock_reasoning_engine.reason_about_interpretation.return_value = mock_reasoning_result
        
        mock_template_manager.select_template.return_value = {"template_id": "schedule_maintenance"}
        mock_template_manager.generate_request.return_value = {"vehicle_id": "F-123"}
        mock_validator.validate_request.return_value = {"is_valid": True, "errors": []}
        
        # Process contextual command
        command = "Schedule maintenance for tomorrow"  # Vehicle ID inferred from context
        result = await command_processor.process_command(command, context)
        
        # Verify context was used
        assert result.success is True
        assert result.entities["vehicle_id"] == "F-123"
        assert "vehicle_in_context" in result.reasoning.context_factors

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, command_processor, processing_context):
        """Test error handling and recovery mechanisms"""
        # Test with completely broken dependencies
        command_processor.intent_classifier.classify_intent.side_effect = Exception("Classifier failed")
        
        command = "Test command"
        result = await command_processor.process_command(command, processing_context)
        
        # Should handle gracefully with fallback
        assert result.success is False
        assert result.error_type == "processing_error"
        assert "Classifier failed" in result.error_message

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_performance_monitoring(self, command_processor, processing_context,
                                        performance_monitor, mock_intent_classifier,
                                        mock_entity_extractor, mock_reasoning_engine,
                                        mock_template_manager, mock_validator):
        """Test performance monitoring during command processing"""
        # Setup quick responses for performance testing
        mock_intent_classifier.classify_intent.return_value = {
            "intent": "vehicle_operations", "confidence": 0.90
        }
        mock_entity_extractor.extract_entities.return_value = {
            "entities": {"vehicle_id": "F-123"}, "confidence": 0.85
        }
        
        mock_reasoning_result = Mock()
        mock_reasoning_result.recommendation = "proceed"
        mock_reasoning_result.confidence = 0.88
        mock_reasoning_engine.reason_about_interpretation.return_value = mock_reasoning_result
        
        mock_template_manager.select_template.return_value = {"template_id": "test_template"}
        mock_template_manager.generate_request.return_value = {"test": "request"}
        mock_validator.validate_request.return_value = {"is_valid": True, "errors": []}
        
        performance_monitor.start()
        
        # Process multiple commands for performance testing
        tasks = [
            command_processor.process_command(f"Test command {i}", processing_context)
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
        
        metrics = performance_monitor.stop()
        
        # Verify all commands processed successfully
        assert len(results) == 10
        for result in results:
            assert result.success is True
        
        # Check performance metrics
        avg_processing_time = metrics['duration'] / len(results) * 1000  # ms per command
        assert avg_processing_time < 1000  # Should be under 1 second per command

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sample_commands_processing(self, command_processor, processing_context,
                                            mock_intent_classifier, mock_entity_extractor,
                                            mock_reasoning_engine, mock_template_manager,
                                            mock_validator):
        """Test processing of sample commands from test data"""
        for sample in SAMPLE_COMMANDS[:3]:  # Test first 3 samples
            # Setup mocks based on expected results
            mock_intent_classifier.classify_intent.return_value = {
                "intent": sample["expected_intent"],
                "confidence": sample["expected_confidence"]
            }
            
            mock_entity_extractor.extract_entities.return_value = {
                "entities": sample["expected_entities"],
                "confidence": sample["expected_confidence"]
            }
            
            mock_reasoning_result = Mock()
            mock_reasoning_result.recommendation = "proceed"
            mock_reasoning_result.confidence = sample["expected_confidence"]
            mock_reasoning_result.risk_level = "low"
            mock_reasoning_engine.reason_about_interpretation.return_value = mock_reasoning_result
            
            mock_template_manager.select_template.return_value = {
                "template_id": f"template_{sample['expected_intent']}"
            }
            mock_template_manager.generate_request.return_value = sample["expected_entities"]
            mock_validator.validate_request.return_value = {"is_valid": True, "errors": []}
            
            # Process sample command
            result = await command_processor.process_command(sample["text"], processing_context)
            
            # Verify processing matches expectations
            assert result.success is True
            assert result.intent == sample["expected_intent"]
            assert result.confidence >= 0.7  # Minimum acceptable confidence
            
            # Check key entities are preserved
            for key, value in sample["expected_entities"].items():
                assert result.entities[key] == value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, command_processor, processing_context,
                                       mock_intent_classifier, mock_entity_extractor,
                                       mock_reasoning_engine, mock_template_manager,
                                       mock_validator):
        """Test concurrent processing of multiple commands"""
        # Setup consistent mock responses
        mock_intent_classifier.classify_intent.return_value = {
            "intent": "vehicle_operations", "confidence": 0.90
        }
        mock_entity_extractor.extract_entities.return_value = {
            "entities": {"vehicle_id": "F-123"}, "confidence": 0.85
        }
        
        mock_reasoning_result = Mock()
        mock_reasoning_result.recommendation = "proceed"
        mock_reasoning_result.confidence = 0.88
        mock_reasoning_engine.reason_about_interpretation.return_value = mock_reasoning_result
        
        mock_template_manager.select_template.return_value = {"template_id": "test_template"}
        mock_template_manager.generate_request.return_value = {"vehicle_id": "F-123"}
        mock_validator.validate_request.return_value = {"is_valid": True, "errors": []}
        
        # Create multiple concurrent processing tasks
        commands = [f"Process vehicle command {i}" for i in range(20)]
        tasks = [
            command_processor.process_command(command, processing_context)
            for command in commands
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all commands processed successfully
        assert len(results) == 20
        for result in results:
            assert result.success is True
            assert result.entities["vehicle_id"] == "F-123"

    @pytest.mark.unit
    def test_processing_result_serialization(self):
        """Test serialization of processing results"""
        result = ProcessingResult(
            success=True,
            command="Test command",
            intent="vehicle_operations",
            entities={"vehicle_id": "F-123"},
            confidence=0.90,
            api_request={"vehicle_id": "F-123", "action": "maintenance"},
            recommendation="proceed"
        )
        
        # Test serialization to dictionary
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["intent"] == "vehicle_operations"
        assert result_dict["entities"]["vehicle_id"] == "F-123"
        assert result_dict["confidence"] == 0.90
        
        # Test deserialization
        restored_result = ProcessingResult.from_dict(result_dict)
        
        assert restored_result.success == result.success
        assert restored_result.intent == result.intent
        assert restored_result.entities == result.entities