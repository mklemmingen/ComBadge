#!/usr/bin/env python3
"""Test ComBadge components without GUI (headless mode)"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Testing ComBadge components in headless mode...")

# Test imports
try:
    print("\n1. Testing core imports...")
    from combadge.core.config_manager import ConfigManager
    from combadge.core.logging_manager import LoggingManager
    from combadge.core.error_handler import ErrorHandler
    print("✓ Core imports successful")
except Exception as e:
    print(f"✗ Core import failed: {e}")
    sys.exit(1)

# Test configuration
try:
    print("\n2. Testing configuration loading...")
    config_manager = ConfigManager()
    config = config_manager.load_config()
    print(f"✓ Configuration loaded: {list(config.keys())}")
except Exception as e:
    print(f"✗ Configuration loading failed: {e}")

# Test logging
try:
    print("\n3. Testing logging system...")
    logger = LoggingManager.get_logger("test")
    logger.info("Test log message")
    print("✓ Logging system working")
except Exception as e:
    print(f"✗ Logging failed: {e}")

# Test Ollama components
try:
    print("\n4. Testing Ollama components...")
    from combadge.intelligence.llm_manager import OllamaServerManager
    from combadge.intelligence.ollama_installer import OllamaInstaller
    
    # Check if Ollama is installed
    installer = OllamaInstaller()
    is_installed = installer.is_ollama_installed()
    print(f"✓ Ollama installed: {is_installed}")
    
    # Check server status
    server_manager = OllamaServerManager()
    is_running = server_manager.is_server_running()
    print(f"✓ Ollama server running: {is_running}")
    
except Exception as e:
    print(f"✗ Ollama component test failed: {e}")

# Test intelligence components
try:
    print("\n5. Testing intelligence components...")
    from combadge.intelligence.intent_classifier import IntentClassifier
    from combadge.intelligence.entity_extractor import EntityExtractor
    from combadge.fleet.processors.command_processor import CommandProcessor
    print("✓ Intelligence components imported successfully")
except Exception as e:
    print(f"✗ Intelligence import failed: {e}")

# Test API components
try:
    print("\n6. Testing API components...")
    from combadge.api.client import FleetManagementClient
    from combadge.api.authentication import APIAuthManager
    print("✓ API components imported successfully")
except Exception as e:
    print(f"✗ API import failed: {e}")

print("\n✓ Headless component testing completed!")
print("\nNote: GUI components cannot be tested in headless mode.")
print("The Tkinter error is expected in a non-GUI environment.")