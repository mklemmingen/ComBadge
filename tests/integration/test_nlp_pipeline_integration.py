"""
Integration tests for NLP pipeline components.

Tests the complete natural language processing pipeline from intent
classification through entity extraction to reasoning and decision making.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from combadge.intelligence.intent_classifier import IntentClassifier
from combadge.intelligence.entity_extractor import EntityExtractor
from combadge.intelligence.reasoning_engine import ReasoningEngine, ReasoningResult
from combadge.intelligence.llm_manager import LLMManager
from tests.fixtures.sample_data import SAMPLE_COMMANDS, SAMPLE_LLM_RESPONSES


class TestNLPPipelineIntegration:
    """Integration tests for complete NLP pipeline"""

    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM manager with realistic responses"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.is_available = Mock(return_value=True)
        mock_llm.generate_response = AsyncMock()
        return mock_llm

    @pytest.fixture
    def integrated_nlp_pipeline(self, mock_llm_manager):
        """Create integrated NLP pipeline with all components"""
        intent_classifier = IntentClassifier(llm_manager=mock_llm_manager)
        entity_extractor = EntityExtractor(llm_manager=mock_llm_manager)
        reasoning_engine = ReasoningEngine(llm_manager=mock_llm_manager)
        
        return {
            "llm_manager": mock_llm_manager,
            "intent_classifier": intent_classifier,
            "entity_extractor": entity_extractor,
            "reasoning_engine": reasoning_engine
        }

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_nlp_pipeline_flow(self, integrated_nlp_pipeline):
        """Test complete NLP pipeline from text to final decision"""
        components = integrated_nlp_pipeline
        
        # Setup realistic LLM responses for each pipeline stage
        components["llm_manager"].generate_response.side_effect = [
            # Intent classification response
            {
                "intent": "maintenance_scheduling",
                "confidence": 0.94,
                "reasoning": [
                    "User mentions 'schedule maintenance'",
                    "Vehicle ID F-123 is clearly specified",
                    "Time reference 'tomorrow' indicates scheduling"
                ],
                "alternative_intents": [
                    {"intent": "vehicle_operations", "confidence": 0.15}
                ]
            },
            # Entity extraction response
            {
                "entities": {
                    "vehicle_id": "F-123",
                    "date": "tomorrow",
                    "time": "10:00 AM",
                    "maintenance_type": "routine",
                    "urgency": "normal"
                },
                "confidence": 0.91,
                "entity_scores": {
                    "vehicle_id": 0.98,
                    "date": 0.85,
                    "time": 0.90,
                    "maintenance_type": 0.88,
                    "urgency": 0.75
                }
            },
            # Chain of thought reasoning response
            {
                "reasoning_steps": [
                    "User requests maintenance scheduling for vehicle F-123",
                    "Date specified as 'tomorrow' which is valid future date",
                    "Time specified as 10:00 AM which is within business hours",
                    "Maintenance type is routine, which is standard operation",
                    "All required information is present and valid",
                    "No conflicting information detected",
                    "Request appears legitimate and safe to proceed"
                ],
                "conclusion": "Valid maintenance scheduling request that should be processed",
                "confidence": 0.93,
                "recommendation": "proceed",
                "risk_level": "low",
                "required_validations": ["vehicle_exists", "time_slot_available"],
                "business_impact": "minimal"
            }
        ]
        
        # Input text
        user_input = "Schedule routine maintenance for vehicle F-123 tomorrow at 10:00 AM"
        
        # Step 1: Intent Classification
        intent_result = await components["intent_classifier"].classify_intent(user_input)
        
        assert intent_result["intent"] == "maintenance_scheduling"
        assert intent_result["confidence"] == 0.94
        assert len(intent_result["reasoning"]) > 0
        
        # Step 2: Entity Extraction (using intent context)
        entity_result = await components["entity_extractor"].extract_entities(
            user_input, 
            intent=intent_result["intent"]
        )
        
        assert entity_result["entities"]["vehicle_id"] == "F-123"
        assert entity_result["entities"]["date"] == "tomorrow"
        assert entity_result["entities"]["time"] == "10:00 AM"
        assert entity_result["confidence"] == 0.91
        
        # Step 3: Chain of Thought Reasoning
        # Create interpretation object for reasoning
        interpretation = Mock()
        interpretation.intent = intent_result["intent"]
        interpretation.entities = entity_result["entities"]
        interpretation.confidence = min(intent_result["confidence"], entity_result["confidence"])
        interpretation.text = user_input
        
        reasoning_result = await components["reasoning_engine"].reason_about_interpretation(interpretation)
        
        assert reasoning_result.recommendation == "proceed"
        assert reasoning_result.confidence == 0.93
        assert reasoning_result.risk_level == "low"
        assert len(reasoning_result.reasoning_steps) == 7
        
        # Verify pipeline coherence
        assert reasoning_result.confidence >= 0.9  # High overall confidence
        assert "required_validations" in reasoning_result.__dict__ or hasattr(reasoning_result, 'required_validations')

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_with_ambiguous_input(self, integrated_nlp_pipeline):
        """Test pipeline handling of ambiguous user input"""
        components = integrated_nlp_pipeline
        
        # Setup responses for ambiguous input
        components["llm_manager"].generate_response.side_effect = [
            # Low confidence intent classification
            {
                "intent": "unknown",
                "confidence": 0.35,
                "reasoning": [
                    "Input is very unclear",
                    "Multiple possible interpretations",
                    "Not enough specific information"
                ],
                "alternative_intents": [
                    {"intent": "maintenance_scheduling", "confidence": 0.25},
                    {"intent": "vehicle_operations", "confidence": 0.20}
                ]
            },
            # Sparse entity extraction
            {
                "entities": {
                    "vehicle_reference": "the vehicle",
                    "action": "something",
                    "time_reference": "soon"
                },
                "confidence": 0.28,
                "entity_scores": {
                    "vehicle_reference": 0.30,
                    "action": 0.25,
                    "time_reference": 0.30
                }
            },
            # Reasoning recommends clarification
            {
                "reasoning_steps": [
                    "User input is highly ambiguous",
                    "No specific vehicle identified",
                    "Action requested is unclear",
                    "Timing is vague ('soon')",
                    "Insufficient information to proceed safely",
                    "High risk of misinterpretation"
                ],
                "conclusion": "Request requires clarification before proceeding",
                "confidence": 0.25,
                "recommendation": "request_clarification",
                "risk_level": "medium",
                "clarification_questions": [
                    "Which specific vehicle are you referring to?",
                    "What action would you like to take?",
                    "When exactly do you need this done?"
                ]
            }
        ]
        
        ambiguous_input = "Can you do something with the vehicle soon?"
        
        # Process through pipeline
        intent_result = await components["intent_classifier"].classify_intent(ambiguous_input)
        entity_result = await components["entity_extractor"].extract_entities(
            ambiguous_input, 
            intent=intent_result["intent"]
        )
        
        interpretation = Mock()
        interpretation.intent = intent_result["intent"]
        interpretation.entities = entity_result["entities"]
        interpretation.confidence = min(intent_result["confidence"], entity_result["confidence"])
        interpretation.text = ambiguous_input
        
        reasoning_result = await components["reasoning_engine"].reason_about_interpretation(interpretation)
        
        # Verify ambiguous input handling
        assert intent_result["confidence"] < 0.5
        assert entity_result["confidence"] < 0.5
        assert reasoning_result.recommendation == "request_clarification"
        assert len(reasoning_result.clarification_questions) > 0
        assert reasoning_result.confidence < 0.5

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_confidence_propagation(self, integrated_nlp_pipeline):
        """Test how confidence scores propagate through the pipeline"""
        components = integrated_nlp_pipeline
        
        # Setup responses with varying confidence levels
        components["llm_manager"].generate_response.side_effect = [
            # High confidence intent
            {
                "intent": "vehicle_reservation",
                "confidence": 0.96,
                "reasoning": ["Very clear reservation request"]
            },
            # Medium confidence entities
            {
                "entities": {
                    "vehicle_id": "V-456",
                    "start_time": "Friday 2pm",
                    "end_time": "Friday 5pm"
                },
                "confidence": 0.78,
                "entity_scores": {
                    "vehicle_id": 0.95,
                    "start_time": 0.70,  # Lower due to informal time format
                    "end_time": 0.70
                }
            },
            # Reasoning adjusts confidence based on analysis
            {
                "reasoning_steps": [
                    "Clear reservation intent with high confidence",
                    "Vehicle ID is well-identified",
                    "Time specifications are somewhat informal",
                    "Need to convert 'Friday 2pm' to specific datetime",
                    "Overall request is valid but needs clarification on exact times"
                ],
                "conclusion": "Valid reservation request with minor time ambiguity",
                "confidence": 0.82,  # Balanced confidence
                "recommendation": "proceed_with_clarification",
                "risk_level": "low"
            }
        ]
        
        user_input = "Reserve vehicle V-456 for Friday from 2pm to 5pm"
        
        # Track confidence through pipeline
        intent_result = await components["intent_classifier"].classify_intent(user_input)
        intent_confidence = intent_result["confidence"]
        
        entity_result = await components["entity_extractor"].extract_entities(
            user_input, 
            intent=intent_result["intent"]
        )
        entity_confidence = entity_result["confidence"]
        
        interpretation = Mock()
        interpretation.intent = intent_result["intent"]
        interpretation.entities = entity_result["entities"]
        interpretation.confidence = min(intent_confidence, entity_confidence)
        interpretation.text = user_input
        
        reasoning_result = await components["reasoning_engine"].reason_about_interpretation(interpretation)
        final_confidence = reasoning_result.confidence
        
        # Verify confidence progression
        assert intent_confidence == 0.96  # High initial confidence
        assert entity_confidence == 0.78   # Reduced by entity ambiguity
        assert 0.75 <= final_confidence <= 0.85  # Reasoning balances factors
        
        # Lower confidence should trigger different handling
        if final_confidence < 0.85:
            assert "clarification" in reasoning_result.recommendation.lower()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_context_awareness(self, integrated_nlp_pipeline):
        """Test pipeline's use of contextual information"""
        components = integrated_nlp_pipeline
        
        # Setup context-aware responses
        components["llm_manager"].generate_response.side_effect = [
            # Context-enhanced intent classification
            {
                "intent": "maintenance_scheduling",
                "confidence": 0.92,
                "reasoning": [
                    "Previous conversation about vehicle F-123",
                    "Context suggests maintenance follow-up",
                    "User has maintenance permissions"
                ],
                "context_factors": ["previous_vehicle", "user_role", "conversation_history"]
            },
            # Context-enhanced entity extraction
            {
                "entities": {
                    "vehicle_id": "F-123",  # Inferred from context
                    "date": "tomorrow",
                    "maintenance_type": "follow_up"
                },
                "confidence": 0.89,
                "context_resolution": {
                    "vehicle_id": "resolved_from_conversation_context"
                }
            },
            # Context-aware reasoning
            {
                "reasoning_steps": [
                    "Previous conversation established focus on vehicle F-123",
                    "User has shown understanding of maintenance procedures",
                    "Follow-up maintenance is consistent with previous discussion",
                    "Context supports the interpretation"
                ],
                "conclusion": "Contextually appropriate maintenance request",
                "confidence": 0.91,
                "recommendation": "proceed",
                "risk_level": "low",
                "context_validation": "passed"
            }
        ]
        
        # Context information
        context = {
            "conversation_history": [
                {"role": "user", "message": "What's the status of vehicle F-123?"},
                {"role": "assistant", "message": "Vehicle F-123 needs maintenance soon."}
            ],
            "current_vehicle": "F-123",
            "user_role": "fleet_manager",
            "session_id": "session_001"
        }
        
        contextual_input = "Schedule the follow-up maintenance for tomorrow"
        
        # Process with context
        intent_result = await components["intent_classifier"].classify_intent(
            contextual_input, 
            context=context
        )
        
        entity_result = await components["entity_extractor"].extract_entities(
            contextual_input,
            intent=intent_result["intent"],
            context=context
        )
        
        interpretation = Mock()
        interpretation.intent = intent_result["intent"]
        interpretation.entities = entity_result["entities"]
        interpretation.confidence = min(intent_result["confidence"], entity_result["confidence"])
        interpretation.text = contextual_input
        
        reasoning_result = await components["reasoning_engine"].reason_about_interpretation(
            interpretation,
            context=context
        )
        
        # Verify context was utilized
        assert entity_result["entities"]["vehicle_id"] == "F-123"  # Resolved from context
        assert "context_factors" in intent_result or "previous_vehicle" in str(intent_result)
        assert reasoning_result.confidence > 0.85  # Context should boost confidence

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_error_recovery(self, integrated_nlp_pipeline):
        """Test pipeline error handling and recovery"""
        components = integrated_nlp_pipeline
        
        # Setup partial failure scenario
        def mock_response_with_failure(prompt, context=None):
            if "classify" in prompt.lower():
                return {
                    "intent": "vehicle_operations",
                    "confidence": 0.88
                }
            elif "extract" in prompt.lower():
                # Simulate extraction failure
                raise Exception("Entity extraction service temporarily unavailable")
            else:
                return {
                    "reasoning_steps": ["Fallback reasoning"],
                    "conclusion": "Unable to complete full analysis",
                    "confidence": 0.40,
                    "recommendation": "manual_review",
                    "risk_level": "medium"
                }
        
        components["llm_manager"].generate_response.side_effect = mock_response_with_failure
        
        user_input = "Test input for error recovery"
        
        # Process through pipeline with error handling
        try:
            intent_result = await components["intent_classifier"].classify_intent(user_input)
            assert intent_result["intent"] == "vehicle_operations"
            
            # This should fail
            with pytest.raises(Exception) as exc_info:
                await components["entity_extractor"].extract_entities(user_input)
            
            assert "temporarily unavailable" in str(exc_info.value)
            
            # Reasoning should still work with partial information
            interpretation = Mock()
            interpretation.intent = intent_result["intent"]
            interpretation.entities = {}  # Empty due to extraction failure
            interpretation.confidence = 0.40  # Reduced due to missing information
            interpretation.text = user_input
            
            reasoning_result = await components["reasoning_engine"].reason_about_interpretation(interpretation)
            
            # Should recommend manual review due to incomplete processing
            assert reasoning_result.recommendation == "manual_review"
            assert reasoning_result.confidence < 0.5
            
        except Exception as e:
            # Alternative: test graceful degradation
            assert "unavailable" in str(e)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_batch_processing(self, integrated_nlp_pipeline):
        """Test pipeline batch processing capabilities"""
        components = integrated_nlp_pipeline
        
        # Setup consistent responses for batch processing
        def batch_response(prompt, context=None):
            if "classify" in prompt.lower():
                return {
                    "intent": "maintenance_scheduling",
                    "confidence": 0.88
                }
            elif "extract" in prompt.lower():
                return {
                    "entities": {"vehicle_id": "F-123", "action": "maintenance"},
                    "confidence": 0.85
                }
            else:
                return {
                    "reasoning_steps": ["Standard maintenance request"],
                    "conclusion": "Proceed with maintenance",
                    "confidence": 0.86,
                    "recommendation": "proceed",
                    "risk_level": "low"
                }
        
        components["llm_manager"].generate_response.side_effect = batch_response
        
        # Batch of user inputs
        user_inputs = [
            "Schedule maintenance for F-123",
            "Service vehicle V-456 tomorrow",
            "Check oil levels for T-789",
            "Inspect brakes on F-456",
            "Replace filters for V-123"
        ]
        
        # Process all inputs through pipeline
        results = []
        for user_input in user_inputs:
            intent_result = await components["intent_classifier"].classify_intent(user_input)
            entity_result = await components["entity_extractor"].extract_entities(
                user_input, 
                intent=intent_result["intent"]
            )
            
            interpretation = Mock()
            interpretation.intent = intent_result["intent"]
            interpretation.entities = entity_result["entities"]
            interpretation.confidence = min(intent_result["confidence"], entity_result["confidence"])
            interpretation.text = user_input
            
            reasoning_result = await components["reasoning_engine"].reason_about_interpretation(interpretation)
            
            results.append({
                "input": user_input,
                "intent": intent_result,
                "entities": entity_result,
                "reasoning": reasoning_result
            })
        
        # Verify all processed successfully
        assert len(results) == 5
        for result in results:
            assert result["intent"]["intent"] == "maintenance_scheduling"
            assert result["entities"]["confidence"] >= 0.8
            assert result["reasoning"].recommendation == "proceed"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_performance_under_load(self, integrated_nlp_pipeline, performance_monitor):
        """Test pipeline performance under concurrent load"""
        components = integrated_nlp_pipeline
        
        # Setup fast responses for performance testing
        components["llm_manager"].generate_response.return_value = {
            "intent": "maintenance_scheduling",
            "confidence": 0.90,
            "entities": {"vehicle_id": "F-123"},
            "reasoning_steps": ["Performance test"],
            "conclusion": "Test conclusion",
            "recommendation": "proceed"
        }
        
        performance_monitor.start()
        
        # Create concurrent processing tasks
        async def process_single_request(text):
            intent_result = await components["intent_classifier"].classify_intent(text)
            entity_result = await components["entity_extractor"].extract_entities(
                text, 
                intent=intent_result["intent"]
            )
            
            interpretation = Mock()
            interpretation.intent = intent_result["intent"]
            interpretation.entities = entity_result["entities"]
            interpretation.confidence = 0.90
            interpretation.text = text
            
            reasoning_result = await components["reasoning_engine"].reason_about_interpretation(interpretation)
            return reasoning_result
        
        # Process 20 concurrent requests
        tasks = [
            process_single_request(f"Performance test request {i}")
            for i in range(20)
        ]
        
        results = await asyncio.gather(*tasks)
        
        metrics = performance_monitor.stop()
        
        # Verify all requests completed
        assert len(results) == 20
        for result in results:
            assert result.recommendation == "proceed"
        
        # Check performance metrics
        avg_processing_time = metrics['duration'] / len(results) * 1000  # ms per request
        assert avg_processing_time < 1000  # Should be under 1 second per complete pipeline

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_with_sample_commands(self, integrated_nlp_pipeline):
        """Test pipeline with sample commands from test data"""
        components = integrated_nlp_pipeline
        
        for sample in SAMPLE_COMMANDS[:3]:  # Test first 3 samples
            # Setup responses based on expected results
            components["llm_manager"].generate_response.side_effect = [
                {
                    "intent": sample["expected_intent"],
                    "confidence": sample["expected_confidence"],
                    "reasoning": [f"Classified as {sample['expected_intent']}"]
                },
                {
                    "entities": sample["expected_entities"],
                    "confidence": sample["expected_confidence"]
                },
                {
                    "reasoning_steps": [f"Analysis of {sample['expected_intent']} request"],
                    "conclusion": f"Valid {sample['expected_intent']} request",
                    "confidence": sample["expected_confidence"],
                    "recommendation": "proceed",
                    "risk_level": "low"
                }
            ]
            
            # Process sample command
            intent_result = await components["intent_classifier"].classify_intent(sample["text"])
            entity_result = await components["entity_extractor"].extract_entities(
                sample["text"],
                intent=intent_result["intent"]
            )
            
            interpretation = Mock()
            interpretation.intent = intent_result["intent"]
            interpretation.entities = entity_result["entities"]
            interpretation.confidence = min(intent_result["confidence"], entity_result["confidence"])
            interpretation.text = sample["text"]
            
            reasoning_result = await components["reasoning_engine"].reason_about_interpretation(interpretation)
            
            # Verify results match expectations
            assert intent_result["intent"] == sample["expected_intent"]
            assert intent_result["confidence"] >= 0.8
            
            for key, expected_value in sample["expected_entities"].items():
                assert entity_result["entities"][key] == expected_value
            
            assert reasoning_result.confidence >= 0.8
            assert reasoning_result.recommendation == "proceed"