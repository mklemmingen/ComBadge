"""
Authentication Management for ComBadge Fleet API Client

Secure authentication system supporting multiple auth methods including
cookies, JWT tokens, API keys, and Windows Credential Manager integration.
"""

import json
import time
import base64
import logging
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

# Platform-specific imports
try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

try:
    import cryptography.fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class CredentialStorageError(Exception):
    """Raised when credential storage operations fail"""
    pass


class SecureStorage:
    """Secure credential storage using platform-specific methods"""
    
    def __init__(self, service_name: str = "ComBadge-FleetAPI"):
        self.service_name = service_name
        self.logger = logging.getLogger(__name__)
        
        # Check available storage methods
        self.keyring_available = HAS_KEYRING
        self.crypto_available = HAS_CRYPTO
        
        if self.crypto_available:
            self._setup_encryption()
    
    def _setup_encryption(self):
        """Setup encryption for credential storage"""
        # Generate a key from a password (in production, use a secure method)
        password = b"combadge-fleet-api-secure-storage"
        salt = b"combadge-salt-2024"
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self.cipher = cryptography.fernet.Fernet(key)
    
    def store_credential(self, key: str, value: str) -> bool:
        """Store credential securely"""
        try:
            if self.keyring_available:
                keyring.set_password(self.service_name, key, value)
                self.logger.info(f"Stored credential '{key}' using keyring")
                return True
            elif self.crypto_available:
                encrypted_value = self.cipher.encrypt(value.encode()).decode()
                # Store in a secure file or registry (simplified for demo)
                self._store_encrypted_credential(key, encrypted_value)
                self.logger.info(f"Stored credential '{key}' using encryption")
                return True
            else:
                self.logger.warning(f"No secure storage available for credential '{key}'")
                return False
        except Exception as e:
            self.logger.error(f"Failed to store credential '{key}': {e}")
            raise CredentialStorageError(f"Failed to store credential: {e}")
    
    def retrieve_credential(self, key: str) -> Optional[str]:
        """Retrieve stored credential"""
        try:
            if self.keyring_available:
                value = keyring.get_password(self.service_name, key)
                if value:
                    self.logger.info(f"Retrieved credential '{key}' from keyring")
                return value
            elif self.crypto_available:
                encrypted_value = self._retrieve_encrypted_credential(key)
                if encrypted_value:
                    value = self.cipher.decrypt(encrypted_value.encode()).decode()
                    self.logger.info(f"Retrieved credential '{key}' using decryption")
                    return value
            return None
        except Exception as e:
            self.logger.error(f"Failed to retrieve credential '{key}': {e}")
            return None
    
    def delete_credential(self, key: str) -> bool:
        """Delete stored credential"""
        try:
            if self.keyring_available:
                keyring.delete_password(self.service_name, key)
                self.logger.info(f"Deleted credential '{key}' from keyring")
                return True
            elif self.crypto_available:
                self._delete_encrypted_credential(key)
                self.logger.info(f"Deleted credential '{key}' from secure storage")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete credential '{key}': {e}")
            return False
    
    def _store_encrypted_credential(self, key: str, encrypted_value: str):
        """Store encrypted credential (implementation depends on platform)"""
        # In a real implementation, store in Windows registry, macOS keychain, etc.
        # For demo, using a simple file approach (NOT recommended for production)
        import os
        storage_dir = os.path.expanduser("~/.combadge")
        os.makedirs(storage_dir, exist_ok=True)
        
        with open(os.path.join(storage_dir, f"{key}.enc"), 'w') as f:
            f.write(encrypted_value)
    
    def _retrieve_encrypted_credential(self, key: str) -> Optional[str]:
        """Retrieve encrypted credential"""
        import os
        storage_path = os.path.expanduser(f"~/.combadge/{key}.enc")
        if os.path.exists(storage_path):
            with open(storage_path, 'r') as f:
                return f.read()
        return None
    
    def _delete_encrypted_credential(self, key: str):
        """Delete encrypted credential file"""
        import os
        storage_path = os.path.expanduser(f"~/.combadge/{key}.enc")
        if os.path.exists(storage_path):
            os.remove(storage_path)


class AuthMethod(ABC):
    """Abstract base class for authentication methods"""
    
    @abstractmethod
    def authenticate(self, session: requests.Session, config: Dict[str, Any]) -> bool:
        """Apply authentication to the session"""
        pass
    
    @abstractmethod
    def is_valid(self) -> bool:
        """Check if current authentication is still valid"""
        pass
    
    @abstractmethod
    def refresh(self, session: requests.Session) -> bool:
        """Refresh authentication if possible"""
        pass


class CookieAuth(AuthMethod):
    """Cookie-based session authentication"""
    
    def __init__(self):
        self.cookies = None
        self.login_url = None
        self.credentials = {}
        self.last_login = None
        self.session_timeout = 3600  # 1 hour default
        self.logger = logging.getLogger(__name__)
    
    def authenticate(self, session: requests.Session, config: Dict[str, Any]) -> bool:
        """Authenticate using login credentials and store cookies"""
        try:
            self.login_url = config.get('login_url')
            self.credentials = {
                'username': config.get('username'),
                'password': config.get('password')
            }
            self.session_timeout = config.get('session_timeout', 3600)
            
            if not all([self.login_url, self.credentials['username'], self.credentials['password']]):
                raise AuthenticationError("Missing required login credentials")
            
            # Attempt login
            login_data = self.credentials.copy()
            login_data.update(config.get('additional_fields', {}))
            
            response = session.post(self.login_url, data=login_data)
            response.raise_for_status()
            
            # Check for successful login (customize based on API)
            if self._is_login_successful(response):
                self.cookies = session.cookies
                self.last_login = time.time()
                self.logger.info("Cookie authentication successful")
                return True
            else:
                raise AuthenticationError("Login failed - invalid credentials")
                
        except Exception as e:
            self.logger.error(f"Cookie authentication failed: {e}")
            raise AuthenticationError(f"Cookie authentication failed: {e}")
    
    def _is_login_successful(self, response: requests.Response) -> bool:
        """Check if login was successful (customize based on API response)"""
        # Common indicators of successful login:
        # - 200 status code with success indicator in response
        # - Redirect to dashboard/home page
        # - Presence of session cookies
        
        if response.status_code == 200:
            # Check response content for success indicators
            try:
                data = response.json()
                return data.get('success', True) and not data.get('error')
            except (ValueError, json.JSONDecodeError):
                # If not JSON, check for common success patterns
                content = response.text.lower()
                error_indicators = ['error', 'invalid', 'failed', 'unauthorized']
                return not any(indicator in content for indicator in error_indicators)
        
        # Check for redirects (common after successful login)
        return 300 <= response.status_code < 400
    
    def is_valid(self) -> bool:
        """Check if session cookies are still valid"""
        if not self.cookies or not self.last_login:
            return False
        
        # Check if session has timed out
        elapsed = time.time() - self.last_login
        return elapsed < self.session_timeout
    
    def refresh(self, session: requests.Session) -> bool:
        """Refresh session by re-authenticating"""
        if not self.credentials.get('username') or not self.credentials.get('password'):
            return False
        
        try:
            config = {
                'login_url': self.login_url,
                'username': self.credentials['username'],
                'password': self.credentials['password'],
                'session_timeout': self.session_timeout
            }
            return self.authenticate(session, config)
        except Exception:
            return False


class JWTAuth(AuthMethod):
    """JWT token-based authentication"""
    
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.token_url = None
        self.credentials = {}
        self.logger = logging.getLogger(__name__)
    
    def authenticate(self, session: requests.Session, config: Dict[str, Any]) -> bool:
        """Authenticate and obtain JWT tokens"""
        try:
            self.token_url = config.get('token_url')
            self.credentials = {
                'username': config.get('username'),
                'password': config.get('password'),
                'client_id': config.get('client_id'),
                'client_secret': config.get('client_secret')
            }
            
            if not self.token_url:
                raise AuthenticationError("Token URL is required for JWT authentication")
            
            # Prepare token request
            token_data = {
                'grant_type': 'password',
                'username': self.credentials['username'],
                'password': self.credentials['password']
            }
            
            # Add client credentials if provided
            if self.credentials['client_id']:
                token_data['client_id'] = self.credentials['client_id']
            if self.credentials['client_secret']:
                token_data['client_secret'] = self.credentials['client_secret']
            
            # Request tokens
            response = session.post(self.token_url, data=token_data)
            response.raise_for_status()
            
            token_response = response.json()
            self.access_token = token_response.get('access_token')
            self.refresh_token = token_response.get('refresh_token')
            
            if not self.access_token:
                raise AuthenticationError("No access token received")
            
            # Calculate expiry time
            expires_in = token_response.get('expires_in', 3600)
            self.token_expiry = time.time() + expires_in - 60  # 60s buffer
            
            # Set authorization header
            session.headers['Authorization'] = f'Bearer {self.access_token}'
            
            self.logger.info("JWT authentication successful")
            return True
            
        except Exception as e:
            self.logger.error(f"JWT authentication failed: {e}")
            raise AuthenticationError(f"JWT authentication failed: {e}")
    
    def is_valid(self) -> bool:
        """Check if JWT token is still valid"""
        if not self.access_token or not self.token_expiry:
            return False
        
        return time.time() < self.token_expiry
    
    def refresh(self, session: requests.Session) -> bool:
        """Refresh JWT token using refresh token"""
        if not self.refresh_token or not self.token_url:
            return False
        
        try:
            refresh_data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }
            
            # Add client credentials if available
            if self.credentials.get('client_id'):
                refresh_data['client_id'] = self.credentials['client_id']
            if self.credentials.get('client_secret'):
                refresh_data['client_secret'] = self.credentials['client_secret']
            
            response = session.post(self.token_url, data=refresh_data)
            response.raise_for_status()
            
            token_response = response.json()
            self.access_token = token_response.get('access_token')
            
            if token_response.get('refresh_token'):
                self.refresh_token = token_response.get('refresh_token')
            
            # Update expiry time
            expires_in = token_response.get('expires_in', 3600)
            self.token_expiry = time.time() + expires_in - 60
            
            # Update authorization header
            session.headers['Authorization'] = f'Bearer {self.access_token}'
            
            self.logger.info("JWT token refreshed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"JWT token refresh failed: {e}")
            return False


class APIKeyAuth(AuthMethod):
    """API key-based authentication"""
    
    def __init__(self):
        self.api_key = None
        self.api_secret = None
        self.header_name = 'X-API-Key'
        self.secret_header_name = 'X-API-Secret'
        self.logger = logging.getLogger(__name__)
    
    def authenticate(self, session: requests.Session, config: Dict[str, Any]) -> bool:
        """Apply API key authentication"""
        try:
            self.api_key = config.get('api_key')
            self.api_secret = config.get('api_secret')
            self.header_name = config.get('header_name', 'X-API-Key')
            self.secret_header_name = config.get('secret_header_name', 'X-API-Secret')
            
            if not self.api_key:
                raise AuthenticationError("API key is required")
            
            # Set API key header
            session.headers[self.header_name] = self.api_key
            
            # Set API secret header if provided
            if self.api_secret:
                session.headers[self.secret_header_name] = self.api_secret
            
            self.logger.info("API key authentication configured")
            return True
            
        except Exception as e:
            self.logger.error(f"API key authentication failed: {e}")
            raise AuthenticationError(f"API key authentication failed: {e}")
    
    def is_valid(self) -> bool:
        """API keys don't expire, so always valid if set"""
        return bool(self.api_key)
    
    def refresh(self, session: requests.Session) -> bool:
        """API keys don't need refreshing"""
        return self.is_valid()


class BasicAuth(AuthMethod):
    """HTTP Basic Authentication"""
    
    def __init__(self):
        self.username = None
        self.password = None
        self.logger = logging.getLogger(__name__)
    
    def authenticate(self, session: requests.Session, config: Dict[str, Any]) -> bool:
        """Apply Basic authentication"""
        try:
            self.username = config.get('username')
            self.password = config.get('password')
            
            if not all([self.username, self.password]):
                raise AuthenticationError("Username and password are required for Basic auth")
            
            session.auth = HTTPBasicAuth(self.username, self.password)
            self.logger.info("Basic authentication configured")
            return True
            
        except Exception as e:
            self.logger.error(f"Basic authentication failed: {e}")
            raise AuthenticationError(f"Basic authentication failed: {e}")
    
    def is_valid(self) -> bool:
        """Basic auth doesn't expire"""
        return bool(self.username and self.password)
    
    def refresh(self, session: requests.Session) -> bool:
        """Basic auth doesn't need refreshing"""
        return self.is_valid()


class AuthenticationManager:
    """
    Centralized authentication management for multiple auth methods.
    
    Supports automatic credential storage, session persistence,
    token refresh, and multi-factor authentication flows.
    """
    
    AUTH_METHODS = {
        'cookie': CookieAuth,
        'jwt': JWTAuth,
        'api_key': APIKeyAuth,
        'basic': BasicAuth
    }
    
    def __init__(self):
        self.auth_method = None
        self.auth_config = {}
        self.secure_storage = SecureStorage()
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
        self.auto_refresh = True
        self.credential_prefix = "combadge_fleet_"
    
    def configure(self, config: Dict[str, Any]):
        """Configure authentication method and settings"""
        with self._lock:
            auth_type = config.get('type', 'cookie')
            
            if auth_type not in self.AUTH_METHODS:
                raise AuthenticationError(f"Unsupported authentication type: {auth_type}")
            
            self.auth_config = config.copy()
            self.auth_method = self.AUTH_METHODS[auth_type]()
            self.auto_refresh = config.get('auto_refresh', True)
            
            # Load stored credentials if available
            self._load_stored_credentials()
            
            self.logger.info(f"Authentication configured for type: {auth_type}")
    
    def _load_stored_credentials(self):
        """Load stored credentials from secure storage"""
        auth_type = self.auth_config.get('type')
        credential_key = f"{self.credential_prefix}{auth_type}"
        
        stored_credentials = self.secure_storage.retrieve_credential(credential_key)
        if stored_credentials:
            try:
                stored_data = json.loads(stored_credentials)
                # Merge stored credentials with config (config takes precedence)
                for key, value in stored_data.items():
                    if key not in self.auth_config:
                        self.auth_config[key] = value
                
                self.logger.info("Loaded stored credentials")
            except (json.JSONDecodeError, Exception) as e:
                self.logger.warning(f"Failed to load stored credentials: {e}")
    
    def store_credentials(self, credentials: Dict[str, str]):
        """Store credentials securely for future use"""
        auth_type = self.auth_config.get('type')
        credential_key = f"{self.credential_prefix}{auth_type}"
        
        try:
            credential_data = json.dumps(credentials)
            success = self.secure_storage.store_credential(credential_key, credential_data)
            if success:
                self.logger.info("Credentials stored securely")
            return success
        except Exception as e:
            self.logger.error(f"Failed to store credentials: {e}")
            return False
    
    def apply_authentication(self, session: requests.Session):
        """Apply authentication to the session"""
        with self._lock:
            if not self.auth_method:
                raise AuthenticationError("Authentication not configured")
            
            # Check if current authentication is valid
            if not self.auth_method.is_valid():
                if self.auto_refresh and hasattr(self.auth_method, 'refresh'):
                    if not self.auth_method.refresh(session):
                        # Refresh failed, re-authenticate
                        self.auth_method.authenticate(session, self.auth_config)
                else:
                    # Re-authenticate
                    self.auth_method.authenticate(session, self.auth_config)
            
            # For some auth methods, we may need to ensure headers are set
            if isinstance(self.auth_method, (JWTAuth, APIKeyAuth)):
                # These methods set headers that may need to be refreshed
                pass
    
    def clear_credentials(self):
        """Clear stored credentials"""
        auth_type = self.auth_config.get('type')
        credential_key = f"{self.credential_prefix}{auth_type}"
        
        success = self.secure_storage.delete_credential(credential_key)
        if success:
            self.logger.info("Stored credentials cleared")
        return success
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated"""
        with self._lock:
            return self.auth_method and self.auth_method.is_valid()
    
    def get_auth_status(self) -> Dict[str, Any]:
        """Get current authentication status"""
        with self._lock:
            if not self.auth_method:
                return {
                    'authenticated': False,
                    'type': None,
                    'valid': False
                }
            
            return {
                'authenticated': True,
                'type': self.auth_config.get('type'),
                'valid': self.auth_method.is_valid(),
                'auto_refresh': self.auto_refresh
            }