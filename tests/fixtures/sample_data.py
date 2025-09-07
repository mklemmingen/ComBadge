"""
Sample test data for ComBadge testing framework.

This module provides realistic sample data for testing all components
of the ComBadge fleet management NLP processor.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any

# Sample Email Data
SAMPLE_EMAILS = [
    {
        "id": "email_001",
        "subject": "Vehicle F-123 needs maintenance",
        "from": "fleet.manager@company.com",
        "to": "operations@company.com",
        "body": "Hello, Vehicle F-123 requires routine maintenance scheduled for tomorrow at 10:00 AM. Please arrange for the service.",
        "timestamp": datetime.now() - timedelta(hours=2),
        "attachments": []
    },
    {
        "id": "email_002", 
        "subject": "Reserve vehicle V-456 for sales meeting",
        "from": "sales.team@company.com",
        "to": "fleet@company.com",
        "body": "Hi, I need to reserve vehicle V-456 for a client meeting on Friday from 2 PM to 5 PM. Thanks!",
        "timestamp": datetime.now() - timedelta(hours=1),
        "attachments": []
    },
    {
        "id": "email_003",
        "subject": "New vehicle registration - Toyota Camry 2024",
        "from": "admin@company.com",
        "to": "fleet@company.com", 
        "body": "Please register a new Toyota Camry 2024, VIN: 1HGCM82633A123456, License: ABC-1234",
        "timestamp": datetime.now() - timedelta(minutes=30),
        "attachments": ["vehicle_docs.pdf"]
    }
]

# Sample Natural Language Commands
SAMPLE_COMMANDS = [
    {
        "id": "cmd_001",
        "text": "Schedule maintenance for vehicle F-123 tomorrow at 10 AM",
        "expected_intent": "maintenance_scheduling",
        "expected_entities": {"vehicle_id": "F-123", "date": "tomorrow", "time": "10 AM"},
        "expected_confidence": 0.95
    },
    {
        "id": "cmd_002", 
        "text": "Reserve vehicle V-456 for Friday 2-5 PM",
        "expected_intent": "vehicle_reservation",
        "expected_entities": {"vehicle_id": "V-456", "date": "Friday", "start_time": "2 PM", "end_time": "5 PM"},
        "expected_confidence": 0.92
    },
    {
        "id": "cmd_003",
        "text": "Add new Toyota Camry to fleet with VIN 1HGCM82633A123456",
        "expected_intent": "vehicle_operations",
        "expected_entities": {"make": "Toyota", "model": "Camry", "vin": "1HGCM82633A123456"},
        "expected_confidence": 0.88
    },
    {
        "id": "cmd_004",
        "text": "Show all vehicles available for reservation next week",
        "expected_intent": "data_query",
        "expected_entities": {"time_range": "next week", "status": "available"},
        "expected_confidence": 0.85
    },
    {
        "id": "cmd_005",
        "text": "Assign parking spot B-12 to vehicle P-789",
        "expected_intent": "parking_management", 
        "expected_entities": {"parking_spot": "B-12", "vehicle_id": "P-789"},
        "expected_confidence": 0.90
    }
]

# Sample API Response Data
SAMPLE_API_RESPONSES = {
    "vehicles_list": {
        "vehicles": [
            {
                "id": "F-123",
                "make": "Ford",
                "model": "Transit",
                "year": 2023,
                "vin": "1FTBW2CM5NKA12345",
                "license_plate": "FLT-123",
                "status": "active",
                "location": "Building A",
                "mileage": 15000,
                "last_service": "2024-01-15"
            },
            {
                "id": "V-456",
                "make": "Chevrolet",
                "model": "Malibu", 
                "year": 2022,
                "vin": "1G1ZE5ST4NF123456",
                "license_plate": "VAN-456",
                "status": "available",
                "location": "Lot C",
                "mileage": 22000,
                "last_service": "2024-02-10"
            }
        ],
        "total": 2
    },
    "maintenance_schedule": {
        "appointments": [
            {
                "id": "M-001",
                "vehicle_id": "F-123",
                "type": "routine",
                "scheduled_date": "2024-03-16T10:00:00Z",
                "status": "scheduled",
                "service_center": "Main Garage"
            }
        ],
        "total": 1
    },
    "reservations": {
        "reservations": [
            {
                "id": "R-001",
                "vehicle_id": "V-456",
                "start_time": "2024-03-15T14:00:00Z",
                "end_time": "2024-03-15T17:00:00Z",
                "status": "confirmed",
                "reserved_by": "sales.team@company.com"
            }
        ],
        "total": 1
    }
}

# Sample Configuration Data
SAMPLE_CONFIGURATIONS = {
    "test_config": {
        "app_name": "ComBadge-Test",
        "environment": "testing",
        "debug_mode": True,
        "llm": {
            "model": "test-model",
            "temperature": 0.1,
            "base_url": "mock://localhost"
        },
        "api": {
            "base_url": "mock://test.api.com",
            "timeout": 15,
            "authentication": {"method": "api_key", "api_key": "test-key"}
        }
    },
    "minimal_config": {
        "app_name": "ComBadge-Minimal",
        "api": {"base_url": "http://localhost:8000"}
    },
    "production_like_config": {
        "app_name": "ComBadge-Prod-Test",
        "environment": "production",
        "debug_mode": False,
        "processing": {"confidence_threshold": 0.95},
        "logging": {"level": "INFO", "audit_enabled": True}
    }
}

# Mock Vehicle Data
MOCK_VEHICLE_DATA = [
    {
        "id": "F-123",
        "make": "Ford",
        "model": "Transit",
        "year": 2023,
        "vin": "1FTBW2CM5NKA12345", 
        "license_plate": "FLT-123",
        "status": "active",
        "location": "Building A",
        "mileage": 15000,
        "fuel_level": 0.75,
        "last_service": "2024-01-15",
        "next_service_due": "2024-04-15",
        "driver_assigned": "john.doe@company.com"
    },
    {
        "id": "V-456",
        "make": "Chevrolet", 
        "model": "Malibu",
        "year": 2022,
        "vin": "1G1ZE5ST4NF123456",
        "license_plate": "VAN-456", 
        "status": "available",
        "location": "Lot C",
        "mileage": 22000,
        "fuel_level": 0.60,
        "last_service": "2024-02-10",
        "next_service_due": "2024-05-10",
        "driver_assigned": None
    },
    {
        "id": "T-789",
        "make": "Toyota",
        "model": "Camry",
        "year": 2024,
        "vin": "1HGCM82633A123456",
        "license_plate": "TOY-789",
        "status": "maintenance",
        "location": "Service Bay 1", 
        "mileage": 5000,
        "fuel_level": 0.25,
        "last_service": "2024-03-10",
        "next_service_due": "2024-06-10",
        "driver_assigned": "jane.smith@company.com"
    }
]

# Sample LLM Responses for Testing
SAMPLE_LLM_RESPONSES = {
    "intent_classification": {
        "high_confidence": {
            "intent": "vehicle_operations",
            "confidence": 0.95,
            "reasoning": ["Clear vehicle operation keyword", "Specific vehicle ID mentioned", "Action verb identified"]
        },
        "medium_confidence": {
            "intent": "maintenance_scheduling", 
            "confidence": 0.75,
            "reasoning": ["Maintenance-related terms", "Some ambiguity in timing", "Vehicle reference unclear"]
        },
        "low_confidence": {
            "intent": "unknown",
            "confidence": 0.30,
            "reasoning": ["Unclear request", "Multiple possible interpretations", "Missing key information"]
        }
    },
    "entity_extraction": {
        "vehicle_entities": {
            "entities": {
                "vehicle_id": "F-123",
                "make": "Ford",
                "model": "Transit",
                "license_plate": "FLT-123"
            },
            "confidence": 0.90
        },
        "temporal_entities": {
            "entities": {
                "date": "2024-03-15",
                "time": "10:00 AM",
                "duration": "2 hours"
            },
            "confidence": 0.85
        },
        "location_entities": {
            "entities": {
                "location": "Building A",
                "parking_spot": "B-12",
                "service_center": "Main Garage"
            },
            "confidence": 0.88
        }
    }
}

# Sample Error Scenarios for Testing
SAMPLE_ERROR_SCENARIOS = {
    "api_errors": {
        "timeout": {"error": "Request timeout", "status_code": 408},
        "authentication": {"error": "Invalid credentials", "status_code": 401},
        "not_found": {"error": "Resource not found", "status_code": 404},
        "server_error": {"error": "Internal server error", "status_code": 500}
    },
    "validation_errors": {
        "missing_required_field": {"error": "Required field 'vehicle_id' missing"},
        "invalid_format": {"error": "Invalid date format"},
        "business_rule_violation": {"error": "Vehicle already reserved for specified time"}
    },
    "llm_errors": {
        "connection_error": {"error": "Failed to connect to LLM service"},
        "parsing_error": {"error": "Failed to parse LLM response"},
        "confidence_too_low": {"error": "LLM confidence below threshold"}
    }
}

# Sample Performance Benchmarks
SAMPLE_PERFORMANCE_BENCHMARKS = {
    "response_times": {
        "intent_classification": {"target": 200, "acceptable": 500},  # milliseconds
        "entity_extraction": {"target": 150, "acceptable": 400},
        "template_generation": {"target": 100, "acceptable": 250},
        "api_request": {"target": 1000, "acceptable": 3000}
    },
    "memory_usage": {
        "baseline": 50,  # MB
        "processing_peak": 150,  # MB
        "acceptable_limit": 300  # MB
    },
    "throughput": {
        "requests_per_minute": {"target": 60, "minimum": 30},
        "concurrent_users": {"target": 10, "minimum": 5}
    }
}

# Test Validation Rules
TEST_VALIDATION_RULES = {
    "vehicle_id_formats": [
        r'^[A-Z]-\d{3,4}$',  # F-123, V-456
        r'^[A-Z]{3}-\d{3}$',  # FLT-123, VAN-456
        r'^[A-Z]\d{3,4}$'     # F123, V456
    ],
    "email_formats": [
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    ],
    "date_formats": [
        r'^\d{4}-\d{2}-\d{2}$',  # 2024-03-15
        r'^\d{1,2}/\d{1,2}/\d{4}$',  # 3/15/2024
        r'^(today|tomorrow|yesterday)$'  # relative dates
    ]
}