"""Configuration Management for ComBadge

Handles loading, validation, and management of application configurations.
Supports hierarchical configuration with environment overrides, secure credential storage,
hot-reloading, and migration support.
"""

import os
import json
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, Optional, List, Union, Set
from datetime import datetime
# Optional watchdog for file monitoring
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    Observer = None
    FileSystemEventHandler = None
    HAS_WATCHDOG = False
import logging

import yaml
from pydantic import BaseModel, Field, ValidationError, validator, SecretStr
import cryptography.fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Platform-specific imports for secure storage
try:
    import win32crypt
    HAS_WIN32_CRYPT = True
except ImportError:
    HAS_WIN32_CRYPT = False

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False


class LLMConfig(BaseModel):
    """Configuration for LLM integration."""
    model: str = Field(default="qwen2.5:14b")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1)
    streaming: bool = Field(default=True)
    timeout: int = Field(default=30, ge=1)
    base_url: str = Field(default="http://localhost:11434")
    
    @validator('model')
    def validate_model(cls, v):
        """Validate model name format"""
        if not v or len(v) < 3:
            raise ValueError("Model name must be at least 3 characters")
        return v


class APIAuthConfig(BaseModel):
    """Configuration for API authentication."""
    method: str = Field(default="cookie", pattern="^(cookie|token|oauth|api_key)$")
    token_url: Optional[str] = None
    client_id: Optional[SecretStr] = None
    client_secret: Optional[SecretStr] = None
    api_key: Optional[SecretStr] = None
    username: Optional[str] = None
    password: Optional[SecretStr] = None


class APIConfig(BaseModel):
    """Configuration for external API integration."""
    base_url: str = Field(default="https://api.company.com")
    timeout: int = Field(default=30, ge=1, le=300)
    retry_attempts: int = Field(default=3, ge=0, le=10)
    retry_delay: float = Field(default=2.0, ge=0.1, le=30.0)
    authentication: APIAuthConfig = Field(default_factory=APIAuthConfig)
    verify_ssl: bool = Field(default=True)
    proxy_url: Optional[str] = None


class UIConfig(BaseModel):
    """Configuration for UI settings."""
    theme: str = Field(default="dark", pattern="^(dark|light|auto)$")
    window_size: List[int] = Field(default=[1200, 800])
    font_size: int = Field(default=12, ge=8, le=24)
    font_family: str = Field(default="Segoe UI")
    auto_approve_high_confidence: bool = Field(default=False)
    confidence_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    show_reasoning_steps: bool = Field(default=True)
    enable_sound_notifications: bool = Field(default=True)
    
    @validator('window_size')
    def validate_window_size(cls, v):
        """Validate window dimensions"""
        if len(v) != 2 or v[0] < 800 or v[1] < 600:
            raise ValueError("Window size must be [width, height] with minimum 800x600")
        return v


class ProcessingConfig(BaseModel):
    """Configuration for request processing."""
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    max_processing_time: int = Field(default=60, ge=10, le=300)
    enable_caching: bool = Field(default=True)
    cache_ttl: int = Field(default=3600, ge=60)
    max_cache_size_mb: int = Field(default=100, ge=10, le=1000)
    enable_fallback_models: bool = Field(default=True)
    

class LoggingConfig(BaseModel):
    """Configuration for logging."""
    level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    file_path: str = Field(default="logs/combadge.log")
    max_file_size: str = Field(default="10MB")
    backup_count: int = Field(default=5, ge=1, le=20)
    audit_enabled: bool = Field(default=True)
    audit_file_path: str = Field(default="logs/audit.log")
    log_to_console: bool = Field(default=True)
    
    @validator('max_file_size')
    def validate_file_size(cls, v):
        """Validate file size format"""
        import re
        if not re.match(r'^\d+[KMG]B$', v.upper()):
            raise ValueError("File size must be in format: 10KB, 10MB, or 1GB")
        return v


class KeyboardShortcuts(BaseModel):
    """Customizable keyboard shortcuts."""
    approve: str = Field(default="Ctrl+A")
    edit_approve: str = Field(default="Ctrl+E")
    regenerate: str = Field(default="Ctrl+R")
    reject: str = Field(default="Ctrl+J")
    cancel: str = Field(default="Escape")
    settings: str = Field(default="Ctrl+,")
    help: str = Field(default="F1")


class AppConfig(BaseModel):
    """Main application configuration."""
    app_name: str = Field(default="ComBadge")
    version: str = Field(default="1.0.0")
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    debug_mode: bool = Field(default=False)
    
    # Component configurations
    llm: LLMConfig = Field(default_factory=LLMConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    keyboard_shortcuts: KeyboardShortcuts = Field(default_factory=KeyboardShortcuts)
    
    # Feature flags
    enable_hot_reload: bool = Field(default=True)
    enable_auto_backup: bool = Field(default=True)
    enable_telemetry: bool = Field(default=False)
    
    class Config:
        validate_assignment = True


class ConfigFileWatcher(FileSystemEventHandler):
    """Watches configuration files for changes."""
    
    def __init__(self, config_manager: 'ConfigManager', files_to_watch: Set[Path]):
        self.config_manager = config_manager
        self.files_to_watch = {str(f) for f in files_to_watch}
        self.last_reload = datetime.now()
        
    def on_modified(self, event):
        if event.src_path in self.files_to_watch and not event.is_directory:
            # Debounce to avoid multiple reloads
            if (datetime.now() - self.last_reload).total_seconds() > 1:
                logging.info(f"Configuration file modified: {event.src_path}")
                self.config_manager.reload_config()
                self.last_reload = datetime.now()


class SecureCredentialStorage:
    """Handles secure storage of sensitive configuration data."""
    
    def __init__(self, app_name: str = "ComBadge"):
        self.app_name = app_name
        self.logger = logging.getLogger(__name__)
        self._setup_encryption()
    
    def _setup_encryption(self):
        """Setup encryption for fallback file storage."""
        # Generate encryption key from a stable source
        password = f"{self.app_name}-secure-config-2024".encode()
        salt = b"combadge-salt-stable"
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self.cipher = cryptography.fernet.Fernet(key)
    
    def store_credential(self, key: str, value: str) -> bool:
        """Store credential securely using best available method."""
        try:
            # Try Windows DPAPI first
            if HAS_WIN32_CRYPT and os.name == 'nt':
                encrypted = win32crypt.CryptProtectData(
                    value.encode('utf-8'),
                    f"{self.app_name}:{key}",
                    None, None, None, 0
                )
                self._store_encrypted_file(key, base64.b64encode(encrypted).decode())
                return True
            
            # Try system keyring
            elif HAS_KEYRING:
                keyring.set_password(self.app_name, key, value)
                return True
            
            # Fallback to encrypted file
            else:
                encrypted = self.cipher.encrypt(value.encode())
                self._store_encrypted_file(key, encrypted.decode())
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to store credential {key}: {e}")
            return False
    
    def retrieve_credential(self, key: str) -> Optional[str]:
        """Retrieve stored credential."""
        try:
            # Try Windows DPAPI first
            if HAS_WIN32_CRYPT and os.name == 'nt':
                encrypted_b64 = self._retrieve_encrypted_file(key)
                if encrypted_b64:
                    encrypted = base64.b64decode(encrypted_b64)
                    decrypted, _ = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)
                    return decrypted.decode('utf-8')
            
            # Try system keyring
            elif HAS_KEYRING:
                value = keyring.get_password(self.app_name, key)
                if value:
                    return value
            
            # Try encrypted file
            encrypted = self._retrieve_encrypted_file(key)
            if encrypted:
                return self.cipher.decrypt(encrypted.encode()).decode()
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve credential {key}: {e}")
        
        return None
    
    def _store_encrypted_file(self, key: str, encrypted_value: str):
        """Store encrypted value in file."""
        config_dir = Path.home() / ".combadge" / "secure"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Set restrictive permissions on directory
        if os.name != 'nt':
            os.chmod(config_dir, 0o700)
        
        file_path = config_dir / f"{key}.enc"
        file_path.write_text(encrypted_value)
        
        # Set restrictive permissions on file
        if os.name != 'nt':
            os.chmod(file_path, 0o600)
    
    def _retrieve_encrypted_file(self, key: str) -> Optional[str]:
        """Retrieve encrypted value from file."""
        file_path = Path.home() / ".combadge" / "secure" / f"{key}.enc"
        if file_path.exists():
            return file_path.read_text()
        return None


class ConfigManager:
    """Manages application configuration loading and validation."""
    
    SENSITIVE_FIELDS = {
        'api.authentication.client_secret',
        'api.authentication.api_key', 
        'api.authentication.password'
    }
    
    def __init__(self, config_path: Optional[Path] = None, environment: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Optional path to configuration file
            environment: Environment name (development, staging, production)
        """
        self.config_base_path = config_path or self._get_default_config_path()
        self.environment = environment or os.getenv('COMBADGE_ENV', 'development')
        self._config: Optional[AppConfig] = None
        self._observer: Optional[Observer] = None
        self._lock = threading.Lock()
        self.secure_storage = SecureCredentialStorage()
        self.logger = logging.getLogger(__name__)
        
        # Configuration file paths
        self.config_files = self._get_config_files()
        
    def _get_default_config_path(self) -> Path:
        """Get the default configuration file path."""
        # Looking for config in order of precedence
        config_locations = [
            Path("config"),
            Path.home() / ".combadge",
            Path("/etc/combadge"),
        ]
        
        for location in config_locations:
            if location.exists() and location.is_dir():
                return location
                
        # If no config exists, use the project default
        return Path("config")
    
    def _get_config_files(self) -> Dict[str, Path]:
        """Get configuration file paths for hierarchical loading."""
        base_dir = self.config_base_path
        
        return {
            'default': base_dir / 'default_config.yaml',
            'environment': base_dir / f'{self.environment}.yaml',
            'user': base_dir / 'user_preferences.yaml',
            'local': base_dir / 'local.yaml'  # For development overrides
        }
    
    def load_config(self) -> AppConfig:
        """Load and validate configuration from file with hierarchical overrides.
        
        Returns:
            Validated application configuration
            
        Raises:
            ValidationError: If config validation fails
        """
        with self._lock:
            if self._config:
                return self._config
            
            try:
                # Start with empty config
                config_data = {}
                
                # Load configurations in order of precedence
                for config_type, config_file in self.config_files.items():
                    if config_file.exists():
                        self.logger.info(f"Loading {config_type} config from {config_file}")
                        file_data = self._load_yaml_file(config_file)
                        self._deep_merge(config_data, file_data)
                
                # Apply environment variable overrides
                env_overrides = self._get_env_overrides()
                if env_overrides:
                    self.logger.info(f"Applying environment overrides: {list(env_overrides.keys())}")
                    self._deep_merge(config_data, env_overrides)
                
                # Load sensitive data from secure storage
                self._load_secure_credentials(config_data)
                
                # Create and validate configuration
                self._config = AppConfig(**config_data)
                
                # Save default config if none exists
                if not self.config_files['default'].exists():
                    self._save_default_config()
                
                # Setup hot reloading if enabled
                if self._config.enable_hot_reload:
                    self._setup_file_watcher()
                
                return self._config
                
            except ValidationError as e:
                self.logger.error(f"Configuration validation failed: {e}")
                raise ValueError(f"Invalid configuration: {e}")
            except Exception as e:
                self.logger.error(f"Failed to load configuration: {e}")
                raise
            
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file.
        
        Returns:
            Configuration dictionary
        """
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            self.logger.error(f"Failed to parse YAML file {file_path}: {e}")
            raise ValueError(f"Invalid YAML in {file_path}: {e}")
    
    def _get_env_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables.
        
        Environment variables follow pattern: COMBADGE_<SECTION>_<KEY>
        Example: COMBADGE_API_BASE_URL -> api.base_url
        """
        overrides = {}
        prefix = "COMBADGE_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Parse environment variable name
                config_path = key[len(prefix):].lower().split('_')
                
                # Build nested dictionary
                current = overrides
                for part in config_path[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                # Set value with type conversion
                final_key = config_path[-1]
                current[final_key] = self._convert_env_value(value)
        
        return overrides
    
    def _convert_env_value(self, value: str) -> Union[str, int, float, bool]:
        """Convert environment variable string to appropriate type."""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Numeric conversion
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # List conversion (comma-separated)
        if ',' in value:
            return [v.strip() for v in value.split(',')]
        
        return value
            
    def _save_default_config(self):
        """Save default configuration to file."""
        # Creating config directory if it doesn't exist
        default_file = self.config_files['default']
        default_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create default config without sensitive data
        config_dict = self._config.model_dump()
        self._remove_sensitive_data(config_dict)
        
        with open(default_file, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        
        self.logger.info(f"Created default configuration at {default_file}")
    
    def _load_secure_credentials(self, config_data: Dict[str, Any]):
        """Load sensitive credentials from secure storage."""
        for field_path in self.SENSITIVE_FIELDS:
            stored_value = self.secure_storage.retrieve_credential(field_path)
            if stored_value:
                # Navigate to the field in config_data
                parts = field_path.split('.')
                current = config_data
                
                # Create nested structure if needed
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                # Set the value
                current[parts[-1]] = stored_value
    
    def _remove_sensitive_data(self, config_dict: Dict[str, Any]):
        """Remove sensitive data from configuration dictionary."""
        for field_path in self.SENSITIVE_FIELDS:
            parts = field_path.split('.')
            current = config_dict
            
            # Navigate to parent of sensitive field
            for part in parts[:-1]:
                if part in current:
                    current = current[part]
                else:
                    break
            
            # Remove sensitive field
            if parts[-1] in current:
                current[parts[-1]] = None
            
    def update_config(self, updates: Dict[str, Any], save_to_user: bool = True) -> AppConfig:
        """Update configuration with new values.
        
        Args:
            updates: Dictionary of configuration updates
            save_to_user: Whether to save updates to user preferences file
            
        Returns:
            Updated configuration
        """
        with self._lock:
            if not self._config:
                self.load_config()
            
            # Backup current configuration
            self._backup_config()
            
            try:
                # Apply updates
                config_dict = self._config.model_dump()
                self._deep_merge(config_dict, updates)
                
                # Extract and store sensitive data
                sensitive_updates = self._extract_sensitive_data(updates)
                for field_path, value in sensitive_updates.items():
                    if value:
                        self.secure_storage.store_credential(field_path, value)
                
                # Create new config
                self._config = AppConfig(**config_dict)
                
                # Save to user preferences if requested
                if save_to_user:
                    self._save_user_preferences(updates)
                
                # Audit configuration change
                self._audit_config_change(updates)
                
                return self._config
                
            except Exception as e:
                self.logger.error(f"Failed to update configuration: {e}")
                # Restore from backup on failure
                self._restore_backup()
                raise
        
    def _deep_merge(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]):
        """Recursively merge nested dictionaries."""
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_merge(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _extract_sensitive_data(self, config_dict: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Extract sensitive data fields from configuration."""
        sensitive_data = {}
        
        for key, value in config_dict.items():
            current_path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                sensitive_data.update(self._extract_sensitive_data(value, current_path))
            elif current_path in self.SENSITIVE_FIELDS:
                sensitive_data[current_path] = value
        
        return sensitive_data
                
    def save_config(self, target: str = "user"):
        """Save current configuration to file.
        
        Args:
            target: Which config file to save to ('default', 'user', 'environment')
        """
        with self._lock:
            if not self._config:
                raise ValueError("No configuration loaded")
            
            if target not in self.config_files:
                raise ValueError(f"Invalid target: {target}")
            
            # Prepare config for saving
            config_dict = self._config.model_dump()
            self._remove_sensitive_data(config_dict)
            
            # Save to target file
            target_file = self.config_files[target]
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(target_file, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"Configuration saved to {target_file}")
    
    def _save_user_preferences(self, updates: Dict[str, Any]):
        """Save user preference updates to user config file."""
        user_file = self.config_files['user']
        
        # Load existing user preferences
        user_prefs = {}
        if user_file.exists():
            user_prefs = self._load_yaml_file(user_file)
        
        # Merge updates
        self._deep_merge(user_prefs, updates)
        
        # Remove sensitive data
        self._remove_sensitive_data(user_prefs)
        
        # Save
        user_file.parent.mkdir(parents=True, exist_ok=True)
        with open(user_file, 'w') as f:
            yaml.dump(user_prefs, f, default_flow_style=False, sort_keys=False)
    
    def _setup_file_watcher(self):
        """Setup file watcher for hot-reloading."""
        try:
            files_to_watch = set()
            for config_file in self.config_files.values():
                if config_file.exists():
                    files_to_watch.add(config_file)
            
            if files_to_watch:
                self._observer = Observer()
                event_handler = ConfigFileWatcher(self, files_to_watch)
                
                for file_path in files_to_watch:
                    self._observer.schedule(
                        event_handler,
                        str(file_path.parent),
                        recursive=False
                    )
                
                self._observer.start()
                self.logger.info("Configuration file watcher started")
                
        except Exception as e:
            self.logger.warning(f"Failed to setup file watcher: {e}")
    
    def reload_config(self):
        """Reload configuration from files."""
        self.logger.info("Reloading configuration...")
        
        with self._lock:
            old_config = self._config
            self._config = None
            
            try:
                self.load_config()
                self.logger.info("Configuration reloaded successfully")
                
                # Notify about changes
                if old_config:
                    changes = self._get_config_changes(old_config, self._config)
                    if changes:
                        self.logger.info(f"Configuration changes: {changes}")
                        
            except Exception as e:
                self.logger.error(f"Failed to reload configuration: {e}")
                self._config = old_config  # Restore old config
                raise
    
    def _get_config_changes(self, old_config: AppConfig, new_config: AppConfig) -> List[str]:
        """Get list of changed configuration fields."""
        changes = []
        old_dict = old_config.model_dump()
        new_dict = new_config.model_dump()
        
        def compare_dicts(old: Dict, new: Dict, prefix: str = ""):
            for key in set(old.keys()) | set(new.keys()):
                current_path = f"{prefix}.{key}" if prefix else key
                
                if key not in old:
                    changes.append(f"{current_path} added")
                elif key not in new:
                    changes.append(f"{current_path} removed")
                elif isinstance(old[key], dict) and isinstance(new[key], dict):
                    compare_dicts(old[key], new[key], current_path)
                elif old[key] != new[key]:
                    if current_path not in self.SENSITIVE_FIELDS:
                        changes.append(f"{current_path}: {old[key]} -> {new[key]}")
                    else:
                        changes.append(f"{current_path}: [REDACTED]")
        
        compare_dicts(old_dict, new_dict)
        return changes
    
    def _backup_config(self):
        """Create backup of current configuration."""
        if not self._config:
            return
        
        backup_dir = self.config_base_path / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"config_backup_{timestamp}.yaml"
        
        config_dict = self._config.model_dump()
        self._remove_sensitive_data(config_dict)
        
        with open(backup_file, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        
        # Keep only last 10 backups
        backups = sorted(backup_dir.glob("config_backup_*.yaml"))
        for old_backup in backups[:-10]:
            old_backup.unlink()
    
    def _restore_backup(self):
        """Restore configuration from most recent backup."""
        backup_dir = self.config_base_path / "backups"
        if not backup_dir.exists():
            return
        
        backups = sorted(backup_dir.glob("config_backup_*.yaml"))
        if backups:
            latest_backup = backups[-1]
            self.logger.info(f"Restoring configuration from {latest_backup}")
            
            backup_data = self._load_yaml_file(latest_backup)
            self._config = AppConfig(**backup_data)
    
    def _audit_config_change(self, changes: Dict[str, Any]):
        """Log configuration changes for audit."""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'user': os.getenv('USERNAME', 'unknown'),
            'changes': self._sanitize_for_audit(changes)
        }
        
        audit_file = Path(self._config.logging.audit_file_path if self._config else "logs/audit.log")
        audit_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(audit_file, 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')
    
    def _sanitize_for_audit(self, data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Sanitize configuration data for audit logging."""
        sanitized = {}
        
        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                sanitized[key] = self._sanitize_for_audit(value, current_path)
            elif current_path in self.SENSITIVE_FIELDS:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def export_config(self, file_path: Path, include_sensitive: bool = False) -> bool:
        """Export current configuration to file.
        
        Args:
            file_path: Path to export configuration
            include_sensitive: Whether to include sensitive data
            
        Returns:
            True if export successful
        """
        try:
            if not self._config:
                self.load_config()
            
            config_dict = self._config.model_dump()
            
            if not include_sensitive:
                self._remove_sensitive_data(config_dict)
            
            with open(file_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"Configuration exported to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export configuration: {e}")
            return False
    
    def import_config(self, file_path: Path) -> bool:
        """Import configuration from file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            True if import successful
        """
        try:
            # Backup current config
            self._backup_config()
            
            # Load and validate new config
            new_config_data = self._load_yaml_file(file_path)
            test_config = AppConfig(**new_config_data)
            
            # Apply the new configuration
            self._config = test_config
            
            # Save to user preferences
            self._save_user_preferences(new_config_data)
            
            self.logger.info(f"Configuration imported from {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import configuration: {e}")
            self._restore_backup()
            return False
    
    def reset_to_defaults(self, preserve_credentials: bool = True):
        """Reset configuration to defaults.
        
        Args:
            preserve_credentials: Whether to preserve stored credentials
        """
        with self._lock:
            # Backup current config
            self._backup_config()
            
            # Store credentials if preserving
            saved_credentials = {}
            if preserve_credentials and self._config:
                for field_path in self.SENSITIVE_FIELDS:
                    value = self.secure_storage.retrieve_credential(field_path)
                    if value:
                        saved_credentials[field_path] = value
            
            # Create new default config
            self._config = AppConfig()
            
            # Restore credentials if requested
            if preserve_credentials and saved_credentials:
                for field_path, value in saved_credentials.items():
                    self.secure_storage.store_credential(field_path, value)
            
            # Remove user preferences file
            user_file = self.config_files['user']
            if user_file.exists():
                user_file.unlink()
            
            self.logger.info("Configuration reset to defaults")
    
    def validate_config(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate configuration data without applying it.
        
        Args:
            config_data: Configuration data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            AppConfig(**config_data)
        except ValidationError as e:
            for error in e.errors():
                field_path = '.'.join(str(loc) for loc in error['loc'])
                errors.append(f"{field_path}: {error['msg']}")
        except Exception as e:
            errors.append(str(e))
        
        return errors
    
    def get_config_metadata(self) -> Dict[str, Any]:
        """Get metadata about current configuration."""
        metadata = {
            'environment': self.environment,
            'loaded_files': [],
            'has_user_preferences': False,
            'hot_reload_enabled': False,
            'last_modified': None
        }
        
        # Check which config files are loaded
        for config_type, config_file in self.config_files.items():
            if config_file.exists():
                metadata['loaded_files'].append(str(config_file))
                
                if config_type == 'user':
                    metadata['has_user_preferences'] = True
                
                # Get last modified time
                mtime = datetime.fromtimestamp(config_file.stat().st_mtime)
                if metadata['last_modified'] is None or mtime > metadata['last_modified']:
                    metadata['last_modified'] = mtime.isoformat()
        
        if self._config:
            metadata['hot_reload_enabled'] = self._config.enable_hot_reload
        
        return metadata
    
    def cleanup(self):
        """Cleanup resources."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self.logger.info("Configuration file watcher stopped")