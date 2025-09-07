"""
API Endpoints Package for ComBadge Fleet Management Client

Contains endpoint classes for different fleet management operations.
"""

from .base_endpoint import BaseEndpoint
from .vehicle_endpoints import VehicleEndpoints
from .maintenance_endpoints import MaintenanceEndpoints
from .reservation_endpoints import ReservationEndpoints

__all__ = [
    'BaseEndpoint',
    'VehicleEndpoints', 
    'MaintenanceEndpoints',
    'ReservationEndpoints'
]