"""
Response Handler for ComBadge Fleet API Client

Processes HTTP responses with comprehensive error handling, status code management,
JSON parsing, and audit logging for enterprise compliance.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime
from dataclasses import dataclass

import requests
from requests.exceptions import JSONDecodeError


class ResponseProcessingError(Exception):
    """Raised when response processing fails"""
    pass


class APIError(Exception):
    """Base class for API-specific errors"""
    
    def __init__(self, message: str, status_code: int = None, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


class ValidationError(APIError):
    """Raised for validation errors (400 status codes)"""
    pass


class AuthenticationError(APIError):
    """Raised for authentication errors (401 status codes)"""
    pass


class AuthorizationError(APIError):
    """Raised for authorization errors (403 status codes)"""
    pass


class NotFoundError(APIError):
    """Raised for resource not found errors (404 status codes)"""
    pass


class ConflictError(APIError):
    """Raised for conflict errors (409 status codes)"""
    pass


class RateLimitError(APIError):
    """Raised for rate limit errors (429 status codes)"""
    pass


class ServerError(APIError):
    """Raised for server errors (5xx status codes)"""
    pass


class ServiceUnavailableError(ServerError):
    """Raised for service unavailable errors (503 status codes)"""
    pass


@dataclass
class ResponseMetadata:
    """Metadata about the response for audit and debugging"""
    status_code: int
    response_time_ms: float
    content_length: int
    content_type: str
    headers: Dict[str, str]
    timestamp: datetime
    request_id: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None


@dataclass
class ProcessedResponse:
    """Processed response with data and metadata"""
    data: Any
    metadata: ResponseMetadata
    raw_response: requests.Response
    success: bool
    errors: List[str] = None


class StatusCodeHandler:
    """Handles different HTTP status codes and their meanings"""
    
    # Status code mappings to exceptions
    ERROR_MAPPINGS = {
        400: ValidationError,
        401: AuthenticationError,
        403: AuthorizationError,
        404: NotFoundError,
        409: ConflictError,
        429: RateLimitError,
        500: ServerError,
        502: ServerError,
        503: ServiceUnavailableError,
        504: ServerError
    }
    
    @classmethod
    def handle_status_code(cls, response: requests.Response) -> bool:
        """
        Check response status code and raise appropriate exceptions
        
        Returns:
            True if status indicates success, raises exception otherwise
        """
        status_code = response.status_code
        
        # Success codes
        if 200 <= status_code < 300:
            return True
        
        # Get error details from response
        error_details = cls._extract_error_details(response)
        
        # Map status code to exception
        exception_class = cls.ERROR_MAPPINGS.get(status_code, APIError)
        
        # Create and raise appropriate exception
        raise exception_class(
            message=error_details.get('message', f'HTTP {status_code} error'),
            status_code=status_code,
            error_code=error_details.get('error_code'),
            details=error_details
        )
    
    @staticmethod
    def _extract_error_details(response: requests.Response) -> Dict[str, Any]:
        """Extract error details from response body"""
        try:
            # Try to parse JSON error response
            error_data = response.json()
            
            # Handle different error response formats
            if isinstance(error_data, dict):
                if 'error' in error_data:
                    error_info = error_data['error']
                    if isinstance(error_info, dict):
                        return {
                            'message': error_info.get('message', 'Unknown error'),
                            'error_code': error_info.get('code'),
                            'details': error_info.get('details', {}),
                            'field_errors': error_info.get('field_errors', [])
                        }
                    else:
                        return {'message': str(error_info)}
                
                # Direct error fields
                return {
                    'message': error_data.get('message', error_data.get('detail', 'Unknown error')),
                    'error_code': error_data.get('code', error_data.get('error_code')),
                    'details': error_data
                }
            
            # If error_data is not a dict, use it as message
            return {'message': str(error_data)}
            
        except (JSONDecodeError, ValueError):
            # Fallback to status text or response text
            return {
                'message': response.reason or response.text[:200] or f'HTTP {response.status_code} error',
                'details': {'response_text': response.text[:500]}
            }


class ResponseParser:
    """Parses different response formats and content types"""
    
    @staticmethod
    def parse_json_response(response: requests.Response) -> Any:
        """Parse JSON response with error handling"""
        try:
            return response.json()
        except JSONDecodeError as e:
            raise ResponseProcessingError(f"Invalid JSON response: {e}")
    
    @staticmethod
    def parse_text_response(response: requests.Response) -> str:
        """Parse text response"""
        return response.text
    
    @staticmethod
    def parse_binary_response(response: requests.Response) -> bytes:
        """Parse binary response"""
        return response.content
    
    @classmethod
    def parse_response(cls, response: requests.Response) -> Any:
        """Parse response based on content type"""
        content_type = response.headers.get('content-type', '').lower()
        
        if 'application/json' in content_type:
            return cls.parse_json_response(response)
        elif 'text/' in content_type:
            return cls.parse_text_response(response)
        else:
            # Default to binary for unknown content types
            return cls.parse_binary_response(response)


class ResponseValidator:
    """Validates response data and structure"""
    
    def __init__(self):
        self.validators: Dict[str, Callable] = {}
    
    def register_validator(self, response_type: str, validator: Callable[[Any], List[str]]):
        """Register a validator for a specific response type"""
        self.validators[response_type] = validator
    
    def validate_response(self, response_type: str, data: Any) -> List[str]:
        """Validate response data and return list of errors"""
        if response_type in self.validators:
            try:
                return self.validators[response_type](data)
            except Exception as e:
                return [f"Validation error: {e}"]
        
        # No specific validator, perform basic validation
        return self._basic_validation(data)
    
    def _basic_validation(self, data: Any) -> List[str]:
        """Basic validation for any response"""
        errors = []
        
        # Check for common error indicators in response
        if isinstance(data, dict):
            if data.get('success') is False:
                errors.append("Response indicates failure")
            
            if 'error' in data and data['error']:
                errors.append(f"Response contains error: {data['error']}")
        
        return errors


class ResponseEnhancer:
    """Enhances responses with additional computed fields and metadata"""
    
    def __init__(self):
        self.enhancers: Dict[str, Callable] = {}
    
    def register_enhancer(self, response_type: str, enhancer: Callable[[Any], Any]):
        """Register an enhancer for a specific response type"""
        self.enhancers[response_type] = enhancer
    
    def enhance_response(self, response_type: str, data: Any) -> Any:
        """Enhance response data with additional fields"""
        if response_type in self.enhancers:
            try:
                return self.enhancers[response_type](data)
            except Exception as e:
                # Log error but return original data
                logging.getLogger(__name__).warning(f"Response enhancement failed: {e}")
        
        return data


class AuditLogger:
    """Logs API responses for audit and compliance purposes"""
    
    def __init__(self, logger_name: str = None):
        self.logger = logging.getLogger(logger_name or __name__)
    
    def log_response(self, response: ProcessedResponse, request_info: Dict[str, Any] = None):
        """Log response for audit trail"""
        log_data = {
            'timestamp': response.metadata.timestamp.isoformat(),
            'status_code': response.metadata.status_code,
            'response_time_ms': response.metadata.response_time_ms,
            'success': response.success,
            'request_id': response.metadata.request_id,
            'content_length': response.metadata.content_length
        }
        
        # Add request info if provided
        if request_info:
            log_data.update({
                'method': request_info.get('method'),
                'url': request_info.get('url'),
                'endpoint': request_info.get('endpoint')
            })
        
        # Add error info if present
        if response.errors:
            log_data['errors'] = response.errors
        
        # Log at appropriate level
        if response.success:
            self.logger.info(f"API Response: {json.dumps(log_data)}")
        else:
            self.logger.error(f"API Error Response: {json.dumps(log_data)}")


class ResponseHandler:
    """
    Comprehensive response handler for fleet management API responses.
    
    Features:
    - Status code handling with appropriate exceptions
    - JSON parsing with fallback handling
    - Response validation and enhancement
    - Metadata extraction and audit logging
    - Performance metrics tracking
    """
    
    def __init__(self):
        self.status_handler = StatusCodeHandler()
        self.parser = ResponseParser()
        self.validator = ResponseValidator()
        self.enhancer = ResponseEnhancer()
        self.audit_logger = AuditLogger()
        self.logger = logging.getLogger(__name__)
        
        # Register default validators and enhancers
        self._register_default_processors()
    
    def handle_response(
        self,
        response: requests.Response,
        expected_type: str = None,
        request_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process HTTP response with comprehensive handling
        
        Args:
            response: requests.Response object
            expected_type: Expected response type for validation/enhancement
            request_info: Information about the original request for logging
            
        Returns:
            Processed response data
            
        Raises:
            Various APIError subclasses based on response status
        """
        start_time = time.time()
        
        try:
            # Extract metadata
            metadata = self._extract_metadata(response)
            
            # Handle status code (raises exception if error)
            success = self.status_handler.handle_status_code(response)
            
            # Parse response data
            parsed_data = self.parser.parse_response(response)
            
            # Validate response if validator exists
            validation_errors = []
            if expected_type:
                validation_errors = self.validator.validate_response(expected_type, parsed_data)
            
            # Enhance response if enhancer exists
            if expected_type:
                parsed_data = self.enhancer.enhance_response(expected_type, parsed_data)
            
            # Create processed response
            processed_response = ProcessedResponse(
                data=parsed_data,
                metadata=metadata,
                raw_response=response,
                success=success,
                errors=validation_errors if validation_errors else None
            )
            
            # Log response for audit
            self.audit_logger.log_response(processed_response, request_info)
            
            # Return the parsed data (maintaining backward compatibility)
            return parsed_data
            
        except APIError:
            # Re-raise API errors
            raise
        except Exception as e:
            # Wrap other exceptions
            self.logger.error(f"Response processing failed: {e}")
            raise ResponseProcessingError(f"Failed to process response: {e}")
    
    def _extract_metadata(self, response: requests.Response) -> ResponseMetadata:
        """Extract metadata from response"""
        # Calculate response time if available
        response_time_ms = 0
        if hasattr(response, 'elapsed'):
            response_time_ms = response.elapsed.total_seconds() * 1000
        
        # Extract rate limit information
        rate_limit_remaining = None
        rate_limit_reset = None
        
        if 'x-ratelimit-remaining' in response.headers:
            try:
                rate_limit_remaining = int(response.headers['x-ratelimit-remaining'])
            except ValueError:
                pass
        
        if 'x-ratelimit-reset' in response.headers:
            try:
                reset_timestamp = int(response.headers['x-ratelimit-reset'])
                rate_limit_reset = datetime.fromtimestamp(reset_timestamp)
            except (ValueError, OSError):
                pass
        
        return ResponseMetadata(
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            content_length=len(response.content),
            content_type=response.headers.get('content-type', ''),
            headers=dict(response.headers),
            timestamp=datetime.now(),
            request_id=response.headers.get('x-request-id'),
            rate_limit_remaining=rate_limit_remaining,
            rate_limit_reset=rate_limit_reset
        )
    
    def _register_default_processors(self):
        """Register default validators and enhancers for common response types"""
        # Vehicle response validator
        def validate_vehicle_response(data: Any) -> List[str]:
            errors = []
            if isinstance(data, dict):
                required_fields = ['vehicle_id', 'make', 'model']
                for field in required_fields:
                    if field not in data:
                        errors.append(f"Missing required field: {field}")
            else:
                errors.append("Vehicle response must be an object")
            return errors
        
        self.validator.register_validator('vehicle', validate_vehicle_response)
        
        # Maintenance response validator
        def validate_maintenance_response(data: Any) -> List[str]:
            errors = []
            if isinstance(data, dict):
                if 'appointment_id' not in data and 'maintenance_id' not in data:
                    errors.append("Missing appointment or maintenance ID")
            return errors
        
        self.validator.register_validator('maintenance', validate_maintenance_response)
        
        # List response enhancer
        def enhance_list_response(data: Any) -> Any:
            if isinstance(data, dict) and 'items' in data:
                # Add computed fields for list responses
                items = data.get('items', [])
                data['item_count'] = len(items)
                if 'total_count' not in data:
                    data['total_count'] = len(items)
            return data
        
        self.enhancer.register_enhancer('list', enhance_list_response)
    
    def register_validator(self, response_type: str, validator: Callable[[Any], List[str]]):
        """Register a custom validator"""
        self.validator.register_validator(response_type, validator)
    
    def register_enhancer(self, response_type: str, enhancer: Callable[[Any], Any]):
        """Register a custom enhancer"""
        self.enhancer.register_enhancer(response_type, enhancer)
    
    def get_error_summary(self, error: APIError) -> Dict[str, Any]:
        """Get a formatted error summary for user display"""
        summary = {
            'error_type': type(error).__name__,
            'message': str(error),
            'status_code': error.status_code,
            'error_code': error.error_code,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add user-friendly suggestions based on error type
        if isinstance(error, ValidationError):
            summary['user_action'] = 'Please check your input and try again'
            if error.details and 'field_errors' in error.details:
                summary['field_errors'] = error.details['field_errors']
        
        elif isinstance(error, AuthenticationError):
            summary['user_action'] = 'Please check your credentials and login again'
        
        elif isinstance(error, AuthorizationError):
            summary['user_action'] = 'You do not have permission to perform this action'
        
        elif isinstance(error, NotFoundError):
            summary['user_action'] = 'The requested resource was not found'
        
        elif isinstance(error, RateLimitError):
            summary['user_action'] = 'Rate limit exceeded. Please wait before trying again'
        
        elif isinstance(error, ServiceUnavailableError):
            summary['user_action'] = 'Service is temporarily unavailable. Please try again later'
        
        else:
            summary['user_action'] = 'An error occurred. Please try again or contact support'
        
        return summary