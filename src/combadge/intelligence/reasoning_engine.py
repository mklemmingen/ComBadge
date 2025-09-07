"""Chain of Thought Reasoning Engine

Core reasoning engine that processes natural language with structured prompts,
manages streaming responses, and calculates confidence scores for API generation.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Callable, Any, AsyncIterator
from dataclasses import dataclass
from enum import Enum
import requests
import threading
from concurrent.futures import ThreadPoolExecutor

from ..core.logging_manager import LoggingManager
from .llm_manager import OllamaServerManager, ServerStatus
from .chain_of_thought.prompt_builder import APIPromptBuilder
from .chain_of_thought.stream_processor import StreamProcessor, ReasoningStep


class ReasoningState(Enum):
    """Reasoning engine processing states."""
    IDLE = "idle"
    PROCESSING = "processing"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ReasoningRequest:
    """Request for Chain of Thought reasoning."""
    request_id: str
    user_input: str
    context: Optional[Dict[str, Any]] = None
    temperature: float = 0.1
    max_tokens: int = 2048
    stream: bool = True


@dataclass
class ReasoningResult:
    """Result from Chain of Thought reasoning."""
    request_id: str
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    api_calls: Optional[List[Dict[str, Any]]] = None
    confidence: float = 0.0
    reasoning_steps: List[ReasoningStep] = None
    processing_time: float = 0.0
    error: Optional[str] = None
    raw_response: Optional[str] = None


class ChainOfThoughtEngine:
    """Chain of Thought reasoning engine for NLP to API conversion."""
    
    def __init__(self, ollama_manager: Optional[OllamaServerManager] = None):
        """Initialize Chain of Thought engine.
        
        Args:
            ollama_manager: Optional Ollama server manager instance
        """
        self.logger = LoggingManager.get_logger(__name__)
        
        # Initialize components
        self.ollama_manager = ollama_manager or OllamaServerManager()
        self.prompt_builder = APIPromptBuilder()
        self.stream_processor = StreamProcessor()
        
        # Engine state
        self.state = ReasoningState.IDLE
        self.current_request: Optional[ReasoningRequest] = None
        self.processing_history: List[ReasoningResult] = []
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Configure stream processor callbacks
        self._setup_stream_processor()
        
        # Performance tracking
        self.total_requests = 0
        self.successful_requests = 0
        self.average_processing_time = 0.0
        
    def _setup_stream_processor(self):
        """Configure stream processor callbacks."""
        self.stream_processor.on_step_parsed = self._on_reasoning_step
        self.stream_processor.on_stream_complete = self._on_stream_complete
        self.stream_processor.on_stream_error = self._on_stream_error
        
    def start_engine(self) -> bool:
        """Start the reasoning engine with Ollama server.
        
        Returns:
            True if engine started successfully
        """
        self.logger.info("Starting Chain of Thought reasoning engine")
        
        try:
            # Start Ollama server
            if not self.ollama_manager.start_server():
                self.logger.error("Failed to start Ollama server")
                return False
                
            # Ensure model is available
            if not self.ollama_manager.ensure_model_available(self.ollama_manager.model_name):
                self.logger.error(f"Failed to ensure model availability: {self.ollama_manager.model_name}")
                return False
                
            self.state = ReasoningState.IDLE
            self.logger.info("Chain of Thought engine started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start reasoning engine: {e}")
            self.state = ReasoningState.ERROR
            return False
            
    def stop_engine(self):
        """Stop the reasoning engine and cleanup resources."""
        self.logger.info("Stopping Chain of Thought reasoning engine")
        
        # Stop current processing
        if self.state == ReasoningState.PROCESSING:
            self.stream_processor.stop_processing()
            
        # Stop Ollama server
        self.ollama_manager.stop_server()
        
        # Cleanup executor
        self.executor.shutdown(wait=True)
        
        self.state = ReasoningState.IDLE
        self.logger.info("Chain of Thought engine stopped")
        
    def process_request(self, user_input: str, 
                       context: Optional[Dict[str, Any]] = None,
                       temperature: float = 0.1,
                       max_tokens: int = 2048,
                       stream: bool = True) -> str:
        """Process a reasoning request.
        
        Args:
            user_input: User's natural language input
            context: Optional context information
            temperature: LLM temperature setting
            max_tokens: Maximum tokens to generate
            stream: Whether to use streaming response
            
        Returns:
            Request ID for tracking
        """
        if self.state not in [ReasoningState.IDLE, ReasoningState.COMPLETED]:
            raise RuntimeError(f"Engine not ready for processing: {self.state}")
            
        # Create request
        request_id = str(uuid.uuid4())[:8]
        request = ReasoningRequest(
            request_id=request_id,
            user_input=user_input,
            context=context,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
        
        self.logger.info(f"Processing reasoning request: {request_id}")
        self.current_request = request
        self.total_requests += 1
        
        # Start processing
        if stream:
            self._process_streaming_request(request)
        else:
            self._process_blocking_request(request)
            
        return request_id
        
    def _process_streaming_request(self, request: ReasoningRequest):
        """Process request with streaming response.
        
        Args:
            request: Reasoning request to process
        """
        self.state = ReasoningState.STREAMING
        
        # Start stream processor
        self.stream_processor.start_processing(request.request_id)
        
        # Submit processing task
        future = self.executor.submit(self._execute_streaming_request, request)
        
    def _process_blocking_request(self, request: ReasoningRequest):
        """Process request with blocking response.
        
        Args:
            request: Reasoning request to process
        """
        self.state = ReasoningState.PROCESSING
        
        # Submit processing task
        future = self.executor.submit(self._execute_blocking_request, request)
        
    def _execute_streaming_request(self, request: ReasoningRequest):
        """Execute streaming request processing.
        
        Args:
            request: Request to process
        """
        start_time = time.time()
        
        try:
            # Build prompts
            system_prompt = self.prompt_builder.build_system_prompt()
            user_prompt = self.prompt_builder.build_user_prompt(
                request.user_input, 
                request.context
            )
            
            # Make streaming request to Ollama
            response = requests.post(
                f"{self.ollama_manager.base_url}/api/generate",
                json={
                    "model": self.ollama_manager.model_name,
                    "system": system_prompt,
                    "prompt": user_prompt,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "stream": True
                },
                stream=True,
                timeout=120
            )
            response.raise_for_status()
            
            # Process streaming response
            accumulated_response = ""
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            chunk = data["response"]
                            accumulated_response += chunk
                            
                            # Send chunk to stream processor
                            self.stream_processor.add_chunk(
                                chunk, 
                                is_complete=data.get("done", False)
                            )
                            
                        if data.get("done", False):
                            break
                            
                    except json.JSONDecodeError:
                        continue
                        
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create result
            result = self._create_reasoning_result(
                request.request_id,
                accumulated_response,
                processing_time
            )
            
            # Store result
            self.processing_history.append(result)
            self._update_performance_metrics(processing_time, success=True)
            
        except Exception as e:
            self.logger.error(f"Streaming request failed: {e}")
            self._handle_processing_error(request.request_id, e)
            
    def _execute_blocking_request(self, request: ReasoningRequest):
        """Execute blocking request processing.
        
        Args:
            request: Request to process
        """
        start_time = time.time()
        
        try:
            # Build prompts
            system_prompt = self.prompt_builder.build_system_prompt()
            user_prompt = self.prompt_builder.build_user_prompt(
                request.user_input,
                request.context
            )
            
            # Make blocking request to Ollama
            response = requests.post(
                f"{self.ollama_manager.base_url}/api/generate",
                json={
                    "model": self.ollama_manager.model_name,
                    "system": system_prompt,
                    "prompt": user_prompt,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            llm_response = data.get("response", "")
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create result
            result = self._create_reasoning_result(
                request.request_id,
                llm_response,
                processing_time
            )
            
            # Store result
            self.processing_history.append(result)
            self._update_performance_metrics(processing_time, success=True)
            
            self.state = ReasoningState.COMPLETED
            
        except Exception as e:
            self.logger.error(f"Blocking request failed: {e}")
            self._handle_processing_error(request.request_id, e)
            
    def _create_reasoning_result(self, request_id: str, 
                               raw_response: str,
                               processing_time: float) -> ReasoningResult:
        """Create reasoning result from LLM response.
        
        Args:
            request_id: Request identifier
            raw_response: Raw LLM response
            processing_time: Time taken to process
            
        Returns:
            Parsed reasoning result
        """
        result = ReasoningResult(
            request_id=request_id,
            raw_response=raw_response,
            processing_time=processing_time,
            reasoning_steps=[]
        )
        
        try:
            # Try to parse JSON response
            if raw_response.strip().startswith('{'):
                parsed_data = json.loads(raw_response)
                
                # Extract summary information
                summary = parsed_data.get("summary", {})
                result.intent = summary.get("intent")
                result.confidence = summary.get("confidence", 0.0)
                
                # Extract Chain of Thought steps
                chain_steps = parsed_data.get("chain_of_thought", [])
                for step_data in chain_steps:
                    if step_data.get("step") == "Entity Extraction":
                        result.entities = step_data.get("entities")
                    elif step_data.get("step") == "API Mapping":
                        result.api_calls = step_data.get("api_calls")
                        
                # Convert to ReasoningStep objects
                result.reasoning_steps = [
                    ReasoningStep(
                        step=step.get("step", "Unknown"),
                        reasoning=step.get("reasoning", ""),
                        findings=step.get("findings"),
                        confidence=step.get("confidence"),
                        entities=step.get("entities"),
                        api_calls=step.get("api_calls")
                    )
                    for step in chain_steps
                ]
                
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to parse LLM response as JSON: {e}")
            # Fall back to text analysis
            result.confidence = self._estimate_confidence_from_text(raw_response)
            
        return result
        
    def _estimate_confidence_from_text(self, text: str) -> float:
        """Estimate confidence from raw text response.
        
        Args:
            text: Raw text response
            
        Returns:
            Estimated confidence score
        """
        # Simple heuristic based on text characteristics
        confidence = 0.3  # Base confidence
        
        # Increase confidence for structured content
        if "API" in text.upper():
            confidence += 0.2
        if any(keyword in text.lower() for keyword in ["vehicle", "reservation", "maintenance"]):
            confidence += 0.2
        if len(text) > 100:  # Detailed response
            confidence += 0.1
            
        return min(confidence, 1.0)
        
    def _on_reasoning_step(self, step: ReasoningStep):
        """Handle parsed reasoning step from stream processor.
        
        Args:
            step: Parsed reasoning step
        """
        self.logger.debug(f"Reasoning step parsed: {step.step}")
        
    def _on_stream_complete(self, result: Dict[str, Any]):
        """Handle stream completion from stream processor.
        
        Args:
            result: Stream completion data
        """
        self.logger.info(f"Stream processing completed: {result['stream_id']}")
        self.state = ReasoningState.COMPLETED
        
    def _on_stream_error(self, error: Exception):
        """Handle stream error from stream processor.
        
        Args:
            error: Stream processing error
        """
        self.logger.error(f"Stream processing error: {error}")
        if self.current_request:
            self._handle_processing_error(self.current_request.request_id, error)
            
    def _handle_processing_error(self, request_id: str, error: Exception):
        """Handle processing error.
        
        Args:
            request_id: Request identifier
            error: Processing error
        """
        # Create error result
        result = ReasoningResult(
            request_id=request_id,
            error=str(error),
            processing_time=0.0
        )
        
        self.processing_history.append(result)
        self._update_performance_metrics(0.0, success=False)
        self.state = ReasoningState.ERROR
        
    def _update_performance_metrics(self, processing_time: float, success: bool):
        """Update performance tracking metrics.
        
        Args:
            processing_time: Time taken for processing
            success: Whether processing was successful
        """
        if success:
            self.successful_requests += 1
            
        # Update average processing time
        if self.successful_requests > 0:
            total_time = self.average_processing_time * (self.successful_requests - 1)
            self.average_processing_time = (total_time + processing_time) / self.successful_requests
            
    def get_result(self, request_id: str) -> Optional[ReasoningResult]:
        """Get reasoning result by request ID.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Reasoning result or None if not found
        """
        for result in self.processing_history:
            if result.request_id == request_id:
                return result
        return None
        
    def get_latest_result(self) -> Optional[ReasoningResult]:
        """Get the most recent reasoning result.
        
        Returns:
            Latest reasoning result or None if no results
        """
        return self.processing_history[-1] if self.processing_history else None
        
    def validate_result(self, result: ReasoningResult) -> Dict[str, Any]:
        """Validate reasoning result quality and accuracy.
        
        Args:
            result: Reasoning result to validate
            
        Returns:
            Validation report
        """
        validation = {
            "overall_score": 0.0,
            "confidence_assessment": "unknown",
            "entity_validation": {},
            "api_validation": {},
            "recommendations": []
        }
        
        # Assess confidence
        if result.confidence >= 0.8:
            validation["confidence_assessment"] = "high"
            validation["overall_score"] += 0.4
        elif result.confidence >= 0.6:
            validation["confidence_assessment"] = "medium"
            validation["overall_score"] += 0.2
        else:
            validation["confidence_assessment"] = "low"
            validation["recommendations"].append("Consider requesting clarification")
            
        # Validate entities if present
        if result.entities:
            validation["entity_validation"] = self.prompt_builder.validate_entities(result.entities)
            if validation["entity_validation"]["errors"]:
                validation["recommendations"].append("Fix entity extraction errors")
            else:
                validation["overall_score"] += 0.3
                
        # Validate API calls
        if result.api_calls:
            validation["api_validation"]["count"] = len(result.api_calls)
            validation["api_validation"]["has_required_fields"] = all(
                "method" in call and "endpoint" in call 
                for call in result.api_calls
            )
            if validation["api_validation"]["has_required_fields"]:
                validation["overall_score"] += 0.3
            else:
                validation["recommendations"].append("API calls missing required fields")
                
        return validation
        
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics.
        
        Returns:
            Dictionary with engine statistics
        """
        return {
            "state": self.state.value,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "success_rate": self.successful_requests / max(self.total_requests, 1),
            "average_processing_time": self.average_processing_time,
            "current_request": self.current_request.request_id if self.current_request else None,
            "history_size": len(self.processing_history),
            "ollama_status": self.ollama_manager.status.value,
            "stream_processor_stats": self.stream_processor.get_processing_stats()
        }
        
    def cleanup(self):
        """Cleanup resources and stop engine."""
        self.logger.info("Cleaning up Chain of Thought engine")
        self.stop_engine()
        
        # Clear history
        self.processing_history.clear()
        self.current_request = None