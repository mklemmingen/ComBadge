"""
Unit tests for the VehicleValidator component.

Tests vehicle data validation, business rule enforcement,
and data integrity checks for fleet management operations.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from combadge.fleet.validators.vehicle_validator import VehicleValidator, ValidationError
from combadge.api.client import HTTPClient
from tests.fixtures.sample_data import MOCK_VEHICLE_DATA


class TestVehicleValidator:
    """Test suite for VehicleValidator component"""

    @pytest.fixture
    def mock_api_client(self):
        """Mock API client for validation checks"""
        mock_client = Mock(spec=HTTPClient)
        mock_client.get = AsyncMock()
        mock_client.post = AsyncMock()
        return mock_client

    @pytest.fixture
    def vehicle_validator(self, mock_api_client):
        """Create VehicleValidator instance with mocked dependencies"""
        return VehicleValidator(api_client=mock_api_client)

    @pytest.fixture
    def valid_vehicle_data(self):
        """Valid vehicle data for testing"""
        return {
            "vehicle_id": "F-123",
            "make": "Ford",
            "model": "Transit",
            "year": 2023,
            "vin": "1FTBW2CM5NKA12345",
            "license_plate": "FLT-123",
            "mileage": 15000,
            "fuel_level": 0.75,
            "status": "active"
        }

    @pytest.mark.unit
    async def test_validate_vehicle_id_format(self, vehicle_validator):
        """Test vehicle ID format validation"""
        # Test valid formats
        valid_ids = ["F-123", "V-456", "T-789", "FLT-001", "VAN-234"]
        for vehicle_id in valid_ids:
            result = vehicle_validator.validate_vehicle_id(vehicle_id)
            assert result.is_valid is True
        
        # Test invalid formats
        invalid_ids = ["123", "F123-", "VV-", "F-12345", "invalid"]
        for vehicle_id in invalid_ids:
            result = vehicle_validator.validate_vehicle_id(vehicle_id)
            assert result.is_valid is False
            assert "format" in result.error_message.lower()

    @pytest.mark.unit
    def test_validate_vin_format(self, vehicle_validator):
        """Test VIN format validation"""
        # Test valid VIN (17 characters, alphanumeric)
        valid_vin = "1FTBW2CM5NKA12345"
        result = vehicle_validator.validate_vin(valid_vin)
        assert result.is_valid is True
        
        # Test invalid VINs
        invalid_vins = [
            "123456789",  # Too short
            "1FTBW2CM5NKA123456789",  # Too long
            "1FTBW2CM5NKA1234O",  # Contains O (not allowed)
            "1FTBW2CM5NKA1234I",  # Contains I (not allowed)
            "1FTBW2CM5NKA1234Q",  # Contains Q (not allowed)
        ]
        
        for vin in invalid_vins:
            result = vehicle_validator.validate_vin(vin)
            assert result.is_valid is False

    @pytest.mark.unit
    def test_validate_license_plate_format(self, vehicle_validator):
        """Test license plate format validation"""
        # Test valid license plates
        valid_plates = ["ABC-123", "FLT-001", "VAN-456", "CAR123", "123-ABC"]
        for plate in valid_plates:
            result = vehicle_validator.validate_license_plate(plate)
            assert result.is_valid is True
        
        # Test invalid license plates
        invalid_plates = ["", "A", "TOOLONGPLATE", "123", "AB-C"]
        for plate in invalid_plates:
            result = vehicle_validator.validate_license_plate(plate)
            assert result.is_valid is False

    @pytest.mark.unit
    def test_validate_vehicle_year(self, vehicle_validator):
        """Test vehicle year validation"""
        current_year = datetime.now().year
        
        # Test valid years
        valid_years = [2020, 2023, current_year, current_year + 1]
        for year in valid_years:
            result = vehicle_validator.validate_year(year)
            assert result.is_valid is True
        
        # Test invalid years
        invalid_years = [1800, 1999, current_year + 5, "2023", None]
        for year in invalid_years:
            result = vehicle_validator.validate_year(year)
            assert result.is_valid is False

    @pytest.mark.unit
    def test_validate_mileage(self, vehicle_validator):
        """Test mileage validation"""
        # Test valid mileage values
        valid_mileage = [0, 1000, 50000, 200000, 500000]
        for mileage in valid_mileage:
            result = vehicle_validator.validate_mileage(mileage)
            assert result.is_valid is True
        
        # Test invalid mileage values
        invalid_mileage = [-1, 1000000, "50000", None]
        for mileage in invalid_mileage:
            result = vehicle_validator.validate_mileage(mileage)
            assert result.is_valid is False

    @pytest.mark.unit
    def test_validate_fuel_level(self, vehicle_validator):
        """Test fuel level validation"""
        # Test valid fuel levels (0.0 to 1.0)
        valid_levels = [0.0, 0.25, 0.5, 0.75, 1.0]
        for level in valid_levels:
            result = vehicle_validator.validate_fuel_level(level)
            assert result.is_valid is True
        
        # Test invalid fuel levels
        invalid_levels = [-0.1, 1.1, 50, "0.5", None]
        for level in invalid_levels:
            result = vehicle_validator.validate_fuel_level(level)
            assert result.is_valid is False

    @pytest.mark.unit
    def test_validate_vehicle_status(self, vehicle_validator):
        """Test vehicle status validation"""
        # Test valid statuses
        valid_statuses = ["active", "maintenance", "retired", "reserved", "out_of_service"]
        for status in valid_statuses:
            result = vehicle_validator.validate_status(status)
            assert result.is_valid is True
        
        # Test invalid statuses
        invalid_statuses = ["invalid_status", "", None, 123, "ACTIVE"]
        for status in invalid_statuses:
            result = vehicle_validator.validate_status(status)
            assert result.is_valid is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_vehicle_existence(self, vehicle_validator, mock_api_client):
        """Test validation of vehicle existence in the system"""
        # Setup mock API response for existing vehicle
        mock_api_client.get.return_value = {
            "vehicle": MOCK_VEHICLE_DATA[0],
            "exists": True
        }
        
        result = await vehicle_validator.validate_vehicle_exists("F-123")
        
        assert result.is_valid is True
        mock_api_client.get.assert_called_once_with("/api/vehicles/F-123")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_vehicle_not_exists(self, vehicle_validator, mock_api_client):
        """Test validation for non-existent vehicle"""
        # Setup mock API response for non-existent vehicle
        mock_api_client.get.side_effect = Exception("Vehicle not found")
        
        result = await vehicle_validator.validate_vehicle_exists("NONEXISTENT")
        
        assert result.is_valid is False
        assert "not found" in result.error_message.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_vin_uniqueness(self, vehicle_validator, mock_api_client):
        """Test VIN uniqueness validation"""
        # Test existing VIN
        mock_api_client.get.return_value = {
            "vehicles": [{"vehicle_id": "F-123", "vin": "1FTBW2CM5NKA12345"}],
            "total": 1
        }
        
        result = await vehicle_validator.validate_vin_unique("1FTBW2CM5NKA12345")
        
        assert result.is_valid is False
        assert "already exists" in result.error_message.lower()
        
        # Test unique VIN
        mock_api_client.get.return_value = {"vehicles": [], "total": 0}
        
        result = await vehicle_validator.validate_vin_unique("1NEWVIN123456789")
        
        assert result.is_valid is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_license_plate_uniqueness(self, vehicle_validator, mock_api_client):
        """Test license plate uniqueness validation"""
        # Test existing license plate
        mock_api_client.get.return_value = {
            "vehicles": [{"vehicle_id": "F-123", "license_plate": "FLT-123"}],
            "total": 1
        }
        
        result = await vehicle_validator.validate_license_plate_unique("FLT-123")
        
        assert result.is_valid is False
        assert "already exists" in result.error_message.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_complete_vehicle_data(self, vehicle_validator, valid_vehicle_data,
                                                 mock_api_client):
        """Test complete vehicle data validation"""
        # Setup mock responses for uniqueness checks
        mock_api_client.get.side_effect = [
            {"vehicles": [], "total": 0},  # VIN unique
            {"vehicles": [], "total": 0}   # License plate unique
        ]
        
        result = await vehicle_validator.validate_vehicle(valid_vehicle_data)
        
        assert result.is_valid is True
        assert len(result.warnings) == 0
        assert len(result.errors) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_vehicle_with_errors(self, vehicle_validator, mock_api_client):
        """Test validation with multiple errors"""
        invalid_vehicle_data = {
            "vehicle_id": "INVALID-ID-FORMAT",
            "make": "",  # Empty make
            "model": "",  # Empty model
            "year": 1999,  # Too old
            "vin": "INVALID",  # Invalid VIN
            "license_plate": "TOOLONGPLATEFORMAT",  # Too long
            "mileage": -1000,  # Negative mileage
            "fuel_level": 2.0,  # Invalid fuel level
            "status": "invalid_status"  # Invalid status
        }
        
        result = await vehicle_validator.validate_vehicle(invalid_vehicle_data)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        
        # Check that specific errors are present
        error_messages = " ".join(result.errors)
        assert "vehicle_id" in error_messages.lower()
        assert "vin" in error_messages.lower()
        assert "year" in error_messages.lower()
        assert "mileage" in error_messages.lower()

    @pytest.mark.unit
    def test_validate_maintenance_schedule(self, vehicle_validator):
        """Test maintenance schedule validation"""
        # Test valid maintenance data
        valid_maintenance = {
            "vehicle_id": "F-123",
            "maintenance_type": "oil_change",
            "scheduled_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "service_center": "Main Garage"
        }
        
        result = vehicle_validator.validate_maintenance_request(valid_maintenance)
        
        assert result.is_valid is True
        
        # Test maintenance scheduled in the past
        past_maintenance = valid_maintenance.copy()
        past_maintenance["scheduled_date"] = (datetime.now() - timedelta(days=1)).isoformat()
        
        result = vehicle_validator.validate_maintenance_request(past_maintenance)
        
        assert result.is_valid is False
        assert "past" in result.error_message.lower()

    @pytest.mark.unit
    def test_validate_reservation_request(self, vehicle_validator):
        """Test reservation request validation"""
        # Test valid reservation
        now = datetime.now()
        start_time = now + timedelta(hours=1)
        end_time = now + timedelta(hours=3)
        
        valid_reservation = {
            "vehicle_id": "V-456",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "reserved_by": "user@company.com"
        }
        
        result = vehicle_validator.validate_reservation_request(valid_reservation)
        
        assert result.is_valid is True
        
        # Test reservation with end time before start time
        invalid_reservation = valid_reservation.copy()
        invalid_reservation["end_time"] = (start_time - timedelta(hours=1)).isoformat()
        
        result = vehicle_validator.validate_reservation_request(invalid_reservation)
        
        assert result.is_valid is False
        assert "end time" in result.error_message.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_vehicle_availability(self, vehicle_validator, mock_api_client):
        """Test vehicle availability validation"""
        # Setup mock response for available vehicle
        mock_api_client.get.return_value = {
            "vehicle": {
                "vehicle_id": "F-123",
                "status": "active",
                "current_reservation": None
            }
        }
        
        start_time = datetime.now() + timedelta(hours=1)
        end_time = datetime.now() + timedelta(hours=3)
        
        result = await vehicle_validator.validate_vehicle_available(
            "F-123", start_time, end_time
        )
        
        assert result.is_valid is True
        
        # Test unavailable vehicle (in maintenance)
        mock_api_client.get.return_value = {
            "vehicle": {
                "vehicle_id": "F-123",
                "status": "maintenance",
                "current_reservation": None
            }
        }
        
        result = await vehicle_validator.validate_vehicle_available(
            "F-123", start_time, end_time
        )
        
        assert result.is_valid is False
        assert "maintenance" in result.error_message.lower()

    @pytest.mark.unit
    def test_validate_business_rules(self, vehicle_validator):
        """Test business rule validation"""
        # Test vehicle cannot be reserved while in maintenance
        maintenance_vehicle = {
            "vehicle_id": "F-123",
            "status": "maintenance",
            "requested_action": "reserve"
        }
        
        result = vehicle_validator.validate_business_rules(maintenance_vehicle)
        
        assert result.is_valid is False
        assert "maintenance" in result.error_message.lower()
        
        # Test valid business rule scenario
        active_vehicle = {
            "vehicle_id": "F-123",
            "status": "active",
            "requested_action": "reserve"
        }
        
        result = vehicle_validator.validate_business_rules(active_vehicle)
        
        assert result.is_valid is True

    @pytest.mark.unit
    def test_validate_required_fields(self, vehicle_validator):
        """Test required field validation"""
        # Test with all required fields
        complete_data = {
            "vehicle_id": "F-123",
            "make": "Ford",
            "model": "Transit",
            "year": 2023,
            "vin": "1FTBW2CM5NKA12345"
        }
        
        result = vehicle_validator.validate_required_fields(
            complete_data, 
            required_fields=["vehicle_id", "make", "model", "year", "vin"]
        )
        
        assert result.is_valid is True
        
        # Test with missing required fields
        incomplete_data = {
            "vehicle_id": "F-123",
            "make": "Ford"
            # Missing model, year, vin
        }
        
        result = vehicle_validator.validate_required_fields(
            incomplete_data,
            required_fields=["vehicle_id", "make", "model", "year", "vin"]
        )
        
        assert result.is_valid is False
        assert "required" in result.error_message.lower()

    @pytest.mark.unit
    def test_validate_data_types(self, vehicle_validator):
        """Test data type validation"""
        # Test with correct data types
        correct_types = {
            "vehicle_id": "F-123",  # string
            "year": 2023,  # int
            "mileage": 15000,  # int
            "fuel_level": 0.75,  # float
            "is_active": True  # bool
        }
        
        result = vehicle_validator.validate_data_types(correct_types, {
            "vehicle_id": str,
            "year": int,
            "mileage": int,
            "fuel_level": float,
            "is_active": bool
        })
        
        assert result.is_valid is True
        
        # Test with incorrect data types
        incorrect_types = {
            "vehicle_id": 123,  # Should be string
            "year": "2023",  # Should be int
            "mileage": "15000",  # Should be int
            "fuel_level": "0.75"  # Should be float
        }
        
        result = vehicle_validator.validate_data_types(incorrect_types, {
            "vehicle_id": str,
            "year": int,
            "mileage": int,
            "fuel_level": float
        })
        
        assert result.is_valid is False

    @pytest.mark.unit
    def test_validate_mock_vehicle_data(self, vehicle_validator):
        """Test validation of mock vehicle data from test fixtures"""
        for vehicle_data in MOCK_VEHICLE_DATA:
            # Test basic format validation (non-async parts)
            vehicle_id_result = vehicle_validator.validate_vehicle_id(vehicle_data["vehicle_id"])
            assert vehicle_id_result.is_valid is True
            
            vin_result = vehicle_validator.validate_vin(vehicle_data["vin"])
            assert vin_result.is_valid is True
            
            year_result = vehicle_validator.validate_year(vehicle_data["year"])
            assert year_result.is_valid is True
            
            fuel_result = vehicle_validator.validate_fuel_level(vehicle_data["fuel_level"])
            assert fuel_result.is_valid is True
            
            status_result = vehicle_validator.validate_status(vehicle_data["status"])
            assert status_result.is_valid is True

    @pytest.mark.unit
    def test_custom_validation_rules(self, vehicle_validator):
        """Test custom validation rules"""
        # Add custom rule: electric vehicles must have different validation
        def validate_electric_vehicle(data):
            if data.get("fuel_type") == "electric":
                if "battery_level" not in data:
                    return False, "Electric vehicles must have battery_level"
                if not (0.0 <= data["battery_level"] <= 1.0):
                    return False, "Battery level must be between 0.0 and 1.0"
            return True, ""
        
        vehicle_validator.add_custom_rule("electric_vehicle", validate_electric_vehicle)
        
        # Test electric vehicle data
        electric_vehicle = {
            "vehicle_id": "E-001",
            "fuel_type": "electric",
            "battery_level": 0.8
        }
        
        result = vehicle_validator.apply_custom_rules(electric_vehicle)
        assert result.is_valid is True
        
        # Test invalid electric vehicle
        invalid_electric = {
            "vehicle_id": "E-002",
            "fuel_type": "electric"
            # Missing battery_level
        }
        
        result = vehicle_validator.apply_custom_rules(invalid_electric)
        assert result.is_valid is False
        assert "battery_level" in result.error_message

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validation_error_aggregation(self, vehicle_validator, mock_api_client):
        """Test aggregation of multiple validation errors"""
        # Setup a vehicle with multiple validation issues
        problematic_vehicle = {
            "vehicle_id": "INVALID-FORMAT",  # Invalid format
            "make": "",  # Empty make
            "year": 1990,  # Too old
            "vin": "SHORT",  # Invalid VIN
            "mileage": -500,  # Negative mileage
            "status": "unknown_status"  # Invalid status
        }
        
        # Mock API responses
        mock_api_client.get.side_effect = [
            {"vehicles": [], "total": 0},  # VIN unique check
            {"vehicles": [], "total": 0}   # License plate unique check
        ]
        
        result = await vehicle_validator.validate_vehicle(problematic_vehicle)
        
        # Should collect all errors
        assert result.is_valid is False
        assert len(result.errors) >= 5  # Should have multiple errors
        
        # Check that all major issues are captured
        all_errors = " ".join(result.errors).lower()
        assert "vehicle_id" in all_errors
        assert "make" in all_errors
        assert "year" in all_errors
        assert "vin" in all_errors
        assert "mileage" in all_errors