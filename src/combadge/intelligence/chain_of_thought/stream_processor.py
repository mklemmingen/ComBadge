"""Real-time Stream Processor

Handles real-time LLM response streaming with queue-based UI updates,
Chain of Thought parsing, and error recovery for interrupted streams.
"""

import asyncio
import json
import queue
import threading
import time
from typing import Dict, List, Optional, Callable, Any, AsyncIterator
from dataclasses import dataclass
from enum import Enum
import re

from ...core.logging_manager import LoggingManager


class StreamState(Enum):
    """Stream processing states."""
    IDLE = "idle"
    STREAMING = "streaming" 
    PARSING = "parsing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class StreamChunk:
    """Represents a chunk of streaming data."""
    content: str
    timestamp: float
    chunk_id: int
    is_complete: bool = False


@dataclass
class ReasoningStep:
    """Represents a parsed reasoning step from Chain of Thought."""
    step: str
    reasoning: str
    findings: Optional[List[str]] = None
    confidence: Optional[float] = None
    entities: Optional[Dict[str, Any]] = None
    api_calls: Optional[List[Dict[str, Any]]] = None


class StreamProcessor:
    """Real-time processor for LLM streaming responses with Chain of Thought parsing."""
    
    def __init__(self, update_interval_ms: int = 50):
        """Initialize stream processor.
        
        Args:
            update_interval_ms: UI update interval in milliseconds
        """
        self.update_interval_ms = update_interval_ms
        self.logger = LoggingManager.get_logger(__name__)
        
        # Stream state
        self.state = StreamState.IDLE
        self.current_stream_id: Optional[str] = None
        
        # Data queues
        self.chunk_queue: queue.Queue[StreamChunk] = queue.Queue()
        self.ui_update_queue: queue.Queue[Dict[str, Any]] = queue.Queue()
        
        # Processing threads
        self.processor_thread: Optional[threading.Thread] = None
        self.ui_update_thread: Optional[threading.Thread] = None
        self.is_processing = False
        
        # Parsed content
        self.accumulated_content = ""
        self.parsed_steps: List[ReasoningStep] = []
        self.current_json_buffer = ""
        
        # Callbacks
        self.on_step_parsed: Optional[Callable[[ReasoningStep], None]] = None
        self.on_stream_complete: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_stream_error: Optional[Callable[[Exception], None]] = None
        
        # Error recovery
        self.retry_count = 0
        self.max_retries = 3
        self.recovery_timeout = 30.0
        
    def start_processing(self, stream_id: str):
        """Start stream processing for a new stream.
        
        Args:
            stream_id: Unique identifier for this stream
        """
        if self.is_processing:
            self.logger.warning("Stream processor already running, stopping previous stream")
            self.stop_processing()
            
        self.logger.info(f"Starting stream processing for: {stream_id}")
        
        # Reset state
        self.current_stream_id = stream_id
        self.state = StreamState.STREAMING
        self.accumulated_content = ""
        self.parsed_steps.clear()
        self.current_json_buffer = ""
        self.retry_count = 0
        
        # Clear queues
        self._clear_queues()
        
        # Start processing threads
        self.is_processing = True
        self._start_processing_threads()
        
    def stop_processing(self):
        """Stop stream processing and cleanup resources."""
        self.logger.info("Stopping stream processing")
        
        self.is_processing = False
        self.state = StreamState.IDLE
        
        # Stop threads
        self._stop_processing_threads()
        
        # Clear queues
        self._clear_queues()
        
        self.current_stream_id = None
        
    def add_chunk(self, content: str, is_complete: bool = False):
        """Add a new chunk of streaming content.
        
        Args:
            content: Content chunk from LLM stream
            is_complete: Whether this is the final chunk
        """
        if not self.is_processing:
            self.logger.warning("Received chunk but processor not running")
            return
            
        chunk = StreamChunk(
            content=content,
            timestamp=time.time(),
            chunk_id=len(self.accumulated_content),
            is_complete=is_complete
        )
        
        try:
            self.chunk_queue.put_nowait(chunk)
        except queue.Full:
            self.logger.warning("Chunk queue full, dropping chunk")
            
    def _start_processing_threads(self):
        """Start processing and UI update threads."""
        # Stream processing thread
        self.processor_thread = threading.Thread(
            target=self._process_chunks_loop,
            name=f"StreamProcessor-{self.current_stream_id}",
            daemon=True
        )
        self.processor_thread.start()
        
        # UI update thread
        self.ui_update_thread = threading.Thread(
            target=self._ui_update_loop,
            name=f"UIUpdater-{self.current_stream_id}",
            daemon=True
        )
        self.ui_update_thread.start()
        
    def _stop_processing_threads(self):
        """Stop processing threads."""
        # Wait for threads to complete
        if self.processor_thread:
            self.processor_thread.join(timeout=2.0)
            
        if self.ui_update_thread:
            self.ui_update_thread.join(timeout=2.0)
            
        self.processor_thread = None
        self.ui_update_thread = None
        
    def _clear_queues(self):
        """Clear all processing queues."""
        while not self.chunk_queue.empty():
            try:
                self.chunk_queue.get_nowait()
            except queue.Empty:
                break
                
        while not self.ui_update_queue.empty():
            try:
                self.ui_update_queue.get_nowait()
            except queue.Empty:
                break
                
    def _process_chunks_loop(self):
        """Main chunk processing loop."""
        self.logger.info("Started chunk processing loop")
        
        while self.is_processing:
            try:
                # Get chunk with timeout
                chunk = self.chunk_queue.get(timeout=1.0)
                
                # Process chunk
                self._process_chunk(chunk)
                
                # Check for completion
                if chunk.is_complete:
                    self._finalize_stream()
                    break
                    
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in chunk processing: {e}")
                self._handle_stream_error(e)
                break
                
        self.logger.info("Chunk processing loop ended")
        
    def _process_chunk(self, chunk: StreamChunk):
        """Process a single chunk of content.
        
        Args:
            chunk: Stream chunk to process
        """
        # Accumulate content
        self.accumulated_content += chunk.content
        
        # Try to parse JSON objects as they become complete
        self._try_parse_json_chunks()
        
        # Update UI with raw content
        self._queue_ui_update({
            "type": "content_update",
            "content": chunk.content,
            "accumulated_length": len(self.accumulated_content),
            "timestamp": chunk.timestamp
        })
        
    def _try_parse_json_chunks(self):
        """Attempt to parse JSON objects from accumulated content."""
        # Look for complete JSON objects in the content
        json_pattern = r'\{(?:[^{}]|{[^{}]*})*\}'
        
        # Find potential JSON matches
        matches = re.finditer(json_pattern, self.accumulated_content)
        
        for match in matches:
            json_str = match.group(0)
            
            try:
                # Attempt to parse JSON
                parsed_data = json.loads(json_str)
                
                # Check if this is a Chain of Thought structure
                if self._is_chain_of_thought_json(parsed_data):
                    self._process_chain_of_thought(parsed_data)
                    
            except json.JSONDecodeError:
                continue
                
    def _is_chain_of_thought_json(self, data: Dict[str, Any]) -> bool:
        """Check if parsed JSON is a Chain of Thought structure.
        
        Args:
            data: Parsed JSON data
            
        Returns:
            True if this appears to be Chain of Thought data
        """
        required_keys = ["chain_of_thought", "summary"]
        return all(key in data for key in required_keys)
        
    def _process_chain_of_thought(self, data: Dict[str, Any]):
        """Process Chain of Thought JSON data.
        
        Args:
            data: Chain of Thought JSON data
        """
        try:
            chain_steps = data.get("chain_of_thought", [])
            
            for step_data in chain_steps:
                reasoning_step = self._parse_reasoning_step(step_data)
                if reasoning_step:
                    self.parsed_steps.append(reasoning_step)
                    
                    # Notify callback
                    if self.on_step_parsed:
                        try:
                            self.on_step_parsed(reasoning_step)
                        except Exception as e:
                            self.logger.error(f"Error in step parsed callback: {e}")
                            
                    # Queue UI update
                    self._queue_ui_update({
                        "type": "reasoning_step",
                        "step": reasoning_step.step,
                        "reasoning": reasoning_step.reasoning,
                        "findings": reasoning_step.findings,
                        "confidence": reasoning_step.confidence,
                        "entities": reasoning_step.entities,
                        "api_calls": reasoning_step.api_calls
                    })
                    
        except Exception as e:
            self.logger.error(f"Error processing Chain of Thought: {e}")
            
    def _parse_reasoning_step(self, step_data: Dict[str, Any]) -> Optional[ReasoningStep]:
        """Parse a single reasoning step from JSON data.
        
        Args:
            step_data: Step data from Chain of Thought JSON
            
        Returns:
            Parsed reasoning step or None if invalid
        """
        try:
            step = ReasoningStep(
                step=step_data.get("step", "Unknown"),
                reasoning=step_data.get("reasoning", ""),
                findings=step_data.get("findings"),
                confidence=step_data.get("confidence"),
                entities=step_data.get("entities"),
                api_calls=step_data.get("api_calls")
            )
            return step
        except Exception as e:
            self.logger.error(f"Error parsing reasoning step: {e}")
            return None
            
    def _ui_update_loop(self):
        """UI update loop running at specified interval."""
        self.logger.info(f"Started UI update loop (interval: {self.update_interval_ms}ms)")
        
        while self.is_processing:
            try:
                # Process queued UI updates
                updates_processed = 0
                while not self.ui_update_queue.empty() and updates_processed < 10:
                    try:
                        update = self.ui_update_queue.get_nowait()
                        self._send_ui_update(update)
                        updates_processed += 1
                    except queue.Empty:
                        break
                        
                # Sleep for update interval
                time.sleep(self.update_interval_ms / 1000.0)
                
            except Exception as e:
                self.logger.error(f"Error in UI update loop: {e}")
                
        self.logger.info("UI update loop ended")
        
    def _queue_ui_update(self, update: Dict[str, Any]):
        """Queue a UI update.
        
        Args:
            update: Update data to queue
        """
        try:
            self.ui_update_queue.put_nowait(update)
        except queue.Full:
            self.logger.warning("UI update queue full, dropping update")
            
    def _send_ui_update(self, update: Dict[str, Any]):
        """Send UI update (placeholder for UI integration).
        
        Args:
            update: Update data to send
        """
        # This would integrate with the actual UI system
        self.logger.debug(f"UI Update: {update['type']}")
        
    def _finalize_stream(self):
        """Finalize stream processing when complete."""
        self.logger.info("Finalizing stream processing")
        
        self.state = StreamState.COMPLETED
        
        # Final parsing attempt
        if self.accumulated_content and not self.parsed_steps:
            self._attempt_final_parse()
            
        # Prepare final result
        result = {
            "stream_id": self.current_stream_id,
            "total_content": self.accumulated_content,
            "parsed_steps": len(self.parsed_steps),
            "processing_time": time.time(),
            "state": self.state.value
        }
        
        # Notify completion callback
        if self.on_stream_complete:
            try:
                self.on_stream_complete(result)
            except Exception as e:
                self.logger.error(f"Error in stream complete callback: {e}")
                
        # Queue final UI update
        self._queue_ui_update({
            "type": "stream_complete",
            "result": result
        })
        
    def _attempt_final_parse(self):
        """Attempt final parsing of accumulated content."""
        try:
            # Try to parse as complete JSON
            parsed_data = json.loads(self.accumulated_content)
            
            if self._is_chain_of_thought_json(parsed_data):
                self._process_chain_of_thought(parsed_data)
            else:
                self.logger.warning("Final content is not Chain of Thought format")
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"Final parse failed: {e}")
            # Try to extract partial JSON
            self._attempt_partial_json_recovery()
            
    def _attempt_partial_json_recovery(self):
        """Attempt to recover partial JSON from malformed content."""
        try:
            # Find the longest valid JSON substring
            for i in range(len(self.accumulated_content), 0, -1):
                try:
                    test_content = self.accumulated_content[:i]
                    if test_content.endswith('}'):
                        parsed_data = json.loads(test_content)
                        self.logger.info("Recovered partial JSON successfully")
                        
                        if self._is_chain_of_thought_json(parsed_data):
                            self._process_chain_of_thought(parsed_data)
                        break
                        
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            self.logger.error(f"JSON recovery failed: {e}")
            
    def _handle_stream_error(self, error: Exception):
        """Handle stream processing error.
        
        Args:
            error: Exception that occurred
        """
        self.logger.error(f"Stream processing error: {error}")
        
        self.state = StreamState.ERROR
        
        # Attempt recovery if retries available
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            self.logger.info(f"Attempting recovery (retry {self.retry_count}/{self.max_retries})")
            
            # Reset state for retry
            self.state = StreamState.STREAMING
            
        else:
            # Notify error callback
            if self.on_stream_error:
                try:
                    self.on_stream_error(error)
                except Exception as callback_error:
                    self.logger.error(f"Error in error callback: {callback_error}")
                    
            # Queue error UI update
            self._queue_ui_update({
                "type": "stream_error",
                "error": str(error),
                "retry_count": self.retry_count
            })
            
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        return {
            "state": self.state.value,
            "stream_id": self.current_stream_id,
            "content_length": len(self.accumulated_content),
            "parsed_steps": len(self.parsed_steps),
            "retry_count": self.retry_count,
            "is_processing": self.is_processing,
            "chunk_queue_size": self.chunk_queue.qsize(),
            "ui_queue_size": self.ui_update_queue.qsize()
        }
        
    def export_results(self) -> Dict[str, Any]:
        """Export processing results.
        
        Returns:
            Complete processing results
        """
        return {
            "stream_id": self.current_stream_id,
            "state": self.state.value,
            "content": self.accumulated_content,
            "steps": [
                {
                    "step": step.step,
                    "reasoning": step.reasoning,
                    "findings": step.findings,
                    "confidence": step.confidence,
                    "entities": step.entities,
                    "api_calls": step.api_calls
                }
                for step in self.parsed_steps
            ],
            "stats": self.get_processing_stats()
        }