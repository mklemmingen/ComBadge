"""Ollama Automatic Installer and Setup Manager

Handles automatic download, installation, and configuration of Ollama
for seamless first-run experience in ComBadge.
"""

import os
import sys
import json
import tempfile
import platform
import subprocess
import hashlib
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Tuple
from urllib.request import urlopen, urlretrieve
from urllib.error import URLError
import time
import shutil

from ..core.logging_manager import LoggingManager


class OllamaInstaller:
    """Manages automatic Ollama installation and model setup."""
    
    # Ollama release URLs (update these as needed)
    OLLAMA_RELEASES = {
        "Windows": {
            "url": "https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe",
            "expected_size": 150 * 1024 * 1024,  # ~150MB
            "installer_name": "OllamaSetup.exe"
        },
        "Darwin": {  # macOS
            "url": "https://github.com/ollama/ollama/releases/latest/download/Ollama-darwin.zip",
            "expected_size": 140 * 1024 * 1024,  # ~140MB
            "installer_name": "Ollama-darwin.zip"
        },
        "Linux": {
            "url": "https://ollama.ai/install.sh",
            "expected_size": 10 * 1024,  # Script is small
            "installer_name": "install.sh"
        }
    }
    
    def __init__(self, 
                 installation_path: Optional[Path] = None,
                 progress_callback: Optional[Callable[[str, float], None]] = None):
        """Initialize Ollama installer.
        
        Args:
            installation_path: Custom installation directory (optional)
            progress_callback: Callback for progress updates (status, percent)
        """
        self.logger = LoggingManager.get_logger(__name__)
        self.platform = platform.system()
        self.installation_path = installation_path
        self.progress_callback = progress_callback
        self.is_installing = False
        self.cancel_requested = False
        
        # Default paths for Ollama
        self.default_paths = {
            "Windows": Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama",
            "Darwin": Path("/usr/local/bin"),
            "Linux": Path("/usr/local/bin")
        }
        
    def is_ollama_installed(self) -> bool:
        """Check if Ollama is already installed.
        
        Returns:
            True if Ollama is found and functional
        """
        # Try common installation paths
        possible_paths = self._get_possible_ollama_paths()
        
        for path in possible_paths:
            try:
                result = subprocess.run(
                    [str(path), "--version"],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                if result.returncode == 0:
                    self.logger.info(f"Found Ollama at: {path}")
                    self.logger.info(f"Version: {result.stdout.strip()}")
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
                
        return False
    
    def _get_possible_ollama_paths(self) -> list[Path]:
        """Get list of possible Ollama binary locations."""
        paths = []
        
        if self.platform == "Windows":
            # Windows paths
            paths.extend([
                Path("ollama.exe"),  # In PATH
                Path("C:/Program Files/Ollama/ollama.exe"),
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
                Path(os.environ.get("ProgramFiles", "")) / "Ollama" / "ollama.exe",
            ])
        else:
            # Unix-like paths
            paths.extend([
                Path("ollama"),  # In PATH
                Path("/usr/local/bin/ollama"),
                Path("/usr/bin/ollama"),
                Path.home() / ".ollama" / "bin" / "ollama",
            ])
            
        # Add custom installation path if provided
        if self.installation_path:
            if self.platform == "Windows":
                paths.append(self.installation_path / "ollama.exe")
            else:
                paths.append(self.installation_path / "ollama")
                
        return paths
    
    def download_ollama(self, force: bool = False) -> Tuple[bool, str]:
        """Download Ollama installer for current platform.
        
        Args:
            force: Force download even if already installed
            
        Returns:
            Tuple of (success, path_to_installer or error_message)
        """
        if not force and self.is_ollama_installed():
            return True, "Ollama already installed"
            
        if self.platform not in self.OLLAMA_RELEASES:
            return False, f"Unsupported platform: {self.platform}"
            
        release_info = self.OLLAMA_RELEASES[self.platform]
        installer_url = release_info["url"]
        installer_name = release_info["installer_name"]
        expected_size = release_info["expected_size"]
        
        # Download to temp directory
        temp_dir = Path(tempfile.gettempdir()) / "combadge_ollama"
        temp_dir.mkdir(exist_ok=True)
        installer_path = temp_dir / installer_name
        
        self.logger.info(f"Downloading Ollama from: {installer_url}")
        self._report_progress("Downloading Ollama installer...", 0)
        
        try:
            # Download with progress tracking
            def download_hook(block_num, block_size, total_size):
                if self.cancel_requested:
                    raise Exception("Download cancelled by user")
                    
                downloaded = block_num * block_size
                percent = min((downloaded / total_size) * 100, 100) if total_size > 0 else 0
                self._report_progress(f"Downloading Ollama... ({downloaded / 1024 / 1024:.1f}MB)", percent)
            
            urlretrieve(installer_url, installer_path, reporthook=download_hook)
            
            # Verify download
            if not installer_path.exists():
                return False, "Download failed - file not found"
                
            actual_size = installer_path.stat().st_size
            if actual_size < expected_size * 0.8:  # Allow 20% variance
                return False, f"Download incomplete - expected ~{expected_size/1024/1024:.0f}MB, got {actual_size/1024/1024:.1f}MB"
                
            self.logger.info(f"Downloaded Ollama installer: {installer_path}")
            return True, str(installer_path)
            
        except URLError as e:
            error_msg = f"Network error downloading Ollama: {e}"
            self.logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Failed to download Ollama: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def install_ollama(self, installer_path: str) -> Tuple[bool, str]:
        """Install Ollama from downloaded installer.
        
        Args:
            installer_path: Path to downloaded installer
            
        Returns:
            Tuple of (success, message)
        """
        installer = Path(installer_path)
        if not installer.exists():
            return False, f"Installer not found: {installer_path}"
            
        self.is_installing = True
        self._report_progress("Installing Ollama...", 0)
        
        try:
            if self.platform == "Windows":
                # Windows silent installation
                self.logger.info("Running Windows installer...")
                
                # Check if running with admin privileges
                import ctypes
                if not ctypes.windll.shell32.IsUserAnAdmin():
                    self.logger.warning("Installation may require administrator privileges")
                
                # Run installer silently
                cmd = [str(installer), "/S"]  # Silent install
                if self.installation_path:
                    cmd.extend([f"/D={self.installation_path}"])
                    
                result = subprocess.run(cmd, capture_output=True, timeout=300)
                
                if result.returncode != 0:
                    return False, f"Installation failed with code {result.returncode}"
                    
                # Give installer time to complete
                time.sleep(5)
                
                # Verify installation
                if self.is_ollama_installed():
                    self._report_progress("Ollama installed successfully!", 100)
                    return True, "Installation completed successfully"
                else:
                    return False, "Installation completed but Ollama not found"
                    
            elif self.platform == "Linux":
                # Linux installation script
                self.logger.info("Running Linux installation script...")
                
                # Make script executable
                os.chmod(installer, 0o755)
                
                # Run installation script
                result = subprocess.run(
                    ["sh", str(installer)],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    self._report_progress("Ollama installed successfully!", 100)
                    return True, "Installation completed successfully"
                else:
                    return False, f"Installation failed: {result.stderr}"
                    
            elif self.platform == "Darwin":
                # macOS installation
                self.logger.info("Extracting macOS application...")
                
                # Extract zip file
                extract_dir = installer.parent / "ollama_extracted"
                shutil.unpack_archive(installer, extract_dir)
                
                # Move to Applications
                app_path = extract_dir / "Ollama.app"
                if app_path.exists():
                    dest = Path("/Applications/Ollama.app")
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.move(str(app_path), str(dest))
                    
                    self._report_progress("Ollama installed successfully!", 100)
                    return True, "Installation completed successfully"
                else:
                    return False, "Ollama.app not found in archive"
                    
            else:
                return False, f"Installation not implemented for {self.platform}"
                
        except subprocess.TimeoutExpired:
            return False, "Installation timed out"
            
        except Exception as e:
            error_msg = f"Installation error: {e}"
            self.logger.error(error_msg)
            return False, error_msg
            
        finally:
            self.is_installing = False
    
    def setup_ollama_service(self) -> Tuple[bool, str]:
        """Ensure Ollama service is running.
        
        Returns:
            Tuple of (success, message)
        """
        self._report_progress("Starting Ollama service...", 0)
        
        try:
            # Check if already running
            try:
                response = urlopen("http://localhost:11434/api/version", timeout=5)
                if response.status == 200:
                    self._report_progress("Ollama service already running", 100)
                    return True, "Service already running"
            except:
                pass
            
            # Start Ollama service
            if self.platform == "Windows":
                # On Windows, Ollama runs as a background service
                subprocess.Popen(["ollama", "serve"], 
                               creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                # On Unix-like systems
                subprocess.Popen(["ollama", "serve"], 
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            
            # Wait for service to start
            for i in range(30):  # 30 seconds timeout
                try:
                    response = urlopen("http://localhost:11434/api/version", timeout=1)
                    if response.status == 200:
                        self._report_progress("Ollama service started", 100)
                        return True, "Service started successfully"
                except:
                    time.sleep(1)
                    self._report_progress(f"Starting Ollama service... ({i+1}/30)", (i+1)/30*100)
                    
            return False, "Service failed to start within timeout"
            
        except Exception as e:
            error_msg = f"Failed to start service: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def download_model(self, model_name: str = "qwen2.5:14b") -> Tuple[bool, str]:
        """Download the specified model using Ollama.
        
        Args:
            model_name: Name of model to download
            
        Returns:
            Tuple of (success, message)
        """
        self._report_progress(f"Preparing to download model {model_name}...", 0)
        
        try:
            # First ensure Ollama service is running
            service_ok, msg = self.setup_ollama_service()
            if not service_ok:
                return False, f"Service setup failed: {msg}"
            
            # Start model download
            self.logger.info(f"Downloading model: {model_name}")
            
            # Use Ollama CLI to pull model
            process = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor download progress
            last_percent = 0
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                    
                if output:
                    # Parse progress from output
                    if "pulling" in output.lower():
                        self._report_progress(f"Downloading {model_name}...", 5)
                    elif "%" in output:
                        # Try to extract percentage
                        try:
                            import re
                            match = re.search(r'(\d+)%', output)
                            if match:
                                percent = int(match.group(1))
                                if percent > last_percent:
                                    last_percent = percent
                                    self._report_progress(
                                        f"Downloading {model_name}... {percent}%", 
                                        percent
                                    )
                        except:
                            pass
            
            # Check result
            if process.returncode == 0:
                self._report_progress(f"Model {model_name} ready!", 100)
                return True, "Model downloaded successfully"
            else:
                stderr = process.stderr.read()
                return False, f"Model download failed: {stderr}"
                
        except Exception as e:
            error_msg = f"Failed to download model: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def full_setup(self, model_name: str = "qwen2.5:14b") -> Tuple[bool, str]:
        """Perform complete Ollama setup: install and download model.
        
        Args:
            model_name: Model to download after installation
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Step 1: Check if already installed
            if self.is_ollama_installed():
                self.logger.info("Ollama already installed, skipping installation")
            else:
                # Step 2: Download installer
                success, result = self.download_ollama()
                if not success:
                    return False, result
                    
                # Step 3: Install Ollama
                success, msg = self.install_ollama(result)
                if not success:
                    return False, msg
            
            # Step 4: Setup service
            success, msg = self.setup_ollama_service()
            if not success:
                return False, msg
                
            # Step 5: Download model
            success, msg = self.download_model(model_name)
            if not success:
                return False, msg
                
            return True, "Setup completed successfully"
            
        except Exception as e:
            error_msg = f"Setup failed: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def cancel_operation(self):
        """Cancel ongoing download/installation."""
        self.cancel_requested = True
        self.logger.info("Operation cancellation requested")
    
    def _report_progress(self, status: str, percent: float):
        """Report progress to callback if available."""
        if self.progress_callback:
            try:
                self.progress_callback(status, percent)
            except Exception as e:
                self.logger.error(f"Progress callback error: {e}")


# Convenience function for one-line setup
def ensure_ollama_ready(model_name: str = "qwen2.5:14b", 
                       progress_callback: Optional[Callable[[str, float], None]] = None) -> bool:
    """Ensure Ollama is installed and model is available.
    
    Args:
        model_name: Model to ensure is available
        progress_callback: Optional progress callback
        
    Returns:
        True if setup successful
    """
    installer = OllamaInstaller(progress_callback=progress_callback)
    success, message = installer.full_setup(model_name)
    
    if not success:
        print(f"Ollama setup failed: {message}")
        
    return success