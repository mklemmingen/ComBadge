"""
End-to-end system integration tests.

Tests the complete ComBadge system from initial input through to final
API execution, including all components working together.
"""

import pytest
import asyncio
import tempfile
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from combadge.core.application import Application
from combadge.core.config_manager import ConfigManager
from combadge.fleet.processors.email_parser import EmailParser
from combadge.fleet.processors.command_processor import CommandProcessor
from combadge.intelligence.llm_manager import LLMManager
from combadge.api.client import HTTPClient
from combadge.ui.components.approval_workflow import ApprovalWorkflow


class TestEndToEndSystem:
    """Complete system integration tests"""

    @pytest.fixture
    async def full_system_application(self, temp_config_dir):
        """Create complete application with all components integrated"""
        # Create test configuration
        test_config = {
            "app_name": "ComBadge-Integration-Test",
            "environment": "testing",
            "debug_mode": True,
            "llm": {
                "model": "test-model",
                "base_url": "http://localhost:11434",
                "temperature": 0.1,
                "timeout": 30
            },
            "api": {
                "base_url": "http://test-api.company.com",
                "timeout": 30,
                "authentication": {
                    "method": "api_key",
                    "api_key": "test-key"
                }
            },
            "ui": {
                "theme": "dark",
                "auto_approve_high_confidence": False
            },
            "processing": {
                "confidence_threshold": 0.8,
                "enable_caching": False
            }
        }
        
        config_file = temp_config_dir / "test_config.yaml"
        with open(config_file, 'w') as f:
            import yaml
            yaml.dump(test_config, f)
        
        # Create application with test config
        app = Application(config_path=str(config_file))
        
        # Setup mocked external dependencies
        mock_llm_manager = Mock(spec=LLMManager)
        mock_llm_manager.is_available = Mock(return_value=True)
        mock_llm_manager.generate_response = AsyncMock()
        
        mock_http_client = Mock(spec=HTTPClient)
        mock_http_client.post = AsyncMock()
        mock_http_client.get = AsyncMock()
        mock_http_client.put = AsyncMock()
        mock_http_client.delete = AsyncMock()
        
        # Inject mocks
        app.llm_manager = mock_llm_manager
        app.http_client = mock_http_client
        
        # Load test templates
        test_templates = {
            "maintenance_scheduling": {
                "schedule_maintenance": {
                    "template_id": "schedule_maintenance",
                    "intent": "maintenance_scheduling",
                    "api_endpoint": "/api/maintenance",
                    "method": "POST",
                    "required_fields": ["vehicle_id", "scheduled_date"],
                    "template": {
                        "vehicle_id": "{{vehicle_id}}",
                        "scheduled_date": "{{date|format_date}}",
                        "maintenance_type": "{{maintenance_type|default:routine}}",
                        "estimated_cost": "{{cost|default:$150}}"
                    }
                }
            },
            "vehicle_reservation": {
                "reserve_vehicle": {
                    "template_id": "reserve_vehicle", 
                    "intent": "vehicle_reservation",
                    "api_endpoint": "/api/reservations",
                    "method": "POST",
                    "required_fields": ["vehicle_id", "start_time", "end_time"],
                    "template": {
                        "vehicle_id": "{{vehicle_id}}",
                        "start_time": "{{start_time|format_datetime}}",
                        "end_time": "{{end_time|format_datetime}}",
                        "reserved_by": "{{user_email}}",
                        "purpose": "{{purpose|default:business_use}}"
                    }
                }
            },
            "vehicle_operations": {
                "create_vehicle": {
                    "template_id": "create_vehicle",
                    "intent": "vehicle_operations", 
                    "api_endpoint": "/api/vehicles",
                    "method": "POST",
                    "required_fields": ["make", "model", "year", "vin"],
                    "template": {
                        "make": "{{make}}",
                        "model": "{{model}}",
                        "year": "{{year|int}}",
                        "vin": "{{vin}}",
                        "license_plate": "{{license_plate|optional}}",
                        "status": "{{status|default:active}}"
                    }
                }
            }
        }
        
        if hasattr(app, 'template_manager'):
            app.template_manager.templates = test_templates
        
        await app.initialize()
        return app

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_email_processing_workflow(self, full_system_application):
        """Test complete workflow from email input to API execution"""
        app = full_system_application
        
        # Setup realistic LLM responses for complete workflow
        app.llm_manager.generate_response.side_effect = [
            # Intent classification
            {
                "intent": "maintenance_scheduling",
                "confidence": 0.94,
                "reasoning": [
                    "Clear maintenance request identified",
                    "Vehicle F-123 specified",
                    "Date and time provided"
                ]
            },
            # Entity extraction
            {
                "entities": {
                    "vehicle_id": "F-123",
                    "date": "2024-03-16T10:00:00",
                    "maintenance_type": "oil_change",
                    "cost": "$175"
                },
                "confidence": 0.91,
                "entity_scores": {
                    "vehicle_id": 0.98,
                    "date": 0.87,
                    "maintenance_type": 0.89,
                    "cost": 0.92
                }
            },
            # Chain of thought reasoning
            {
                "reasoning_steps": [
                    "User requests oil change for vehicle F-123",
                    "Scheduled for tomorrow at 10 AM",
                    "Cost specified as $175 which is reasonable",
                    "All required information present",
                    "Standard maintenance request with low risk",
                    "Vehicle should be validated for existence",
                    "Time slot should be checked for availability"
                ],
                "conclusion": "Valid maintenance request ready for processing",
                "confidence": 0.93,
                "recommendation": "proceed",
                "risk_level": "low",
                "required_validations": ["vehicle_exists", "time_available"],
                "estimated_duration": "45 minutes"
            }
        ]
        
        # Setup API responses
        app.http_client.get.return_value = {
            "vehicle": {"id": "F-123", "status": "active", "make": "Ford"},
            "exists": True
        }
        
        app.http_client.post.return_value = {
            "appointment_id": "M-12345",
            "status": "scheduled",
            "vehicle_id": "F-123",
            "scheduled_date": "2024-03-16T10:00:00",
            "maintenance_type": "oil_change",
            "estimated_cost": "$175",
            "service_center": "Main Garage",
            "confirmation_code": "MAINT-12345"
        }
        
        # Input email
        maintenance_email = """From: fleet.manager@company.com
To: operations@company.com
Subject: Oil Change Needed - Vehicle F-123
Date: Fri, 15 Mar 2024 09:00:00 +0000
Message-ID: <email123@company.com>

Hello Operations Team,

Vehicle F-123 needs an oil change scheduled for tomorrow (March 16th) at 10:00 AM.
The estimated cost should be around $175.

Please confirm the appointment.

Best regards,
Fleet Manager
fleet.manager@company.com
"""
        
        # Execute complete workflow
        result = await app.process_email(maintenance_email)
        
        # Verify complete workflow results
        assert result["success"] is True
        assert result["workflow_type"] == "email_to_api"
        
        # Verify email parsing
        assert result["email_parsed"]["subject"] == "Oil Change Needed - Vehicle F-123"
        assert result["email_parsed"]["sender"] == "fleet.manager@company.com"
        
        # Verify NLP processing
        assert result["nlp_processing"]["intent"] == "maintenance_scheduling"
        assert result["nlp_processing"]["confidence"] >= 0.90
        assert result["nlp_processing"]["entities"]["vehicle_id"] == "F-123"
        
        # Verify reasoning
        assert result["reasoning"]["recommendation"] == "proceed"
        assert result["reasoning"]["risk_level"] == "low"
        
        # Verify API execution
        assert result["api_execution"]["appointment_id"] == "M-12345"
        assert result["api_execution"]["confirmation_code"] == "MAINT-12345"
        
        # Verify API calls were made correctly
        app.http_client.get.assert_called_with("/api/vehicles/F-123")  # Vehicle validation
        app.http_client.post.assert_called_with(
            "/api/maintenance",
            json={
                "vehicle_id": "F-123",
                "scheduled_date": "2024-03-16T10:00:00", 
                "maintenance_type": "oil_change",
                "estimated_cost": "$175"
            }
        )

    @pytest.mark.integration
    @pytest.mark.asyncio 
    async def test_natural_language_command_processing(self, full_system_application):
        """Test direct natural language command processing"""
        app = full_system_application
        
        # Setup LLM responses for vehicle reservation
        app.llm_manager.generate_response.side_effect = [
            {
                "intent": "vehicle_reservation",
                "confidence": 0.92,
                "reasoning": ["Clear reservation request", "Specific vehicle and time"]
            },
            {
                "entities": {
                    "vehicle_id": "V-456",
                    "start_time": "2024-03-18T14:00:00",
                    "end_time": "2024-03-18T17:00:00",
                    "user_email": "sales.team@company.com",
                    "purpose": "client_meeting"
                },
                "confidence": 0.89
            },
            {
                "reasoning_steps": [
                    "Sales team requests vehicle V-456",
                    "Monday 2-5 PM timeframe specified",
                    "Client meeting purpose is appropriate",
                    "Standard business reservation"
                ],
                "conclusion": "Approve vehicle reservation",
                "confidence": 0.90,
                "recommendation": "proceed",
                "risk_level": "low"
            }
        ]
        
        # Setup API responses
        app.http_client.get.return_value = {
            "vehicle": {"id": "V-456", "status": "available"},
            "availability": True
        }
        
        app.http_client.post.return_value = {
            "reservation_id": "R-98765",
            "status": "confirmed", 
            "vehicle_id": "V-456",
            "start_time": "2024-03-18T14:00:00",
            "end_time": "2024-03-18T17:00:00",
            "reserved_by": "sales.team@company.com"
        }
        
        # Process natural language command
        command = "Reserve vehicle V-456 for Monday from 2 PM to 5 PM for client meeting"
        
        result = await app.process_command(
            command,
            user_id="sales.team@company.com",
            session_id="session_001"
        )
        
        # Verify processing results
        assert result["success"] is True
        assert result["intent"] == "vehicle_reservation"
        assert result["entities"]["vehicle_id"] == "V-456"
        assert result["entities"]["purpose"] == "client_meeting"
        assert result["api_result"]["reservation_id"] == "R-98765"
        
        # Verify API calls
        app.http_client.post.assert_called_with(
            "/api/reservations",
            json={
                "vehicle_id": "V-456",
                "start_time": "2024-03-18T14:00:00",
                "end_time": "2024-03-18T17:00:00",
                "reserved_by": "sales.team@company.com",
                "purpose": "client_meeting"
            }
        )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ui_approval_integration(self, full_system_application):
        """Test UI approval workflow integration"""
        app = full_system_application
        
        # Setup LLM responses for medium confidence scenario
        app.llm_manager.generate_response.side_effect = [
            {
                "intent": "vehicle_operations",
                "confidence": 0.78,  # Medium confidence
                "reasoning": ["Vehicle creation request", "Some details unclear"]
            },
            {
                "entities": {
                    "make": "Toyota",
                    "model": "Camry",
                    "year": "2024",
                    "vin": "1HGCM82633A004352",
                    "status": "active"
                },
                "confidence": 0.82
            },
            {
                "reasoning_steps": [
                    "Request to add new Toyota Camry",
                    "VIN appears valid",
                    "Year is current (2024)", 
                    "Medium confidence due to informal description"
                ],
                "conclusion": "Valid vehicle addition with minor uncertainties",
                "confidence": 0.79,
                "recommendation": "require_approval",  # Medium confidence triggers approval
                "risk_level": "medium"
            }
        ]
        
        # Mock UI approval workflow
        mock_approval_workflow = Mock(spec=ApprovalWorkflow)
        mock_approval_workflow.load_interpretation = Mock()
        mock_approval_workflow.await_user_decision = AsyncMock(return_value={
            "decision": "approved",
            "modifications": {},
            "user_id": "fleet.manager@company.com",
            "timestamp": datetime.now()
        })
        
        app.approval_workflow = mock_approval_workflow
        
        # Setup API response
        app.http_client.post.return_value = {
            "vehicle_id": "NEW-001",
            "status": "created",
            "make": "Toyota",
            "model": "Camry",
            "vin": "1HGCM82633A004352"
        }
        
        # Process command requiring approval
        command = "Add new Toyota Camry 2024 with VIN 1HGCM82633A004352 to the fleet"
        
        result = await app.process_command_with_approval(
            command,
            user_id="user@company.com"
        )
        
        # Verify approval workflow was triggered
        mock_approval_workflow.load_interpretation.assert_called_once()
        mock_approval_workflow.await_user_decision.assert_called_once()
        
        # Verify final result after approval
        assert result["success"] is True
        assert result["approval_required"] is True
        assert result["user_decision"] == "approved"
        assert result["api_result"]["vehicle_id"] == "NEW-001"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, full_system_application):
        """Test system-wide error handling and recovery"""
        app = full_system_application
        
        # Test LLM service failure
        app.llm_manager.generate_response.side_effect = Exception("LLM service down")
        
        command = "Test command during LLM failure"
        
        result = await app.process_command(command, user_id="test@company.com")
        
        # System should handle gracefully
        assert result["success"] is False
        assert result["error_type"] == "llm_service_error"
        assert "LLM service down" in result["error_message"]
        
        # Test API service failure
        app.llm_manager.generate_response.side_effect = None
        app.llm_manager.generate_response.return_value = {
            "intent": "maintenance_scheduling",
            "confidence": 0.90,
            "entities": {"vehicle_id": "F-123"},
            "reasoning_steps": ["Valid request"],
            "recommendation": "proceed"
        }
        
        app.http_client.post.side_effect = Exception("API service unavailable")
        
        result = await app.process_command(
            "Schedule maintenance for F-123",
            user_id="test@company.com"
        )
        
        # Should process NLP but fail at API execution
        assert result["success"] is False
        assert result["error_type"] == "api_execution_error"
        assert result["nlp_processing"]["success"] is True  # NLP should have succeeded

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_request_processing(self, full_system_application):
        """Test system handling of concurrent requests"""
        app = full_system_application
        
        # Setup consistent responses
        app.llm_manager.generate_response.side_effect = [
            {"intent": "maintenance_scheduling", "confidence": 0.90},
            {"entities": {"vehicle_id": "F-123"}, "confidence": 0.88},
            {"conclusion": "Valid request", "recommendation": "proceed", "confidence": 0.89}
        ] * 10  # Repeat for 10 concurrent requests
        
        app.http_client.post.return_value = {"appointment_id": "M-001", "status": "scheduled"}
        
        # Create concurrent requests
        commands = [
            f"Schedule maintenance for vehicle F-12{i}"
            for i in range(10)
        ]
        
        # Process concurrently
        tasks = [
            app.process_command(command, user_id=f"user{i}@company.com")
            for i, command in enumerate(commands)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all processed successfully
        assert len(results) == 10
        for result in results:
            assert result["success"] is True
        
        # Verify API was called for each request
        assert app.http_client.post.call_count == 10

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_configuration_driven_behavior(self, full_system_application):
        """Test system behavior changes based on configuration"""
        app = full_system_application
        
        # Test with high confidence threshold
        app.config.processing.confidence_threshold = 0.95
        
        app.llm_manager.generate_response.side_effect = [
            {"intent": "maintenance_scheduling", "confidence": 0.92},  # Below threshold
            {"entities": {"vehicle_id": "F-123"}, "confidence": 0.90},
            {"conclusion": "Valid but uncertain", "confidence": 0.91, "recommendation": "proceed"}
        ]
        
        result = await app.process_command(
            "Maybe schedule maintenance for F-123?",
            user_id="test@company.com"
        )
        
        # Should require approval due to low confidence relative to threshold
        assert result["confidence_below_threshold"] is True
        if "approval_required" in result:
            assert result["approval_required"] is True
        
        # Test with auto-approval enabled
        app.config.ui.auto_approve_high_confidence = True
        app.config.ui.confidence_threshold = 0.85
        
        app.llm_manager.generate_response.side_effect = [
            {"intent": "maintenance_scheduling", "confidence": 0.96},  # Above threshold
            {"entities": {"vehicle_id": "F-123"}, "confidence": 0.94},
            {"conclusion": "High confidence request", "confidence": 0.95, "recommendation": "proceed"}
        ]
        
        app.http_client.post.return_value = {"appointment_id": "M-002"}
        
        result = await app.process_command(
            "Schedule maintenance for F-123 tomorrow",
            user_id="test@company.com"
        )
        
        # Should auto-execute due to high confidence
        assert result["success"] is True
        assert result.get("auto_approved", False) is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_audit_logging_integration(self, full_system_application):
        """Test comprehensive audit logging"""
        app = full_system_application
        
        # Enable audit logging
        app.config.logging.audit_enabled = True
        
        # Setup successful processing
        app.llm_manager.generate_response.side_effect = [
            {"intent": "vehicle_reservation", "confidence": 0.93},
            {"entities": {"vehicle_id": "V-456"}, "confidence": 0.90},
            {"conclusion": "Valid reservation", "confidence": 0.91, "recommendation": "proceed"}
        ]
        
        app.http_client.post.return_value = {"reservation_id": "R-001"}
        
        # Process command with audit logging
        result = await app.process_command(
            "Reserve vehicle V-456 for tomorrow",
            user_id="fleet.manager@company.com",
            session_id="session_123"
        )
        
        # Verify audit logs were created
        if hasattr(app, 'audit_logger'):
            audit_logs = app.audit_logger.get_recent_logs(limit=5)
            
            # Should log key events
            log_events = [log["event_type"] for log in audit_logs]
            expected_events = [
                "command_received",
                "nlp_processing_completed", 
                "api_request_executed",
                "command_completed"
            ]
            
            for event in expected_events:
                assert event in log_events

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_system_performance_end_to_end(self, full_system_application, performance_monitor):
        """Test complete system performance"""
        app = full_system_application
        
        # Setup fast responses
        app.llm_manager.generate_response.side_effect = [
            {"intent": "maintenance_scheduling", "confidence": 0.90},
            {"entities": {"vehicle_id": "F-123"}, "confidence": 0.88},
            {"conclusion": "Valid", "confidence": 0.89, "recommendation": "proceed"}
        ] * 20  # For 20 iterations
        
        app.http_client.post.return_value = {"success": True}
        
        performance_monitor.start()
        
        # Process multiple commands end-to-end
        tasks = [
            app.process_command(
                f"Schedule maintenance for vehicle F-12{i % 10}",
                user_id=f"user{i}@company.com"
            ) for i in range(20)
        ]
        
        results = await asyncio.gather(*tasks)
        
        metrics = performance_monitor.stop()
        
        # Verify all completed successfully
        assert len(results) == 20
        for result in results:
            assert result["success"] is True
        
        # Check performance metrics
        avg_end_to_end_time = metrics['duration'] / len(results) * 1000  # ms per command
        assert avg_end_to_end_time < 3000  # Should be under 3 seconds end-to-end
        
        # Memory usage should be reasonable
        peak_memory_mb = metrics.get('peak_memory', 0) / (1024 * 1024)
        assert peak_memory_mb < 500  # Should use less than 500MB

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_data_validation_integration(self, full_system_application):
        """Test data validation throughout the system"""
        app = full_system_application
        
        # Setup responses that would normally pass but fail validation
        app.llm_manager.generate_response.side_effect = [
            {"intent": "vehicle_reservation", "confidence": 0.88},
            {
                "entities": {
                    "vehicle_id": "V-456",
                    "start_time": "2024-03-15T16:00:00",
                    "end_time": "2024-03-15T14:00:00"  # End before start - validation error
                },
                "confidence": 0.85
            },
            {"conclusion": "Reservation request", "confidence": 0.86, "recommendation": "proceed"}
        ]
        
        # Process command with validation issue
        result = await app.process_command(
            "Reserve V-456 from 4 PM to 2 PM tomorrow",  # Invalid time range
            user_id="test@company.com"
        )
        
        # Should fail validation
        assert result["success"] is False
        assert result["validation_failed"] is True
        assert "end time" in result["validation_errors"][0].lower()
        
        # API should not be called due to validation failure
        app.http_client.post.assert_not_called()

    @pytest.mark.integration
    def test_system_cleanup_and_resource_management(self, full_system_application):
        """Test proper system cleanup and resource management"""
        app = full_system_application
        
        # Verify system can be properly cleaned up
        initial_resources = {
            "open_connections": len(getattr(app.http_client, '_connections', [])),
            "active_sessions": len(getattr(app.llm_manager, '_sessions', [])),
            "temp_files": len(list(Path(tempfile.gettempdir()).glob("combadge_*")))
        }
        
        # Perform cleanup
        asyncio.run(app.cleanup())
        
        # Verify cleanup occurred (mock verification)
        if hasattr(app.http_client, 'close'):
            app.http_client.close.assert_called_once()
        
        if hasattr(app.llm_manager, 'cleanup'):
            app.llm_manager.cleanup.assert_called_once()
        
        # System should be in clean state
        assert app.is_initialized is False