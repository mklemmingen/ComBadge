# ComBadge Build System Documentation

This document provides comprehensive information about building, packaging, and deploying ComBadge for enterprise distribution.

## Overview

ComBadge uses a professional build system designed for enterprise deployment with the following components:

- **PyInstaller executable generation** with optimization
- **NSIS Windows installer creation** with system validation
- **Automated CI/CD pipelines** with security scanning
- **Update management system** with rollback capabilities
- **Comprehensive testing and validation** tools

## Quick Start

### Prerequisites

- Python 3.11+
- Windows 10+ (for Windows builds)
- [NSIS](https://nsis.sourceforge.io/) installed (for installer creation)
- Git (for version information)

### Basic Build Process

```bash
# 1. Build executable
python scripts/build/build_executable.py --clean

# 2. Create installer
python scripts/build/package_installer.py --type installer

# 3. Create portable package
python scripts/build/package_installer.py --type portable

# 4. Validate installation
python scripts/deployment/validate_installation.py --path dist
```

## Build Scripts Reference

### 1. Executable Builder (`scripts/build/build_executable.py`)

Creates optimized Windows executables using PyInstaller.

#### Usage

```bash
python scripts/build/build_executable.py [options]

Options:
  --mode {onefile,onedir}   Build mode (default: onefile)
  --clean                   Clean build artifacts before building
  --validate-only          Only validate environment, don't build
```

#### Features

- **Environment validation**: Checks Python version, PyInstaller installation, disk space
- **Dependency management**: Automatically detects and includes hidden imports
- **Optimization**: UPX compression, size validation, unused module exclusion
- **Version integration**: Embeds version information from pyproject.toml
- **Build verification**: Tests executable launch and basic functionality

#### Configuration

The builder automatically configures:

- **Hidden imports**: `ollama`, `customtkinter`, `tkinter`, `PIL`, etc.
- **Data files**: `knowledge/`, `config/`, `data/`, `docs/`
- **Exclusions**: Test frameworks, development tools, unused libraries
- **Optimization**: UPX compression, module filtering, spec file generation

#### Output

- `dist/ComBadge.exe` - Main executable
- `build_info.json` - Build metadata
- `combadge.spec` - PyInstaller specification file

### 2. Installer Creator (`scripts/build/package_installer.py`)

Creates professional Windows installers using NSIS.

#### Usage

```bash
python scripts/build/package_installer.py [options]

Options:
  --type {installer,portable,both}  Package type (default: installer)
  --version VERSION                 Override version number
```

#### Installer Features

- **System requirements checking**: RAM, disk space, Windows version
- **Ollama integration**: Detection and installation guidance
- **Professional UI**: Modern installer interface with branding
- **Registry integration**: Proper Windows integration and uninstall support
- **Component selection**: Core app, desktop shortcuts, file associations

#### Generated Files

- `ComBadge_X.X.X_Setup.exe` - Windows installer
- `ComBadge_X.X.X_Portable.zip` - Portable package
- Installation validation and system integration

### 3. System Requirements Checker (`scripts/deployment/system_requirements.py`)

Validates system compatibility before installation.

#### Usage

```bash
python scripts/deployment/system_requirements.py [options]

Options:
  --output FILE    Save report to JSON file
  --verbose        Detailed output
  --silent         Only show errors
```

#### Validation Categories

- **Hardware**: RAM (8GB+), disk space (10GB+), CPU cores (4+)
- **Operating System**: Windows 10+, 64-bit architecture
- **Network**: Internet connectivity, DNS resolution
- **Security**: Windows Defender status, execution policies
- **Optional**: GPU memory, Python version

#### Exit Codes

- `0`: All critical requirements met
- `1`: Critical requirement failures detected

### 4. Installation Validator (`scripts/deployment/validate_installation.py`)

Comprehensive post-installation testing and validation.

#### Usage

```bash
python scripts/deployment/validate_installation.py [options]

Options:
  --path PATH           Installation path to validate
  --tests TEST1 TEST2   Specific tests to run
  --output FILE         Save validation report
  --critical-only       Run only critical tests
```

#### Test Categories

- **File System**: Executable existence, directory structure, permissions
- **Application**: Launch testing, version checking, configuration loading
- **Dependencies**: Ollama detection, model availability
- **Integration**: Database creation, NLP pipeline, template system
- **Performance**: Memory usage, startup time benchmarks

## Update System

### Update Manager (`scripts/maintenance/update_manager.py`)

Handles automatic updates with rollback capabilities.

#### Usage

```bash
python scripts/maintenance/update_manager.py [options]

Commands:
  --check              Check for available updates
  --download           Download latest update
  --install PATH       Install update from path
  --rollback PATH      Rollback to backup
  --history           Show update history
```

#### Configuration

Update behavior is controlled via `update_config.json`:

```json
{
  "auto_check_enabled": true,
  "auto_download_enabled": false,
  "auto_install_enabled": false,
  "check_interval_hours": 24,
  "backup_retention_days": 30,
  "critical_updates_auto": true
}
```

#### Features

- **GitHub releases integration**: Automatic version checking
- **Incremental updates**: Smart download and patching
- **Backup creation**: Automatic backup before updates
- **Rollback support**: Restore previous version if needed
- **Background processing**: Non-intrusive update checking

## CI/CD Pipeline

### GitHub Actions Workflows

#### Build Workflow (`.github/workflows/build.yml`)

Runs on every push and pull request:

1. **Quality Check**: Linting, type checking, unit tests
2. **Security Scan**: Safety, Bandit, Semgrep analysis
3. **Windows Build**: Executable creation and validation
4. **macOS Build**: Limited compatibility testing
5. **Performance Test**: Benchmarking and performance regression testing

#### Release Workflow (`.github/workflows/release.yml`)

Triggered by version tags:

1. **Release Creation**: Automated changelog generation
2. **Windows Build**: Professional installer and portable packages
3. **Security Scan**: Release asset validation
4. **Documentation Update**: Version-specific documentation updates
5. **Notification**: Release announcements and summaries

### Triggering Builds

#### Manual Release

```bash
# Create and push version tag
git tag v1.2.3
git push origin v1.2.3

# Or use GitHub Actions manual trigger
gh workflow run release.yml -f version=v1.2.3
```

#### Development Builds

```bash
# Push to main or develop branch
git push origin main

# Build artifacts available in Actions tab
```

## Build Environment Setup

### Local Development Build

1. **Clone repository**:
   ```bash
   git clone https://github.com/mklemmingen/Combadge.git
   cd combadge
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements/base.txt
   pip install pyinstaller nsis
   ```

3. **Install NSIS** (Windows):
   - Download from [NSIS website](https://nsis.sourceforge.io/)
   - Add to PATH: `C:\Program Files (x86)\NSIS`

4. **Build executable**:
   ```bash
   python scripts/build/build_executable.py --clean
   ```

### Production Build Environment

For reproducible production builds:

1. **Use Docker** (recommended):
   ```dockerfile
   FROM python:3.11-windowsservercore
   RUN pip install pyinstaller
   # Copy source and build
   ```

2. **GitHub Actions** (automated):
   - Builds run on `windows-latest`
   - Consistent environment and dependencies
   - Automated security scanning

## Troubleshooting

### Common Build Issues

#### PyInstaller Errors

**Import Errors**:
```python
# Add to hidden imports in build_executable.py
hidden_imports = [
    'your.missing.module',
    'another.module'
]
```

**Missing Data Files**:
```python
# Add to data files list
data_files = [
    ('source/path', 'dest/path'),
]
```

#### NSIS Installer Issues

**Path Problems**:
- Ensure NSIS is in PATH
- Use absolute paths in scripts
- Check file permissions

**System Requirements**:
```nsis
; Add custom requirement checks
Function CheckCustomRequirement
  ; Your validation logic
FunctionEnd
```

#### Validation Failures

**Check logs**:
```bash
python scripts/deployment/validate_installation.py --verbose
```

**Debug specific tests**:
```bash
python scripts/deployment/validate_installation.py --tests executable_exists config_directory
```

### Performance Optimization

#### Executable Size

- Review excluded modules in `build_executable.py`
- Use UPX compression (automatic)
- Remove unnecessary data files

#### Build Speed

- Use `--no-clean` for iterative builds
- Enable PyInstaller caching
- Parallel CI/CD jobs

## Security Considerations

### Code Signing

For production releases:

1. **Obtain code signing certificate**
2. **Configure signing in build script**:
   ```python
   # In package_installer.py
   def sign_executable(exe_path, cert_path):
       subprocess.run([
           'signtool', 'sign',
           '/f', cert_path,
           '/t', 'http://timestamp.digicert.com',
           str(exe_path)
       ])
   ```

### Security Scanning

The build pipeline includes:

- **Safety**: Dependency vulnerability scanning
- **Bandit**: Python security linting
- **Semgrep**: Static analysis security testing
- **VirusTotal**: Binary scanning (when configured)

### Supply Chain Security

- **Dependency pinning**: Exact versions in requirements.txt
- **Build reproducibility**: Consistent environments
- **Artifact signing**: Checksums and digital signatures
- **Audit trails**: Complete build logging

## Maintenance

### Regular Tasks

1. **Update dependencies**: Monthly security updates
2. **Refresh build environment**: Clean CI/CD caches
3. **Security scans**: Regular vulnerability assessments
4. **Documentation updates**: Keep build docs current

### Monitoring

- **Build success rates**: Track CI/CD pipeline health
- **Installation success**: Monitor validation metrics
- **Update adoption**: Track update installation rates
- **Performance regression**: Monitor build artifacts size and speed

## Advanced Topics

### Custom Build Configurations

Create environment-specific builds:

```python
# custom_build.py
from scripts.build.build_executable import ComBadgeBuilder

builder = ComBadgeBuilder()
builder.config = {
    'debug': True,
    'include_dev_tools': True,
    'custom_icon': 'assets/dev_icon.ico'
}
builder.build_executable()
```

### Integration with Package Managers

Future integrations:

- **Chocolatey**: Windows package manager
- **Scoop**: Command-line installer for Windows
- **WinGet**: Microsoft package manager
- **Enterprise deployment**: SCCM, Group Policy

### Cross-Platform Builds

While primarily Windows-focused, the build system can be extended:

```python
# In build_executable.py
def build_for_platform(platform):
    if platform == 'macos':
        # macOS-specific configuration
    elif platform == 'linux':
        # Linux-specific configuration
```

## References

- [PyInstaller Documentation](https://pyinstaller.readthedocs.io/)
- [NSIS Documentation](https://nsis.sourceforge.io/Docs/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Windows Installer Best Practices](https://docs.microsoft.com/en-us/windows/win32/msi/)