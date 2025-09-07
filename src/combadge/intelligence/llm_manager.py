"""Ollama Server Manager

Automatic Ollama server lifecycle management with health monitoring,
model downloading, and memory-efficient caching for ComBadge NLP processing.
"""

import asyncio
import subprocess
import time
import json
import os
import platform
import signal
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import requests
import threading
from functools import lru_cache

from ..core.logging_manager import LoggingManager


class ServerStatus(Enum):
    """Ollama server status states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class ModelInfo:
    """Information about an Ollama model."""
    name: str
    size: int = 0
    modified: str = ""
    digest: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DownloadProgress:
    """Model download progress information."""
    status: str
    completed: int = 0
    total: int = 0
    percent: float = 0.0


class OllamaServerManager:
    """Manages Ollama server lifecycle and model operations."""
    
    def __init__(self, base_url: str = "http://localhost:11434", 
                 model_name: str = "qwen2.5:14b"):
        """Initialize Ollama server manager.
        
        Args:
            base_url: Ollama server base URL
            model_name: Default model name to use
        """
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.logger = LoggingManager.get_logger(__name__)
        
        # Server state
        self.status = ServerStatus.STOPPED
        self.server_process: Optional[subprocess.Popen] = None
        self.health_check_thread: Optional[threading.Thread] = None
        self.is_monitoring = False
        
        # Model cache with 2GB memory limit
        self.model_cache: Dict[str, Any] = {}
        self.cache_memory_limit = 2 * 1024 * 1024 * 1024  # 2GB
        self.current_cache_size = 0
        
        # Callbacks
        self.on_status_change: Optional[Callable[[ServerStatus], None]] = None
        self.on_download_progress: Optional[Callable[[DownloadProgress], None]] = None
        
    def start_server(self, timeout: int = 30) -> bool:
        """Start Ollama server with automatic setup.
        
        Args:
            timeout: Maximum time to wait for server startup
            
        Returns:
            True if server started successfully, False otherwise
        """
        if self.is_server_running():
            self.logger.info("Ollama server is already running")
            self.status = ServerStatus.RUNNING
            self._notify_status_change()
            return True
            
        self.logger.info("Starting Ollama server...")
        self.status = ServerStatus.STARTING
        self._notify_status_change()
        
        try:
            # Start Ollama server process
            if not self._start_ollama_process():
                return False
                
            # Wait for server to be ready
            if not self._wait_for_server(timeout):
                self.logger.error("Server failed to start within timeout")
                self.stop_server()
                return False
                
            self.status = ServerStatus.RUNNING
            self._notify_status_change()
            
            # Start health monitoring
            self._start_health_monitoring()
            
            self.logger.info("Ollama server started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Ollama server: {e}")
            self.status = ServerStatus.ERROR
            self._notify_status_change()
            return False
            
    def _start_ollama_process(self) -> bool:
        """Start the Ollama server process.
        
        Returns:
            True if process started successfully
        """
        try:
            # Check if ollama binary exists
            ollama_cmd = self._find_ollama_binary()
            if not ollama_cmd:
                self.logger.error("Ollama binary not found. Please install Ollama first.")
                return False
                
            # Start server process
            if platform.system() == "Windows":
                # Windows-specific startup
                self.server_process = subprocess.Popen(
                    [ollama_cmd, "serve"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                # Unix-like systems
                self.server_process = subprocess.Popen(
                    [ollama_cmd, "serve"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid
                )
                
            self.logger.info(f"Started Ollama server process (PID: {self.server_process.pid})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Ollama process: {e}")
            return False
            
    def _find_ollama_binary(self) -> Optional[str]:
        """Find Ollama binary path.
        
        Returns:
            Path to ollama binary or None if not found
        """
        # Common installation paths
        possible_paths = [
            "ollama",  # In PATH
            "/usr/local/bin/ollama",
            "/usr/bin/ollama",
            os.path.expanduser("~/.ollama/bin/ollama"),
        ]
        
        if platform.system() == "Windows":
            possible_paths.extend([
                "ollama.exe",
                "C:\\Program Files\\Ollama\\ollama.exe",
                os.path.expanduser("~\\AppData\\Local\\Programs\\Ollama\\ollama.exe")
            ])
            
        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.logger.info(f"Found Ollama at: {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
                
        return None
        
    def _wait_for_server(self, timeout: int) -> bool:
        """Wait for Ollama server to be ready.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if server is ready, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_server_running():
                return True
            time.sleep(1)
            
        return False
        
    def stop_server(self):
        """Stop Ollama server and cleanup resources."""
        self.logger.info("Stopping Ollama server...")
        
        # Stop health monitoring
        self._stop_health_monitoring()
        
        # Terminate server process
        if self.server_process:
            try:
                if platform.system() == "Windows":
                    # Windows process termination
                    self.server_process.terminate()
                else:
                    # Unix-like systems - kill process group
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                    
                # Wait for graceful shutdown
                try:
                    self.server_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if not terminated
                    if platform.system() == "Windows":
                        self.server_process.kill()
                    else:
                        os.killpg(os.getpgid(self.server_process.pid), signal.SIGKILL)
                        
            except Exception as e:
                self.logger.warning(f"Error stopping server process: {e}")
                
            self.server_process = None
            
        self.status = ServerStatus.STOPPED
        self._notify_status_change()
        self.logger.info("Ollama server stopped")
        
    def is_server_running(self) -> bool:
        """Check if Ollama server is running via health check.
        
        Returns:
            True if server is running and responsive
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
            
    def get_available_models(self) -> List[ModelInfo]:
        """Get list of available models from server.
        
        Returns:
            List of available model information
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            models = []
            
            for model_data in data.get("models", []):
                model = ModelInfo(
                    name=model_data.get("name", ""),
                    size=model_data.get("size", 0),
                    modified=model_data.get("modified_at", ""),
                    digest=model_data.get("digest", ""),
                    details=model_data.get("details", {})
                )
                models.append(model)
                
            return models
            
        except Exception as e:
            self.logger.error(f"Failed to get available models: {e}")
            return []
            
    def download_model(self, model_name: str) -> bool:
        """Download a model with progress tracking.
        
        Args:
            model_name: Name of model to download
            
        Returns:
            True if download completed successfully
        """
        self.logger.info(f"Starting download of model: {model_name}")
        
        try:
            # Start download
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                stream=True,
                timeout=300  # 5 minutes timeout for download start
            )
            response.raise_for_status()
            
            # Process streaming response
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        progress_data = json.loads(line)
                        progress = self._parse_download_progress(progress_data)
                        
                        if self.on_download_progress:
                            self.on_download_progress(progress)
                            
                        # Check if download completed
                        if progress.status == "success":
                            self.logger.info(f"Model {model_name} downloaded successfully")
                            return True
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            self.logger.error(f"Failed to download model {model_name}: {e}")
            return False
            
        return False
        
    def _parse_download_progress(self, data: Dict[str, Any]) -> DownloadProgress:
        """Parse download progress data from Ollama response.
        
        Args:
            data: Progress data from Ollama
            
        Returns:
            Parsed download progress
        """
        status = data.get("status", "unknown")
        completed = data.get("completed", 0)
        total = data.get("total", 0)
        
        percent = 0.0
        if total > 0:
            percent = (completed / total) * 100
            
        return DownloadProgress(
            status=status,
            completed=completed,
            total=total,
            percent=percent
        )
        
    def ensure_model_available(self, model_name: str) -> bool:
        """Ensure a model is available, downloading if necessary.
        
        Args:
            model_name: Name of model to ensure availability
            
        Returns:
            True if model is available
        """
        # Check if model already exists
        available_models = self.get_available_models()
        for model in available_models:
            if model.name.startswith(model_name):
                self.logger.info(f"Model {model_name} is already available")
                return True
                
        # Download model if not available
        self.logger.info(f"Model {model_name} not found, downloading...")
        return self.download_model(model_name)
        
    def _start_health_monitoring(self):
        """Start health monitoring thread."""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.health_check_thread = threading.Thread(
            target=self._health_monitor_loop,
            daemon=True
        )
        self.health_check_thread.start()
        
    def _stop_health_monitoring(self):
        """Stop health monitoring thread."""
        self.is_monitoring = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
            self.health_check_thread = None
            
    def _health_monitor_loop(self):
        """Health monitoring loop."""
        while self.is_monitoring:
            try:
                if self.status == ServerStatus.RUNNING:
                    if not self.is_server_running():
                        self.logger.warning("Server health check failed")
                        self.status = ServerStatus.ERROR
                        self._notify_status_change()
                        
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")
                time.sleep(10)
                
    def _notify_status_change(self):
        """Notify status change callback."""
        if self.on_status_change:
            try:
                self.on_status_change(self.status)
            except Exception as e:
                self.logger.error(f"Status change callback error: {e}")
                
    @lru_cache(maxsize=32)
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """Get cached model information.
        
        Args:
            model_name: Name of model
            
        Returns:
            Model information or None if not found
        """
        models = self.get_available_models()
        for model in models:
            if model.name.startswith(model_name):
                return model
        return None
        
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics and resource usage.
        
        Returns:
            Dictionary with server statistics
        """
        stats = {
            "status": self.status.value,
            "server_running": self.is_server_running(),
            "base_url": self.base_url,
            "model_name": self.model_name,
            "available_models": len(self.get_available_models())
        }
        
        # Add process information if available
        if self.server_process:
            try:
                process = psutil.Process(self.server_process.pid)
                stats.update({
                    "pid": self.server_process.pid,
                    "memory_usage_mb": process.memory_info().rss / 1024 / 1024,
                    "cpu_percent": process.cpu_percent(),
                    "create_time": process.create_time()
                })
            except Exception as e:
                self.logger.warning(f"Failed to get process stats: {e}")
                
        return stats
        
    def cleanup(self):
        """Cleanup resources and stop server."""
        self.logger.info("Cleaning up Ollama server manager")
        self.stop_server()
        
        # Clear caches
        self.get_model_info.cache_clear()
        self.model_cache.clear()
        self.current_cache_size = 0