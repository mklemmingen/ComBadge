# ComBadge Installation Guide

Complete installation and deployment guide for system administrators.

## System Requirements

### Minimum Requirements

**Hardware:**
- **CPU**: 4 cores, 2.0GHz (Intel i5 or AMD equivalent)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 2GB for application, 10GB for data/logs
- **Network**: 100Mbps ethernet, stable internet connection

**Operating Systems:**
- **Windows**: Windows 10/11, Windows Server 2019/2022
- **Linux**: Ubuntu 20.04+, RHEL 8+, CentOS 8+, Debian 11+
- **macOS**: macOS 11.0+ (Big Sur) for development/testing

**Software Dependencies:**
- **Python**: 3.9+ (3.11 recommended)
- **Database**: PostgreSQL 13+ or SQLite 3.35+
- **Web Server**: nginx 1.18+ (for production deployments)

### Recommended Production Requirements

**Hardware:**
- **CPU**: 8 cores, 3.0GHz with AVX support
- **RAM**: 32GB for high-load environments
- **Storage**: SSD with 100GB+ available space
- **Network**: Redundant connections, dedicated VLAN

**Infrastructure:**
- **Load Balancer**: HAProxy or nginx for multiple instances
- **Monitoring**: Prometheus + Grafana or equivalent
- **Backup**: Automated database and configuration backups
- **Security**: SSL certificates, firewall, intrusion detection

## Pre-Installation Checklist

### Network Requirements

**Outbound Connections:**
```bash
# LLM Service (if using remote)
curl -I https://api.openai.com/v1/models
curl -I http://localhost:11434/api/tags  # For local Ollama

# Fleet Management API
curl -I https://your-fleet-api.company.com/health

# Package repositories
curl -I https://pypi.org/simple/
```

**Inbound Connections:**
- Port 8000 (HTTP) - Application interface
- Port 8443 (HTTPS) - Secure application access
- Port 5432 (PostgreSQL) - Database access (if remote)

### Security Considerations

**Firewall Configuration:**
```bash
# Example UFW rules for Ubuntu
sudo ufw allow 8000/tcp
sudo ufw allow 8443/tcp  
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 5432/tcp   # PostgreSQL (if needed)
```

**SSL Certificate:**
- Obtain SSL certificate from your CA
- Or use Let's Encrypt for automatic certificates
- Configure reverse proxy for HTTPS termination

### User Accounts

**Service Account:**
```bash
# Create dedicated service account
sudo useradd -r -s /bin/false -m combadge
sudo usermod -a -G combadge-users combadge
```

**Database User:**
```sql
-- PostgreSQL setup
CREATE USER combadge_user WITH PASSWORD 'secure_password';
CREATE DATABASE combadge_db OWNER combadge_user;
GRANT ALL PRIVILEGES ON DATABASE combadge_db TO combadge_user;
```

## Installation Methods

### Method 1: Package Installation (Recommended)

**Ubuntu/Debian:**
```bash
# Add repository
curl -fsSL https://packages.company.com/combadge/gpg | sudo apt-key add -
echo "deb https://packages.company.com/combadge/ubuntu focal main" | sudo tee /etc/apt/sources.list.d/combadge.list

# Install
sudo apt update
sudo apt install combadge

# Start service
sudo systemctl enable combadge
sudo systemctl start combadge
```

**RHEL/CentOS:**
```bash
# Add repository
sudo yum install -y https://packages.company.com/combadge/centos8/combadge-release.rpm

# Install
sudo yum install combadge

# Start service
sudo systemctl enable combadge
sudo systemctl start combadge
```

**Windows:**
```powershell
# Download installer
Invoke-WebRequest -Uri "https://releases.company.com/combadge/combadge-installer.msi" -OutFile "combadge-installer.msi"

# Install (run as Administrator)
msiexec /i combadge-installer.msi /quiet

# Start service
Start-Service ComBadge
Set-Service -Name ComBadge -StartupType Automatic
```

### Method 2: Source Installation

**Prerequisites:**
```bash
# Install Python and dependencies
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
sudo apt install build-essential libffi-dev libssl-dev
sudo apt install postgresql-client git curl
```

**Download and Setup:**
```bash
# Clone repository
cd /opt
sudo git clone https://github.com/company/combadge.git
sudo chown -R combadge:combadge combadge
cd combadge

# Switch to service account
sudo -u combadge bash

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

**Configuration:**
```bash
# Copy configuration template
cp config/default_config.yaml config/production.yaml
cp config/.env.example .env

# Edit configuration (see Configuration Guide)
nano config/production.yaml
nano .env
```

**System Service:**
```bash
# Create systemd service file
sudo tee /etc/systemd/system/combadge.service > /dev/null <<EOF
[Unit]
Description=ComBadge Fleet Management Assistant
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=combadge
Group=combadge
WorkingDirectory=/opt/combadge
Environment=COMBADGE_CONFIG=/opt/combadge/config/production.yaml
ExecStart=/opt/combadge/venv/bin/python -m combadge.main
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable combadge
sudo systemctl start combadge
```

### Method 3: Docker Deployment

**Docker Compose Setup:**
```yaml
# docker-compose.yml
version: '3.8'

services:
  combadge:
    image: combadge:latest
    container_name: combadge-app
    ports:
      - "8000:8000"
    environment:
      - COMBADGE_CONFIG=/app/config/docker.yaml
      - COMBADGE_ENV=production
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
      - combadge-data:/app/data
    depends_on:
      - database
    restart: unless-stopped

  database:
    image: postgres:15
    container_name: combadge-db
    environment:
      - POSTGRES_DB=combadge_db
      - POSTGRES_USER=combadge_user
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    secrets:
      - db_password
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: combadge-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - combadge
    restart: unless-stopped

volumes:
  combadge-data:
  postgres-data:

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

**Deploy:**
```bash
# Create directory structure
mkdir -p combadge-deploy/{config,logs,secrets,ssl}
cd combadge-deploy

# Download compose file and configs
curl -O https://deploy.company.com/combadge/docker-compose.yml
curl -O https://deploy.company.com/combadge/nginx.conf

# Set database password
echo "your_secure_database_password" > secrets/db_password.txt
chmod 600 secrets/db_password.txt

# Deploy
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs combadge
```

## Database Setup

### PostgreSQL Setup (Recommended)

**Installation:**
```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# RHEL/CentOS
sudo yum install postgresql-server postgresql-contrib
sudo postgresql-setup initdb
```

**Configuration:**
```bash
# Edit PostgreSQL configuration
sudo -u postgres psql

# Create database and user
CREATE DATABASE combadge_db;
CREATE USER combadge_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE combadge_db TO combadge_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO combadge_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO combadge_user;

# Exit PostgreSQL
\q
```

**Performance Tuning:**
```bash
# Edit postgresql.conf
sudo nano /etc/postgresql/15/main/postgresql.conf

# Recommended settings for ComBadge
shared_buffers = 256MB          # 25% of RAM
effective_cache_size = 1GB      # 75% of RAM  
work_mem = 4MB                  # For sorting operations
maintenance_work_mem = 64MB     # For maintenance operations
checkpoint_completion_target = 0.7
wal_buffers = 16MB
default_statistics_target = 100
```

### SQLite Setup (Development/Small Deployments)

**Configuration:**
```yaml
# config/production.yaml
database:
  type: sqlite
  path: /opt/combadge/data/combadge.db
  backup_enabled: true
  backup_retention_days: 30
```

**Setup:**
```bash
# Create database directory
sudo mkdir -p /opt/combadge/data
sudo chown combadge:combadge /opt/combadge/data

# Initialize database
sudo -u combadge python -m combadge.db.init
```

## Initial Configuration

### Environment Variables

**Production .env file:**
```bash
# Environment
COMBADGE_ENV=production
COMBADGE_DEBUG_MODE=false

# Database
COMBADGE_DATABASE_URL=postgresql://combadge_user:password@localhost:5432/combadge_db

# API Configuration
COMBADGE_API_BASE_URL=https://fleet-api.company.com
COMBADGE_API_AUTHENTICATION_METHOD=oauth2
COMBADGE_API_AUTHENTICATION_CLIENT_ID=your_client_id
COMBADGE_API_AUTHENTICATION_CLIENT_SECRET=your_client_secret

# LLM Configuration
COMBADGE_LLM_BASE_URL=http://localhost:11434
COMBADGE_LLM_MODEL=qwen2.5:14b
COMBADGE_LLM_TEMPERATURE=0.1

# Security
COMBADGE_SECRET_KEY=your-256-bit-secret-key-here
COMBADGE_ENCRYPTION_KEY=your-encryption-key-here

# Logging
COMBADGE_LOGGING_LEVEL=INFO
COMBADGE_LOGGING_FILE_PATH=/var/log/combadge/app.log
COMBADGE_LOGGING_AUDIT_ENABLED=true

# Features
COMBADGE_ENABLE_AUTO_BACKUP=true
COMBADGE_ENABLE_TELEMETRY=false
```

### SSL Certificate Setup

**Using Let's Encrypt (Automatic):**
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d combadge.company.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

**Using Custom Certificate:**
```bash
# Copy certificates
sudo mkdir -p /etc/ssl/combadge
sudo cp your-cert.pem /etc/ssl/combadge/cert.pem
sudo cp your-private-key.pem /etc/ssl/combadge/private.pem
sudo chown root:root /etc/ssl/combadge/*
sudo chmod 600 /etc/ssl/combadge/private.pem
sudo chmod 644 /etc/ssl/combadge/cert.pem
```

### Reverse Proxy Configuration

**nginx Configuration:**
```nginx
# /etc/nginx/sites-available/combadge
server {
    listen 80;
    server_name combadge.company.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name combadge.company.com;

    ssl_certificate /etc/ssl/combadge/cert.pem;
    ssl_certificate_key /etc/ssl/combadge/private.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;

    client_max_body_size 10M;
    proxy_read_timeout 300;
    proxy_connect_timeout 300;
    proxy_send_timeout 300;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

**Enable Site:**
```bash
sudo ln -s /etc/nginx/sites-available/combadge /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Post-Installation Verification

### Health Checks

**Service Status:**
```bash
# Check service status
sudo systemctl status combadge
sudo systemctl status nginx
sudo systemctl status postgresql

# Check ports
sudo netstat -tlnp | grep -E ':(8000|443|5432)'
```

**Application Health:**
```bash
# Health endpoint
curl -k https://combadge.company.com/health

# Expected response:
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": "connected",
    "llm": "available",
    "api": "connected"
  },
  "timestamp": "2024-03-15T10:00:00Z"
}
```

**Database Connection:**
```bash
# Test database connection
sudo -u combadge python -c "
from combadge.core.database import Database
db = Database()
print('Database connection:', db.test_connection())
"
```

### Initial Admin Setup

**Create Administrator Account:**
```bash
# Create admin user
sudo -u combadge python -m combadge.admin create-user \
  --username admin \
  --email admin@company.com \
  --role administrator \
  --password-prompt

# Set permissions
sudo -u combadge python -m combadge.admin set-permissions \
  --user admin \
  --permissions all
```

**Web Interface Test:**
1. Open browser to https://combadge.company.com
2. Login with admin credentials
3. Verify all UI components load
4. Test a simple request: "What vehicles are available?"

### Security Validation

**SSL Certificate:**
```bash
# Check SSL certificate
openssl s_client -connect combadge.company.com:443 -servername combadge.company.com

# Verify certificate chain
curl -vI https://combadge.company.com
```

**Security Headers:**
```bash
# Check security headers
curl -I https://combadge.company.com

# Expected headers:
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
# Strict-Transport-Security: max-age=31536000
```

## Troubleshooting Installation Issues

### Common Problems

**Service Won't Start:**
```bash
# Check logs
sudo journalctl -u combadge -f

# Check configuration
sudo -u combadge python -m combadge.config validate

# Check permissions
ls -la /opt/combadge/
sudo -u combadge test -w /opt/combadge/logs/
```

**Database Connection Failed:**
```bash
# Test PostgreSQL connection
sudo -u postgres psql -d combadge_db -c "SELECT 1;"

# Check pg_hba.conf
sudo nano /etc/postgresql/15/main/pg_hba.conf
# Ensure: local combadge_db combadge_user md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

**SSL Certificate Issues:**
```bash
# Check certificate validity
openssl x509 -in /etc/ssl/combadge/cert.pem -text -noout

# Verify nginx configuration
sudo nginx -t

# Check file permissions
ls -la /etc/ssl/combadge/
```

**Port Conflicts:**
```bash
# Check what's using port 8000
sudo lsof -i :8000

# If port in use, change in config:
nano config/production.yaml
# server:
#   port: 8001
```

### Log Analysis

**Application Logs:**
```bash
# Real-time monitoring
sudo tail -f /var/log/combadge/app.log

# Error filtering
sudo grep -i error /var/log/combadge/app.log | tail -20

# Performance issues
sudo grep -i "slow\|timeout\|performance" /var/log/combadge/app.log
```

**System Logs:**
```bash
# Service issues
sudo journalctl -u combadge --since "1 hour ago"

# Database issues
sudo journalctl -u postgresql --since "1 hour ago"

# Web server issues
sudo journalctl -u nginx --since "1 hour ago"
```

## Next Steps

After successful installation:

1. **📋 [Configuration Guide](configuration.md)** - Detailed configuration options
2. **🔒 [Security Setup](security_setup.md)** - Harden your installation
3. **🔧 [Maintenance Guide](maintenance.md)** - Ongoing maintenance procedures
4. **📊 [Monitoring Guide](monitoring.md)** - Set up monitoring and alerting

**Support Resources:**
- Installation Support: install-support@company.com
- Documentation: https://docs.company.com/combadge
- Community Forum: https://community.company.com/combadge

---

*For enterprise installation support and professional services, contact your ComBadge representative.*