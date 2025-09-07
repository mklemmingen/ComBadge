"""
Request Builder for ComBadge Fleet API Client

Constructs HTTP requests from JSON templates with authentication headers,
content-type handling, request signing, and validation.
"""

import json
import hmac
import hashlib
import time
import logging
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urlencode
from datetime import datetime

import requests


class RequestValidationError(Exception):
    """Raised when request validation fails"""
    pass


class RequestSigningError(Exception):
    """Raised when request signing fails"""
    pass


class RequestTemplate:
    """Represents a request template with metadata and validation rules"""
    
    def __init__(
        self,
        template_id: str,
        method: str,
        endpoint: str,
        required_fields: Optional[List[str]] = None,
        optional_fields: Optional[List[str]] = None,
        field_validators: Optional[Dict[str, callable]] = None,
        default_values: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.template_id = template_id
        self.method = method.upper()
        self.endpoint = endpoint
        self.required_fields = required_fields or []
        self.optional_fields = optional_fields or []
        self.field_validators = field_validators or {}
        self.default_values = default_values or {}
        self.headers = headers or {}
    
    def validate_data(self, data: Dict[str, Any]) -> List[str]:
        """Validate request data against template requirements"""
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Required field '{field}' is missing")
        
        # Validate field values
        for field, validator in self.field_validators.items():
            if field in data:
                try:
                    if not validator(data[field]):
                        errors.append(f"Field '{field}' failed validation")
                except Exception as e:
                    errors.append(f"Field '{field}' validation error: {e}")
        
        return errors
    
    def apply_defaults(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values to request data"""
        result = data.copy()
        
        for field, default_value in self.default_values.items():
            if field not in result or result[field] is None:
                result[field] = default_value
        
        return result


class RequestSigner:
    """Handles request signing for APIs that require request authentication"""
    
    def __init__(self, signing_method: str = 'hmac_sha256'):
        self.signing_method = signing_method
        self.logger = logging.getLogger(__name__)
    
    def sign_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        secret_key: str = None,
        timestamp: Optional[int] = None
    ) -> Dict[str, str]:
        """Sign request and return additional headers"""
        if not secret_key:
            raise RequestSigningError("Secret key is required for request signing")
        
        if timestamp is None:
            timestamp = int(time.time())
        
        if self.signing_method == 'hmac_sha256':
            return self._sign_hmac_sha256(method, url, headers, body, secret_key, timestamp)
        else:
            raise RequestSigningError(f"Unsupported signing method: {self.signing_method}")
    
    def _sign_hmac_sha256(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str],
        secret_key: str,
        timestamp: int
    ) -> Dict[str, str]:
        """Sign request using HMAC-SHA256"""
        # Create string to sign
        string_to_sign_parts = [
            method.upper(),
            url,
            str(timestamp)
        ]
        
        # Add content hash if body exists
        if body:
            content_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
            string_to_sign_parts.append(content_hash)
        
        # Add relevant headers (sorted for consistency)
        header_string = ''
        if headers:
            sorted_headers = sorted(
                [(k.lower(), v) for k, v in headers.items() 
                 if k.lower() in ['content-type', 'host', 'user-agent']]
            )
            header_string = '&'.join([f"{k}:{v}" for k, v in sorted_headers])
            if header_string:
                string_to_sign_parts.append(header_string)
        
        string_to_sign = '\n'.join(string_to_sign_parts)
        
        # Create signature
        signature = hmac.new(
            secret_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        self.logger.debug(f"Created signature for {method} {url}")
        
        return {
            'X-Timestamp': str(timestamp),
            'X-Signature': signature,
            'X-Signature-Method': 'HMAC-SHA256'
        }


class ContentTypeHandler:
    """Handles different content types for request bodies"""
    
    @staticmethod
    def prepare_json_content(data: Dict[str, Any]) -> tuple[str, Dict[str, str]]:
        """Prepare JSON content and headers"""
        try:
            body = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            headers = {'Content-Type': 'application/json'}
            return body, headers
        except (TypeError, ValueError) as e:
            raise RequestValidationError(f"Failed to serialize JSON data: {e}")
    
    @staticmethod
    def prepare_form_content(data: Dict[str, Any]) -> tuple[str, Dict[str, str]]:
        """Prepare form-encoded content and headers"""
        try:
            body = urlencode(data)
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            return body, headers
        except Exception as e:
            raise RequestValidationError(f"Failed to encode form data: {e}")
    
    @staticmethod
    def prepare_multipart_content(data: Dict[str, Any], files: Dict[str, Any]) -> tuple[Any, Dict[str, str]]:
        """Prepare multipart content for file uploads"""
        # For multipart, we let requests handle the encoding
        # Don't set Content-Type header - requests will set it with boundary
        return (data, files), {}


class RequestBuilder:
    """
    Builds HTTP requests from JSON templates with validation, signing, and formatting.
    
    Features:
    - Request template management and validation
    - Multiple content type support (JSON, form, multipart)
    - Request signing for authenticated APIs
    - Header management and authentication integration
    - Request logging and audit trails
    """
    
    def __init__(self):
        self.templates = {}
        self.signer = RequestSigner()
        self.content_handler = ContentTypeHandler()
        self.logger = logging.getLogger(__name__)
        self.default_timeout = 30
        self.default_headers = {
            'User-Agent': 'ComBadge-FleetAPI/1.0.0',
            'Accept': 'application/json'
        }
    
    def register_template(self, template: RequestTemplate):
        """Register a request template"""
        self.templates[template.template_id] = template
        self.logger.info(f"Registered request template: {template.template_id}")
    
    def build_from_template(
        self,
        template_id: str,
        data: Dict[str, Any],
        additional_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Build request from a registered template"""
        if template_id not in self.templates:
            raise RequestValidationError(f"Unknown template: {template_id}")
        
        template = self.templates[template_id]
        
        # Validate data against template
        validation_errors = template.validate_data(data)
        if validation_errors:
            error_msg = f"Template validation failed for '{template_id}': {validation_errors}"
            self.logger.error(error_msg)
            raise RequestValidationError(error_msg)
        
        # Apply default values
        processed_data = template.apply_defaults(data)
        
        # Build request
        headers = self.default_headers.copy()
        headers.update(template.headers)
        if additional_headers:
            headers.update(additional_headers)
        
        return self.build_request(
            data=processed_data,
            headers=headers
        )
    
    def build_request(
        self,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        content_type: str = 'json',
        files: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        allow_redirects: bool = True,
        verify_ssl: bool = True,
        signing_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Build complete request configuration
        
        Args:
            data: Request body data
            params: URL query parameters
            headers: HTTP headers
            content_type: Content type for body ('json', 'form', 'multipart')
            files: Files for multipart uploads
            timeout: Request timeout
            allow_redirects: Whether to follow redirects
            verify_ssl: Whether to verify SSL certificates
            signing_config: Configuration for request signing
            **kwargs: Additional requests parameters
            
        Returns:
            Dictionary with complete request configuration
        """
        request_config = {
            'timeout': timeout or self.default_timeout,
            'allow_redirects': allow_redirects,
            'verify': verify_ssl
        }
        
        # Add any additional kwargs
        request_config.update(kwargs)
        
        # Handle headers
        final_headers = self.default_headers.copy()
        if headers:
            final_headers.update(headers)
        
        # Handle query parameters
        if params:
            # Clean up parameters (remove None values)
            cleaned_params = {k: v for k, v in params.items() if v is not None}
            if cleaned_params:
                request_config['params'] = cleaned_params
        
        # Handle request body
        if data is not None:
            try:
                if content_type == 'json':
                    body, content_headers = self.content_handler.prepare_json_content(data)
                    request_config['data'] = body
                    final_headers.update(content_headers)
                    
                elif content_type == 'form':
                    body, content_headers = self.content_handler.prepare_form_content(data)
                    request_config['data'] = body
                    final_headers.update(content_headers)
                    
                elif content_type == 'multipart':
                    body_data, content_headers = self.content_handler.prepare_multipart_content(data, files or {})
                    if isinstance(body_data, tuple) and len(body_data) == 2:
                        request_config['data'] = body_data[0]
                        request_config['files'] = body_data[1]
                    else:
                        request_config['data'] = body_data
                    final_headers.update(content_headers)
                    
                else:
                    raise RequestValidationError(f"Unsupported content type: {content_type}")
                    
            except Exception as e:
                self.logger.error(f"Failed to prepare request body: {e}")
                raise RequestValidationError(f"Failed to prepare request body: {e}")
        
        # Handle request signing
        if signing_config:
            try:
                method = signing_config.get('method', 'GET')
                url = signing_config.get('url', '')
                secret_key = signing_config.get('secret_key')
                
                if secret_key:
                    body_for_signing = request_config.get('data')
                    if isinstance(body_for_signing, bytes):
                        body_for_signing = body_for_signing.decode('utf-8')
                    elif not isinstance(body_for_signing, str):
                        body_for_signing = None
                    
                    signature_headers = self.signer.sign_request(
                        method=method,
                        url=url,
                        headers=final_headers,
                        body=body_for_signing,
                        secret_key=secret_key
                    )
                    final_headers.update(signature_headers)
                    
            except Exception as e:
                self.logger.error(f"Request signing failed: {e}")
                raise RequestSigningError(f"Request signing failed: {e}")
        
        # Set final headers
        request_config['headers'] = final_headers
        
        # Log request details
        self.logger.debug(f"Built request config: {self._sanitize_for_logging(request_config)}")
        
        return request_config
    
    def _sanitize_for_logging(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize request config for logging (remove sensitive data)"""
        sanitized = config.copy()
        
        # Remove or mask sensitive headers
        if 'headers' in sanitized:
            headers = sanitized['headers'].copy()
            sensitive_headers = ['authorization', 'x-api-key', 'x-signature', 'cookie']
            
            for header in sensitive_headers:
                for key in list(headers.keys()):
                    if key.lower() == header:
                        headers[key] = '[MASKED]'
            
            sanitized['headers'] = headers
        
        # Truncate large body content
        if 'data' in sanitized and isinstance(sanitized['data'], str):
            if len(sanitized['data']) > 1000:
                sanitized['data'] = sanitized['data'][:1000] + '... [TRUNCATED]'
        
        return sanitized
    
    def validate_template_data(self, template_id: str, data: Dict[str, Any]) -> List[str]:
        """Validate data against a template without building the request"""
        if template_id not in self.templates:
            return [f"Unknown template: {template_id}"]
        
        template = self.templates[template_id]
        return template.validate_data(data)
    
    def get_template_info(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered template"""
        if template_id not in self.templates:
            return None
        
        template = self.templates[template_id]
        return {
            'template_id': template.template_id,
            'method': template.method,
            'endpoint': template.endpoint,
            'required_fields': template.required_fields,
            'optional_fields': template.optional_fields,
            'default_values': template.default_values,
            'headers': template.headers
        }
    
    def list_templates(self) -> List[str]:
        """List all registered template IDs"""
        return list(self.templates.keys())
    
    def create_fleet_templates(self):
        """Create common fleet management request templates"""
        # Vehicle operations templates
        self.register_template(RequestTemplate(
            template_id='create_vehicle',
            method='POST',
            endpoint='/api/vehicles',
            required_fields=['make', 'model', 'year', 'vin', 'license_plate'],
            optional_fields=['color', 'fuel_type', 'vehicle_type', 'assigned_department'],
            field_validators={
                'year': lambda x: isinstance(x, int) and 2000 <= x <= 2025,
                'vin': lambda x: isinstance(x, str) and len(x) == 17
            },
            default_values={'fuel_type': 'gasoline', 'vehicle_type': 'sedan'}
        ))
        
        self.register_template(RequestTemplate(
            template_id='update_vehicle',
            method='PUT',
            endpoint='/api/vehicles/{vehicle_id}',
            required_fields=['vehicle_id'],
            optional_fields=['assigned_department', 'assigned_driver', 'status', 'mileage']
        ))
        
        self.register_template(RequestTemplate(
            template_id='get_vehicle',
            method='GET',
            endpoint='/api/vehicles/{vehicle_id}',
            required_fields=['vehicle_id']
        ))
        
        # Maintenance templates
        self.register_template(RequestTemplate(
            template_id='schedule_maintenance',
            method='POST',
            endpoint='/api/maintenance/appointments',
            required_fields=['vehicle_id', 'maintenance_type', 'requested_date'],
            optional_fields=['priority', 'description', 'preferred_technician'],
            default_values={'priority': 'normal'}
        ))
        
        # Reservation templates
        self.register_template(RequestTemplate(
            template_id='create_reservation',
            method='POST',
            endpoint='/api/reservations',
            required_fields=['vehicle_id', 'user_id', 'start_datetime'],
            optional_fields=['end_datetime', 'purpose', 'destination'],
            field_validators={
                'passenger_count': lambda x: isinstance(x, int) and 1 <= x <= 8
            },
            default_values={'passenger_count': 1}
        ))
        
        self.logger.info("Created fleet management request templates")