"""
Integration tests for email-to-API workflow.

Tests the complete flow from email parsing through to API request generation,
including all intermediate processing steps and validation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from combadge.fleet.processors.email_parser import EmailParser
from combadge.fleet.processors.command_processor import CommandProcessor
from combadge.intelligence.intent_classifier import IntentClassifier
from combadge.intelligence.entity_extractor import EntityExtractor
from combadge.intelligence.reasoning_engine import ReasoningEngine
from combadge.fleet.templates.template_manager import TemplateManager
from combadge.api.client import HTTPClient
from combadge.core.application import Application


class TestEmailToAPIWorkflow:
    """Integration tests for complete email-to-API workflow"""

    @pytest.fixture
    async def integrated_application(self):
        """Create integrated application with all components"""
        # Create real components with some mocking for external dependencies
        email_parser = EmailParser()
        
        # Mock LLM components for predictable responses
        mock_llm_manager = Mock()
        mock_llm_manager.is_available = Mock(return_value=True)
        mock_llm_manager.generate_response = AsyncMock()
        
        intent_classifier = IntentClassifier(llm_manager=mock_llm_manager)
        entity_extractor = EntityExtractor(llm_manager=mock_llm_manager)
        reasoning_engine = ReasoningEngine(llm_manager=mock_llm_manager)
        
        template_manager = TemplateManager()
        # Load test templates
        test_templates = {
            "maintenance_scheduling": {
                "schedule_maintenance": {
                    "template_id": "schedule_maintenance",
                    "intent": "maintenance_scheduling",
                    "api_endpoint": "/api/maintenance",
                    "method": "POST",
                    "template": {
                        "vehicle_id": "{{vehicle_id}}",
                        "scheduled_date": "{{date}}",
                        "maintenance_type": "{{maintenance_type|default:routine}}"
                    }
                }
            },
            "vehicle_reservation": {
                "reserve_vehicle": {
                    "template_id": "reserve_vehicle",
                    "intent": "vehicle_reservation",
                    "api_endpoint": "/api/reservations",
                    "method": "POST",
                    "template": {
                        "vehicle_id": "{{vehicle_id}}",
                        "start_time": "{{start_time}}",
                        "end_time": "{{end_time}}",
                        "reserved_by": "{{user_email}}"
                    }
                }
            }
        }
        template_manager.templates = test_templates
        
        # Mock HTTP client
        mock_http_client = Mock(spec=HTTPClient)
        mock_http_client.post = AsyncMock()
        mock_http_client.get = AsyncMock()
        
        command_processor = CommandProcessor(
            intent_classifier=intent_classifier,
            entity_extractor=entity_extractor,
            reasoning_engine=reasoning_engine,
            template_manager=template_manager
        )
        
        # Create application instance
        app = Application()
        app.email_parser = email_parser
        app.command_processor = command_processor
        app.http_client = mock_http_client
        app.llm_manager = mock_llm_manager
        
        return app

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_maintenance_request_email_workflow(self, integrated_application):
        """Test complete workflow for maintenance request email"""
        app = integrated_application
        
        # Setup LLM responses for this workflow
        app.llm_manager.generate_response.side_effect = [
            # Intent classification response
            {
                "intent": "maintenance_scheduling",
                "confidence": 0.95,
                "reasoning": ["Clear maintenance request", "Vehicle ID identified"]
            },
            # Entity extraction response
            {
                "entities": {
                    "vehicle_id": "F-123",
                    "date": "2024-03-16T10:00:00",
                    "maintenance_type": "oil_change"
                },
                "confidence": 0.90
            },
            # Reasoning response
            {
                "reasoning_steps": [
                    "User requests maintenance for vehicle F-123",
                    "Specific maintenance type identified as oil change",
                    "Date specified for tomorrow",
                    "All required information present"
                ],
                "conclusion": "Valid maintenance scheduling request",
                "confidence": 0.93,
                "recommendation": "proceed",
                "risk_level": "low"
            }
        ]
        
        # Setup HTTP client response
        app.http_client.post.return_value = {
            "appointment_id": "M-001",
            "status": "scheduled",
            "vehicle_id": "F-123",
            "scheduled_date": "2024-03-16T10:00:00"
        }
        
        # Test email input
        maintenance_email = """From: fleet.manager@company.com
To: operations@company.com
Subject: Vehicle F-123 oil change needed
Date: Thu, 15 Mar 2024 09:00:00 +0000

Hello,

Vehicle F-123 needs an oil change scheduled for tomorrow at 10 AM.
Please arrange for this service.

Thanks,
Fleet Manager
"""
        
        # Execute complete workflow
        # Step 1: Parse email
        parsed_email = app.email_parser.parse_email(maintenance_email)
        
        assert parsed_email.subject == "Vehicle F-123 oil change needed"
        assert parsed_email.sender == "fleet.manager@company.com"
        assert "oil change" in parsed_email.body
        
        # Step 2: Process command from email body
        processing_context = Mock()
        processing_context.user_id = parsed_email.sender
        processing_context.timestamp = parsed_email.timestamp
        
        result = await app.command_processor.process_command(
            parsed_email.body, 
            processing_context
        )
        
        # Verify processing results
        assert result.success is True
        assert result.intent == "maintenance_scheduling"
        assert result.entities["vehicle_id"] == "F-123"
        assert result.entities["maintenance_type"] == "oil_change"
        assert result.recommendation == "proceed"
        
        # Step 3: Verify API request was generated correctly
        assert result.api_request["vehicle_id"] == "F-123"
        assert result.api_request["maintenance_type"] == "oil_change"
        assert result.api_endpoint == "/api/maintenance"
        assert result.http_method == "POST"
        
        # Step 4: Execute API request (simulated)
        api_response = await app.http_client.post(
            result.api_endpoint,
            json=result.api_request
        )
        
        # Verify API call was made correctly
        app.http_client.post.assert_called_once_with(
            "/api/maintenance",
            json=result.api_request
        )
        
        assert api_response["appointment_id"] == "M-001"
        assert api_response["status"] == "scheduled"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_vehicle_reservation_email_workflow(self, integrated_application):
        """Test complete workflow for vehicle reservation email"""
        app = integrated_application
        
        # Setup LLM responses
        app.llm_manager.generate_response.side_effect = [
            # Intent classification
            {
                "intent": "vehicle_reservation",
                "confidence": 0.92,
                "reasoning": ["Reservation request identified", "Vehicle and time specified"]
            },
            # Entity extraction
            {
                "entities": {
                    "vehicle_id": "V-456",
                    "start_time": "2024-03-15T14:00:00",
                    "end_time": "2024-03-15T17:00:00",
                    "user_email": "sales.team@company.com"
                },
                "confidence": 0.88
            },
            # Reasoning
            {
                "reasoning_steps": [
                    "Sales team requests vehicle reservation",
                    "Specific vehicle V-456 identified",
                    "Time slot Friday 2-5 PM confirmed",
                    "Valid business request"
                ],
                "conclusion": "Approve vehicle reservation",
                "confidence": 0.90,
                "recommendation": "proceed",
                "risk_level": "low"
            }
        ]
        
        # Setup HTTP response
        app.http_client.post.return_value = {
            "reservation_id": "R-001",
            "status": "confirmed",
            "vehicle_id": "V-456",
            "start_time": "2024-03-15T14:00:00",
            "end_time": "2024-03-15T17:00:00"
        }
        
        # Test email
        reservation_email = """From: sales.team@company.com
To: fleet@company.com
Subject: Vehicle reservation request
Date: Thu, 14 Mar 2024 12:00:00 +0000

Hi,

I need to reserve vehicle V-456 for a client meeting on Friday from 2 PM to 5 PM.
This is for an important sales presentation.

Please confirm the reservation.

Thanks,
Sales Team
"""
        
        # Execute workflow
        parsed_email = app.email_parser.parse_email(reservation_email)
        
        processing_context = Mock()
        processing_context.user_id = parsed_email.sender
        processing_context.timestamp = parsed_email.timestamp
        
        result = await app.command_processor.process_command(
            parsed_email.body,
            processing_context
        )
        
        # Verify results
        assert result.success is True
        assert result.intent == "vehicle_reservation"
        assert result.entities["vehicle_id"] == "V-456"
        assert result.entities["user_email"] == "sales.team@company.com"
        assert result.recommendation == "proceed"
        
        # Execute API request
        api_response = await app.http_client.post(
            result.api_endpoint,
            json=result.api_request
        )
        
        assert api_response["reservation_id"] == "R-001"
        assert api_response["status"] == "confirmed"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ambiguous_email_workflow(self, integrated_application):
        """Test workflow with ambiguous email content"""
        app = integrated_application
        
        # Setup LLM responses for ambiguous content
        app.llm_manager.generate_response.side_effect = [
            # Intent classification - low confidence
            {
                "intent": "unknown",
                "confidence": 0.35,
                "reasoning": ["Unclear request", "Multiple possible interpretations"]
            },
            # Entity extraction - minimal entities
            {
                "entities": {
                    "vehicle_reference": "the vehicle",
                    "action": "do something"
                },
                "confidence": 0.25
            },
            # Reasoning - request clarification
            {
                "reasoning_steps": [
                    "Email content is very ambiguous",
                    "No specific vehicle identified",
                    "Action requested is unclear",
                    "Insufficient information for processing"
                ],
                "conclusion": "Request requires clarification",
                "confidence": 0.20,
                "recommendation": "request_clarification",
                "risk_level": "medium",
                "clarification_questions": [
                    "Which specific vehicle are you referring to?",
                    "What action would you like to take?",
                    "When do you need this completed?"
                ]
            }
        ]
        
        # Test ambiguous email
        ambiguous_email = """From: user@company.com
To: fleet@company.com
Subject: Question about the vehicle
Date: Thu, 15 Mar 2024 11:00:00 +0000

Hi,

Can you do something with the vehicle? It's about that thing we discussed.
Let me know.

Thanks
"""
        
        # Execute workflow
        parsed_email = app.email_parser.parse_email(ambiguous_email)
        
        processing_context = Mock()
        processing_context.user_id = parsed_email.sender
        
        result = await app.command_processor.process_command(
            parsed_email.body,
            processing_context
        )
        
        # Verify ambiguous handling
        assert result.success is False
        assert result.confidence < 0.5
        assert result.recommendation == "request_clarification"
        assert result.needs_clarification is True
        assert len(result.clarification_questions) > 0
        assert "Which specific vehicle" in result.clarification_questions[0]
        
        # Should not make API calls for ambiguous requests
        app.http_client.post.assert_not_called()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, integrated_application):
        """Test error handling throughout the workflow"""
        app = integrated_application
        
        # Setup LLM failure
        app.llm_manager.generate_response.side_effect = Exception("LLM service unavailable")
        
        # Test email
        test_email = """From: test@company.com
To: fleet@company.com
Subject: Test request
Date: Thu, 15 Mar 2024 10:00:00 +0000

Test request content.
"""
        
        # Execute workflow
        parsed_email = app.email_parser.parse_email(test_email)
        
        processing_context = Mock()
        processing_context.user_id = parsed_email.sender
        
        # Should handle LLM failure gracefully
        with pytest.raises(Exception) as exc_info:
            await app.command_processor.process_command(
                parsed_email.body,
                processing_context
            )
        
        assert "LLM service unavailable" in str(exc_info.value)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_email_processing_workflow(self, integrated_application):
        """Test batch processing of multiple emails"""
        app = integrated_application
        
        # Setup consistent LLM responses for batch processing
        def mock_llm_response(prompt, context=None):
            if "classify" in prompt.lower():
                return {
                    "intent": "maintenance_scheduling",
                    "confidence": 0.90,
                    "reasoning": ["Standard maintenance request"]
                }
            elif "extract" in prompt.lower():
                return {
                    "entities": {
                        "vehicle_id": "F-123",
                        "date": "2024-03-16T10:00:00",
                        "maintenance_type": "routine"
                    },
                    "confidence": 0.85
                }
            else:  # reasoning
                return {
                    "reasoning_steps": ["Valid maintenance request"],
                    "conclusion": "Proceed with maintenance",
                    "confidence": 0.87,
                    "recommendation": "proceed",
                    "risk_level": "low"
                }
        
        app.llm_manager.generate_response.side_effect = mock_llm_response
        
        # Setup HTTP responses
        app.http_client.post.return_value = {
            "appointment_id": "M-001",
            "status": "scheduled"
        }
        
        # Test multiple emails
        emails = [
            """From: user1@company.com
Subject: Maintenance F-123
Test maintenance request 1.""",
            """From: user2@company.com
Subject: Service F-456
Test maintenance request 2.""",
            """From: user3@company.com
Subject: Check F-789
Test maintenance request 3."""
        ]
        
        # Process all emails
        results = []
        for email_content in emails:
            parsed_email = app.email_parser.parse_email(email_content)
            
            processing_context = Mock()
            processing_context.user_id = parsed_email.sender
            
            result = await app.command_processor.process_command(
                parsed_email.body,
                processing_context
            )
            results.append(result)
        
        # Verify all processed successfully
        assert len(results) == 3
        for result in results:
            assert result.success is True
            assert result.intent == "maintenance_scheduling"
            assert result.recommendation == "proceed"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_performance(self, integrated_application, performance_monitor):
        """Test end-to-end performance of email workflow"""
        app = integrated_application
        
        # Setup fast LLM responses
        app.llm_manager.generate_response.side_effect = [
            {"intent": "maintenance_scheduling", "confidence": 0.90},
            {"entities": {"vehicle_id": "F-123"}, "confidence": 0.85},
            {"conclusion": "Proceed", "confidence": 0.87, "recommendation": "proceed", "risk_level": "low"}
        ] * 10  # Repeat for 10 iterations
        
        app.http_client.post.return_value = {"appointment_id": "M-001"}
        
        # Test email
        test_email = """From: test@company.com
Subject: Maintenance request
Schedule maintenance for vehicle F-123 tomorrow.
"""
        
        performance_monitor.start()
        
        # Process multiple emails for performance testing
        tasks = []
        for i in range(10):
            parsed_email = app.email_parser.parse_email(test_email)
            processing_context = Mock()
            processing_context.user_id = f"user{i}@company.com"
            
            task = app.command_processor.process_command(
                parsed_email.body,
                processing_context
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        metrics = performance_monitor.stop()
        
        # Verify all processed successfully
        assert len(results) == 10
        for result in results:
            assert result.success is True
        
        # Check performance metrics
        avg_processing_time = metrics['duration'] / len(results) * 1000  # ms per email
        assert avg_processing_time < 2000  # Should be under 2 seconds per email

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_with_validation_failure(self, integrated_application):
        """Test workflow when validation fails"""
        app = integrated_application
        
        # Setup LLM responses that would normally succeed
        app.llm_manager.generate_response.side_effect = [
            {
                "intent": "vehicle_reservation",
                "confidence": 0.90,
                "reasoning": ["Reservation request"]
            },
            {
                "entities": {
                    "vehicle_id": "V-456",
                    "start_time": "2024-03-15T16:00:00",  # End time before start time
                    "end_time": "2024-03-15T14:00:00",    # This will fail validation
                    "user_email": "user@company.com"
                },
                "confidence": 0.85
            },
            {
                "reasoning_steps": ["Initial assessment looks good"],
                "conclusion": "Proceed with reservation",
                "confidence": 0.80,
                "recommendation": "proceed",
                "risk_level": "low"
            }
        ]
        
        # Test email with invalid time range
        invalid_email = """From: user@company.com
Subject: Vehicle reservation
Reserve vehicle V-456 from 4 PM to 2 PM on Friday.
"""
        
        # Execute workflow
        parsed_email = app.email_parser.parse_email(invalid_email)
        
        processing_context = Mock()
        processing_context.user_id = parsed_email.sender
        
        result = await app.command_processor.process_command(
            parsed_email.body,
            processing_context
        )
        
        # Should fail due to validation error
        assert result.success is False
        assert result.is_valid is False
        assert "end time" in " ".join(result.validation_errors).lower()
        
        # Should not make API calls when validation fails
        app.http_client.post.assert_not_called()

    @pytest.mark.integration
    def test_email_parsing_edge_cases(self, integrated_application):
        """Test email parsing with various edge cases"""
        app = integrated_application
        
        # Test forwarded email
        forwarded_email = """From: admin@company.com
Subject: FWD: Maintenance request

---------- Forwarded message ----------
From: original@company.com
Subject: Maintenance request

Original maintenance request for F-123.
"""
        
        parsed = app.email_parser.parse_email(forwarded_email)
        assert parsed.is_forwarded is True
        assert parsed.original_sender == "original@company.com"
        
        # Test email with attachments
        attachment_email = """From: user@company.com
Subject: Vehicle docs
Content-Type: multipart/mixed; boundary="boundary123"

--boundary123
Content-Type: text/plain

Please process the attached vehicle documentation.

--boundary123
Content-Type: application/pdf
Content-Disposition: attachment; filename="vehicle_info.pdf"

PDF content here
--boundary123--
"""
        
        parsed = app.email_parser.parse_email(attachment_email)
        assert len(parsed.attachments) == 1
        assert parsed.attachments[0]["filename"] == "vehicle_info.pdf"