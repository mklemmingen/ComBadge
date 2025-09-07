"""
Unit tests for the IntentClassifier component.

Tests intent classification accuracy, confidence scoring,
and error handling for the NLP intent classification system.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from combadge.intelligence.intent_classifier import IntentClassifier
from combadge.intelligence.llm_manager import LLMManager
from tests.fixtures.sample_data import SAMPLE_COMMANDS, SAMPLE_LLM_RESPONSES


class TestIntentClassifier:
    """Test suite for IntentClassifier component"""

    @pytest.fixture
    def llm_manager(self):
        """Mock LLM manager for testing"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.is_available = Mock(return_value=True)
        mock_llm.generate_response = AsyncMock()
        return mock_llm

    @pytest.fixture
    def intent_classifier(self, llm_manager):
        """Create IntentClassifier instance with mocked dependencies"""
        return IntentClassifier(llm_manager=llm_manager)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_classify_intent_high_confidence(self, intent_classifier, llm_manager):
        """Test intent classification with high confidence response"""
        # Setup mock response
        llm_manager.generate_response.return_value = {
            "intent": "vehicle_operations",
            "confidence": 0.95,
            "reasoning": ["Clear vehicle operation request", "Specific vehicle ID mentioned"]
        }
        
        # Test classification
        text = "Schedule maintenance for vehicle F-123 tomorrow"
        result = await intent_classifier.classify_intent(text)
        
        # Verify results
        assert result["intent"] == "vehicle_operations"
        assert result["confidence"] == 0.95
        assert "reasoning" in result
        
        # Verify LLM was called correctly
        llm_manager.generate_response.assert_called_once()
        call_args = llm_manager.generate_response.call_args[0]
        assert "classify" in call_args[0].lower()
        assert text in call_args[0]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_classify_intent_low_confidence(self, intent_classifier, llm_manager):
        """Test intent classification with low confidence response"""
        # Setup mock response for ambiguous input
        llm_manager.generate_response.return_value = {
            "intent": "unknown",
            "confidence": 0.30,
            "reasoning": ["Unclear request", "Multiple possible interpretations"]
        }
        
        text = "Something about the thing"
        result = await intent_classifier.classify_intent(text)
        
        assert result["intent"] == "unknown"
        assert result["confidence"] == 0.30
        assert result["confidence"] < intent_classifier.confidence_threshold

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_classify_intent_with_context(self, intent_classifier, llm_manager):
        """Test intent classification with additional context"""
        llm_manager.generate_response.return_value = {
            "intent": "maintenance_scheduling",
            "confidence": 0.88,
            "reasoning": ["Maintenance context provided", "Vehicle and timing specified"]
        }
        
        text = "Schedule service"
        context = {"previous_vehicle": "F-123", "conversation_history": ["discussing vehicle F-123"]}
        
        result = await intent_classifier.classify_intent(text, context=context)
        
        assert result["intent"] == "maintenance_scheduling"
        assert result["confidence"] == 0.88
        
        # Verify context was passed to LLM
        call_args = llm_manager.generate_response.call_args[0]
        assert "F-123" in call_args[0] or "context" in call_args[0].lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_classify_multiple_samples(self, intent_classifier, llm_manager):
        """Test classification accuracy across multiple sample commands"""
        for sample in SAMPLE_COMMANDS[:3]:  # Test first 3 samples
            # Setup mock response based on expected intent
            llm_manager.generate_response.return_value = {
                "intent": sample["expected_intent"],
                "confidence": sample["expected_confidence"],
                "reasoning": [f"Classified as {sample['expected_intent']}"]
            }
            
            result = await intent_classifier.classify_intent(sample["text"])
            
            assert result["intent"] == sample["expected_intent"]
            assert result["confidence"] >= 0.8  # Minimum acceptable confidence

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_classify_intent_llm_error(self, intent_classifier, llm_manager):
        """Test error handling when LLM fails"""
        # Setup LLM to raise exception
        llm_manager.generate_response.side_effect = Exception("LLM service unavailable")
        
        with pytest.raises(Exception) as exc_info:
            await intent_classifier.classify_intent("test text")
        
        assert "LLM service unavailable" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_classify_intent_invalid_response(self, intent_classifier, llm_manager):
        """Test handling of malformed LLM response"""
        # Setup invalid response format
        llm_manager.generate_response.return_value = {
            "invalid_field": "invalid_value"
            # Missing required fields: intent, confidence
        }
        
        result = await intent_classifier.classify_intent("test text")
        
        # Should handle gracefully with fallback
        assert "intent" in result
        assert "confidence" in result
        assert result["confidence"] < 0.5  # Low confidence for invalid response

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_batch_classify_intents(self, intent_classifier, llm_manager):
        """Test batch processing of multiple texts"""
        texts = [
            "Schedule maintenance for F-123",
            "Reserve vehicle V-456", 
            "Add new Toyota Camry"
        ]
        
        expected_intents = ["maintenance_scheduling", "vehicle_reservation", "vehicle_operations"]
        
        # Setup sequential responses
        llm_manager.generate_response.side_effect = [
            {"intent": intent, "confidence": 0.9, "reasoning": [f"Classified as {intent}"]}
            for intent in expected_intents
        ]
        
        results = await intent_classifier.batch_classify(texts)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result["intent"] == expected_intents[i]
            assert result["confidence"] >= 0.8

    @pytest.mark.unit
    def test_confidence_threshold_validation(self, intent_classifier):
        """Test confidence threshold validation"""
        # Test valid thresholds
        intent_classifier.set_confidence_threshold(0.8)
        assert intent_classifier.confidence_threshold == 0.8
        
        intent_classifier.set_confidence_threshold(0.95)
        assert intent_classifier.confidence_threshold == 0.95
        
        # Test invalid thresholds
        with pytest.raises(ValueError):
            intent_classifier.set_confidence_threshold(-0.1)  # Too low
        
        with pytest.raises(ValueError):
            intent_classifier.set_confidence_threshold(1.1)   # Too high

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_classification(self, intent_classifier, llm_manager):
        """Test fallback classification when confidence is too low"""
        # Setup low confidence response
        llm_manager.generate_response.return_value = {
            "intent": "vehicle_operations",
            "confidence": 0.4,  # Below threshold
            "reasoning": ["Uncertain classification"]
        }
        
        result = await intent_classifier.classify_intent("ambiguous text")
        
        # Should trigger fallback behavior
        assert result["confidence"] < intent_classifier.confidence_threshold
        assert "fallback" in result.get("classification_method", "").lower() or result["intent"] == "unknown"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_intent_classification_performance(self, intent_classifier, llm_manager, performance_monitor):
        """Test performance benchmarks for intent classification"""
        llm_manager.generate_response.return_value = {
            "intent": "vehicle_operations",
            "confidence": 0.90,
            "reasoning": ["Performance test classification"]
        }
        
        performance_monitor.start()
        
        # Classify multiple intents
        tasks = [
            intent_classifier.classify_intent(f"Test classification {i}")
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
        
        metrics = performance_monitor.stop()
        
        # Verify all classifications completed
        assert len(results) == 10
        for result in results:
            assert "intent" in result
            assert "confidence" in result
        
        # Check performance metrics
        avg_response_time = metrics['duration'] / len(results) * 1000  # ms per classification
        assert avg_response_time < 500  # Should be under 500ms per classification

    @pytest.mark.unit
    def test_get_supported_intents(self, intent_classifier):
        """Test retrieval of supported intent types"""
        intents = intent_classifier.get_supported_intents()
        
        expected_intents = [
            "vehicle_operations",
            "maintenance_scheduling", 
            "vehicle_reservation",
            "parking_management",
            "data_query",
            "unknown"
        ]
        
        for intent in expected_intents:
            assert intent in intents

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_classification_with_metadata(self, intent_classifier, llm_manager):
        """Test intent classification with metadata tracking"""
        llm_manager.generate_response.return_value = {
            "intent": "vehicle_operations",
            "confidence": 0.85,
            "reasoning": ["Test classification with metadata"],
            "entities_mentioned": ["F-123", "maintenance"]
        }
        
        text = "Schedule maintenance for F-123"
        result = await intent_classifier.classify_intent(
            text, 
            include_metadata=True,
            user_id="test_user",
            session_id="test_session"
        )
        
        assert result["intent"] == "vehicle_operations"
        assert result["confidence"] == 0.85
        assert "metadata" in result
        assert result["metadata"]["user_id"] == "test_user"
        assert result["metadata"]["session_id"] == "test_session"
        assert result["metadata"]["input_length"] == len(text)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_intent_history_tracking(self, intent_classifier, llm_manager):
        """Test tracking of intent classification history"""
        # Setup multiple classifications
        classifications = [
            ("Schedule maintenance for F-123", "maintenance_scheduling"),
            ("Reserve vehicle V-456", "vehicle_reservation"),
            ("Show vehicle status", "data_query")
        ]
        
        for text, expected_intent in classifications:
            llm_manager.generate_response.return_value = {
                "intent": expected_intent,
                "confidence": 0.9,
                "reasoning": [f"Classified as {expected_intent}"]
            }
            
            await intent_classifier.classify_intent(text)
        
        # Check classification history
        history = intent_classifier.get_classification_history()
        
        assert len(history) == 3
        for i, (text, expected_intent) in enumerate(classifications):
            assert history[i]["text"] == text
            assert history[i]["intent"] == expected_intent
            assert "timestamp" in history[i]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_classifications(self, intent_classifier, llm_manager):
        """Test handling of concurrent classification requests"""
        # Setup consistent response
        llm_manager.generate_response.return_value = {
            "intent": "vehicle_operations", 
            "confidence": 0.88,
            "reasoning": ["Concurrent classification test"]
        }
        
        # Create multiple concurrent classification tasks
        texts = [f"Test concurrent classification {i}" for i in range(5)]
        tasks = [intent_classifier.classify_intent(text) for text in texts]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all classifications completed successfully
        assert len(results) == 5
        for result in results:
            assert result["intent"] == "vehicle_operations"
            assert result["confidence"] == 0.88
        
        # Verify LLM was called for each classification
        assert llm_manager.generate_response.call_count == 5