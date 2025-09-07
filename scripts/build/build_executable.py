#!/usr/bin/env python3
"""
ComBadge Executable Builder

Professional PyInstaller automation for creating enterprise-ready executables
with comprehensive dependency management and optimization.
"""

import os
import sys
import shutil
import logging
import platform
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import json


class ComBadgeBuilder:
    """Professional executable builder for ComBadge."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize builder with project paths and configuration."""
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist" 
        self.assets_dir = self.project_root / "assets"
        self.spec_file = self.project_root / "combadge.spec"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def validate_environment(self) -> bool:
        """Validate build environment and dependencies."""
        self.logger.info("Validating build environment...")
        
        # Check Python version
        if sys.version_info < (3, 9):
            self.logger.error("Python 3.9+ required for building")
            return False
            
        # Check required files
        required_files = [
            self.project_root / "main.py",
            self.project_root / "src" / "combadge",
            self.project_root / "config",
            self.project_root / "knowledge"
        ]
        
        for file_path in required_files:
            if not file_path.exists():
                self.logger.error(f"Required file/directory missing: {file_path}")
                return False
                
        # Check PyInstaller installation
        try:
            import PyInstaller
            self.logger.info(f"PyInstaller version: {PyInstaller.__version__}")
        except ImportError:
            self.logger.error("PyInstaller not installed. Run: pip install pyinstaller")
            return False
            
        # Check disk space (minimum 2GB)
        if shutil.disk_usage(self.project_root)[2] < 2 * 1024**3:
            self.logger.warning("Low disk space detected. Build may fail.")
            
        self.logger.info("Environment validation completed successfully")
        return True
    
    def clean_build_artifacts(self):
        """Clean previous build artifacts."""
        self.logger.info("Cleaning previous build artifacts...")
        
        cleanup_dirs = [self.build_dir, self.dist_dir]
        for dir_path in cleanup_dirs:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                self.logger.info(f"Cleaned: {dir_path}")
                
        if self.spec_file.exists():
            os.remove(self.spec_file)
            self.logger.info(f"Removed spec file: {self.spec_file}")
    
    def get_hidden_imports(self) -> List[str]:
        """Get list of hidden imports for PyInstaller."""
        return [
            'ollama',
            'customtkinter',
            'tkinter',
            'PIL',
            'PIL._tkinter_finder',
            'requests',
            'yaml',
            'sqlite3',
            'json',
            'asyncio',
            'threading',
            'queue',
            'logging.handlers',
            'platform',
            'subprocess',
            'psutil',
            'cryptography',
            'urllib3',
            'certifi',
            'urllib.request',
            'urllib.error',
            'tempfile',
            'hashlib',
            'ctypes'
        ]
    
    def get_data_files(self) -> List[tuple]:
        """Get data files and directories to include."""
        data_files = []
        
        # Core data directories
        data_dirs = [
            ('knowledge', 'knowledge'),
            ('config', 'config'), 
            ('data', 'data'),
            ('docs/user_guide', 'docs/user_guide'),
            ('docs/admin_guide', 'docs/admin_guide')
        ]
        
        for src, dst in data_dirs:
            src_path = self.project_root / src
            if src_path.exists():
                data_files.append((str(src_path), dst))
                
        # Assets (if they exist)
        if self.assets_dir.exists():
            data_files.append((str(self.assets_dir), 'assets'))
            
        return data_files
    
    def create_icon_file(self) -> Optional[str]:
        """Create or locate application icon."""
        # Check for existing icons
        icon_paths = [
            self.assets_dir / "icons" / "combadge.ico",
            self.assets_dir / "combadge.ico", 
            self.project_root / "combadge.ico"
        ]
        
        for icon_path in icon_paths:
            if icon_path.exists():
                self.logger.info(f"Using icon: {icon_path}")
                return str(icon_path)
                
        self.logger.warning("No application icon found")
        return None
    
    def get_exclude_modules(self) -> List[str]:
        """Get modules to exclude from build."""
        return [
            'pytest',
            'pytest_cov',
            'jupyter',
            'notebook',
            'matplotlib',
            'pandas',
            'numpy',  # Only if not actually used
            'scipy',
            'sklearn',
            'tensorflow',
            'torch',
            'IPython'
        ]
    
    def build_pyinstaller_spec(self) -> str:
        """Generate PyInstaller spec file for advanced customization."""
        icon_file = self.create_icon_file()
        hidden_imports = self.get_hidden_imports()
        data_files = self.get_data_files()
        exclude_modules = self.get_exclude_modules()
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# Build configuration
block_cipher = None
project_root = Path(r"{self.project_root}")

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root), str(project_root / "src")],
    binaries=[],
    datas={data_files!r},
    hiddenimports={hidden_imports!r},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={exclude_modules!r},
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out unwanted modules
a.binaries = TOC([x for x in a.binaries if not any(
    excluded in x[0].lower() for excluded in {exclude_modules!r}
)])

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ComBadge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={repr(icon_file) if icon_file else None},
    version_file=None,  # Add version info if available
    uac_admin=False,
    uac_uiaccess=False,
)

# Create distribution directory structure
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles, 
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ComBadge'
)
'''
        
        with open(self.spec_file, 'w') as f:
            f.write(spec_content)
            
        self.logger.info(f"Generated spec file: {self.spec_file}")
        return str(self.spec_file)
    
    def optimize_executable(self):
        """Post-build optimization of executable."""
        exe_path = self.dist_dir / "ComBadge.exe"
        if not exe_path.exists():
            exe_path = self.dist_dir / "ComBadge" / "ComBadge.exe"
            
        if exe_path.exists():
            original_size = exe_path.stat().st_size
            self.logger.info(f"Original executable size: {original_size / 1024**2:.1f} MB")
            
            # UPX compression (if available)
            try:
                result = subprocess.run(['upx', '--best', str(exe_path)], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    compressed_size = exe_path.stat().st_size
                    compression_ratio = (1 - compressed_size/original_size) * 100
                    self.logger.info(f"UPX compression: {compression_ratio:.1f}% reduction")
                else:
                    self.logger.warning("UPX compression failed")
            except FileNotFoundError:
                self.logger.info("UPX not available, skipping compression")
    
    def create_version_info(self) -> Optional[str]:
        """Create Windows version info file."""
        try:
            # Try to get version from pyproject.toml or __init__.py
            version = "1.0.0"  # Default version
            
            # Check pyproject.toml
            pyproject_file = self.project_root / "pyproject.toml"
            if pyproject_file.exists():
                with open(pyproject_file, 'r') as f:
                    content = f.read()
                    for line in content.split('\n'):
                        if line.strip().startswith('version'):
                            version = line.split('=')[1].strip().strip('"\'')
                            break
            
            version_info_content = f'''VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version.replace('.', ', ')}, 0),
    prodvers=({version.replace('.', ', ')}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'ComBadge Development Team'),
        StringStruct(u'FileDescription', u'ComBadge - Natural Language to API Converter'),
        StringStruct(u'FileVersion', u'{version}'),
        StringStruct(u'InternalName', u'ComBadge'),
        StringStruct(u'LegalCopyright', u'Copyright (C) 2024 ComBadge'),
        StringStruct(u'OriginalFilename', u'ComBadge.exe'),
        StringStruct(u'ProductName', u'ComBadge'),
        StringStruct(u'ProductVersion', u'{version}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)'''
            
            version_file = self.project_root / "version_info.py"
            with open(version_file, 'w') as f:
                f.write(version_info_content)
                
            return str(version_file)
            
        except Exception as e:
            self.logger.warning(f"Could not create version info: {e}")
            return None
    
    def build_executable(self, mode: str = "onefile") -> bool:
        """Build the ComBadge executable."""
        self.logger.info(f"Starting ComBadge build process (mode: {mode})...")
        
        try:
            # Create spec file for advanced configuration
            spec_file = self.build_pyinstaller_spec()
            
            # Build using spec file
            cmd = [
                sys.executable, "-m", "PyInstaller",
                spec_file,
                "--clean",
                "--noconfirm",
                "--log-level=INFO"
            ]
            
            self.logger.info(f"Running PyInstaller: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.error(f"PyInstaller failed: {result.stderr}")
                return False
                
            self.logger.info("PyInstaller build completed successfully")
            
            # Post-build optimization
            self.optimize_executable()
            
            # Validate build
            if self.validate_build():
                self.logger.info("Build validation successful")
                return True
            else:
                self.logger.error("Build validation failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Build failed with exception: {e}")
            return False
    
    def validate_build(self) -> bool:
        """Validate the built executable."""
        # Check if executable exists
        exe_paths = [
            self.dist_dir / "ComBadge.exe",
            self.dist_dir / "ComBadge" / "ComBadge.exe"
        ]
        
        exe_path = None
        for path in exe_paths:
            if path.exists():
                exe_path = path
                break
                
        if not exe_path:
            self.logger.error("Executable not found after build")
            return False
            
        # Check executable size (should be reasonable)
        exe_size = exe_path.stat().st_size
        if exe_size < 10 * 1024**2:  # Less than 10MB seems too small
            self.logger.warning(f"Executable size seems small: {exe_size / 1024**2:.1f} MB")
        elif exe_size > 500 * 1024**2:  # More than 500MB seems too large  
            self.logger.warning(f"Executable size seems large: {exe_size / 1024**2:.1f} MB")
        else:
            self.logger.info(f"Executable size: {exe_size / 1024**2:.1f} MB")
            
        # Try to run executable with --help flag (quick validation)
        try:
            result = subprocess.run(
                [str(exe_path), "--help"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # If it runs without crashing, that's a good sign
            self.logger.info("Executable basic validation passed")
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.warning("Executable validation timeout (may still be valid)")
            return True
        except Exception as e:
            self.logger.error(f"Executable validation failed: {e}")
            return False
    
    def create_build_info(self):
        """Create build information file."""
        import datetime
        
        build_info = {
            "build_date": datetime.datetime.now().isoformat(),
            "build_platform": platform.platform(),
            "python_version": sys.version,
            "pyinstaller_version": None,
            "build_mode": "onefile"
        }
        
        try:
            import PyInstaller
            build_info["pyinstaller_version"] = PyInstaller.__version__
        except ImportError:
            pass
            
        build_info_file = self.dist_dir / "build_info.json"
        with open(build_info_file, 'w') as f:
            json.dump(build_info, f, indent=2)
            
        self.logger.info(f"Build info saved to: {build_info_file}")


def main():
    """Main build entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build ComBadge executable")
    parser.add_argument("--mode", choices=["onefile", "onedir"], 
                       default="onefile", help="Build mode")
    parser.add_argument("--clean", action="store_true", 
                       help="Clean build artifacts before building")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate environment, don't build")
    
    args = parser.parse_args()
    
    builder = ComBadgeBuilder()
    
    # Validate environment
    if not builder.validate_environment():
        sys.exit(1)
        
    if args.validate_only:
        print("Environment validation completed successfully")
        sys.exit(0)
    
    # Clean if requested
    if args.clean:
        builder.clean_build_artifacts()
    
    # Build executable
    success = builder.build_executable(mode=args.mode)
    
    if success:
        builder.create_build_info()
        print("Build completed successfully!")
        print(f"Executable location: {builder.dist_dir}")
    else:
        print("Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()