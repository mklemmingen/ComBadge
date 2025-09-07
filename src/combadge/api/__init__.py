"""
ComBadge API Client Package

Enterprise-grade HTTP client for fleet management API integration.
Provides authentication, retry logic, error handling, and audit logging.
"""

from .client import HTTPClient
from .authentication import AuthenticationManager
from .request_builder import RequestBuilder
from .response_handler import ResponseHandler
from .endpoints.base_endpoint import BaseEndpoint
from .endpoints.vehicle_endpoints import VehicleEndpoints
from .endpoints.maintenance_endpoints import MaintenanceEndpoints
from .endpoints.reservation_endpoints import ReservationEndpoints

__all__ = [
    'HTTPClient',
    'AuthenticationManager', 
    'RequestBuilder',
    'ResponseHandler',
    'BaseEndpoint',
    'VehicleEndpoints',
    'MaintenanceEndpoints',
    'ReservationEndpoints'
]

__version__ = '1.0.0'