"""
Unit tests for the LLMManager component.

Tests LLM connection management, response generation,
streaming capabilities, and error handling.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, AsyncGenerator
import aiohttp
from aiohttp import ClientError, ClientTimeout

from combadge.intelligence.llm_manager import LLMManager, LLMConfig
from tests.fixtures.sample_data import SAMPLE_LLM_RESPONSES


class TestLLMManager:
    """Test suite for LLMManager component"""

    @pytest.fixture
    def llm_config(self):
        """Sample LLM configuration for testing"""
        return LLMConfig(
            base_url="http://localhost:11434",
            model="qwen2.5:14b",
            temperature=0.1,
            max_tokens=2048,
            timeout=30,
            streaming=False
        )

    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp session"""
        session = Mock(spec=aiohttp.ClientSession)
        session.post = AsyncMock()
        session.get = AsyncMock()
        session.close = AsyncMock()
        return session

    @pytest.fixture
    def llm_manager(self, llm_config, mock_session):
        """Create LLMManager instance with mocked dependencies"""
        manager = LLMManager(config=llm_config)
        manager._session = mock_session
        return manager

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_response_success(self, llm_manager, mock_session):
        """Test successful response generation"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "response": "This is a test response",
            "model": "qwen2.5:14b",
            "created_at": "2024-03-15T10:00:00Z"
        })
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        prompt = "What is the status of vehicle F-123?"
        result = await llm_manager.generate_response(prompt)
        
        assert result == "This is a test response"
        
        # Verify API call was made correctly
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "http://localhost:11434/api/generate" in call_args[0][0]
        
        # Check request payload
        json_data = call_args[1]["json"]
        assert json_data["model"] == "qwen2.5:14b"
        assert json_data["prompt"] == prompt
        assert json_data["temperature"] == 0.1
        assert json_data["options"]["num_predict"] == 2048

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_response_with_context(self, llm_manager, mock_session):
        """Test response generation with context"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "response": "Vehicle F-123 is scheduled for maintenance",
            "model": "qwen2.5:14b"
        })
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        prompt = "What is the status?"
        context = {"vehicle_id": "F-123", "previous_query": "maintenance schedule"}
        
        result = await llm_manager.generate_response(prompt, context=context)
        
        assert result == "Vehicle F-123 is scheduled for maintenance"
        
        # Verify context was included in the request
        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert "F-123" in json_data["prompt"] or "context" in json_data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_response_timeout(self, llm_manager, mock_session):
        """Test timeout handling"""
        # Setup timeout exception
        mock_session.post.side_effect = asyncio.TimeoutError("Request timeout")
        
        with pytest.raises(asyncio.TimeoutError):
            await llm_manager.generate_response("test prompt")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_response_http_error(self, llm_manager, mock_session):
        """Test HTTP error handling"""
        # Setup HTTP error response
        mock_response = Mock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(Exception) as exc_info:
            await llm_manager.generate_response("test prompt")
        
        assert "500" in str(exc_info.value) or "Internal Server Error" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_response_connection_error(self, llm_manager, mock_session):
        """Test connection error handling"""
        # Setup connection error
        mock_session.post.side_effect = aiohttp.ClientConnectorError(
            connection_key=None, os_error=None
        )
        
        with pytest.raises(aiohttp.ClientConnectorError):
            await llm_manager.generate_response("test prompt")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stream_response_success(self, llm_manager, mock_session):
        """Test successful streaming response"""
        # Create mock streaming response
        async def mock_stream():
            lines = [
                '{"response": "This", "done": false}\n',
                '{"response": " is", "done": false}\n', 
                '{"response": " streaming", "done": false}\n',
                '{"response": "", "done": true}\n'
            ]
            for line in lines:
                yield line.encode()
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.content.readline = AsyncMock()
        mock_response.content.readline.side_effect = [
            line.encode() for line in [
                '{"response": "This", "done": false}',
                '{"response": " is", "done": false}',
                '{"response": " streaming", "done": false}',
                '{"response": "", "done": true}',
                b''  # End of stream
            ]
        ]
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        chunks = []
        async for chunk in llm_manager.stream_response("test prompt"):
            chunks.append(chunk)
        
        assert chunks == ["This", " is", " streaming"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stream_response_error(self, llm_manager, mock_session):
        """Test streaming response error handling"""
        # Setup error response
        mock_response = Mock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Model not found")
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        chunks = []
        with pytest.raises(Exception):
            async for chunk in llm_manager.stream_response("test prompt"):
                chunks.append(chunk)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_available_success(self, llm_manager, mock_session):
        """Test LLM availability check - success"""
        # Setup successful health check
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        is_available = await llm_manager.is_available()
        
        assert is_available is True
        mock_session.get.assert_called_once_with(
            "http://localhost:11434/api/tags",
            timeout=aiohttp.ClientTimeout(total=10)
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_available_failure(self, llm_manager, mock_session):
        """Test LLM availability check - failure"""
        # Setup connection failure
        mock_session.get.side_effect = aiohttp.ClientConnectorError(
            connection_key=None, os_error=None
        )
        
        is_available = await llm_manager.is_available()
        
        assert is_available is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_models(self, llm_manager, mock_session):
        """Test listing available models"""
        # Setup models response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "models": [
                {"name": "qwen2.5:14b", "size": 8000000000},
                {"name": "llama2:7b", "size": 4000000000},
                {"name": "mistral:latest", "size": 4000000000}
            ]
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        models = await llm_manager.list_models()
        
        assert len(models) == 3
        assert "qwen2.5:14b" in models
        assert "llama2:7b" in models
        assert "mistral:latest" in models

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_batch_generate_responses(self, llm_manager, mock_session):
        """Test batch response generation"""
        prompts = [
            "What is vehicle F-123 status?",
            "Schedule maintenance for V-456",
            "Reserve T-789 for tomorrow"
        ]
        
        responses = [
            "Vehicle F-123 is available",
            "Maintenance scheduled for V-456",
            "T-789 reserved for tomorrow"
        ]
        
        # Setup sequential responses
        mock_responses = []
        for response in responses:
            mock_resp = Mock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={"response": response})
            mock_responses.append(mock_resp)
        
        mock_session.post.return_value.__aenter__.side_effect = mock_responses
        
        results = await llm_manager.batch_generate(prompts)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result == responses[i]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_with_retry_logic(self, llm_manager, mock_session):
        """Test retry logic on temporary failures"""
        # First call fails, second succeeds
        mock_responses = [
            Exception("Temporary failure"),
            Mock()
        ]
        
        success_response = Mock()
        success_response.status = 200
        success_response.json = AsyncMock(return_value={"response": "Success after retry"})
        
        mock_session.post.side_effect = [
            aiohttp.ClientError("Temporary failure"),
            success_response.__aenter__()
        ]
        
        # Configure retry settings
        llm_manager.max_retries = 2
        llm_manager.retry_delay = 0.1  # Fast retry for testing
        
        result = await llm_manager.generate_response("test prompt")
        
        assert result == "Success after retry"
        assert mock_session.post.call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_custom_model_parameters(self, llm_manager, mock_session):
        """Test custom model parameters in requests"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"response": "Custom response"})
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        custom_params = {
            "temperature": 0.8,
            "top_p": 0.9,
            "repeat_penalty": 1.1
        }
        
        result = await llm_manager.generate_response(
            "test prompt",
            **custom_params
        )
        
        assert result == "Custom response"
        
        # Check that custom parameters were included
        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["temperature"] == 0.8
        assert json_data["options"]["top_p"] == 0.9
        assert json_data["options"]["repeat_penalty"] == 1.1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_response_caching(self, llm_manager, mock_session):
        """Test response caching mechanism"""
        # Enable caching
        llm_manager.enable_caching = True
        llm_manager.cache_ttl = 300  # 5 minutes
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"response": "Cached response"})
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        prompt = "What is the status of vehicle F-123?"
        
        # First call should hit the API
        result1 = await llm_manager.generate_response(prompt)
        assert result1 == "Cached response"
        assert mock_session.post.call_count == 1
        
        # Second call should use cache
        result2 = await llm_manager.generate_response(prompt)
        assert result2 == "Cached response"
        assert mock_session.post.call_count == 1  # No additional API call

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_model_switching(self, llm_manager, mock_session):
        """Test switching between different models"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"response": "Model switched response"})
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        # Switch to different model
        await llm_manager.switch_model("llama2:7b")
        
        result = await llm_manager.generate_response("test prompt")
        
        assert result == "Model switched response"
        
        # Verify the model was switched in the request
        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["model"] == "llama2:7b"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_response_validation(self, llm_manager, mock_session):
        """Test response validation and error handling"""
        # Setup invalid response format
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "invalid_field": "no response field",
            "model": "qwen2.5:14b"
        })
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(ValueError) as exc_info:
            await llm_manager.generate_response("test prompt")
        
        assert "response" in str(exc_info.value).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_performance_monitoring(self, llm_manager, mock_session, performance_monitor):
        """Test performance monitoring for LLM requests"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"response": "Performance test response"})
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        performance_monitor.start()
        
        # Generate multiple responses
        tasks = [
            llm_manager.generate_response(f"Test prompt {i}")
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks)
        
        metrics = performance_monitor.stop()
        
        # Verify all responses completed
        assert len(results) == 5
        for result in results:
            assert result == "Performance test response"
        
        # Check performance metrics
        avg_response_time = metrics['duration'] / len(results) * 1000  # ms per request
        assert avg_response_time < 1000  # Should be under 1 second per request

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, llm_manager, mock_session):
        """Test handling of concurrent LLM requests"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"response": "Concurrent response"})
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        # Create multiple concurrent requests
        prompts = [f"Concurrent test {i}" for i in range(10)]
        tasks = [llm_manager.generate_response(prompt) for prompt in prompts]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all requests completed successfully
        assert len(results) == 10
        for result in results:
            assert result == "Concurrent response"
        
        # Verify all requests were made
        assert mock_session.post.call_count == 10

    @pytest.mark.unit
    def test_config_validation(self):
        """Test configuration validation"""
        # Test valid config
        valid_config = LLMConfig(
            base_url="http://localhost:11434",
            model="qwen2.5:14b",
            temperature=0.1,
            max_tokens=2048,
            timeout=30
        )
        manager = LLMManager(config=valid_config)
        assert manager.config.temperature == 0.1
        
        # Test invalid temperature
        with pytest.raises(ValueError):
            LLMConfig(
                base_url="http://localhost:11434",
                model="qwen2.5:14b",
                temperature=2.0,  # Too high
                max_tokens=2048,
                timeout=30
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_session_lifecycle_management(self, llm_config):
        """Test proper session lifecycle management"""
        manager = LLMManager(config=llm_config)
        
        # Test session initialization
        assert manager._session is None
        
        # Initialize session
        await manager.initialize()
        assert manager._session is not None
        
        # Test session cleanup
        await manager.cleanup()
        manager._session.close.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_request_logging_and_metrics(self, llm_manager, mock_session):
        """Test request logging and metrics collection"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"response": "Logged response"})
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        # Enable detailed logging
        llm_manager.enable_metrics = True
        
        result = await llm_manager.generate_response("test prompt")
        
        assert result == "Logged response"
        
        # Check that metrics were collected
        metrics = llm_manager.get_metrics()
        assert metrics["total_requests"] >= 1
        assert "average_response_time" in metrics
        assert "total_tokens_processed" in metrics