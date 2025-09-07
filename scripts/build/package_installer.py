#!/usr/bin/env python3
"""
ComBadge Professional Installer Creator

Creates enterprise-ready Windows installers using NSIS (Nullsoft Scriptable Install System)
with comprehensive installation options, system validation, and professional UI.
"""

import os
import sys
import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class InstallerConfig:
    """Configuration for installer creation."""
    app_name: str = "ComBadge"
    app_version: str = "1.0.0"
    company_name: str = "ComBadge Development Team"
    website: str = "https://github.com/mklemmingen/Combadge"
    executable_name: str = "ComBadge.exe"
    install_dir_name: str = "ComBadge"
    license_file: Optional[str] = None
    icon_file: Optional[str] = None
    banner_image: Optional[str] = None
    minimum_windows_version: str = "10.0"
    required_ram_gb: int = 8
    required_disk_gb: int = 10


class NSISInstallerBuilder:
    """Professional NSIS installer builder for ComBadge."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize installer builder."""
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.build_dir = self.project_root / "build" / "installer"
        self.dist_dir = self.project_root / "dist"
        self.nsis_dir = self.build_dir / "nsis"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.config = InstallerConfig()
        
    def setup_build_environment(self):
        """Setup build environment and directories."""
        self.logger.info("Setting up installer build environment...")
        
        # Create directories
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.nsis_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for installer components
        (self.nsis_dir / "includes").mkdir(exist_ok=True)
        (self.nsis_dir / "plugins").mkdir(exist_ok=True)
        (self.nsis_dir / "assets").mkdir(exist_ok=True)
        
    def validate_nsis_installation(self) -> bool:
        """Validate NSIS installation."""
        try:
            result = subprocess.run(['makensis', '/VERSION'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                self.logger.info(f"NSIS version: {version}")
                return True
            else:
                self.logger.error("NSIS not found or invalid")
                return False
        except FileNotFoundError:
            self.logger.error("NSIS (makensis) not found in PATH")
            self.logger.error("Download NSIS from: https://nsis.sourceforge.io/")
            return False
    
    def detect_executable_path(self) -> Optional[Path]:
        """Detect the built ComBadge executable."""
        possible_paths = [
            self.dist_dir / "ComBadge.exe",
            self.dist_dir / "ComBadge" / "ComBadge.exe"
        ]
        
        for path in possible_paths:
            if path.exists():
                self.logger.info(f"Found executable: {path}")
                return path
                
        self.logger.error("ComBadge executable not found. Build it first using build_executable.py")
        return None
    
    def load_version_info(self) -> str:
        """Load version information from project."""
        # Try multiple sources for version info
        version_sources = [
            self.project_root / "pyproject.toml",
            self.project_root / "src" / "combadge" / "__init__.py",
            self.dist_dir / "build_info.json"
        ]
        
        for source in version_sources:
            if source.exists():
                if source.name == "build_info.json":
                    try:
                        with open(source, 'r') as f:
                            build_info = json.load(f)
                            return build_info.get('version', '1.0.0')
                    except:
                        continue
                elif source.name == "pyproject.toml":
                    try:
                        with open(source, 'r') as f:
                            for line in f:
                                if line.strip().startswith('version'):
                                    return line.split('=')[1].strip().strip('"\\'')
                    except:
                        continue
                        
        return "1.0.0"  # Default version
    
    def create_system_requirements_check(self) -> str:
        """Create NSIS system requirements validation function."""
        return '''
; System Requirements Check Function
Function CheckSystemRequirements
  ${GetSize} "$EXEDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  
  ; Check Windows version
  ${If} ${AtMostWin2000}
    MessageBox MB_ICONSTOP "This application requires Windows 10 or later."
    Abort
  ${EndIf}
  
  ${If} ${AtMostWinXP}
    MessageBox MB_ICONSTOP "This application requires Windows 10 or later."
    Abort
  ${EndIf}
  
  ${If} ${AtMostWin2003}
    MessageBox MB_ICONSTOP "This application requires Windows 10 or later."
    Abort
  ${EndIf}
  
  ${If} ${AtMostWinVista}
    MessageBox MB_ICONSTOP "This application requires Windows 10 or later."
    Abort
  ${EndIf}
  
  ${If} ${AtMostWin7}
    MessageBox MB_ICONSTOP "This application requires Windows 10 or later."
    Abort
  ${EndIf}
  
  ${If} ${AtMostWin8}
    MessageBox MB_ICONSTOP "This application requires Windows 10 or later."
    Abort
  ${EndIf}
  
  ${If} ${AtMostWin8.1}
    MessageBox MB_ICONSTOP "This application requires Windows 10 or later."
    Abort
  ${EndIf}
  
  ; Check available RAM (8GB minimum)
  ${MemoryGetTotal} $0
  IntOp $0 $0 / 1024  ; Convert to MB
  IntOp $0 $0 / 1024  ; Convert to GB
  IntCmp $0 8 ram_ok ram_insufficient ram_ok
  
  ram_insufficient:
    MessageBox MB_ICONSTOP "This application requires at least 8GB of RAM. Available: $0 GB"
    Abort
    
  ram_ok:
  
  ; Check available disk space (10GB minimum)
  ${DriveSpace} "$PROGRAMFILES" "/S=M" $0
  IntCmp $0 10240 disk_ok disk_insufficient disk_ok  ; 10GB = 10240MB
  
  disk_insufficient:
    MessageBox MB_ICONSTOP "This application requires at least 10GB of free disk space."
    Abort
    
  disk_ok:
  
FunctionEnd
'''
    
    def create_ollama_detection(self) -> str:
        """Create NSIS Ollama detection and installation guidance."""
        return '''
; Ollama Detection Function
Function CheckOllamaInstallation
  ; Check if Ollama is installed
  ReadRegStr $0 HKLM "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Ollama" "DisplayName"
  StrCmp $0 "" check_user_registry check_complete
  
  check_user_registry:
    ReadRegStr $0 HKCU "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Ollama" "DisplayName"
    StrCmp $0 "" ollama_not_found check_complete
  
  check_complete:
    DetailPrint "Ollama installation detected: $0"
    Goto ollama_check_done
    
  ollama_not_found:
    MessageBox MB_YESNO "Ollama is required for ComBadge but was not detected.$\\n$\\nDo you want to download Ollama now?" IDYES download_ollama IDNO skip_ollama
    
  download_ollama:
    ExecShell "open" "https://ollama.ai/download"
    MessageBox MB_OK "Please install Ollama and then continue with ComBadge installation."
    Goto ollama_check_done
    
  skip_ollama:
    MessageBox MB_OK "ComBadge will automatically download and start Ollama when first run.$\\n$\\nEnsure you have internet connectivity for first use."
    
  ollama_check_done:
    
FunctionEnd
'''
    
    def create_main_nsis_script(self, exe_path: Path) -> str:
        """Create the main NSIS installer script."""
        version = self.load_version_info()
        self.config.app_version = version
        
        script_content = f'''
; ComBadge Professional Installer
; Generated by ComBadge Build System

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "WinVer.nsh"
!include "x64.nsh"
!include "LogicLib.nsh"

; Application Information
!define APP_NAME "{self.config.app_name}"
!define APP_VERSION "{self.config.app_version}"
!define COMPANY_NAME "{self.config.company_name}"
!define WEB_SITE "{self.config.website}"
!define MUI_PRODUCT "${{APP_NAME}} ${{APP_VERSION}}"
!define REG_ROOT "HKLM"
!define REG_APP_PATH "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\${{APP_NAME}}.exe"
!define UNINSTALL_PATH "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}"

; Output and Compression
OutFile "${{APP_NAME}}_${{APP_VERSION}}_Setup.exe"
InstallDir "$PROGRAMFILES\\{self.config.install_dir_name}"
InstallDirRegKey ${{REG_ROOT}} "${{REG_APP_PATH}}" ""
SetCompressor lzma
SetCompressorDictSize 64

; Request Administrator Privileges
RequestExecutionLevel admin

; Variables
Var StartMenuFolder

; Modern UI Configuration
!define MUI_ABORTWARNING
!define MUI_UNABORTWARNING

; Header Image (if available)
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_HEADERIMAGE_BITMAP "${{NSISDIR}}\\Contrib\\Graphics\\Header\\nsis3-metro.bmp"

; Welcome Page
!define MUI_WELCOMEPAGE_TITLE "Welcome to ${{APP_NAME}} Setup"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of ${{APP_NAME}}.$\\r$\\n$\\r$\\n${{APP_NAME}} transforms natural language requests into API calls with AI-powered processing.$\\r$\\n$\\r$\\nClick Next to continue."

; License Page (if license file exists)
!ifdef LICENSE_FILE
!insertmacro MUI_PAGE_LICENSE "${{LICENSE_FILE}}"
!endif

; Components Page
!insertmacro MUI_PAGE_COMPONENTS

; Directory Page
!insertmacro MUI_PAGE_DIRECTORY

; Start Menu Folder Page
!define MUI_STARTMENUPAGE_DEFAULTFOLDER "${{APP_NAME}}"
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "${{REG_ROOT}}"
!define MUI_STARTMENUPAGE_REGISTRY_KEY "${{UNINSTALL_PATH}}"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "StartMenu"
!insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder

; Installation Page
!insertmacro MUI_PAGE_INSTFILES

; Finish Page
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${{APP_NAME}}"
!define MUI_FINISHPAGE_RUN_FUNCTION "LaunchApplication"
!define MUI_FINISHPAGE_SHOWREADME ""
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
!define MUI_FINISHPAGE_SHOWREADME_TEXT "View Getting Started Guide"
!define MUI_FINISHPAGE_SHOWREADME_FUNCTION "ShowReadme"
!insertmacro MUI_PAGE_FINISH

; Uninstaller Pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"

; Custom Functions
{self.create_system_requirements_check()}

{self.create_ollama_detection()}

Function LaunchApplication
  Exec '"$INSTDIR\\{self.config.executable_name}"'
FunctionEnd

Function ShowReadme
  ExecShell "open" "$INSTDIR\\docs\\getting_started.html"
FunctionEnd

; Version Information
VIProductVersion "${{APP_VERSION}}.0"
VIAddVersionKey "ProductName" "${{APP_NAME}}"
VIAddVersionKey "CompanyName" "${{COMPANY_NAME}}"
VIAddVersionKey "LegalCopyright" "Copyright (C) 2024 ${{COMPANY_NAME}}"
VIAddVersionKey "FileDescription" "${{APP_NAME}} Installer"
VIAddVersionKey "FileVersion" "${{APP_VERSION}}.0"
VIAddVersionKey "ProductVersion" "${{APP_VERSION}}.0"

; Installation Types
InstType "Complete"
InstType "Minimal"
InstType /NOCUSTOM

; Sections
Section "Core Application" SecCore
  SectionIn 1 2 RO
  
  ; System requirements check
  Call CheckSystemRequirements
  
  ; Ollama check
  Call CheckOllamaInstallation
  
  SetOutPath "$INSTDIR"
  
  ; Main executable
  File "{str(exe_path)}"
  
  ; Configuration files
  SetOutPath "$INSTDIR\\config"
  File /r "{str(self.project_root / 'config')}\\*"
  
  ; Knowledge base
  SetOutPath "$INSTDIR\\knowledge"
  File /r "{str(self.project_root / 'knowledge')}\\*"
  
  ; Documentation
  SetOutPath "$INSTDIR\\docs"
  File /r "{str(self.project_root / 'docs' / 'user_guide')}\\*"
  File /r "{str(self.project_root / 'docs' / 'admin_guide')}\\*"
  
  ; Data files
  SetOutPath "$INSTDIR\\data"
  File /r "{str(self.project_root / 'data')}\\*"
  
  ; Registry entries
  WriteRegStr ${{REG_ROOT}} "${{REG_APP_PATH}}" "" "$INSTDIR\\{self.config.executable_name}"
  WriteRegStr ${{REG_ROOT}} "${{UNINSTALL_PATH}}" "DisplayName" "${{APP_NAME}}"
  WriteRegStr ${{REG_ROOT}} "${{UNINSTALL_PATH}}" "DisplayVersion" "${{APP_VERSION}}"
  WriteRegStr ${{REG_ROOT}} "${{UNINSTALL_PATH}}" "Publisher" "${{COMPANY_NAME}}"
  WriteRegStr ${{REG_ROOT}} "${{UNINSTALL_PATH}}" "UninstallString" "$INSTDIR\\uninstall.exe"
  WriteRegStr ${{REG_ROOT}} "${{UNINSTALL_PATH}}" "DisplayIcon" "$INSTDIR\\{self.config.executable_name}"
  WriteRegDWORD ${{REG_ROOT}} "${{UNINSTALL_PATH}}" "NoModify" 1
  WriteRegDWORD ${{REG_ROOT}} "${{UNINSTALL_PATH}}" "NoRepair" 1
  
  ; Calculate and write installation size
  ${{GetSize}} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD ${{REG_ROOT}} "${{UNINSTALL_PATH}}" "EstimatedSize" "$0"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\\uninstall.exe"
  
SectionEnd

Section "Desktop Shortcut" SecDesktop
  SectionIn 1
  CreateShortCut "$DESKTOP\\${{APP_NAME}}.lnk" "$INSTDIR\\{self.config.executable_name}" "" "$INSTDIR\\{self.config.executable_name}" 0
SectionEnd

Section "Start Menu Shortcuts" SecStartMenu
  SectionIn 1 2
  
  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
  
  CreateDirectory "$SMPROGRAMS\\$StartMenuFolder"
  CreateShortCut "$SMPROGRAMS\\$StartMenuFolder\\${{APP_NAME}}.lnk" "$INSTDIR\\{self.config.executable_name}" "" "$INSTDIR\\{self.config.executable_name}" 0
  CreateShortCut "$SMPROGRAMS\\$StartMenuFolder\\Uninstall.lnk" "$INSTDIR\\uninstall.exe"
  CreateShortCut "$SMPROGRAMS\\$StartMenuFolder\\Getting Started.lnk" "$INSTDIR\\docs\\getting_started.html"
  
  !insertmacro MUI_STARTMENU_WRITE_END
  
SectionEnd

Section "File Associations" SecFileAssoc
  SectionIn 1
  
  ; Associate .combadge files with the application
  WriteRegStr HKCR ".combadge" "" "ComBadge.Document"
  WriteRegStr HKCR "ComBadge.Document" "" "ComBadge Configuration File"
  WriteRegStr HKCR "ComBadge.Document\\shell\\open\\command" "" '"$INSTDIR\\{self.config.executable_name}" "%1"'
  WriteRegStr HKCR "ComBadge.Document\\DefaultIcon" "" "$INSTDIR\\{self.config.executable_name},0"
  
SectionEnd

Section "Developer Tools" SecDev
  SectionIn 1
  
  ; Additional development documentation
  SetOutPath "$INSTDIR\\docs\\developer"
  File /nonfatal /r "{str(self.project_root / 'docs' / 'developer_guide')}\\*"
  
  ; Template examples
  SetOutPath "$INSTDIR\\examples"
  File /nonfatal /r "{str(self.project_root / 'knowledge' / 'templates')}\\*"
  
SectionEnd

; Section Descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
!insertmacro MUI_DESCRIPTION_TEXT ${{SecCore}} "Core application files (required)"
!insertmacro MUI_DESCRIPTION_TEXT ${{SecDesktop}} "Create desktop shortcut"  
!insertmacro MUI_DESCRIPTION_TEXT ${{SecStartMenu}} "Create Start Menu shortcuts"
!insertmacro MUI_DESCRIPTION_TEXT ${{SecFileAssoc}} "Associate .combadge files with ComBadge"
!insertmacro MUI_DESCRIPTION_TEXT ${{SecDev}} "Developer documentation and examples"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; Uninstaller
Section "Uninstall"
  
  ; Remove registry keys
  DeleteRegKey ${{REG_ROOT}} "${{UNINSTALL_PATH}}"
  DeleteRegKey ${{REG_ROOT}} "${{REG_APP_PATH}}"
  
  ; Remove file associations
  DeleteRegKey HKCR ".combadge"
  DeleteRegKey HKCR "ComBadge.Document"
  
  ; Remove shortcuts
  Delete "$DESKTOP\\${{APP_NAME}}.lnk"
  
  !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
  Delete "$SMPROGRAMS\\$StartMenuFolder\\*.*"
  RMDir "$SMPROGRAMS\\$StartMenuFolder"
  
  ; Remove application files
  RMDir /r "$INSTDIR\\config"
  RMDir /r "$INSTDIR\\knowledge"
  RMDir /r "$INSTDIR\\docs"
  RMDir /r "$INSTDIR\\data"
  RMDir /r "$INSTDIR\\examples"
  Delete "$INSTDIR\\{self.config.executable_name}"
  Delete "$INSTDIR\\uninstall.exe"
  
  ; Remove installation directory if empty
  RMDir "$INSTDIR"
  
SectionEnd

; Functions
Function .onInit
  
  ; Check if already installed
  ReadRegStr $0 ${{REG_ROOT}} "${{UNINSTALL_PATH}}" "UninstallString"
  StrCmp $0 "" done
  
  MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \\
    "${{APP_NAME}} is already installed.$\\n$\\nClick OK to remove the previous version or Cancel to cancel this upgrade." \\
    IDOK uninst
  Abort
  
  uninst:
    ClearErrors
    ExecWait '$0 /S _?=$INSTDIR'
    
    IfErrors no_remove_uninstaller done
    no_remove_uninstaller:
    
  done:
  
FunctionEnd
'''
        
        return script_content
    
    def build_installer(self) -> bool:
        """Build the NSIS installer."""
        self.logger.info("Starting installer build process...")
        
        try:
            # Setup environment
            self.setup_build_environment()
            
            # Validate NSIS
            if not self.validate_nsis_installation():
                return False
            
            # Find executable
            exe_path = self.detect_executable_path()
            if not exe_path:
                return False
            
            # Create NSIS script
            nsis_script = self.create_main_nsis_script(exe_path)
            script_file = self.nsis_dir / "combadge_installer.nsi"
            
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(nsis_script)
            
            self.logger.info(f"Created NSIS script: {script_file}")
            
            # Build installer
            cmd = ['makensis', '/NOCD', str(script_file)]
            
            self.logger.info(f"Running NSIS: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=self.nsis_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.error(f"NSIS build failed: {result.stderr}")
                self.logger.error(f"NSIS stdout: {result.stdout}")
                return False
            
            # Find the generated installer
            installer_name = f"{self.config.app_name}_{self.config.app_version}_Setup.exe"
            installer_path = self.nsis_dir / installer_name
            
            if installer_path.exists():
                # Move to dist directory
                final_path = self.dist_dir / installer_name
                shutil.move(str(installer_path), str(final_path))
                
                installer_size = final_path.stat().st_size
                self.logger.info(f"Installer created successfully: {final_path}")
                self.logger.info(f"Installer size: {installer_size / 1024**2:.1f} MB")
                
                return True
            else:
                self.logger.error("Installer file not found after build")
                return False
                
        except Exception as e:
            self.logger.error(f"Installer build failed: {e}")
            return False
    
    def create_portable_package(self) -> bool:
        """Create a portable ZIP package for restricted environments."""
        self.logger.info("Creating portable package...")
        
        try:
            # Find executable
            exe_path = self.detect_executable_path()
            if not exe_path:
                return False
            
            # Create portable directory
            portable_dir = self.build_dir / "portable"
            if portable_dir.exists():
                shutil.rmtree(portable_dir)
            portable_dir.mkdir(parents=True)
            
            # Copy executable
            shutil.copy2(exe_path, portable_dir / self.config.executable_name)
            
            # Copy essential directories
            essential_dirs = ['config', 'knowledge', 'data']
            for dir_name in essential_dirs:
                src_dir = self.project_root / dir_name
                if src_dir.exists():
                    shutil.copytree(src_dir, portable_dir / dir_name)
            
            # Copy user documentation
            docs_src = self.project_root / "docs" / "user_guide"
            if docs_src.exists():
                docs_dest = portable_dir / "docs"
                shutil.copytree(docs_src, docs_dest)
            
            # Create portable info file
            portable_info = {
                "app_name": self.config.app_name,
                "version": self.config.app_version,
                "package_type": "portable",
                "usage": "Run ComBadge.exe to start the application",
                "requirements": {
                    "windows_version": "Windows 10 or later",
                    "ram_gb": 8,
                    "disk_gb": 10,
                    "ollama": "Will be downloaded automatically on first run"
                }
            }
            
            with open(portable_dir / "README.json", 'w') as f:
                json.dump(portable_info, f, indent=2)
            
            # Create portable batch file
            batch_content = f'''@echo off
title {self.config.app_name} Portable
echo Starting {self.config.app_name}...
echo.
echo This is the portable version of {self.config.app_name}.
echo All data will be stored in the current directory.
echo.
pause
start "" "{self.config.executable_name}"
'''
            
            with open(portable_dir / "Start_ComBadge.bat", 'w') as f:
                f.write(batch_content)
            
            # Create ZIP archive
            zip_name = f"{self.config.app_name}_{self.config.app_version}_Portable"
            zip_path = self.dist_dir / f"{zip_name}.zip"
            
            shutil.make_archive(str(zip_path.with_suffix('')), 'zip', portable_dir)
            
            zip_size = zip_path.stat().st_size
            self.logger.info(f"Portable package created: {zip_path}")
            self.logger.info(f"Package size: {zip_size / 1024**2:.1f} MB")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Portable package creation failed: {e}")
            return False


def main():
    """Main installer builder entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build ComBadge installer")
    parser.add_argument("--type", choices=["installer", "portable", "both"],
                       default="installer", help="Package type to build")
    parser.add_argument("--version", help="Override version number")
    
    args = parser.parse_args()
    
    builder = NSISInstallerBuilder()
    
    if args.version:
        builder.config.app_version = args.version
    
    success = True
    
    if args.type in ["installer", "both"]:
        if not builder.build_installer():
            success = False
    
    if args.type in ["portable", "both"]:
        if not builder.create_portable_package():
            success = False
    
    if success:
        print("Package creation completed successfully!")
        print(f"Output directory: {builder.dist_dir}")
    else:
        print("Package creation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()