# ComBadge Deployment Guide

This guide covers enterprise deployment strategies, installation methods, and maintenance procedures for ComBadge in production environments.

## Deployment Overview

ComBadge supports multiple deployment strategies:

- **Standard Installation**: GUI installer with user interaction
- **Silent Installation**: Automated deployment for IT departments  
- **Portable Deployment**: Self-contained package for restricted environments
- **Enterprise Distribution**: Group Policy and SCCM integration

## Pre-Deployment Planning

### System Requirements Assessment

Before deployment, assess target environment:

```bash
# Run on representative systems
python scripts/deployment/system_requirements.py --output requirements-report.json

# Analyze results across environment
python scripts/deployment/analyze_requirements.py requirements-report.json
```

### Network Requirements

- **Internet access** for initial Ollama model download (qwen2.5:14b ~8GB)
- **Firewall exceptions** for Ollama server (localhost:11434)
- **Proxy configuration** if required for model downloads

### Storage Planning

| Component | Disk Space | Purpose |
|-----------|------------|---------|
| Application | ~200MB | Core executable and files |
| AI Model | ~8GB | Qwen2.5-14B model |
| User Data | ~100MB | Configurations, logs, cache |
| **Total** | **~8.3GB** | **Minimum recommended** |

## Deployment Methods

### 1. Standard GUI Installation

For individual workstations and small deployments.

#### Download and Install

```bash
# Download latest installer
curl -L -o ComBadge_Setup.exe https://github.com/mklemmingen/Combadge/releases/latest/download/ComBadge_X.X.X_Setup.exe

# Verify checksum
Get-FileHash -Path ComBadge_Setup.exe -Algorithm SHA256

# Run installer
.\ComBadge_Setup.exe
```

#### Installation Options

The installer provides:

- **Installation Path**: Default `C:\Program Files\ComBadge`
- **Components**: Core app, desktop shortcuts, Start Menu entries
- **File Associations**: `.combadge` configuration files
- **System Integration**: Windows registry, uninstaller

### 2. Silent Installation

For automated enterprise deployment.

#### Command Line Options

```bash
# Silent installation with default options
ComBadge_Setup.exe /S

# Silent installation with custom path
ComBadge_Setup.exe /S /D=C:\Applications\ComBadge

# Silent installation with component selection
ComBadge_Setup.exe /S /COMPONENTS="core,shortcuts"
```

#### Group Policy Deployment

1. **Copy installer to network share**:
   ```
   \\domain\software\ComBadge\ComBadge_X.X.X_Setup.exe
   ```

2. **Create Group Policy Object**:
   - Computer Configuration → Policies → Software Settings
   - Software Installation → New Package
   - Select ComBadge installer

3. **Configure installation options**:
   - Deployment Type: Assigned
   - Installation UI Options: Silent

### 3. SCCM Deployment

For large enterprise environments using System Center Configuration Manager.

#### Create Application

1. **Application Properties**:
   - Name: ComBadge Natural Language Processor
   - Version: X.X.X
   - Publisher: ComBadge Development Team

2. **Detection Method**:
   ```powershell
   # PowerShell detection script
   $InstallPath = "${env:ProgramFiles}\ComBadge\ComBadge.exe"
   if (Test-Path $InstallPath) {
       # Get version from executable
       $Version = (Get-ItemProperty $InstallPath).VersionInfo.FileVersion
       Write-Host "ComBadge version $Version detected"
   }
   ```

3. **Installation Program**:
   ```bash
   ComBadge_X.X.X_Setup.exe /S
   ```

4. **Uninstall Program**:
   ```bash
   "${env:ProgramFiles}\ComBadge\uninstall.exe" /S
   ```

#### Deployment Configuration

- **Purpose**: Required (for mandatory deployment)
- **Schedule**: Define maintenance window
- **User Experience**: Hide notifications during business hours
- **Prerequisites**: Check system requirements

### 4. Portable Deployment

For environments with installation restrictions.

#### Setup

```bash
# Download portable package
curl -L -o ComBadge_Portable.zip https://github.com/mklemmingen/Combadge/releases/latest/download/ComBadge_X.X.X_Portable.zip

# Extract to desired location
Expand-Archive -Path ComBadge_Portable.zip -DestinationPath C:\Tools\ComBadge

# Run application
C:\Tools\ComBadge\ComBadge.exe
```

#### Network Deployment

For shared network installations:

```bash
# Extract to network share
\\fileserver\applications\ComBadge\

# Create shortcuts pointing to network location
Target: \\fileserver\applications\ComBadge\ComBadge.exe
Start In: %USERPROFILE%\AppData\Local\ComBadge
```

## Post-Deployment Validation

### Installation Verification

Run validation on deployed systems:

```bash
# Basic validation
python scripts/deployment/validate_installation.py --critical-only

# Full validation with report
python scripts/deployment/validate_installation.py --output validation-report.json

# Batch validation across multiple systems
psexec \\* -c python scripts/deployment/validate_installation.py
```

### Functional Testing

#### Test Checklist

- [ ] Application launches successfully
- [ ] Ollama server starts automatically
- [ ] AI model downloads and loads
- [ ] Configuration files are accessible
- [ ] Documentation is available
- [ ] Uninstaller functions correctly

#### Automated Testing Script

```powershell
# deployment-test.ps1
$TestResults = @()

# Test 1: Application Launch
try {
    $Process = Start-Process -FilePath "C:\Program Files\ComBadge\ComBadge.exe" -ArgumentList "--version" -Wait -PassThru
    $TestResults += @{Test="Launch"; Result=($Process.ExitCode -eq 0)}
}
catch {
    $TestResults += @{Test="Launch"; Result=$false}
}

# Test 2: Configuration Access
$ConfigExists = Test-Path "C:\Program Files\ComBadge\config\default_config.yaml"
$TestResults += @{Test="Config"; Result=$ConfigExists}

# Test 3: Ollama Integration
try {
    $Response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 30
    $TestResults += @{Test="Ollama"; Result=($Response.StatusCode -eq 200)}
}
catch {
    $TestResults += @{Test="Ollama"; Result=$false}
}

# Report Results
$TestResults | Format-Table
```

## Configuration Management

### Default Configuration

ComBadge ships with sensible defaults but may require customization:

```yaml
# config/production.yaml
llm:
  model: "qwen2.5:14b"
  temperature: 0.1
  timeout: 60

ui:
  theme: "corporate"
  auto_save: true

fleet:
  api_base_url: "https://fleet.company.com/api/v1"
  timeout: 30
  retry_attempts: 3

logging:
  level: "INFO"
  max_size_mb: 10
  backup_count: 5
```

### Enterprise Configuration Deployment

#### Method 1: Pre-configured Installation

1. **Customize configuration files** in build process
2. **Rebuild installer** with enterprise settings
3. **Deploy customized installer**

#### Method 2: Post-Installation Configuration

```powershell
# enterprise-config.ps1
$ConfigPath = "${env:ProgramFiles}\ComBadge\config\production.yaml"
$EnterpriseConfig = @"
llm:
  model: "qwen2.5:14b"
fleet:
  api_base_url: "https://fleet.company.com/api/v1"
  auth_token: "$($env:FLEET_API_TOKEN)"
"@

Set-Content -Path $ConfigPath -Value $EnterpriseConfig
```

#### Method 3: Group Policy Preferences

1. **Create GPO for file deployment**
2. **Target configuration files**:
   - `config/production.yaml`
   - `config/user_preferences.yaml`
3. **Set appropriate permissions**

## Update Management

### Automatic Updates

Configure update behavior enterprise-wide:

```json
{
  "auto_check_enabled": true,
  "auto_download_enabled": true,
  "auto_install_enabled": false,
  "check_interval_hours": 24,
  "update_server": "https://company-updates.com/combadge",
  "require_approval": true
}
```

### Centralized Update Server

For air-gapped or controlled environments:

1. **Set up internal update server**
2. **Mirror GitHub releases**
3. **Configure clients to use internal server**
4. **Control update rollout schedule**

#### Update Server Setup

```python
# internal-update-server.py
from flask import Flask, jsonify
import json

app = Flask(__name__)

@app.route('/api/latest')
def latest_version():
    return jsonify({
        "version": "1.2.3",
        "download_url": "https://updates.company.com/ComBadge_1.2.3_Setup.exe",
        "checksum": "sha256:...",
        "size_bytes": 52428800,
        "release_notes": "Security updates and performance improvements",
        "critical": False
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

### Manual Update Process

For controlled environments requiring approval:

```bash
# 1. Check for updates
python scripts/maintenance/update_manager.py --check

# 2. Download update (if available)  
python scripts/maintenance/update_manager.py --download

# 3. Create backup before update
python scripts/maintenance/backup_manager.py create --type full

# 4. Install update
python scripts/maintenance/update_manager.py --install ComBadge_X.X.X_Setup.exe

# 5. Validate installation
python scripts/deployment/validate_installation.py
```

## Monitoring and Maintenance

### System Monitoring

#### Performance Metrics

Monitor key performance indicators:

- **Memory Usage**: Typical 200-500MB during operation
- **CPU Usage**: Spikes during AI processing, idle otherwise  
- **Disk I/O**: Model loading and database operations
- **Network**: Ollama API calls and update checks

#### Health Check Script

```powershell
# health-check.ps1
$HealthStatus = @{}

# Process Check
$Process = Get-Process -Name "ComBadge" -ErrorAction SilentlyContinue
$HealthStatus.ProcessRunning = $Process -ne $null

# Memory Usage
if ($Process) {
    $HealthStatus.MemoryMB = [Math]::Round($Process.WorkingSet64 / 1MB, 2)
}

# Ollama Service
try {
    $Response = Invoke-RestMethod -Uri "http://localhost:11434/api/version" -TimeoutSec 10
    $HealthStatus.OllamaStatus = "Running"
    $HealthStatus.OllamaVersion = $Response.version
}
catch {
    $HealthStatus.OllamaStatus = "Not responding"
}

# Configuration Files
$ConfigPath = "${env:ProgramFiles}\ComBadge\config\default_config.yaml"
$HealthStatus.ConfigAccessible = Test-Path $ConfigPath

# Log Recent Errors
$LogPath = "${env:ProgramFiles}\ComBadge\logs\combadge.log"
if (Test-Path $LogPath) {
    $RecentErrors = Get-Content $LogPath | Select-String "ERROR" | Select-Object -Last 5
    $HealthStatus.RecentErrors = $RecentErrors.Count
}

# Output Status
$HealthStatus | ConvertTo-Json -Depth 2
```

### Log Management

#### Log Locations

- **Application Logs**: `logs/combadge.log`
- **Error Logs**: `logs/errors.log`
- **Audit Logs**: `logs/audit.log`
- **Update Logs**: `logs/updates.log`

#### Log Rotation Configuration

```yaml
# config/logging.yaml
version: 1
formatters:
  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

handlers:
  file:
    class: logging.handlers.RotatingFileHandler
    filename: logs/combadge.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
    formatter: detailed

loggers:
  combadge:
    level: INFO
    handlers: [file]
    propagate: false
```

### Backup and Recovery

#### Automated Backups

```bash
# Schedule daily configuration backups
python scripts/maintenance/backup_manager.py create --type incremental

# Weekly full backups
python scripts/maintenance/backup_manager.py create --type full

# Cleanup old backups (30-day retention)
python scripts/maintenance/backup_manager.py cleanup --days 30
```

#### Disaster Recovery

1. **Backup Locations**:
   - Local: `backups/`
   - Network: `\\backup-server\combadge\`
   - Cloud: Azure/AWS storage (if configured)

2. **Recovery Process**:
   ```bash
   # Restore from backup
   python scripts/maintenance/backup_manager.py restore backup_id_12345

   # Validate restored installation
   python scripts/deployment/validate_installation.py
   
   # Restart services if needed
   net stop ComBadgeService
   net start ComBadgeService
   ```

## Troubleshooting

### Common Issues

#### Installation Failures

**Insufficient Permissions**:
```bash
# Run installer as administrator
runas /user:Administrator ComBadge_Setup.exe
```

**System Requirements Not Met**:
```bash
# Check detailed requirements
python scripts/deployment/system_requirements.py --verbose
```

#### Runtime Issues

**Ollama Not Starting**:
```powershell
# Check Ollama installation
ollama --version

# Reinstall if needed
winget install ollama

# Check port availability
netstat -an | findstr :11434
```

**Model Download Failures**:
```bash
# Manual model download
ollama pull qwen2.5:14b

# Check available space
df -h

# Check internet connectivity
curl -I https://ollama.ai
```

#### Performance Issues

**High Memory Usage**:
```powershell
# Check memory consumption
Get-Process ComBadge | Select-Object ProcessName, WorkingSet64, PagedMemorySize64

# Restart application
taskkill /f /im ComBadge.exe
Start-Process "${env:ProgramFiles}\ComBadge\ComBadge.exe"
```

**Slow Response Times**:
```bash
# Check model loading status
curl http://localhost:11434/api/tags

# Monitor GPU usage (if available)
nvidia-smi

# Review configuration
cat config/production.yaml
```

### Support Tools

#### Diagnostic Collection

```powershell
# collect-diagnostics.ps1
$DiagPath = "C:\Temp\ComBadge-Diagnostics-$(Get-Date -Format 'yyyyMMdd-HHmm')"
New-Item -Path $DiagPath -ItemType Directory -Force

# System Information
Get-ComputerInfo > "$DiagPath\system-info.txt"
Get-Process ComBadge > "$DiagPath\process-info.txt"

# Application Logs
Copy-Item "${env:ProgramFiles}\ComBadge\logs\*" "$DiagPath\logs\" -Recurse -ErrorAction SilentlyContinue

# Configuration Files
Copy-Item "${env:ProgramFiles}\ComBadge\config\*" "$DiagPath\config\" -Recurse -ErrorAction SilentlyContinue

# Network Connectivity
Test-NetConnection -ComputerName "localhost" -Port 11434 > "$DiagPath\network-test.txt"

# Create ZIP archive
Compress-Archive -Path "$DiagPath\*" -DestinationPath "$DiagPath.zip"
Write-Host "Diagnostics collected: $DiagPath.zip"
```

#### Remote Assistance

```bash
# Enable remote PowerShell if needed
Enable-PSRemoting -Force

# Remote diagnostic execution
Invoke-Command -ComputerName TARGET-PC -FilePath collect-diagnostics.ps1

# Remote installation validation
Invoke-Command -ComputerName TARGET-PC -ScriptBlock {
    python "${env:ProgramFiles}\ComBadge\scripts\deployment\validate_installation.py"
}
```

## Security Considerations

### Firewall Configuration

```powershell
# Allow Ollama local server
New-NetFirewallRule -DisplayName "Ollama Local Server" -Direction Inbound -Protocol TCP -LocalPort 11434 -Action Allow

# Block external access to Ollama
New-NetFirewallRule -DisplayName "Block Ollama External" -Direction Inbound -Protocol TCP -LocalPort 11434 -RemoteAddress Any -Action Block
```

### User Permissions

Recommended permissions for ComBadge users:

- **Read/Write**: Application data directory
- **Read**: Configuration files
- **Execute**: Application executable
- **Network**: Localhost connections only

### Data Protection

- **Configuration encryption**: Sensitive API keys and tokens
- **Audit logging**: All user actions and API calls
- **Data retention**: Configurable log and data retention policies

## Best Practices

### Deployment Planning

1. **Pilot deployment**: Test with small user group first
2. **Phased rollout**: Deploy to departments gradually
3. **Rollback plan**: Maintain ability to revert quickly
4. **Communication**: Inform users of deployment schedule

### Configuration Management

1. **Standardized configs**: Use consistent settings across environment
2. **Version control**: Track configuration changes
3. **Testing**: Validate configurations before deployment
4. **Documentation**: Maintain configuration documentation

### Monitoring and Maintenance

1. **Regular health checks**: Automated monitoring of key metrics
2. **Proactive updates**: Stay current with security patches
3. **User feedback**: Monitor and address user issues promptly
4. **Performance optimization**: Regular performance reviews

## References

- [Windows Installer Best Practices](https://docs.microsoft.com/en-us/windows/win32/msi/)
- [Group Policy Management](https://docs.microsoft.com/en-us/windows-server/identity/ad-ds/)
- [SCCM Application Management](https://docs.microsoft.com/en-us/mem/configmgr/)
- [PowerShell Deployment Scripts](https://docs.microsoft.com/en-us/powershell/)