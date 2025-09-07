"""ComBadge Intelligence Package

Local LLM integration for natural language to API conversion using Ollama
with Qwen 2.5-14B model for Chain of Thought reasoning.
"""

from .llm_manager import OllamaServerManager
from .reasoning_engine import ChainOfThoughtEngine
from .chain_of_thought.stream_processor import StreamProcessor
from .chain_of_thought.prompt_builder import APIPromptBuilder

__all__ = [
    "OllamaServerManager",
    "ChainOfThoughtEngine", 
    "StreamProcessor",
    "APIPromptBuilder"
]