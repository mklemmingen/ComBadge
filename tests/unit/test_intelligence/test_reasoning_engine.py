"""
Unit tests for the ReasoningEngine component.

Tests chain of thought reasoning, decision making logic,
and confidence assessment for the AI reasoning system.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
from dataclasses import dataclass

from combadge.intelligence.reasoning_engine import ReasoningEngine, ReasoningStep
from combadge.intelligence.llm_manager import LLMManager
from tests.fixtures.sample_data import SAMPLE_COMMANDS, SAMPLE_LLM_RESPONSES


@dataclass
class MockInterpretation:
    """Mock interpretation for testing"""
    intent: str
    entities: Dict[str, Any]
    confidence: float
    text: str


class TestReasoningEngine:
    """Test suite for ReasoningEngine component"""

    @pytest.fixture
    def llm_manager(self):
        """Mock LLM manager for testing"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.is_available = Mock(return_value=True)
        mock_llm.generate_response = AsyncMock()
        return mock_llm

    @pytest.fixture
    def reasoning_engine(self, llm_manager):
        """Create ReasoningEngine instance with mocked dependencies"""
        return ReasoningEngine(llm_manager=llm_manager)

    @pytest.fixture
    def sample_interpretation(self):
        """Sample interpretation for testing"""
        return MockInterpretation(
            intent="vehicle_operations",
            entities={"vehicle_id": "F-123", "action": "maintenance"},
            confidence=0.85,
            text="Schedule maintenance for vehicle F-123"
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_basic_reasoning_flow(self, reasoning_engine, llm_manager, sample_interpretation):
        """Test basic chain of thought reasoning flow"""
        # Setup mock reasoning response
        llm_manager.generate_response.return_value = {
            "reasoning_steps": [
                "User wants to perform vehicle operation",
                "Vehicle ID F-123 identified",
                "Action appears to be maintenance scheduling",
                "All required information seems present"
            ],
            "conclusion": "Schedule maintenance for vehicle F-123",
            "confidence": 0.92,
            "recommendation": "proceed",
            "risk_level": "low"
        }
        
        result = await reasoning_engine.reason_about_interpretation(sample_interpretation)
        
        assert len(result.reasoning_steps) == 4
        assert result.conclusion == "Schedule maintenance for vehicle F-123"
        assert result.confidence == 0.92
        assert result.recommendation == "proceed"
        assert result.risk_level == "low"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_high_risk_scenario_reasoning(self, reasoning_engine, llm_manager):
        """Test reasoning for high-risk scenarios"""
        high_risk_interpretation = MockInterpretation(
            intent="vehicle_operations",
            entities={"action": "delete", "vehicle_id": "ALL"},
            confidence=0.60,
            text="Delete all vehicles from the fleet"
        )
        
        llm_manager.generate_response.return_value = {
            "reasoning_steps": [
                "User is requesting to delete ALL vehicles",
                "This is a potentially destructive operation",
                "Low confidence in interpretation (0.6)",
                "High risk of unintended consequences",
                "Should require manual approval"
            ],
            "conclusion": "Bulk deletion request with high risk",
            "confidence": 0.30,  # Lower confidence due to risk
            "recommendation": "require_approval",
            "risk_level": "high",
            "concerns": ["destructive_operation", "low_interpretation_confidence", "bulk_action"]
        }
        
        result = await reasoning_engine.reason_about_interpretation(high_risk_interpretation)
        
        assert result.risk_level == "high"
        assert result.recommendation == "require_approval"
        assert result.confidence < 0.5
        assert "destructive_operation" in result.concerns

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ambiguous_request_reasoning(self, reasoning_engine, llm_manager):
        """Test reasoning for ambiguous or unclear requests"""
        ambiguous_interpretation = MockInterpretation(
            intent="unknown",
            entities={"vehicle_reference": "that one", "action": "fix"},
            confidence=0.40,
            text="Fix that one please"
        )
        
        llm_manager.generate_response.return_value = {
            "reasoning_steps": [
                "Request is very ambiguous",
                "Vehicle reference 'that one' is unclear",
                "Action 'fix' is not specific",
                "Low confidence in interpretation",
                "Need clarification from user"
            ],
            "conclusion": "Request requires clarification",
            "confidence": 0.25,
            "recommendation": "request_clarification",
            "risk_level": "medium",
            "clarification_questions": [
                "Which specific vehicle do you mean?",
                "What type of issue needs to be fixed?",
                "When should this be done?"
            ]
        }
        
        result = await reasoning_engine.reason_about_interpretation(ambiguous_interpretation)
        
        assert result.recommendation == "request_clarification"
        assert result.confidence < 0.5
        assert len(result.clarification_questions) > 0
        assert "Which specific vehicle" in result.clarification_questions[0]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_business_rule_validation_reasoning(self, reasoning_engine, llm_manager):
        """Test reasoning that includes business rule validation"""
        interpretation = MockInterpretation(
            intent="vehicle_reservation",
            entities={
                "vehicle_id": "F-123",
                "start_time": "2024-03-15T14:00:00",
                "end_time": "2024-03-15T10:00:00"  # End before start!
            },
            confidence=0.85,
            text="Reserve F-123 from 2pm to 10am"
        )
        
        llm_manager.generate_response.return_value = {
            "reasoning_steps": [
                "User wants to reserve vehicle F-123",
                "Start time is 2pm (14:00)",
                "End time is 10am (10:00) - this is before start time",
                "This violates business logic - end cannot be before start",
                "Likely error in time interpretation"
            ],
            "conclusion": "Invalid reservation due to time conflict",
            "confidence": 0.20,
            "recommendation": "reject",
            "risk_level": "low",
            "validation_errors": ["end_time_before_start_time"]
        }
        
        result = await reasoning_engine.reason_about_interpretation(interpretation)
        
        assert result.recommendation == "reject"
        assert "end_time_before_start_time" in result.validation_errors
        assert result.confidence < 0.5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_context_aware_reasoning(self, reasoning_engine, llm_manager):
        """Test reasoning that takes context into account"""
        interpretation = MockInterpretation(
            intent="maintenance_scheduling",
            entities={"vehicle_id": "F-123", "date": "tomorrow"},
            confidence=0.80,
            text="Schedule maintenance for F-123 tomorrow"
        )
        
        context = {
            "vehicle_status": {"F-123": "currently_in_service"},
            "maintenance_history": {"F-123": {"last_service": "2024-03-01"}},
            "business_hours": {"start": "08:00", "end": "17:00"},
            "current_workload": "high"
        }
        
        llm_manager.generate_response.return_value = {
            "reasoning_steps": [
                "Vehicle F-123 is currently in service",
                "Last service was recent (2024-03-01)",
                "Tomorrow falls within business hours",
                "Current workload is high - may affect scheduling",
                "Service may not be urgent given recent maintenance"
            ],
            "conclusion": "Non-urgent maintenance request during high workload",
            "confidence": 0.75,
            "recommendation": "schedule_non_priority",
            "risk_level": "low",
            "context_factors": ["vehicle_in_service", "recent_service", "high_workload"]
        }
        
        result = await reasoning_engine.reason_about_interpretation(
            interpretation, 
            context=context
        )
        
        assert result.recommendation == "schedule_non_priority"
        assert "high_workload" in result.context_factors
        assert "recent_service" in result.context_factors

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_multi_step_reasoning_complex_request(self, reasoning_engine, llm_manager):
        """Test complex multi-step reasoning for compound requests"""
        complex_interpretation = MockInterpretation(
            intent="vehicle_operations",
            entities={
                "vehicles": ["F-123", "V-456", "T-789"],
                "action": "service_rotation",
                "schedule": "weekly"
            },
            confidence=0.75,
            text="Set up weekly service rotation for vehicles F-123, V-456, and T-789"
        )
        
        llm_manager.generate_response.return_value = {
            "reasoning_steps": [
                "User wants to set up service rotation for 3 vehicles",
                "This involves creating recurring maintenance schedules",
                "Need to coordinate schedules to avoid conflicts",
                "Weekly rotation means staggered service dates",
                "Requires checking vehicle availability and service capacity",
                "Complex operation affecting multiple vehicles",
                "Should verify all vehicles exist and are serviceable"
            ],
            "conclusion": "Complex multi-vehicle service rotation setup",
            "confidence": 0.68,
            "recommendation": "proceed_with_verification",
            "risk_level": "medium",
            "required_verifications": [
                "verify_vehicle_existence",
                "check_service_capacity", 
                "validate_schedule_feasibility"
            ],
            "complexity_score": 0.8
        }
        
        result = await reasoning_engine.reason_about_interpretation(complex_interpretation)
        
        assert len(result.reasoning_steps) == 7
        assert result.complexity_score == 0.8
        assert result.recommendation == "proceed_with_verification"
        assert len(result.required_verifications) == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reasoning_error_handling(self, reasoning_engine, llm_manager):
        """Test error handling in reasoning engine"""
        # Test LLM service failure
        llm_manager.generate_response.side_effect = Exception("LLM service down")
        
        interpretation = MockInterpretation(
            intent="vehicle_operations",
            entities={"vehicle_id": "F-123"},
            confidence=0.80,
            text="Test request"
        )
        
        with pytest.raises(Exception) as exc_info:
            await reasoning_engine.reason_about_interpretation(interpretation)
        
        assert "LLM service down" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reasoning_with_malformed_response(self, reasoning_engine, llm_manager, sample_interpretation):
        """Test handling of malformed reasoning response"""
        # Setup malformed response
        llm_manager.generate_response.return_value = {
            "invalid_field": "invalid_value"
            # Missing required fields
        }
        
        result = await reasoning_engine.reason_about_interpretation(sample_interpretation)
        
        # Should provide fallback reasoning
        assert hasattr(result, 'reasoning_steps')
        assert hasattr(result, 'conclusion')
        assert hasattr(result, 'confidence')
        assert result.confidence < 0.5  # Low confidence for malformed response

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_confidence_adjustment_reasoning(self, reasoning_engine, llm_manager):
        """Test how reasoning adjusts confidence based on analysis"""
        interpretation = MockInterpretation(
            intent="vehicle_operations",
            entities={"vehicle_id": "F-123", "action": "service"},
            confidence=0.90,  # High initial confidence
            text="Service vehicle F-123"
        )
        
        # But reasoning reveals issues
        llm_manager.generate_response.return_value = {
            "reasoning_steps": [
                "High confidence interpretation initially",
                "However, 'service' is very generic",
                "Could mean maintenance, cleaning, inspection, etc.",
                "Ambiguity in action type reduces reliability"
            ],
            "conclusion": "Ambiguous service request despite high NLP confidence",
            "confidence": 0.60,  # Adjusted down due to reasoning
            "recommendation": "request_clarification",
            "risk_level": "low",
            "confidence_adjustment": -0.30
        }
        
        result = await reasoning_engine.reason_about_interpretation(interpretation)
        
        assert result.confidence == 0.60  # Adjusted down from 0.90
        assert result.confidence_adjustment == -0.30
        assert result.recommendation == "request_clarification"

    @pytest.mark.unit 
    @pytest.mark.asyncio
    async def test_batch_reasoning(self, reasoning_engine, llm_manager):
        """Test reasoning on multiple interpretations in batch"""
        interpretations = [
            MockInterpretation("vehicle_operations", {"vehicle_id": "F-123"}, 0.85, "Service F-123"),
            MockInterpretation("vehicle_reservation", {"vehicle_id": "V-456"}, 0.90, "Reserve V-456"),
            MockInterpretation("unknown", {"unclear": "request"}, 0.30, "Do something")
        ]
        
        # Setup different responses for each interpretation
        llm_manager.generate_response.side_effect = [
            {
                "reasoning_steps": ["Clear vehicle service request"],
                "conclusion": "Service vehicle F-123",
                "confidence": 0.85,
                "recommendation": "proceed"
            },
            {
                "reasoning_steps": ["Clear reservation request"],
                "conclusion": "Reserve vehicle V-456", 
                "confidence": 0.90,
                "recommendation": "proceed"
            },
            {
                "reasoning_steps": ["Unclear request", "Needs clarification"],
                "conclusion": "Ambiguous request",
                "confidence": 0.20,
                "recommendation": "request_clarification"
            }
        ]
        
        results = await reasoning_engine.batch_reason(interpretations)
        
        assert len(results) == 3
        assert results[0].recommendation == "proceed"
        assert results[1].recommendation == "proceed"
        assert results[2].recommendation == "request_clarification"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reasoning_performance_benchmarks(self, reasoning_engine, llm_manager, performance_monitor, sample_interpretation):
        """Test performance benchmarks for reasoning engine"""
        llm_manager.generate_response.return_value = {
            "reasoning_steps": ["Performance test reasoning"],
            "conclusion": "Test conclusion",
            "confidence": 0.85,
            "recommendation": "proceed"
        }
        
        performance_monitor.start()
        
        # Run multiple reasoning tasks
        tasks = [
            reasoning_engine.reason_about_interpretation(sample_interpretation)
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)
        
        metrics = performance_monitor.stop()
        
        # Verify all reasoning completed
        assert len(results) == 10
        for result in results:
            assert hasattr(result, 'reasoning_steps')
            assert hasattr(result, 'conclusion')
        
        # Check performance metrics
        avg_response_time = metrics['duration'] / len(results) * 1000  # ms per reasoning
        assert avg_response_time < 600  # Should be under 600ms per reasoning

    @pytest.mark.unit
    def test_reasoning_step_creation(self, reasoning_engine):
        """Test creation and manipulation of reasoning steps"""
        step = ReasoningStep(
            step_number=1,
            description="Analyze user request",
            evidence=["User mentioned vehicle F-123", "Action is maintenance"],
            conclusion="Vehicle maintenance request identified",
            confidence=0.85
        )
        
        assert step.step_number == 1
        assert step.description == "Analyze user request"
        assert len(step.evidence) == 2
        assert step.confidence == 0.85

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reasoning_with_domain_knowledge(self, reasoning_engine, llm_manager):
        """Test reasoning enhanced with domain-specific knowledge"""
        interpretation = MockInterpretation(
            intent="maintenance_scheduling",
            entities={"vehicle_id": "F-123", "maintenance_type": "oil_change"},
            confidence=0.85,
            text="Schedule oil change for F-123"
        )
        
        domain_knowledge = {
            "maintenance_intervals": {"oil_change": 90},  # days
            "vehicle_types": {"F-123": "truck"},
            "service_requirements": {"truck": {"oil_change": "synthetic_oil"}}
        }
        
        llm_manager.generate_response.return_value = {
            "reasoning_steps": [
                "Oil change requested for truck F-123",
                "Trucks require synthetic oil per service requirements",
                "Standard oil change interval is 90 days",
                "Need to check last service date to validate timing"
            ],
            "conclusion": "Valid oil change request with synthetic oil requirement",
            "confidence": 0.88,
            "recommendation": "proceed",
            "domain_insights": ["synthetic_oil_required", "90_day_interval"]
        }
        
        result = await reasoning_engine.reason_about_interpretation(
            interpretation, 
            domain_knowledge=domain_knowledge
        )
        
        assert result.confidence == 0.88
        assert "synthetic_oil_required" in result.domain_insights
        assert result.recommendation == "proceed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reasoning_history_tracking(self, reasoning_engine, llm_manager):
        """Test tracking of reasoning history"""
        interpretations = [
            MockInterpretation("vehicle_operations", {"vehicle_id": "F-123"}, 0.85, "Service F-123"),
            MockInterpretation("vehicle_reservation", {"vehicle_id": "V-456"}, 0.90, "Reserve V-456")
        ]
        
        # Setup responses
        llm_manager.generate_response.side_effect = [
            {"reasoning_steps": ["Service reasoning"], "conclusion": "Service F-123", "confidence": 0.85, "recommendation": "proceed"},
            {"reasoning_steps": ["Reservation reasoning"], "conclusion": "Reserve V-456", "confidence": 0.90, "recommendation": "proceed"}
        ]
        
        # Process interpretations
        for interpretation in interpretations:
            await reasoning_engine.reason_about_interpretation(interpretation)
        
        # Check reasoning history
        history = reasoning_engine.get_reasoning_history()
        
        assert len(history) == 2
        assert history[0]["conclusion"] == "Service F-123"
        assert history[1]["conclusion"] == "Reserve V-456"
        assert "timestamp" in history[0]