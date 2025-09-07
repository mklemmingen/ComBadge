"""
Core HTTP Client for ComBadge Fleet Management API

Enterprise-grade HTTP client with session management, connection pooling,
retry logic, and comprehensive error handling for fleet management systems.
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, Union, Callable
from urllib.parse import urljoin, urlparse
from contextlib import contextmanager
import json

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.exceptions import (
    RequestException, ConnectionError, Timeout, 
    HTTPError, SSLError, TooManyRedirects
)

from .authentication import AuthenticationManager
from .request_builder import RequestBuilder
from .response_handler import ResponseHandler


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and blocking requests"""
    pass


class CircuitBreaker:
    """Circuit breaker pattern implementation for handling persistent failures"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half_open
        self._lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self._lock:
            if self.state == 'open':
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = 'half_open'
                else:
                    raise CircuitBreakerError("Circuit breaker is open")
            
            try:
                result = func(*args, **kwargs)
                if self.state == 'half_open':
                    self.state = 'closed'
                    self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = 'open'
                
                raise e


class ConnectionPool:
    """Connection pool manager for efficient HTTP connections"""
    
    def __init__(self, pool_connections: int = 10, pool_maxsize: int = 10):
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize
        self.adapters = {}
    
    def get_adapter(self, scheme: str) -> HTTPAdapter:
        """Get or create HTTP adapter for the given scheme"""
        if scheme not in self.adapters:
            retry_strategy = Retry(
                total=0,  # We handle retries at a higher level
                status_forcelist=[500, 502, 503, 504],
                backoff_factor=1
            )
            
            adapter = HTTPAdapter(
                pool_connections=self.pool_connections,
                pool_maxsize=self.pool_maxsize,
                max_retries=retry_strategy
            )
            self.adapters[scheme] = adapter
        
        return self.adapters[scheme]


class PerformanceMetrics:
    """Performance metrics tracking for API calls"""
    
    def __init__(self):
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.last_request_time = None
        self._lock = threading.Lock()
    
    def record_request(self, response_time: float, success: bool):
        """Record metrics for a completed request"""
        with self._lock:
            self.request_count += 1
            self.total_response_time += response_time
            self.last_request_time = time.time()
            
            if success:
                self.success_count += 1
            else:
                self.error_count += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        with self._lock:
            if self.request_count == 0:
                return {
                    'request_count': 0,
                    'success_rate': 0.0,
                    'average_response_time': 0.0,
                    'last_request_time': None
                }
            
            return {
                'request_count': self.request_count,
                'success_count': self.success_count,
                'error_count': self.error_count,
                'success_rate': self.success_count / self.request_count,
                'average_response_time': self.total_response_time / self.request_count,
                'last_request_time': self.last_request_time
            }
    
    def reset(self):
        """Reset all metrics"""
        with self._lock:
            self.request_count = 0
            self.success_count = 0
            self.error_count = 0
            self.total_response_time = 0.0
            self.last_request_time = None


class HTTPClient:
    """
    Enterprise HTTP client for fleet management API integration.
    
    Features:
    - Session management with persistent authentication
    - Connection pooling and reuse
    - Retry logic with exponential backoff
    - Circuit breaker pattern for fault tolerance
    - Comprehensive error handling and logging
    - Performance metrics tracking
    - SSL verification and proxy support
    """
    
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_factor: float = 1.0,
        pool_connections: int = 10,
        pool_maxsize: int = 10,
        verify_ssl: bool = True,
        proxies: Optional[Dict[str, str]] = None,
        user_agent: str = "ComBadge-FleetAPI/1.0.0"
    ):
        """
        Initialize HTTP client with configuration
        
        Args:
            base_url: Base URL for all API requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff_factor: Factor for exponential backoff
            pool_connections: Number of connection pools
            pool_maxsize: Maximum size per connection pool
            verify_ssl: Whether to verify SSL certificates
            proxies: Proxy configuration
            user_agent: User agent string for requests
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.verify_ssl = verify_ssl
        self.proxies = proxies or {}
        self.user_agent = user_agent
        
        # Initialize components
        self.session = requests.Session()
        self.auth_manager = AuthenticationManager()
        self.request_builder = RequestBuilder()
        self.response_handler = ResponseHandler()
        self.connection_pool = ConnectionPool(pool_connections, pool_maxsize)
        self.circuit_breaker = CircuitBreaker()
        self.metrics = PerformanceMetrics()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Configure session
        self._configure_session()
    
    def _configure_session(self):
        """Configure the requests session with adapters and headers"""
        # Set default headers
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Configure adapters
        for scheme in ['http', 'https']:
            adapter = self.connection_pool.get_adapter(scheme)
            self.session.mount(f'{scheme}://', adapter)
        
        # Set SSL verification and proxies
        self.session.verify = self.verify_ssl
        if self.proxies:
            self.session.proxies.update(self.proxies)
    
    def set_authentication(self, auth_config: Dict[str, Any]):
        """Configure authentication for the client"""
        self.auth_manager.configure(auth_config)
    
    @contextmanager
    def authenticated_session(self):
        """Context manager for authenticated API sessions"""
        try:
            # Apply authentication to session
            self.auth_manager.apply_authentication(self.session)
            yield self.session
        finally:
            # Cleanup or refresh authentication if needed
            pass
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from base URL and endpoint"""
        return urljoin(self.base_url, endpoint.lstrip('/'))
    
    def _execute_with_retries(self, method: str, url: str, **kwargs) -> requests.Response:
        """Execute HTTP request with retry logic and circuit breaker"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Execute request through circuit breaker
                response = self.circuit_breaker.call(
                    self.session.request,
                    method=method,
                    url=url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # Check for HTTP errors
                response.raise_for_status()
                return response
                
            except (ConnectionError, Timeout, SSLError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = (self.retry_backoff_factor * (2 ** attempt))
                    self.logger.warning(
                        f"Request failed (attempt {attempt + 1}), retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"Request failed after {self.max_retries} retries: {e}")
                    break
                    
            except HTTPError as e:
                # Don't retry client errors (4xx), only server errors (5xx)
                if e.response.status_code < 500:
                    raise e
                
                last_exception = e
                if attempt < self.max_retries:
                    delay = (self.retry_backoff_factor * (2 ** attempt))
                    self.logger.warning(
                        f"Server error (attempt {attempt + 1}), retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"Server error after {self.max_retries} retries: {e}")
                    break
                    
            except CircuitBreakerError as e:
                self.logger.error(f"Circuit breaker is open: {e}")
                raise e
                
            except RequestException as e:
                self.logger.error(f"Request exception: {e}")
                last_exception = e
                break
        
        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        else:
            raise RequestException("Request failed after all retry attempts")
    
    def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an authenticated HTTP request
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: URL query parameters
            headers: Additional headers
            **kwargs: Additional arguments for requests
            
        Returns:
            Parsed response data
            
        Raises:
            Various request exceptions for different failure scenarios
        """
        start_time = time.time()
        success = False
        
        try:
            # Build full URL
            url = self._build_url(endpoint)
            
            # Prepare request
            request_kwargs = self.request_builder.build_request(
                data=data,
                params=params,
                headers=headers,
                **kwargs
            )
            
            # Add authentication headers
            with self.authenticated_session():
                # Log request
                self.logger.info(f"Making {method} request to {url}")
                self.logger.debug(f"Request data: {request_kwargs}")
                
                # Execute request with retries
                response = self._execute_with_retries(method, url, **request_kwargs)
                
                # Process response
                result = self.response_handler.handle_response(response)
                
                success = True
                self.logger.info(f"Request completed successfully in {time.time() - start_time:.2f}s")
                return result
                
        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            # Re-raise with additional context
            raise
            
        finally:
            # Record metrics
            response_time = time.time() - start_time
            self.metrics.record_request(response_time, success)
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make GET request"""
        return self.request('GET', endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make POST request"""
        return self.request('POST', endpoint, data=data, **kwargs)
    
    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make PUT request"""
        return self.request('PUT', endpoint, data=data, **kwargs)
    
    def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make PATCH request"""
        return self.request('PATCH', endpoint, data=data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make DELETE request"""
        return self.request('DELETE', endpoint, **kwargs)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the API"""
        try:
            # Try a simple endpoint to check connectivity
            response = self.get('/health', timeout=5)
            return {
                'status': 'healthy',
                'response_time': self.metrics.get_metrics().get('average_response_time', 0),
                'details': response
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'details': None
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        base_metrics = self.metrics.get_metrics()
        base_metrics.update({
            'circuit_breaker_state': self.circuit_breaker.state,
            'circuit_breaker_failures': self.circuit_breaker.failure_count
        })
        return base_metrics
    
    def reset_metrics(self):
        """Reset performance metrics"""
        self.metrics.reset()
    
    def close(self):
        """Close the HTTP client and cleanup resources"""
        if self.session:
            self.session.close()
            self.logger.info("HTTP client session closed")