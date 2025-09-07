"""
Pytest configuration and shared fixtures for ComBadge testing.

Provides comprehensive test fixtures, mock objects, and configuration
for unit, integration, and performance testing.
"""

import os
import json
import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, MagicMock
from dataclasses import dataclass

import pytest
import pytest_asyncio
from unittest.mock import patch
import yaml

# Test data imports
from .fixtures.sample_data import (
    SAMPLE_EMAILS,
    SAMPLE_COMMANDS, 
    SAMPLE_API_RESPONSES,
    SAMPLE_CONFIGURATIONS,
    MOCK_VEHICLE_DATA
)


@dataclass
class TestConfig:
    """Test configuration settings"""
    mock_llm: bool = True
    mock_api: bool = True
    use_temp_db: bool = True
    enable_logging: bool = False
    test_timeout: int = 30


@pytest.fixture(scope="session")
def test_config():
    """Global test configuration"""
    return TestConfig()


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Configuration Fixtures
@pytest.fixture
def temp_config_dir():
    """Temporary directory for test configuration files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()
        
        # Create test config files
        default_config = {
            "app_name": "ComBadge-Test",
            "version": "1.0.0-test",
            "environment": "testing",
            "debug_mode": True,
            "llm": {
                "model": "test-model",
                "temperature": 0.1,
                "max_tokens": 1000,
                "streaming": False,
                "timeout": 10,
                "base_url": "http://localhost:11434"
            },
            "api": {
                "base_url": "http://test.api.com",
                "timeout": 15,
                "retry_attempts": 2,
                "authentication": {
                    "method": "api_key",
                    "api_key": "test-key"
                }
            },
            "ui": {
                "theme": "dark",
                "window_size": [800, 600],
                "font_size": 10
            },
            "processing": {
                "confidence_threshold": 0.8,
                "enable_caching": False
            },
            "logging": {
                "level": "DEBUG",
                "log_to_console": False,
                "audit_enabled": False
            }
        }
        
        with open(config_dir / "default_config.yaml", "w") as f:
            yaml.dump(default_config, f)
            
        yield config_dir


@pytest.fixture
def mock_config_manager(temp_config_dir):
    """Mock configuration manager with test settings"""
    from combadge.core.config_manager import ConfigManager
    
    with patch.object(ConfigManager, '_get_default_config_path') as mock_path:
        mock_path.return_value = temp_config_dir
        config_manager = ConfigManager()
        config = config_manager.load_config()
        yield config_manager


# LLM and Intelligence Fixtures
@pytest.fixture
def mock_llm_manager():
    """Mock LLM manager for testing without actual model calls"""
    from combadge.intelligence.llm_manager import LLMManager
    
    mock_manager = Mock(spec=LLMManager)
    mock_manager.is_available = Mock(return_value=True)
    mock_manager.generate_response = AsyncMock()
    mock_manager.stream_response = AsyncMock()
    
    # Default responses for different types of requests
    mock_responses = {
        "intent_classification": {
            "intent": "vehicle_operations",
            "confidence": 0.95,
            "entities": {"vehicle_id": "F-123"}
        },
        "entity_extraction": {
            "entities": {
                "vehicle_id": "F-123",
                "date": "2024-03-15",
                "time": "10:00"
            },
            "confidence": 0.90
        },
        "chain_of_thought": {
            "reasoning_steps": [
                "User wants to perform vehicle operation",
                "Vehicle ID F-123 identified", 
                "Action appears to be maintenance scheduling"
            ],
            "conclusion": "Schedule maintenance for vehicle F-123",
            "confidence": 0.92
        }
    }
    
    def side_effect(prompt, context=None):
        # Determine response type based on prompt content
        if "classify" in prompt.lower() or "intent" in prompt.lower():
            return mock_responses["intent_classification"]
        elif "extract" in prompt.lower() or "entities" in prompt.lower():
            return mock_responses["entity_extraction"]  
        elif "reasoning" in prompt.lower() or "think" in prompt.lower():
            return mock_responses["chain_of_thought"]
        else:
            return {"response": "Mock LLM response", "confidence": 0.85}
    
    mock_manager.generate_response.side_effect = side_effect
    return mock_manager


@pytest.fixture
def mock_intent_classifier():
    """Mock intent classifier with realistic responses"""
    from combadge.intelligence.intent_classifier import IntentClassifier
    
    mock_classifier = Mock(spec=IntentClassifier)
    
    classification_responses = {
        "schedule maintenance": {
            "intent": "maintenance_scheduling",
            "confidence": 0.95,
            "entities": {"vehicle_id": "F-123", "date": "tomorrow"}
        },
        "reserve vehicle": {
            "intent": "vehicle_reservation", 
            "confidence": 0.92,
            "entities": {"vehicle_id": "V-456", "start_time": "2pm"}
        },
        "create vehicle": {
            "intent": "vehicle_operations",
            "confidence": 0.88,
            "entities": {"make": "Toyota", "model": "Camry"}
        },
        "parking assignment": {
            "intent": "parking_management",
            "confidence": 0.90,
            "entities": {"vehicle_id": "P-789", "location": "Building A"}
        }
    }
    
    def classify_side_effect(text):
        # Simple keyword matching for test responses
        text_lower = text.lower()
        for keyword, response in classification_responses.items():
            if keyword in text_lower:
                return response
        
        # Default response for unrecognized input
        return {
            "intent": "unknown",
            "confidence": 0.3,
            "entities": {}
        }
    
    mock_classifier.classify_intent = AsyncMock(side_effect=classify_side_effect)
    return mock_classifier


@pytest.fixture 
def mock_entity_extractor():
    """Mock entity extractor with comprehensive extraction patterns"""
    from combadge.intelligence.entity_extractor import EntityExtractor
    
    mock_extractor = Mock(spec=EntityExtractor)
    
    def extract_side_effect(text, intent=None):
        entities = {}
        text_lower = text.lower()
        
        # Vehicle ID patterns
        import re
        vehicle_patterns = [
            r'\b[A-Z]-?\d{3,4}\b',  # F-123, V456
            r'\bvehicle\s+([A-Z]-?\d{3,4})\b',
            r'\bvin\s+([A-Z0-9]{17})\b'
        ]
        
        for pattern in vehicle_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities['vehicle_id'] = match.group(1) if match.groups() else match.group(0)
                break
        
        # Date patterns
        date_patterns = [
            r'\btomorrow\b',
            r'\bnext\s+\w+day\b',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}/\d{1,2}/\d{4}'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, text_lower):
                entities['date'] = re.search(pattern, text_lower).group(0)
                break
        
        # Time patterns
        time_patterns = [
            r'\d{1,2}:\d{2}\s?(?:am|pm)?',
            r'\d{1,2}\s?(?:am|pm)',
            r'\d{1,2}-\d{1,2}\s?(?:am|pm)?'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                entities['time'] = match.group(0)
                break
        
        # Location patterns
        if 'building' in text_lower or 'lot' in text_lower:
            location_match = re.search(r'(building|lot)\s+([A-Z0-9]+)', text, re.IGNORECASE)
            if location_match:
                entities['location'] = f"{location_match.group(1).title()} {location_match.group(2)}"
        
        # Add confidence scores
        confidence = 0.9 if entities else 0.3
        return {
            'entities': entities,
            'confidence': confidence
        }
    
    mock_extractor.extract_entities = AsyncMock(side_effect=extract_side_effect)
    return mock_extractor


# API and HTTP Client Fixtures
@pytest.fixture
def mock_http_client():
    """Mock HTTP client for API testing"""
    from combadge.api.client import HTTPClient
    
    mock_client = Mock(spec=HTTPClient)
    
    # Mock responses for different endpoints
    api_responses = {
        '/api/vehicles': {
            'GET': {'vehicles': MOCK_VEHICLE_DATA, 'total': len(MOCK_VEHICLE_DATA)},
            'POST': {'vehicle_id': 'V-NEW-001', 'status': 'created'}
        },
        '/api/maintenance': {
            'GET': {'appointments': [], 'total': 0},
            'POST': {'appointment_id': 'M-001', 'status': 'scheduled'}
        },
        '/api/reservations': {
            'GET': {'reservations': [], 'total': 0},
            'POST': {'reservation_id': 'R-001', 'status': 'confirmed'}
        },
        '/health': {
            'GET': {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
        }
    }
    
    def request_side_effect(method, endpoint, **kwargs):
        endpoint_responses = api_responses.get(endpoint, {})
        return endpoint_responses.get(method, {'error': 'Not found'})
    
    mock_client.request = AsyncMock(side_effect=request_side_effect)
    mock_client.get = AsyncMock(side_effect=lambda endpoint, **kwargs: request_side_effect('GET', endpoint, **kwargs))
    mock_client.post = AsyncMock(side_effect=lambda endpoint, **kwargs: request_side_effect('POST', endpoint, **kwargs))
    mock_client.put = AsyncMock(side_effect=lambda endpoint, **kwargs: request_side_effect('PUT', endpoint, **kwargs))
    mock_client.delete = AsyncMock(side_effect=lambda endpoint, **kwargs: request_side_effect('DELETE', endpoint, **kwargs))
    
    return mock_client


@pytest.fixture
def mock_auth_manager():
    """Mock authentication manager"""
    from combadge.api.authentication import AuthenticationManager
    
    mock_auth = Mock(spec=AuthenticationManager)
    mock_auth.is_authenticated = Mock(return_value=True)
    mock_auth.get_auth_status = Mock(return_value={
        'authenticated': True,
        'type': 'api_key',
        'valid': True
    })
    mock_auth.apply_authentication = Mock()
    
    return mock_auth


# Fleet Processing Fixtures
@pytest.fixture
def mock_email_parser():
    """Mock email parser with realistic parsing results"""
    from combadge.fleet.processors.email_parser import EmailParser
    
    mock_parser = Mock(spec=EmailParser)
    
    def parse_side_effect(email_content):
        # Extract basic info from email structure
        if isinstance(email_content, dict):
            return {
                'subject': email_content.get('subject', ''),
                'sender': email_content.get('from', ''),
                'body': email_content.get('body', ''),
                'timestamp': datetime.now(),
                'attachments': email_content.get('attachments', []),
                'parsed_content': email_content.get('body', '')
            }
        else:
            return {
                'subject': 'Parsed Email',
                'sender': 'test@example.com',
                'body': email_content,
                'timestamp': datetime.now(),
                'attachments': [],
                'parsed_content': email_content
            }
    
    mock_parser.parse_email = Mock(side_effect=parse_side_effect)
    return mock_parser


@pytest.fixture
def mock_template_manager():
    """Mock template manager with predefined templates"""
    from combadge.fleet.templates.template_manager import TemplateManager
    
    mock_manager = Mock(spec=TemplateManager)
    
    # Mock templates
    mock_templates = {
        'vehicle_operations': {
            'create_vehicle': {
                'template_id': 'create_vehicle',
                'intent': 'vehicle_operations',
                'api_endpoint': '/api/vehicles',
                'method': 'POST',
                'required_fields': ['make', 'model', 'year'],
                'template': {
                    'make': '{{make}}',
                    'model': '{{model}}',
                    'year': '{{year}}'
                }
            }
        },
        'maintenance_scheduling': {
            'schedule_maintenance': {
                'template_id': 'schedule_maintenance',
                'intent': 'maintenance_scheduling',
                'api_endpoint': '/api/maintenance',
                'method': 'POST',
                'required_fields': ['vehicle_id', 'date'],
                'template': {
                    'vehicle_id': '{{vehicle_id}}',
                    'scheduled_date': '{{date}}',
                    'maintenance_type': '{{maintenance_type|default:routine}}'
                }
            }
        }
    }
    
    mock_manager.get_templates = Mock(return_value=mock_templates)
    mock_manager.select_template = Mock(side_effect=lambda intent: mock_templates.get(intent, {}))
    mock_manager.load_templates = Mock()
    
    return mock_manager


# UI Component Fixtures
@pytest.fixture
def mock_tkinter_root():
    """Mock tkinter root for UI testing"""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # Hide the test window
        yield root
        root.destroy()
    except ImportError:
        # If tkinter not available, provide mock
        yield Mock()


@pytest.fixture
def mock_approval_workflow():
    """Mock approval workflow component"""
    from combadge.ui.components.approval_workflow import ApprovalWorkflow
    
    mock_workflow = Mock(spec=ApprovalWorkflow)
    mock_workflow.load_interpretation = Mock()
    mock_workflow.get_approval_stats = Mock(return_value={
        'total_decisions': 10,
        'approved': 8,
        'rejected': 2,
        'approval_rate': 0.8
    })
    
    return mock_workflow


# Test Data Fixtures
@pytest.fixture
def sample_emails():
    """Sample email data for testing"""
    return SAMPLE_EMAILS.copy()


@pytest.fixture
def sample_commands():
    """Sample command data for testing"""
    return SAMPLE_COMMANDS.copy()


@pytest.fixture
def sample_api_responses():
    """Sample API response data for testing"""
    return SAMPLE_API_RESPONSES.copy()


@pytest.fixture
def sample_configurations():
    """Sample configuration data for testing"""
    return SAMPLE_CONFIGURATIONS.copy()


@pytest.fixture
def mock_vehicle_data():
    """Mock vehicle data for testing"""
    return MOCK_VEHICLE_DATA.copy()


# Performance Testing Fixtures
@pytest.fixture
def performance_monitor():
    """Performance monitoring fixture for benchmarks"""
    import time
    import psutil
    import threading
    from collections import defaultdict
    
    class PerformanceMonitor:
        def __init__(self):
            self.metrics = defaultdict(list)
            self.start_time = None
            self.start_memory = None
            self._monitoring = False
            self._monitor_thread = None
            
        def start(self):
            self.start_time = time.time()
            self.start_memory = psutil.Process().memory_info().rss
            self._monitoring = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop)
            self._monitor_thread.start()
            
        def stop(self):
            self._monitoring = False
            if self._monitor_thread:
                self._monitor_thread.join()
                
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            
            return {
                'duration': end_time - self.start_time,
                'memory_delta': end_memory - self.start_memory,
                'peak_memory': max(self.metrics['memory']) if self.metrics['memory'] else end_memory,
                'cpu_usage': self.metrics['cpu']
            }
        
        def _monitor_loop(self):
            process = psutil.Process()
            while self._monitoring:
                self.metrics['memory'].append(process.memory_info().rss)
                self.metrics['cpu'].append(process.cpu_percent())
                time.sleep(0.1)
    
    return PerformanceMonitor()


# Database Fixtures
@pytest.fixture
def temp_database():
    """Temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
        db_path = temp_file.name
    
    yield db_path
    
    # Cleanup
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


# Async Testing Helpers
@pytest_asyncio.fixture
async def async_test_client():
    """Async test client for integration testing"""
    from combadge.core.application import Application
    
    # Create test application
    app = Application(config_path="test_config.yaml")
    await app.initialize()
    
    yield app
    
    await app.cleanup()


# Test Environment Setup
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, temp_config_dir):
    """Automatically setup test environment for all tests"""
    # Set environment variables for testing
    monkeypatch.setenv("COMBADGE_ENV", "testing")
    monkeypatch.setenv("COMBADGE_DEBUG_MODE", "true")
    monkeypatch.setenv("COMBADGE_LOGGING_LEVEL", "DEBUG")
    monkeypatch.setenv("COMBADGE_PROCESSING_ENABLE_CACHING", "false")
    
    # Disable external services
    monkeypatch.setenv("COMBADGE_LLM_BASE_URL", "mock://localhost")
    monkeypatch.setenv("COMBADGE_API_BASE_URL", "mock://test.api.com")


# Error Injection Fixtures for Robustness Testing
@pytest.fixture
def network_error_injector():
    """Inject network errors for robustness testing"""
    class NetworkErrorInjector:
        def __init__(self):
            self.error_rate = 0.0
            self.error_types = ['timeout', 'connection_error', 'http_error']
            
        def set_error_rate(self, rate: float):
            self.error_rate = rate
            
        def should_inject_error(self) -> bool:
            import random
            return random.random() < self.error_rate
            
        def get_random_error(self):
            import random
            import requests
            
            error_type = random.choice(self.error_types)
            if error_type == 'timeout':
                return requests.Timeout("Injected timeout error")
            elif error_type == 'connection_error':
                return requests.ConnectionError("Injected connection error")
            else:
                response = Mock()
                response.status_code = random.choice([500, 502, 503, 504])
                return requests.HTTPError("Injected HTTP error", response=response)
    
    return NetworkErrorInjector()


# Test Markers
pytest_plugins = [
    "pytest_asyncio",
    "pytest_mock", 
    "pytest_cov"
]

# Custom pytest markers
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )


# Test Collection Hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location"""
    for item in items:
        # Add markers based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)


# Test Reporting Helpers
@pytest.fixture
def test_report():
    """Test reporting helper"""
    class TestReport:
        def __init__(self):
            self.metrics = {}
            self.logs = []
            
        def add_metric(self, name: str, value: Any):
            self.metrics[name] = value
            
        def add_log(self, message: str, level: str = "INFO"):
            self.logs.append({
                'timestamp': datetime.now(),
                'level': level,
                'message': message
            })
            
        def get_summary(self) -> Dict[str, Any]:
            return {
                'metrics': self.metrics,
                'log_count': len(self.logs),
                'timestamp': datetime.now().isoformat()
            }
    
    return TestReport()