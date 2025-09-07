"""
Base Endpoint Class for ComBadge Fleet API

Abstract base class providing common functionality for all API endpoints
including error handling, logging, and standardized request patterns.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime

from ..client import HTTPClient
from ..response_handler import APIError, ResponseProcessingError


class EndpointError(Exception):
    """Base exception for endpoint-specific errors"""
    pass


class BaseEndpoint(ABC):
    """
    Abstract base class for fleet management API endpoints.
    
    Provides common functionality including:
    - HTTP client integration
    - Standardized error handling
    - Request/response logging
    - Common query parameters
    - Pagination support
    - Caching capabilities
    """
    
    def __init__(self, client: HTTPClient):
        """
        Initialize endpoint with HTTP client
        
        Args:
            client: Configured HTTPClient instance
        """
        self.client = client
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_path = self._get_base_path()
        
        # Common configuration
        self.default_timeout = 30
        self.max_page_size = 100
        self.default_page_size = 50
        
        # Cache for frequently accessed data
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes default TTL
    
    @abstractmethod
    def _get_base_path(self) -> str:
        """Return the base API path for this endpoint (e.g., '/api/vehicles')"""
        pass
    
    def _build_endpoint(self, path: str = '', **path_params) -> str:
        """
        Build full endpoint path with optional parameters
        
        Args:
            path: Additional path segments
            **path_params: Path parameters to substitute
            
        Returns:
            Complete endpoint path
        """
        endpoint = self.base_path
        
        if path:
            endpoint = endpoint.rstrip('/') + '/' + path.lstrip('/')
        
        # Substitute path parameters
        if path_params:
            endpoint = endpoint.format(**path_params)
        
        return endpoint
    
    def _handle_common_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle common query parameters for all endpoints
        
        Args:
            params: Request parameters
            
        Returns:
            Processed parameters with common ones handled
        """
        processed_params = params.copy()
        
        # Handle pagination
        if 'page' in processed_params and processed_params['page'] < 1:
            processed_params['page'] = 1
        
        if 'limit' in processed_params:
            limit = processed_params['limit']
            if limit > self.max_page_size:
                processed_params['limit'] = self.max_page_size
            elif limit < 1:
                processed_params['limit'] = self.default_page_size
        
        # Handle sorting
        if 'sort' in processed_params:
            sort_value = processed_params['sort']
            if isinstance(sort_value, list):
                processed_params['sort'] = ','.join(sort_value)
        
        # Remove None values
        return {k: v for k, v in processed_params.items() if v is not None}
    
    def _handle_request_error(self, error: Exception, operation: str, **context) -> None:
        """
        Handle request errors with standardized logging and re-raising
        
        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
            **context: Additional context for logging
        """
        error_context = {
            'operation': operation,
            'endpoint_class': self.__class__.__name__,
            'timestamp': datetime.now().isoformat(),
            **context
        }
        
        if isinstance(error, APIError):
            self.logger.error(
                f"API error during {operation}: {error} "
                f"(status: {error.status_code}, code: {error.error_code})",
                extra=error_context
            )
        elif isinstance(error, ResponseProcessingError):
            self.logger.error(f"Response processing error during {operation}: {error}", extra=error_context)
        else:
            self.logger.error(f"Unexpected error during {operation}: {error}", extra=error_context)
        
        # Re-raise the original exception
        raise
    
    def _log_operation(self, operation: str, **context):
        """Log successful operations"""
        self.logger.info(f"Successfully completed {operation}", extra=context)
    
    def _validate_required_params(self, params: Dict[str, Any], required_fields: List[str]):
        """
        Validate that required parameters are present
        
        Args:
            params: Parameters to validate
            required_fields: List of required field names
            
        Raises:
            EndpointError: If any required fields are missing
        """
        missing_fields = []
        
        for field in required_fields:
            if field not in params or params[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            raise EndpointError(f"Missing required parameters: {missing_fields}")
    
    def _build_cache_key(self, operation: str, **params) -> str:
        """Build cache key for operation and parameters"""
        param_str = '_'.join(f"{k}:{v}" for k, v in sorted(params.items()) if v is not None)
        return f"{self.__class__.__name__}:{operation}:{param_str}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if still valid"""
        if cache_key in self._cache:
            cached_item = self._cache[cache_key]
            if datetime.now().timestamp() - cached_item['timestamp'] < self._cache_ttl:
                self.logger.debug(f"Returning cached result for {cache_key}")
                return cached_item['data']
            else:
                # Remove expired cache entry
                del self._cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: Any):
        """Cache result with timestamp"""
        self._cache[cache_key] = {
            'data': result,
            'timestamp': datetime.now().timestamp()
        }
        self.logger.debug(f"Cached result for {cache_key}")
    
    def _clear_cache(self, pattern: str = None):
        """Clear cache entries, optionally matching a pattern"""
        if pattern:
            keys_to_remove = [key for key in self._cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()
    
    # Common CRUD operations
    
    def _get_resource(
        self,
        resource_id: str,
        additional_path: str = '',
        use_cache: bool = True,
        **params
    ) -> Dict[str, Any]:
        """
        Generic GET operation for a specific resource
        
        Args:
            resource_id: ID of the resource to retrieve
            additional_path: Additional path segments after the ID
            use_cache: Whether to use caching for this request
            **params: Additional query parameters
            
        Returns:
            Resource data
        """
        try:
            # Build cache key if caching is enabled
            cache_key = None
            if use_cache:
                cache_key = self._build_cache_key('get', id=resource_id, path=additional_path, **params)
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result
            
            # Build endpoint
            path = resource_id
            if additional_path:
                path += '/' + additional_path.lstrip('/')
            
            endpoint = self._build_endpoint(path)
            
            # Process parameters
            processed_params = self._handle_common_parameters(params)
            
            # Make request
            result = self.client.get(endpoint, params=processed_params)
            
            # Cache result if caching is enabled
            if use_cache and cache_key:
                self._cache_result(cache_key, result)
            
            self._log_operation('get_resource', resource_id=resource_id, endpoint=endpoint)
            return result
            
        except Exception as e:
            self._handle_request_error(e, 'get_resource', resource_id=resource_id)
    
    def _list_resources(
        self,
        additional_path: str = '',
        use_cache: bool = False,
        **params
    ) -> Dict[str, Any]:
        """
        Generic LIST operation for resources
        
        Args:
            additional_path: Additional path segments
            use_cache: Whether to use caching for this request
            **params: Query parameters including pagination
            
        Returns:
            List of resources with pagination metadata
        """
        try:
            # Build cache key if caching is enabled
            cache_key = None
            if use_cache:
                cache_key = self._build_cache_key('list', path=additional_path, **params)
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result
            
            # Build endpoint
            endpoint = self._build_endpoint(additional_path)
            
            # Process parameters with pagination defaults
            processed_params = self._handle_common_parameters(params)
            if 'limit' not in processed_params:
                processed_params['limit'] = self.default_page_size
            
            # Make request
            result = self.client.get(endpoint, params=processed_params)
            
            # Cache result if caching is enabled
            if use_cache and cache_key:
                self._cache_result(cache_key, result)
            
            self._log_operation('list_resources', endpoint=endpoint, params=processed_params)
            return result
            
        except Exception as e:
            self._handle_request_error(e, 'list_resources', params=params)
    
    def _create_resource(self, data: Dict[str, Any], additional_path: str = '') -> Dict[str, Any]:
        """
        Generic CREATE operation for resources
        
        Args:
            data: Resource data to create
            additional_path: Additional path segments
            
        Returns:
            Created resource data
        """
        try:
            # Build endpoint
            endpoint = self._build_endpoint(additional_path)
            
            # Make request
            result = self.client.post(endpoint, data=data)
            
            # Clear relevant cache entries
            self._clear_cache('list')
            
            self._log_operation('create_resource', endpoint=endpoint)
            return result
            
        except Exception as e:
            self._handle_request_error(e, 'create_resource', data_keys=list(data.keys()))
    
    def _update_resource(
        self,
        resource_id: str,
        data: Dict[str, Any],
        additional_path: str = '',
        method: str = 'PUT'
    ) -> Dict[str, Any]:
        """
        Generic UPDATE operation for resources
        
        Args:
            resource_id: ID of the resource to update
            data: Updated resource data
            additional_path: Additional path segments
            method: HTTP method to use (PUT or PATCH)
            
        Returns:
            Updated resource data
        """
        try:
            # Build endpoint
            path = resource_id
            if additional_path:
                path += '/' + additional_path.lstrip('/')
            
            endpoint = self._build_endpoint(path)
            
            # Make request
            if method.upper() == 'PATCH':
                result = self.client.patch(endpoint, data=data)
            else:
                result = self.client.put(endpoint, data=data)
            
            # Clear relevant cache entries
            self._clear_cache(resource_id)
            self._clear_cache('list')
            
            self._log_operation('update_resource', resource_id=resource_id, endpoint=endpoint, method=method)
            return result
            
        except Exception as e:
            self._handle_request_error(e, 'update_resource', resource_id=resource_id, method=method)
    
    def _delete_resource(self, resource_id: str, additional_path: str = '') -> Dict[str, Any]:
        """
        Generic DELETE operation for resources
        
        Args:
            resource_id: ID of the resource to delete
            additional_path: Additional path segments
            
        Returns:
            Deletion confirmation or empty response
        """
        try:
            # Build endpoint
            path = resource_id
            if additional_path:
                path += '/' + additional_path.lstrip('/')
            
            endpoint = self._build_endpoint(path)
            
            # Make request
            result = self.client.delete(endpoint)
            
            # Clear relevant cache entries
            self._clear_cache(resource_id)
            self._clear_cache('list')
            
            self._log_operation('delete_resource', resource_id=resource_id, endpoint=endpoint)
            return result
            
        except Exception as e:
            self._handle_request_error(e, 'delete_resource', resource_id=resource_id)
    
    # Pagination helpers
    
    def get_all_pages(
        self,
        list_method: Callable[..., Dict[str, Any]],
        max_pages: int = None,
        **params
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all pages of results from a paginated endpoint
        
        Args:
            list_method: Method that returns paginated results
            max_pages: Maximum number of pages to retrieve
            **params: Parameters for the list method
            
        Returns:
            List of all items across all pages
        """
        all_items = []
        page = 1
        pages_retrieved = 0
        
        while True:
            # Check page limit
            if max_pages and pages_retrieved >= max_pages:
                self.logger.warning(f"Reached maximum page limit ({max_pages})")
                break
            
            # Get current page
            params['page'] = page
            result = list_method(**params)
            
            # Extract items (handle different response formats)
            if isinstance(result, dict):
                items = result.get('items', result.get('data', result.get('results', [])))
                
                # Check if we have pagination info
                pagination = result.get('pagination', {})
                total_pages = pagination.get('total_pages')
                has_next = pagination.get('has_next', len(items) > 0)
                
                all_items.extend(items)
                pages_retrieved += 1
                
                # Check if we should continue
                if not has_next or (total_pages and page >= total_pages):
                    break
                
                page += 1
            else:
                # If result is not a dict, assume it's the items list
                all_items.extend(result if isinstance(result, list) else [])
                break
        
        self.logger.info(f"Retrieved {len(all_items)} items across {pages_retrieved} pages")
        return all_items
    
    # Health and status methods
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of this endpoint"""
        try:
            # Try a simple list operation with minimal results
            result = self._list_resources(limit=1)
            return {
                'status': 'healthy',
                'endpoint': self.__class__.__name__,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'endpoint': self.__class__.__name__,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }