# ComBadge Build Scripts

Quick reference for building and deploying ComBadge.

## Quick Build Commands

```bash
# Build executable
python scripts/build/build_executable.py --clean

# Create Windows installer  
python scripts/build/package_installer.py --type installer

# Create portable package
python scripts/build/package_installer.py --type portable

# Validate installation
python scripts/deployment/validate_installation.py --path dist

# Check system requirements
python scripts/deployment/system_requirements.py
```

## Scripts Overview

### Build Scripts (`scripts/build/`)

- **`build_executable.py`** - PyInstaller automation for creating Windows executable
- **`package_installer.py`** - NSIS installer and portable package creation

### Deployment Scripts (`scripts/deployment/`)

- **`system_requirements.py`** - System compatibility validation
- **`validate_installation.py`** - Post-installation testing

### Maintenance Scripts (`scripts/maintenance/`)

- **`update_manager.py`** - Automatic update system
- **`backup_manager.py`** - Configuration backup/restore
- **`cleanup_utility.py`** - Uninstallation and cleanup

## Prerequisites

- Python 3.11+
- [NSIS](https://nsis.sourceforge.io/) (for Windows installer)
- PyInstaller (`pip install pyinstaller`)

## Complete Build Process

```bash
# 1. Environment validation
python scripts/build/build_executable.py --validate-only

# 2. Clean build
python scripts/build/build_executable.py --clean

# 3. Create installer and portable package
python scripts/build/package_installer.py --type both

# 4. Validate results
python scripts/deployment/validate_installation.py --path dist --output validation-report.json

# 5. Check final packages
ls -la dist/
```

## CI/CD Integration

Builds are automated via GitHub Actions:

- **`.github/workflows/build.yml`** - Continuous integration
- **`.github/workflows/release.yml`** - Release automation

## Documentation

For detailed information, see:

- [Build System Documentation](../docs/developer_guide/build_system.md)
- [Deployment Guide](../docs/developer_guide/deployment_guide.md)