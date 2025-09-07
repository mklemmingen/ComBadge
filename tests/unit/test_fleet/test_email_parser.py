"""
Unit tests for the EmailParser component.

Tests email parsing, content extraction, and metadata handling
for the fleet management email processing system.
"""

import pytest
import email
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
import tempfile
import os

from combadge.fleet.processors.email_parser import EmailParser, EmailContent
from tests.fixtures.sample_data import SAMPLE_EMAILS


class TestEmailParser:
    """Test suite for EmailParser component"""

    @pytest.fixture
    def email_parser(self):
        """Create EmailParser instance"""
        return EmailParser()

    @pytest.fixture
    def sample_raw_email(self):
        """Create a sample raw email message"""
        raw_email = """From: fleet.manager@company.com
To: operations@company.com
Subject: Vehicle F-123 needs maintenance
Date: Thu, 15 Mar 2024 10:00:00 +0000
Content-Type: text/plain

Hello,

Vehicle F-123 requires routine maintenance scheduled for tomorrow at 10:00 AM.
Please arrange for the service.

Best regards,
Fleet Manager
"""
        return raw_email

    @pytest.fixture
    def multipart_email(self):
        """Create a multipart email with attachments"""
        raw_email = """From: admin@company.com
To: fleet@company.com
Subject: New vehicle registration - Toyota Camry 2024
Date: Thu, 15 Mar 2024 12:00:00 +0000
Content-Type: multipart/mixed; boundary="boundary123"

--boundary123
Content-Type: text/plain

Please register a new Toyota Camry 2024, VIN: 1HGCM82633A123456, License: ABC-1234

--boundary123
Content-Type: application/pdf
Content-Disposition: attachment; filename="vehicle_docs.pdf"
Content-Transfer-Encoding: base64

JVBERi0xLjQKJdPr6eEKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4K

--boundary123--
"""
        return raw_email

    @pytest.mark.unit
    def test_parse_simple_email(self, email_parser, sample_raw_email):
        """Test parsing of simple text email"""
        result = email_parser.parse_email(sample_raw_email)
        
        assert result.subject == "Vehicle F-123 needs maintenance"
        assert result.sender == "fleet.manager@company.com"
        assert result.recipient == "operations@company.com"
        assert "Vehicle F-123 requires routine maintenance" in result.body
        assert result.timestamp is not None
        assert len(result.attachments) == 0

    @pytest.mark.unit
    def test_parse_multipart_email(self, email_parser, multipart_email):
        """Test parsing of multipart email with attachments"""
        result = email_parser.parse_email(multipart_email)
        
        assert result.subject == "New vehicle registration - Toyota Camry 2024"
        assert result.sender == "admin@company.com"
        assert "Toyota Camry 2024" in result.body
        assert "1HGCM82633A123456" in result.body
        assert len(result.attachments) == 1
        assert result.attachments[0]["filename"] == "vehicle_docs.pdf"
        assert result.attachments[0]["content_type"] == "application/pdf"

    @pytest.mark.unit
    def test_parse_email_with_html_content(self, email_parser):
        """Test parsing email with HTML content"""
        html_email = """From: sales@company.com
To: fleet@company.com
Subject: Vehicle Reservation Request
Content-Type: text/html

<html>
<body>
<h1>Reservation Request</h1>
<p>I need to reserve vehicle <strong>V-456</strong> for a client meeting.</p>
<p>Date: <em>Friday, March 15th</em></p>
<p>Time: <em>2:00 PM - 5:00 PM</em></p>
</body>
</html>
"""
        
        result = email_parser.parse_email(html_email)
        
        assert result.subject == "Vehicle Reservation Request"
        assert "V-456" in result.body
        assert "Friday, March 15th" in result.body
        assert "2:00 PM - 5:00 PM" in result.body
        # HTML tags should be stripped
        assert "<strong>" not in result.body
        assert "<em>" not in result.body

    @pytest.mark.unit
    def test_parse_email_from_dict(self, email_parser):
        """Test parsing email from dictionary format"""
        email_dict = {
            "subject": "Test Subject",
            "from": "test@company.com",
            "to": "fleet@company.com",
            "body": "Test email body content",
            "date": "Thu, 15 Mar 2024 10:00:00 +0000",
            "attachments": []
        }
        
        result = email_parser.parse_email(email_dict)
        
        assert result.subject == "Test Subject"
        assert result.sender == "test@company.com"
        assert result.recipient == "fleet@company.com"
        assert result.body == "Test email body content"
        assert result.timestamp is not None

    @pytest.mark.unit
    def test_parse_invalid_email_format(self, email_parser):
        """Test handling of invalid email format"""
        invalid_email = "This is not a valid email format"
        
        with pytest.raises(ValueError) as exc_info:
            email_parser.parse_email(invalid_email)
        
        assert "invalid email format" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_extract_vehicle_references(self, email_parser):
        """Test extraction of vehicle references from email content"""
        content = "Please service vehicles F-123, V-456, and T-789. Also check fleet vehicle FLT-001."
        
        vehicles = email_parser.extract_vehicle_references(content)
        
        expected_vehicles = ["F-123", "V-456", "T-789", "FLT-001"]
        for vehicle in expected_vehicles:
            assert vehicle in vehicles

    @pytest.mark.unit
    def test_extract_dates_and_times(self, email_parser):
        """Test extraction of dates and times from email content"""
        content = """
        Schedule maintenance for tomorrow at 10:00 AM.
        Also reserve vehicle for March 15, 2024 from 2pm to 5pm.
        Follow up on 3/20/2024.
        """
        
        temporal_info = email_parser.extract_temporal_references(content)
        
        assert "tomorrow" in temporal_info["relative_dates"]
        assert "10:00 AM" in temporal_info["times"]
        assert "2pm" in temporal_info["times"]
        assert "5pm" in temporal_info["times"]
        assert any("2024" in date for date in temporal_info["absolute_dates"])

    @pytest.mark.unit
    def test_extract_contact_information(self, email_parser):
        """Test extraction of contact information"""
        content = """
        Contact John Doe at john.doe@company.com or call +1-555-123-4567.
        Alternative contact: jane.smith@company.com, extension 1234.
        """
        
        contacts = email_parser.extract_contact_information(content)
        
        expected_emails = ["john.doe@company.com", "jane.smith@company.com"]
        expected_phones = ["+1-555-123-4567", "1234"]
        
        for email_addr in expected_emails:
            assert email_addr in contacts["emails"]
        
        for phone in expected_phones:
            assert any(phone in p for p in contacts["phone_numbers"])

    @pytest.mark.unit
    def test_classify_email_intent(self, email_parser):
        """Test classification of email intent"""
        test_cases = [
            ("Schedule maintenance for F-123", "maintenance_request"),
            ("Reserve vehicle V-456 for meeting", "reservation_request"), 
            ("Add new Toyota Camry to fleet", "vehicle_registration"),
            ("What is the status of T-789?", "status_inquiry"),
            ("Assign parking spot to vehicle", "parking_assignment")
        ]
        
        for content, expected_intent in test_cases:
            intent = email_parser.classify_email_intent(content)
            assert intent == expected_intent

    @pytest.mark.unit
    def test_parse_priority_indicators(self, email_parser):
        """Test parsing of email priority indicators"""
        high_priority_email = """From: manager@company.com
Subject: URGENT: Vehicle F-123 breakdown
Priority: High

URGENT: Vehicle F-123 has broken down and needs immediate assistance!
"""
        
        result = email_parser.parse_email(high_priority_email)
        
        assert result.priority == "high"
        assert result.urgency_indicators == ["URGENT", "immediate"]

    @pytest.mark.unit
    def test_handle_forwarded_email(self, email_parser):
        """Test handling of forwarded emails"""
        forwarded_email = """From: admin@company.com
Subject: FWD: Vehicle maintenance request

---------- Forwarded message ----------
From: user@company.com
Subject: Vehicle maintenance request

Original request for vehicle F-123 maintenance.
"""
        
        result = email_parser.parse_email(forwarded_email)
        
        assert result.is_forwarded is True
        assert result.original_sender == "user@company.com"
        assert "Original request for vehicle F-123" in result.body

    @pytest.mark.unit
    def test_handle_email_thread(self, email_parser):
        """Test handling of email threads and replies"""
        thread_email = """From: user@company.com
Subject: RE: Vehicle F-123 maintenance
In-Reply-To: <original-message-id@company.com>

Thanks for scheduling the maintenance.

On Thu, Mar 15, 2024, fleet@company.com wrote:
> Vehicle F-123 maintenance has been scheduled for tomorrow.
> Please confirm the appointment.
"""
        
        result = email_parser.parse_email(thread_email)
        
        assert result.is_reply is True
        assert result.thread_id is not None
        assert "Thanks for scheduling" in result.body
        # Quoted text should be identified
        assert len(result.quoted_content) > 0

    @pytest.mark.unit
    def test_sanitize_email_content(self, email_parser):
        """Test sanitization of email content"""
        malicious_content = """
        <script>alert('xss')</script>
        Visit this link: http://malicious-site.com
        Run this command: rm -rf /
        SQL injection: '; DROP TABLE vehicles; --
        """
        
        sanitized = email_parser.sanitize_content(malicious_content)
        
        # Should remove script tags
        assert "<script>" not in sanitized
        assert "alert('xss')" not in sanitized
        # Should flag dangerous commands
        assert email_parser.has_security_concerns(malicious_content)

    @pytest.mark.unit
    def test_parse_batch_emails(self, email_parser):
        """Test batch processing of multiple emails"""
        email_batch = [
            "From: user1@company.com\nSubject: Test 1\n\nContent 1",
            "From: user2@company.com\nSubject: Test 2\n\nContent 2",
            "From: user3@company.com\nSubject: Test 3\n\nContent 3"
        ]
        
        results = email_parser.parse_batch(email_batch)
        
        assert len(results) == 3
        for i, result in enumerate(results, 1):
            assert result.subject == f"Test {i}"
            assert result.body == f"Content {i}"

    @pytest.mark.unit
    def test_extract_structured_data(self, email_parser):
        """Test extraction of structured data from emails"""
        structured_email = """
        Vehicle Information:
        - Vehicle ID: F-123
        - Make: Ford
        - Model: Transit
        - Year: 2023
        - Mileage: 15,000
        - License Plate: FLT-123
        
        Service Details:
        - Service Type: Oil Change
        - Scheduled Date: 2024-03-16
        - Service Center: Main Garage
        - Cost Estimate: $150.00
        """
        
        structured_data = email_parser.extract_structured_data(structured_email)
        
        assert structured_data["vehicle"]["vehicle_id"] == "F-123"
        assert structured_data["vehicle"]["make"] == "Ford"
        assert structured_data["service"]["service_type"] == "Oil Change"
        assert structured_data["service"]["cost_estimate"] == "$150.00"

    @pytest.mark.unit
    def test_handle_encoding_issues(self, email_parser):
        """Test handling of different character encodings"""
        # Email with special characters
        encoded_email = """From: françois@company.com
Subject: Véhicule maintenance
Content-Type: text/plain; charset=utf-8

Bonjour! Le véhicule F-123 nécessite un entretien.
Cost: €150.50
"""
        
        result = email_parser.parse_email(encoded_email)
        
        assert result.sender == "françois@company.com"
        assert "véhicule" in result.body.lower()
        assert "€150.50" in result.body

    @pytest.mark.unit
    def test_attachment_processing(self, email_parser):
        """Test processing of email attachments"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Configure parser to save attachments
            email_parser.save_attachments = True
            email_parser.attachment_directory = temp_dir
            
            result = email_parser.parse_email(self.multipart_email)
            
            # Check that attachment was saved
            saved_files = os.listdir(temp_dir)
            assert len(saved_files) == 1
            assert saved_files[0].endswith(".pdf")

    @pytest.mark.unit
    def test_parse_auto_generated_emails(self, email_parser):
        """Test handling of auto-generated system emails"""
        auto_email = """From: system@fleet.company.com
Subject: [AUTO] Vehicle F-123 Service Reminder
X-Auto-Response-Suppress: All
Auto-Submitted: auto-generated

This is an automated reminder that vehicle F-123 is due for service.
Service interval: 90 days
Last service: 2024-01-15
Next service due: 2024-04-15
"""
        
        result = email_parser.parse_email(auto_email)
        
        assert result.is_automated is True
        assert result.sender == "system@fleet.company.com"
        assert "automated reminder" in result.body.lower()

    @pytest.mark.unit
    def test_parse_error_handling(self, email_parser):
        """Test error handling in email parsing"""
        # Test with None input
        with pytest.raises(ValueError):
            email_parser.parse_email(None)
        
        # Test with empty string
        with pytest.raises(ValueError):
            email_parser.parse_email("")
        
        # Test with corrupted email
        corrupted_email = "From: test@company.com\nSubject: Test\n\nBody\x00\x01\x02"
        result = email_parser.parse_email(corrupted_email)
        # Should handle gracefully and clean the content
        assert result.body != "Body\x00\x01\x02"

    @pytest.mark.unit
    def test_performance_large_email(self, email_parser, performance_monitor):
        """Test performance with large email content"""
        # Create a large email body
        large_body = "Vehicle information: " + "F-123 needs service. " * 1000
        large_email = f"From: test@company.com\nSubject: Large Email\n\n{large_body}"
        
        performance_monitor.start()
        
        result = email_parser.parse_email(large_email)
        
        metrics = performance_monitor.stop()
        
        assert result.subject == "Large Email"
        assert "F-123 needs service" in result.body
        # Should complete within reasonable time even for large emails
        assert metrics['duration'] < 5.0  # Less than 5 seconds

    @pytest.mark.unit
    def test_email_metadata_extraction(self, email_parser):
        """Test extraction of comprehensive email metadata"""
        detailed_email = """Delivered-To: fleet@company.com
Received: from mail.company.com by fleet.company.com
Message-ID: <12345@company.com>
From: sender@company.com
To: fleet@company.com
CC: manager@company.com
BCC: admin@company.com
Subject: Test Email
Date: Thu, 15 Mar 2024 10:00:00 +0000
X-Priority: 1
X-Spam-Score: 0.1

Test email content.
"""
        
        result = email_parser.parse_email(detailed_email)
        
        assert result.message_id == "<12345@company.com>"
        assert result.cc == ["manager@company.com"]
        assert result.bcc == ["admin@company.com"]
        assert result.spam_score == 0.1
        assert result.received_path is not None

    @pytest.mark.unit
    def test_sample_emails_parsing(self, email_parser):
        """Test parsing of sample emails from test data"""
        for sample_email in SAMPLE_EMAILS:
            # Convert sample email to email format
            email_content = f"""From: {sample_email['from']}
To: {sample_email['to']}
Subject: {sample_email['subject']}
Date: {sample_email['timestamp'].strftime('%a, %d %b %Y %H:%M:%S %z')}

{sample_email['body']}
"""
            
            result = email_parser.parse_email(email_content)
            
            assert result.subject == sample_email['subject']
            assert result.sender == sample_email['from']
            assert result.body == sample_email['body']
            assert len(result.attachments) == len(sample_email['attachments'])