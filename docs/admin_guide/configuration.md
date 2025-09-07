# ComBadge Configuration Guide

Comprehensive configuration management guide for ComBadge administrators.

## Overview

ComBadge uses a hierarchical configuration system that allows flexible deployment across different environments while maintaining security and ease of management.

### Configuration Hierarchy

```
1. Default Configuration (lowest priority)
   ↓
2. Environment Configuration Files
   ↓ 
3. Environment Variables
   ↓
4. Runtime Configuration Changes (highest priority)
```

### Configuration File Locations

```bash
# Default configurations (read-only)
/opt/combadge/config/default_config.yaml
/opt/combadge/config/schema.yaml

# Environment-specific configurations
/opt/combadge/config/production.yaml
/opt/combadge/config/staging.yaml
/opt/combadge/config/development.yaml

# Local overrides (not tracked in git)
/opt/combadge/config/local.yaml
/opt/combadge/.env
/opt/combadge/.env.local
```

## Core Configuration Sections

### 1. Application Settings

```yaml
# config/production.yaml
application:
  name: "ComBadge Fleet Management"
  version: "1.0.0"
  debug: false
  timezone: "UTC"
  
  # Server configuration
  server:
    host: "0.0.0.0"
    port: 8000
    workers: 4
    max_connections: 1000
    keepalive_timeout: 60
    
  # Security settings
  security:
    secret_key: "${COMBADGE_SECRET_KEY}"
    session_timeout: 3600  # 1 hour
    max_login_attempts: 5
    lockout_duration: 900  # 15 minutes
    require_https: true
    
  # Request processing
  processing:
    max_request_size: 10485760  # 10MB
    request_timeout: 300  # 5 minutes
    concurrent_requests: 50
    queue_size: 1000
```

### 2. Database Configuration

```yaml
database:
  # PostgreSQL (Production)
  type: "postgresql"
  host: "${COMBADGE_DB_HOST:localhost}"
  port: "${COMBADGE_DB_PORT:5432}"
  name: "${COMBADGE_DB_NAME:combadge_db}"
  user: "${COMBADGE_DB_USER:combadge_user}"
  password: "${COMBADGE_DB_PASSWORD}"
  
  # Connection pool settings
  pool:
    min_size: 5
    max_size: 20
    max_overflow: 30
    pool_timeout: 30
    pool_recycle: 3600
    
  # Advanced settings
  options:
    echo: false  # Set to true for SQL logging
    autocommit: false
    isolation_level: "READ_COMMITTED"
    
  # Backup configuration
  backup:
    enabled: true
    schedule: "0 2 * * *"  # Daily at 2 AM
    retention_days: 30
    s3_bucket: "${BACKUP_S3_BUCKET}"
    encryption: true
```

**SQLite Configuration (Development/Small Deployments):**

```yaml
database:
  type: "sqlite"
  path: "/opt/combadge/data/combadge.db"
  backup:
    enabled: true
    schedule: "0 */4 * * *"  # Every 4 hours
    retention_days: 7
```

### 3. API Integration Settings

```yaml
api:
  # Fleet Management API
  base_url: "${COMBADGE_API_BASE_URL}"
  timeout: 30
  retries: 3
  retry_delay: 1.0  # seconds
  
  # Authentication
  authentication:
    method: "oauth2"  # oauth2, jwt, api_key, basic
    
    # OAuth2 Configuration
    oauth2:
      client_id: "${COMBADGE_API_CLIENT_ID}"
      client_secret: "${COMBADGE_API_CLIENT_SECRET}"
      token_url: "${COMBADGE_API_TOKEN_URL}"
      scope: "fleet:read fleet:write maintenance:read maintenance:write"
      
    # JWT Configuration (alternative)
    jwt:
      secret: "${COMBADGE_JWT_SECRET}"
      algorithm: "HS256"
      expiration: 3600
      
    # API Key Configuration (alternative)
    api_key:
      key: "${COMBADGE_API_KEY}"
      header: "X-API-Key"
      
  # Rate limiting
  rate_limiting:
    requests_per_minute: 100
    burst_limit: 20
    
  # Circuit breaker
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 60
    timeout: 30
```

### 4. LLM Configuration

```yaml
llm:
  # Local LLM (Ollama)
  provider: "ollama"
  base_url: "http://localhost:11434"
  model: "qwen2.5:14b"
  
  # OpenAI (alternative)
  # provider: "openai"
  # api_key: "${OPENAI_API_KEY}"
  # model: "gpt-4"
  # base_url: "https://api.openai.com/v1"
  
  # Model parameters
  parameters:
    temperature: 0.1
    max_tokens: 2048
    top_p: 0.9
    frequency_penalty: 0.0
    presence_penalty: 0.0
    
  # Request settings
  timeout: 60
  retries: 2
  
  # Context management
  context:
    max_context_length: 8192
    context_window: 4096
    memory_size: 10  # Number of previous interactions to remember
```

### 5. Email Integration

```yaml
email:
  # SMTP Configuration
  smtp:
    host: "${COMBADGE_SMTP_HOST:smtp.company.com}"
    port: "${COMBADGE_SMTP_PORT:587}"
    username: "${COMBADGE_SMTP_USER}"
    password: "${COMBADGE_SMTP_PASSWORD}"
    use_tls: true
    use_ssl: false
    
  # Email processing (incoming)
  imap:
    enabled: true
    host: "${COMBADGE_IMAP_HOST:imap.company.com}"
    port: "${COMBADGE_IMAP_PORT:993}"
    username: "${COMBADGE_IMAP_USER}"
    password: "${COMBADGE_IMAP_PASSWORD}"
    use_ssl: true
    mailbox: "INBOX"
    
  # Email settings
  settings:
    from_address: "combadge@company.com"
    from_name: "ComBadge Fleet Assistant"
    reply_to: "noreply@company.com"
    
    # Processing rules
    allowed_senders: []  # Empty = allow all authenticated users
    blocked_senders: ["spam@*", "noreply@*"]
    max_email_size: 5242880  # 5MB
    
  # Templates
  templates:
    confirmation: "email/confirmation.html"
    notification: "email/notification.html"
    error: "email/error.html"
```

### 6. Logging Configuration

```yaml
logging:
  version: 1
  disable_existing_loggers: false
  
  formatters:
    standard:
      format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
      datefmt: "%Y-%m-%d %H:%M:%S"
      
    detailed:
      format: "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(funcName)s(): %(message)s"
      datefmt: "%Y-%m-%d %H:%M:%S"
      
    json:
      format: '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
      
  handlers:
    console:
      class: logging.StreamHandler
      level: INFO
      formatter: standard
      stream: ext://sys.stdout
      
    file:
      class: logging.handlers.RotatingFileHandler
      level: DEBUG
      formatter: detailed
      filename: "/var/log/combadge/app.log"
      maxBytes: 10485760  # 10MB
      backupCount: 10
      
    audit:
      class: logging.handlers.RotatingFileHandler
      level: INFO
      formatter: json
      filename: "/var/log/combadge/audit.log"
      maxBytes: 10485760  # 10MB
      backupCount: 30
      
  loggers:
    combadge:
      level: INFO
      handlers: [console, file]
      propagate: false
      
    combadge.audit:
      level: INFO
      handlers: [audit]
      propagate: false
      
    combadge.performance:
      level: DEBUG
      handlers: [file]
      propagate: false
      
  root:
    level: WARNING
    handlers: [console]
```

### 7. Cache Configuration

```yaml
cache:
  # Redis (Production)
  backend: "redis"
  redis:
    host: "${COMBADGE_REDIS_HOST:localhost}"
    port: "${COMBADGE_REDIS_PORT:6379}"
    db: "${COMBADGE_REDIS_DB:0}"
    password: "${COMBADGE_REDIS_PASSWORD}"
    
    # Connection pool
    connection_pool:
      max_connections: 50
      retry_on_timeout: true
      socket_timeout: 5
      socket_connect_timeout: 5
      
  # Memory cache (Development)
  # backend: "memory"
  # memory:
  #   max_size: 1000
    
  # Cache settings
  settings:
    default_timeout: 300  # 5 minutes
    key_prefix: "combadge:"
    
    # Specific cache timeouts
    timeouts:
      user_sessions: 3600    # 1 hour
      api_responses: 300     # 5 minutes
      vehicle_data: 600      # 10 minutes
      templates: 1800        # 30 minutes
```

## Environment-Specific Configuration

### Production Configuration

```yaml
# config/production.yaml
environment: "production"

application:
  debug: false
  
logging:
  root:
    level: WARNING
  loggers:
    combadge:
      level: INFO
      
api:
  timeout: 30
  retries: 3
  
database:
  pool:
    max_size: 20
    
cache:
  backend: "redis"
  settings:
    default_timeout: 600
```

### Staging Configuration

```yaml
# config/staging.yaml
environment: "staging"

application:
  debug: true
  
logging:
  root:
    level: INFO
  loggers:
    combadge:
      level: DEBUG
      
api:
  base_url: "https://staging-api.company.com"
  timeout: 60
  
database:
  pool:
    max_size: 10
```

### Development Configuration

```yaml
# config/development.yaml
environment: "development"

application:
  debug: true
  server:
    port: 8001
    workers: 1
    
logging:
  root:
    level: DEBUG
  loggers:
    combadge:
      level: DEBUG
      
database:
  type: "sqlite"
  path: "./dev_data/combadge.db"
  
cache:
  backend: "memory"
  
llm:
  parameters:
    temperature: 0.3  # More creative for testing
```

## Environment Variables

### Required Environment Variables

```bash
# Core Application
COMBADGE_ENV=production
COMBADGE_SECRET_KEY=your-256-bit-secret-key
COMBADGE_ENCRYPTION_KEY=your-encryption-key

# Database
COMBADGE_DB_HOST=localhost
COMBADGE_DB_PORT=5432
COMBADGE_DB_NAME=combadge_db
COMBADGE_DB_USER=combadge_user
COMBADGE_DB_PASSWORD=secure_database_password

# API Integration
COMBADGE_API_BASE_URL=https://api.fleet.company.com
COMBADGE_API_CLIENT_ID=your_client_id
COMBADGE_API_CLIENT_SECRET=your_client_secret
COMBADGE_API_TOKEN_URL=https://auth.fleet.company.com/oauth2/token

# LLM Configuration
COMBADGE_LLM_BASE_URL=http://localhost:11434
COMBADGE_LLM_MODEL=qwen2.5:14b

# Email
COMBADGE_SMTP_HOST=smtp.company.com
COMBADGE_SMTP_PORT=587
COMBADGE_SMTP_USER=combadge@company.com
COMBADGE_SMTP_PASSWORD=smtp_password
```

### Optional Environment Variables

```bash
# Redis Cache
COMBADGE_REDIS_HOST=localhost
COMBADGE_REDIS_PORT=6379
COMBADGE_REDIS_PASSWORD=redis_password

# Backup Configuration
BACKUP_S3_BUCKET=combadge-backups
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret

# Monitoring
COMBADGE_TELEMETRY_ENDPOINT=https://metrics.company.com
COMBADGE_LOG_LEVEL=INFO

# Features
COMBADGE_ENABLE_EMAIL_PROCESSING=true
COMBADGE_ENABLE_VOICE_INPUT=false
COMBADGE_ENABLE_TELEMETRY=false
```

## Configuration Management Commands

### Validation and Testing

```bash
# Validate configuration
sudo -u combadge python -m combadge.config validate

# Test configuration
sudo -u combadge python -m combadge.config test

# Show effective configuration
sudo -u combadge python -m combadge.config show

# Check environment variables
sudo -u combadge python -m combadge.config env-check
```

### Configuration Updates

```bash
# Reload configuration (hot-reload)
sudo systemctl reload combadge

# Restart with new configuration
sudo systemctl restart combadge

# Test configuration before restart
sudo -u combadge python -m combadge.config validate config/production.yaml
```

### Backup and Restore

```bash
# Backup current configuration
sudo cp -r /opt/combadge/config/ /opt/combadge/config.backup.$(date +%Y%m%d)

# Restore configuration
sudo cp -r /opt/combadge/config.backup.20240315/ /opt/combadge/config/
sudo chown -R combadge:combadge /opt/combadge/config/
```

## Security Configuration

### SSL/TLS Settings

```yaml
security:
  ssl:
    enabled: true
    cert_file: "/etc/ssl/combadge/cert.pem"
    key_file: "/etc/ssl/combadge/private.pem"
    ca_file: "/etc/ssl/combadge/ca.pem"
    
    # SSL protocols
    protocols:
      - "TLSv1.2"
      - "TLSv1.3"
      
    # Cipher suites
    ciphers: "ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256"
    
    # Security headers
    headers:
      strict_transport_security: "max-age=31536000; includeSubDomains"
      x_frame_options: "DENY"
      x_content_type_options: "nosniff"
      x_xss_protection: "1; mode=block"
```

### Authentication & Authorization

```yaml
authentication:
  # Session configuration
  session:
    lifetime: 3600  # 1 hour
    refresh_threshold: 300  # 5 minutes before expiry
    secure_cookies: true
    http_only: true
    same_site: "strict"
    
  # Multi-factor authentication
  mfa:
    enabled: false
    methods: ["totp", "email"]
    backup_codes: 10
    
  # LDAP integration (optional)
  ldap:
    enabled: false
    server: "ldap://dc.company.com"
    bind_dn: "cn=combadge,ou=services,dc=company,dc=com"
    bind_password: "${COMBADGE_LDAP_PASSWORD}"
    user_search_base: "ou=users,dc=company,dc=com"
    group_search_base: "ou=groups,dc=company,dc=com"
    
authorization:
  # Role-based access control
  rbac:
    enabled: true
    default_role: "user"
    
  # Permission system
  permissions:
    vehicle_read: "View vehicle information"
    vehicle_write: "Modify vehicle information"
    maintenance_read: "View maintenance schedules"
    maintenance_write: "Schedule and modify maintenance"
    admin: "Full system administration"
    
  # Role definitions
  roles:
    user:
      permissions: ["vehicle_read", "maintenance_read"]
    operator:
      permissions: ["vehicle_read", "vehicle_write", "maintenance_read", "maintenance_write"]
    administrator:
      permissions: ["admin"]
```

## Performance Configuration

### Resource Limits

```yaml
performance:
  # Request processing
  request_processing:
    max_concurrent_requests: 50
    request_timeout: 300
    queue_size: 1000
    worker_timeout: 60
    
  # Memory management
  memory:
    max_memory_usage: "2GB"
    gc_threshold: "1.5GB"
    
  # Database connections
  database:
    connection_timeout: 30
    query_timeout: 60
    slow_query_threshold: 1.0
    
  # Cache optimization
  cache:
    memory_limit: "512MB"
    eviction_policy: "lru"
    compression: true
```

### Monitoring and Metrics

```yaml
monitoring:
  # Performance metrics
  metrics:
    enabled: true
    collection_interval: 60  # seconds
    retention_days: 30
    
    # Metric categories
    categories:
      - "request_latency"
      - "database_performance"
      - "cache_hit_ratio" 
      - "memory_usage"
      - "error_rates"
      
  # Health checks
  health_checks:
    enabled: true
    interval: 30  # seconds
    timeout: 10
    
    checks:
      - "database_connection"
      - "api_connectivity"
      - "llm_availability"
      - "disk_space"
      - "memory_usage"
      
  # Alerting
  alerts:
    enabled: true
    webhook_url: "${COMBADGE_ALERT_WEBHOOK}"
    
    thresholds:
      error_rate: 5  # percent
      response_time: 5000  # milliseconds
      memory_usage: 90  # percent
      disk_usage: 85  # percent
```

## Feature Configuration

### Email Processing

```yaml
features:
  email_processing:
    enabled: true
    processing_interval: 60  # seconds
    max_emails_per_batch: 10
    
    # Content filtering
    filters:
      min_confidence: 0.7
      max_email_age_days: 7
      allowed_domains: ["company.com"]
      
    # Auto-approval settings
    auto_approval:
      enabled: false
      confidence_threshold: 0.95
      max_auto_approvals_per_hour: 10
```

### Voice Input

```yaml
features:
  voice_input:
    enabled: false
    provider: "google"  # google, azure, aws
    
    # Google Speech-to-Text
    google:
      api_key: "${GOOGLE_STT_API_KEY}"
      language: "en-US"
      model: "latest_long"
      
    # Processing settings
    settings:
      max_duration: 60  # seconds
      auto_punctuation: true
      profanity_filter: true
```

### Template Management

```yaml
features:
  templates:
    enabled: true
    auto_save: true
    version_control: true
    
    # Template categories
    categories:
      - "reservations"
      - "maintenance" 
      - "inquiries"
      - "fleet_operations"
      
    # Sharing settings
    sharing:
      allow_user_templates: true
      allow_template_sharing: true
      require_approval: false
```

## Configuration Best Practices

### 1. Environment Separation

```bash
# Use different databases for each environment
production: combadge_prod
staging: combadge_staging  
development: combadge_dev

# Separate configuration files
/opt/combadge/config/production.yaml
/opt/combadge/config/staging.yaml
/opt/combadge/config/development.yaml
```

### 2. Secret Management

```bash
# Use environment variables for secrets
COMBADGE_DB_PASSWORD="${{secrets.DB_PASSWORD}}"
COMBADGE_API_SECRET="${{secrets.API_SECRET}}"

# Consider using secret management systems
# - HashiCorp Vault
# - AWS Secrets Manager
# - Azure Key Vault
# - Kubernetes Secrets
```

### 3. Configuration Validation

```yaml
# Always validate configuration before deployment
validation:
  strict_mode: true
  required_fields: [
    "database.host",
    "database.password",
    "api.base_url",
    "api.authentication.client_id"
  ]
  
  # Field validation rules
  rules:
    database.port:
      type: "integer"
      range: [1024, 65535]
    api.timeout:
      type: "integer"
      minimum: 1
      maximum: 300
```

### 4. Performance Optimization

```yaml
# Optimize for your environment
performance:
  # Small deployment (< 100 users)
  small:
    database.pool.max_size: 10
    api.rate_limiting.requests_per_minute: 50
    cache.settings.default_timeout: 300
    
  # Medium deployment (100-500 users)
  medium:
    database.pool.max_size: 20
    api.rate_limiting.requests_per_minute: 200
    cache.settings.default_timeout: 600
    
  # Large deployment (500+ users)
  large:
    database.pool.max_size: 50
    api.rate_limiting.requests_per_minute: 500
    cache.settings.default_timeout: 1200
```

### 5. Backup and Recovery

```bash
# Automated configuration backup
#!/bin/bash
# /opt/combadge/scripts/backup-config.sh

BACKUP_DIR="/opt/combadge/backups/config"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" -C /opt/combadge config/
find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +30 -delete
```

## Troubleshooting Configuration

### Common Issues

**Configuration File Not Found:**
```bash
# Check file permissions
ls -la /opt/combadge/config/
sudo chown combadge:combadge /opt/combadge/config/*.yaml

# Verify file exists
sudo -u combadge ls -la /opt/combadge/config/production.yaml
```

**Environment Variable Not Set:**
```bash
# Check environment variables
sudo -u combadge env | grep COMBADGE

# Test variable resolution
sudo -u combadge python -c "
import os
print('DB Password:', os.environ.get('COMBADGE_DB_PASSWORD', 'NOT SET'))
"
```

**Database Connection Failed:**
```bash
# Test database connection
sudo -u combadge python -m combadge.config test-db

# Check database configuration
sudo -u combadge python -m combadge.config show database
```

**Invalid Configuration Format:**
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('/opt/combadge/config/production.yaml'))"

# Use configuration validator
sudo -u combadge python -m combadge.config validate
```

## Configuration Migration

### Upgrading from Previous Versions

```bash
# Backup current configuration
sudo cp -r /opt/combadge/config/ /opt/combadge/config.v1.0.backup/

# Run migration script
sudo -u combadge python -m combadge.migrations.config migrate --from=1.0 --to=1.1

# Validate migrated configuration
sudo -u combadge python -m combadge.config validate
```

### Configuration Schema Updates

When upgrading ComBadge, configuration schema may change:

```bash
# Check for schema changes
sudo -u combadge python -m combadge.config diff-schema

# Update configuration to new schema
sudo -u combadge python -m combadge.config update-schema

# Verify compatibility
sudo -u combadge python -m combadge.config validate-schema
```

---

**Next Steps:**
1. **🔒 [Security Setup Guide](security_setup.md)** - Secure your installation
2. **🔧 [Maintenance Guide](maintenance.md)** - Keep your system running smoothly  
3. **📊 [Monitoring Guide](monitoring.md)** - Monitor performance and health
4. **🚨 [Troubleshooting Guide](troubleshooting.md)** - Resolve common issues

**Support:**
- Configuration Support: config-support@company.com
- Documentation: https://docs.company.com/combadge/configuration
- Community: https://community.company.com/combadge

---

*For enterprise configuration management and professional services, contact your ComBadge representative.*