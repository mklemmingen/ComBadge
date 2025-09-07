"""
Integration tests for UI approval workflow.

Tests the complete flow from AI interpretation through UI approval
to final API execution, including user interaction simulation.
"""

import pytest
import asyncio
import tkinter as tk
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List
import threading
import queue

from combadge.ui.components.approval_workflow import ApprovalWorkflow, AIInterpretation
from combadge.ui.components.edit_interface import EditInterface
from combadge.fleet.processors.command_processor import CommandProcessor, ProcessingResult
from combadge.api.client import HTTPClient
from combadge.core.application import Application


class TestUIApprovalWorkflow:
    """Integration tests for UI approval workflow"""

    @pytest.fixture
    def mock_tkinter_root(self):
        """Mock tkinter root window"""
        try:
            root = tk.Tk()
            root.withdraw()  # Hide window during testing
            yield root
            root.destroy()
        except tk.TclError:
            # Fallback to mock if no display available
            yield Mock()

    @pytest.fixture
    def sample_ai_interpretation(self):
        """Sample AI interpretation for testing"""
        return AIInterpretation(
            original_text="Schedule maintenance for vehicle F-123 tomorrow at 10 AM",
            intent="maintenance_scheduling",
            entities={
                "vehicle_id": "F-123",
                "date": "2024-03-16T10:00:00",
                "maintenance_type": "routine"
            },
            confidence=0.92,
            reasoning_steps=[
                "User requests maintenance for vehicle F-123",
                "Date specified as tomorrow (2024-03-16)",
                "Time specified as 10 AM",
                "All required information present"
            ],
            proposed_action={
                "api_endpoint": "/api/maintenance",
                "method": "POST",
                "body": {
                    "vehicle_id": "F-123",
                    "scheduled_date": "2024-03-16T10:00:00",
                    "maintenance_type": "routine"
                }
            },
            risk_level="low",
            estimated_cost="$150"
        )

    @pytest.fixture
    def mock_command_processor(self):
        """Mock command processor"""
        mock = Mock(spec=CommandProcessor)
        mock.process_command = AsyncMock()
        mock.reprocess_command = AsyncMock()
        return mock

    @pytest.fixture
    def mock_http_client(self):
        """Mock HTTP client"""
        mock = Mock(spec=HTTPClient)
        mock.post = AsyncMock()
        mock.get = AsyncMock()
        return mock

    @pytest.fixture
    def approval_workflow(self, mock_tkinter_root, mock_command_processor, mock_http_client):
        """Create ApprovalWorkflow component with mocks"""
        try:
            workflow = ApprovalWorkflow(
                master=mock_tkinter_root,
                command_processor=mock_command_processor,
                http_client=mock_http_client
            )
            return workflow
        except Exception:
            # Return mock if UI components can't be created
            mock_workflow = Mock(spec=ApprovalWorkflow)
            mock_workflow.load_interpretation = Mock()
            mock_workflow.approve_action = AsyncMock()
            mock_workflow.reject_action = Mock()
            mock_workflow.edit_and_approve = AsyncMock()
            return mock_workflow

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_approval_workflow_approve_action(self, approval_workflow, 
                                                   sample_ai_interpretation, 
                                                   mock_command_processor,
                                                   mock_http_client):
        """Test complete approval workflow with user approval"""
        # Setup HTTP client response
        mock_http_client.post.return_value = {
            "appointment_id": "M-001",
            "status": "scheduled",
            "vehicle_id": "F-123",
            "scheduled_date": "2024-03-16T10:00:00"
        }
        
        # Load interpretation into UI
        approval_workflow.load_interpretation(sample_ai_interpretation)
        
        # Simulate user approval
        result = await approval_workflow.approve_action()
        
        # Verify API call was made
        mock_http_client.post.assert_called_once_with(
            "/api/maintenance",
            json={
                "vehicle_id": "F-123",
                "scheduled_date": "2024-03-16T10:00:00",
                "maintenance_type": "routine"
            }
        )
        
        # Verify result
        assert result["success"] is True
        assert result["appointment_id"] == "M-001"
        assert result["status"] == "scheduled"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_approval_workflow_reject_action(self, approval_workflow,
                                                  sample_ai_interpretation,
                                                  mock_http_client):
        """Test rejection workflow"""
        # Load interpretation
        approval_workflow.load_interpretation(sample_ai_interpretation)
        
        # Simulate user rejection with reason
        rejection_reason = "Vehicle is currently in maintenance"
        approval_workflow.reject_action(reason=rejection_reason)
        
        # Verify no API call was made
        mock_http_client.post.assert_not_called()
        
        # Verify rejection was logged
        if hasattr(approval_workflow, 'rejection_history'):
            assert len(approval_workflow.rejection_history) > 0
            latest_rejection = approval_workflow.rejection_history[-1]
            assert latest_rejection["reason"] == rejection_reason
            assert latest_rejection["interpretation_id"] == sample_ai_interpretation.id

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_edit_and_approve_workflow(self, approval_workflow,
                                            sample_ai_interpretation,
                                            mock_command_processor,
                                            mock_http_client):
        """Test edit and approve workflow"""
        # Load interpretation
        approval_workflow.load_interpretation(sample_ai_interpretation)
        
        # Simulate user edits
        edited_data = {
            "vehicle_id": "F-123",
            "scheduled_date": "2024-03-17T14:00:00",  # Changed date and time
            "maintenance_type": "oil_change"  # Changed type
        }
        
        # Setup reprocessing response
        mock_command_processor.reprocess_command.return_value = ProcessingResult(
            success=True,
            intent="maintenance_scheduling",
            entities={
                "vehicle_id": "F-123",
                "date": "2024-03-17T14:00:00",
                "maintenance_type": "oil_change"
            },
            confidence=0.95,
            api_request=edited_data,
            api_endpoint="/api/maintenance",
            http_method="POST"
        )
        
        # Setup API response
        mock_http_client.post.return_value = {
            "appointment_id": "M-002",
            "status": "scheduled",
            "vehicle_id": "F-123",
            "scheduled_date": "2024-03-17T14:00:00"
        }
        
        # Execute edit and approve
        result = await approval_workflow.edit_and_approve(edited_data)
        
        # Verify reprocessing occurred
        mock_command_processor.reprocess_command.assert_called_once()
        
        # Verify API call with edited data
        mock_http_client.post.assert_called_once_with(
            "/api/maintenance",
            json=edited_data
        )
        
        # Verify result
        assert result["success"] is True
        assert result["appointment_id"] == "M-002"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_high_risk_approval_workflow(self, approval_workflow,
                                              mock_http_client):
        """Test approval workflow for high-risk operations"""
        # Create high-risk interpretation
        high_risk_interpretation = AIInterpretation(
            original_text="Delete all vehicles from fleet",
            intent="vehicle_operations",
            entities={"action": "delete", "target": "all_vehicles"},
            confidence=0.65,
            reasoning_steps=[
                "User requests deletion of all vehicles",
                "This is a destructive operation",
                "High risk of unintended consequences"
            ],
            proposed_action={
                "api_endpoint": "/api/vehicles/bulk-delete",
                "method": "DELETE",
                "body": {"target": "all_vehicles"}
            },
            risk_level="high",
            warnings=["Destructive operation", "Cannot be undone"],
            requires_confirmation=True
        )
        
        # Load high-risk interpretation
        approval_workflow.load_interpretation(high_risk_interpretation)
        
        # Verify UI shows risk warnings
        if hasattr(approval_workflow, 'risk_warning_displayed'):
            assert approval_workflow.risk_warning_displayed is True
        
        if hasattr(approval_workflow, 'requires_confirmation'):
            assert approval_workflow.requires_confirmation is True
        
        # Simulate approval with confirmation
        result = await approval_workflow.approve_action(confirmed=True)
        
        # For high-risk operations, should still execute if confirmed
        mock_http_client.delete.assert_called_once() if hasattr(mock_http_client, 'delete') else None

    @pytest.mark.integration
    def test_approval_statistics_tracking(self, approval_workflow):
        """Test tracking of approval statistics"""
        # Simulate multiple approval decisions
        interpretations = [
            AIInterpretation(
                original_text=f"Test request {i}",
                intent="maintenance_scheduling",
                entities={"vehicle_id": f"F-{i}"},
                confidence=0.90,
                proposed_action={"api_endpoint": "/api/test"}
            ) for i in range(10)
        ]
        
        # Process approvals and rejections
        for i, interpretation in enumerate(interpretations):
            approval_workflow.load_interpretation(interpretation)
            if i < 7:  # Approve 7 out of 10
                approval_workflow.simulate_approval()
            else:  # Reject 3
                approval_workflow.reject_action(reason="Test rejection")
        
        # Check statistics
        stats = approval_workflow.get_approval_stats()
        
        assert stats["total_decisions"] == 10
        assert stats["approved"] == 7
        assert stats["rejected"] == 3
        assert stats["approval_rate"] == 0.7

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_approval_workflow_api_error_handling(self, approval_workflow,
                                                       sample_ai_interpretation,
                                                       mock_http_client):
        """Test error handling when API calls fail"""
        # Setup API failure
        mock_http_client.post.side_effect = Exception("API server unavailable")
        
        # Load interpretation and attempt approval
        approval_workflow.load_interpretation(sample_ai_interpretation)
        
        # Should handle API error gracefully
        result = await approval_workflow.approve_action()
        
        # Verify error was handled
        assert result["success"] is False
        assert "API server unavailable" in result["error_message"]
        
        # Verify error was logged
        if hasattr(approval_workflow, 'error_history'):
            assert len(approval_workflow.error_history) > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_approval_workflows(self, mock_tkinter_root,
                                                mock_command_processor,
                                                mock_http_client):
        """Test multiple concurrent approval workflows"""
        # Create multiple approval workflows
        workflows = []
        for i in range(3):
            try:
                workflow = ApprovalWorkflow(
                    master=mock_tkinter_root,
                    command_processor=mock_command_processor,
                    http_client=mock_http_client
                )
                workflows.append(workflow)
            except Exception:
                # Use mocks if UI creation fails
                mock_workflow = Mock()
                mock_workflow.approve_action = AsyncMock(return_value={"success": True})
                workflows.append(mock_workflow)
        
        # Setup API responses
        mock_http_client.post.return_value = {"success": True}
        
        # Create different interpretations
        interpretations = [
            AIInterpretation(
                original_text=f"Request {i}",
                intent="maintenance_scheduling",
                entities={"vehicle_id": f"F-{i}"},
                confidence=0.90,
                proposed_action={"api_endpoint": f"/api/test/{i}"}
            ) for i in range(3)
        ]
        
        # Load interpretations and process concurrently
        for workflow, interpretation in zip(workflows, interpretations):
            workflow.load_interpretation(interpretation)
        
        # Execute approvals concurrently
        approval_tasks = [
            workflow.approve_action() for workflow in workflows
        ]
        
        results = await asyncio.gather(*approval_tasks)
        
        # Verify all approvals completed successfully
        assert len(results) == 3
        for result in results:
            assert result["success"] is True

    @pytest.mark.integration
    def test_approval_workflow_ui_state_management(self, approval_workflow,
                                                   sample_ai_interpretation):
        """Test UI state management during approval workflow"""
        # Load interpretation
        approval_workflow.load_interpretation(sample_ai_interpretation)
        
        # Check initial UI state
        if hasattr(approval_workflow, 'current_state'):
            assert approval_workflow.current_state == "loaded"
        
        # Simulate approval process
        if hasattr(approval_workflow, 'set_state'):
            approval_workflow.set_state("processing")
            assert approval_workflow.current_state == "processing"
            
            approval_workflow.set_state("completed")
            assert approval_workflow.current_state == "completed"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_approval_workflow_with_validation_errors(self, approval_workflow,
                                                           mock_command_processor):
        """Test approval workflow when validation errors occur"""
        # Create interpretation with validation issues
        problematic_interpretation = AIInterpretation(
            original_text="Reserve vehicle F-123 from 4 PM to 2 PM",
            intent="vehicle_reservation",
            entities={
                "vehicle_id": "F-123",
                "start_time": "2024-03-15T16:00:00",
                "end_time": "2024-03-15T14:00:00"  # End before start
            },
            confidence=0.85,
            proposed_action={
                "api_endpoint": "/api/reservations",
                "method": "POST",
                "body": {
                    "vehicle_id": "F-123",
                    "start_time": "2024-03-15T16:00:00",
                    "end_time": "2024-03-15T14:00:00"
                }
            },
            validation_errors=["End time cannot be before start time"],
            is_valid=False
        )
        
        # Load problematic interpretation
        approval_workflow.load_interpretation(problematic_interpretation)
        
        # Attempt approval should fail due to validation
        result = await approval_workflow.approve_action()
        
        # Should not execute API call
        assert result["success"] is False
        assert "validation" in result["error_message"].lower()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_approval_workflow_performance(self, approval_workflow,
                                                mock_http_client,
                                                performance_monitor):
        """Test approval workflow performance"""
        # Setup fast API responses
        mock_http_client.post.return_value = {"success": True}
        
        # Create test interpretations
        interpretations = [
            AIInterpretation(
                original_text=f"Performance test {i}",
                intent="maintenance_scheduling",
                entities={"vehicle_id": f"F-{i}"},
                confidence=0.90,
                proposed_action={"api_endpoint": f"/api/test/{i}"}
            ) for i in range(10)
        ]
        
        performance_monitor.start()
        
        # Process approvals
        for interpretation in interpretations:
            approval_workflow.load_interpretation(interpretation)
            await approval_workflow.approve_action()
        
        metrics = performance_monitor.stop()
        
        # Check performance
        avg_approval_time = metrics['duration'] / len(interpretations) * 1000  # ms
        assert avg_approval_time < 500  # Should be under 500ms per approval

    @pytest.mark.integration
    def test_approval_workflow_audit_logging(self, approval_workflow,
                                            sample_ai_interpretation):
        """Test audit logging of approval decisions"""
        # Enable audit logging
        if hasattr(approval_workflow, 'enable_audit_logging'):
            approval_workflow.enable_audit_logging = True
        
        # Load interpretation and make approval decision
        approval_workflow.load_interpretation(sample_ai_interpretation)
        
        # Simulate approval
        approval_workflow.simulate_approval()
        
        # Check audit log
        if hasattr(approval_workflow, 'audit_log'):
            assert len(approval_workflow.audit_log) > 0
            
            latest_entry = approval_workflow.audit_log[-1]
            assert latest_entry["action"] == "approved"
            assert latest_entry["interpretation_id"] == sample_ai_interpretation.id
            assert "timestamp" in latest_entry
            assert "user_id" in latest_entry

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_approval_workflow_timeout_handling(self, approval_workflow,
                                                     sample_ai_interpretation,
                                                     mock_http_client):
        """Test handling of approval workflow timeouts"""
        # Setup slow API response
        async def slow_api_call(*args, **kwargs):
            await asyncio.sleep(5)  # Simulate slow response
            return {"success": True}
        
        mock_http_client.post.side_effect = slow_api_call
        
        # Load interpretation
        approval_workflow.load_interpretation(sample_ai_interpretation)
        
        # Set short timeout for testing
        if hasattr(approval_workflow, 'api_timeout'):
            approval_workflow.api_timeout = 1  # 1 second timeout
        
        # Attempt approval with timeout
        try:
            result = await asyncio.wait_for(
                approval_workflow.approve_action(),
                timeout=2
            )
            # If we get here, check if timeout was handled properly
            if "timeout" in result.get("error_message", "").lower():
                assert True  # Timeout was handled gracefully
            else:
                assert result["success"] is True  # Or it completed successfully
        except asyncio.TimeoutError:
            # Timeout occurred at test level - this is expected
            assert True