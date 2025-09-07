#!/usr/bin/env python3
"""
ComBadge Update Manager

Comprehensive update management system for seamless version management,
automatic update checking, downloading, and installation with rollback capabilities.
"""

import os
import sys
import json
import hashlib
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from urllib.request import urlopen, urlretrieve
from urllib.parse import urljoin
import zipfile
import threading
import time
from datetime import datetime, timedelta
import sqlite3


@dataclass
class VersionInfo:
    """Version information structure."""
    version: str
    release_date: str
    download_url: str
    checksum: str
    size_bytes: int
    release_notes: str
    critical: bool = False
    minimum_version: Optional[str] = None


@dataclass
class UpdateResult:
    """Update operation result."""
    success: bool
    message: str
    version: Optional[str] = None
    backup_path: Optional[str] = None
    error_details: Optional[str] = None


class UpdateManager:
    """Comprehensive update management for ComBadge."""
    
    def __init__(self, app_directory: Optional[Path] = None, update_server: Optional[str] = None):
        """Initialize update manager."""
        self.app_directory = app_directory or Path(sys.executable).parent
        self.update_server = update_server or "https://api.github.com/repos/mklemmingen/Combadge/releases"
        
        # Update management directories
        self.update_dir = self.app_directory / "updates"
        self.backup_dir = self.app_directory / "backups"
        self.temp_dir = self.app_directory / "temp"
        
        # Database for update tracking
        self.db_path = self.app_directory / "update_history.db"
        
        # Configuration
        self.config_file = self.app_directory / "update_config.json"
        self.current_version_file = self.app_directory / "version.json"
        
        # Ensure directories exist
        for directory in [self.update_dir, self.backup_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup database
        self._setup_database()
        
        # Load configuration
        self.config = self._load_config()
        
    def _setup_database(self):
        """Setup SQLite database for update tracking."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS update_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        from_version TEXT,
                        to_version TEXT NOT NULL,
                        status TEXT NOT NULL,
                        backup_path TEXT,
                        notes TEXT,
                        rollback_available INTEGER DEFAULT 1
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS update_checks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        current_version TEXT NOT NULL,
                        latest_version TEXT,
                        update_available INTEGER DEFAULT 0,
                        check_result TEXT
                    )
                ''')
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to setup database: {e}")
    
    def _load_config(self) -> Dict:
        """Load update configuration."""
        default_config = {
            "auto_check_enabled": True,
            "auto_download_enabled": False,
            "auto_install_enabled": False,
            "check_interval_hours": 24,
            "backup_retention_days": 30,
            "pre_release_updates": False,
            "critical_updates_auto": True,
            "update_server": self.update_server,
            "proxy": None,
            "verify_signatures": True
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                self.logger.error(f"Failed to load config: {e}")
        
        return default_config
    
    def _save_config(self):
        """Save update configuration."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    def get_current_version(self) -> Optional[str]:
        """Get the current application version."""
        try:
            if self.current_version_file.exists():
                with open(self.current_version_file, 'r') as f:
                    version_data = json.load(f)
                    return version_data.get('version')
            
            # Try to get version from executable
            try:
                result = subprocess.run([
                    str(self.app_directory / "ComBadge.exe"), "--version"
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    version = result.stdout.strip()
                    # Save for future reference
                    self._save_current_version(version)
                    return version
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            return "1.0.0"  # Default version
            
        except Exception as e:
            self.logger.error(f"Failed to get current version: {e}")
            return None
    
    def _save_current_version(self, version: str):
        """Save current version information."""
        try:
            version_data = {
                "version": version,
                "updated_at": datetime.now().isoformat(),
                "update_method": "automatic"
            }
            
            with open(self.current_version_file, 'w') as f:
                json.dump(version_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save version: {e}")
    
    def check_for_updates(self) -> Tuple[bool, Optional[VersionInfo]]:
        """Check for available updates."""
        self.logger.info("Checking for updates...")
        
        try:
            current_version = self.get_current_version()
            if not current_version:
                self.logger.error("Could not determine current version")
                return False, None
            
            # Get latest release information
            latest_version = self._fetch_latest_version()
            
            if not latest_version:
                self.logger.error("Could not fetch latest version information")
                return False, None
            
            # Record check in database
            self._record_update_check(current_version, latest_version)
            
            # Compare versions
            update_available = self._compare_versions(current_version, latest_version.version) < 0
            
            if update_available:
                self.logger.info(f"Update available: {current_version} -> {latest_version.version}")
                return True, latest_version
            else:
                self.logger.info("No updates available")
                return False, latest_version
                
        except Exception as e:
            self.logger.error(f"Update check failed: {e}")
            return False, None
    
    def _fetch_latest_version(self) -> Optional[VersionInfo]:
        """Fetch latest version information from update server."""
        try:
            # For GitHub releases API
            if "github.com" in self.config["update_server"]:
                return self._fetch_github_release()
            else:
                # Custom update server
                return self._fetch_custom_release()
                
        except Exception as e:
            self.logger.error(f"Failed to fetch version info: {e}")
            return None
    
    def _fetch_github_release(self) -> Optional[VersionInfo]:
        """Fetch release info from GitHub API."""
        try:
            with urlopen(self.config["update_server"]) as response:
                releases = json.loads(response.read().decode())
            
            # Find appropriate release
            for release in releases:
                if release["draft"]:
                    continue
                    
                if release["prerelease"] and not self.config["pre_release_updates"]:
                    continue
                
                # Look for Windows executable asset
                for asset in release["assets"]:
                    if asset["name"].endswith("_Setup.exe") or asset["name"].endswith(".exe"):
                        return VersionInfo(
                            version=release["tag_name"].lstrip("v"),
                            release_date=release["published_at"],
                            download_url=asset["browser_download_url"],
                            checksum="",  # GitHub doesn't provide checksums directly
                            size_bytes=asset["size"],
                            release_notes=release["body"],
                            critical=self._is_critical_update(release["body"])
                        )
            
            return None
            
        except Exception as e:
            self.logger.error(f"GitHub API request failed: {e}")
            return None
    
    def _fetch_custom_release(self) -> Optional[VersionInfo]:
        """Fetch release info from custom update server."""
        try:
            update_url = urljoin(self.config["update_server"], "latest.json")
            
            with urlopen(update_url) as response:
                release_info = json.loads(response.read().decode())
            
            return VersionInfo(**release_info)
            
        except Exception as e:
            self.logger.error(f"Custom server request failed: {e}")
            return None
    
    def _is_critical_update(self, release_notes: str) -> bool:
        """Determine if an update is critical based on release notes."""
        critical_keywords = [
            "critical", "security", "vulnerability", "urgent",
            "hotfix", "emergency", "patch", "exploit"
        ]
        
        notes_lower = release_notes.lower()
        return any(keyword in notes_lower for keyword in critical_keywords)
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings. Returns -1, 0, or 1."""
        def version_tuple(v):
            return tuple(map(int, v.split('.')))
        
        try:
            v1_tuple = version_tuple(version1)
            v2_tuple = version_tuple(version2)
            
            if v1_tuple < v2_tuple:
                return -1
            elif v1_tuple > v2_tuple:
                return 1
            else:
                return 0
                
        except ValueError:
            # Fallback to string comparison
            if version1 < version2:
                return -1
            elif version1 > version2:
                return 1
            else:
                return 0
    
    def download_update(self, version_info: VersionInfo, progress_callback=None) -> Optional[Path]:
        """Download update package."""
        self.logger.info(f"Downloading update {version_info.version}...")
        
        try:
            # Create download path
            filename = f"ComBadge_{version_info.version}_Setup.exe"
            download_path = self.update_dir / filename
            
            # Download with progress tracking
            def progress_hook(block_num, block_size, total_size):
                if progress_callback:
                    downloaded = block_num * block_size
                    progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                    progress_callback(min(progress, 100))
            
            urlretrieve(version_info.download_url, download_path, progress_hook)
            
            # Verify download
            if self._verify_download(download_path, version_info):
                self.logger.info(f"Update downloaded successfully: {download_path}")
                return download_path
            else:
                self.logger.error("Download verification failed")
                download_path.unlink(missing_ok=True)
                return None
                
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return None
    
    def _verify_download(self, file_path: Path, version_info: VersionInfo) -> bool:
        """Verify downloaded file integrity."""
        try:
            # Check file size
            actual_size = file_path.stat().st_size
            if version_info.size_bytes > 0 and abs(actual_size - version_info.size_bytes) > 1024:
                self.logger.error(f"Size mismatch: expected {version_info.size_bytes}, got {actual_size}")
                return False
            
            # Check checksum if provided
            if version_info.checksum:
                actual_checksum = self._calculate_checksum(file_path)
                if actual_checksum.lower() != version_info.checksum.lower():
                    self.logger.error(f"Checksum mismatch: expected {version_info.checksum}, got {actual_checksum}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Verification failed: {e}")
            return False
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def create_backup(self) -> Optional[Path]:
        """Create backup of current installation."""
        self.logger.info("Creating installation backup...")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_version = self.get_current_version()
            backup_name = f"backup_{current_version}_{timestamp}"
            backup_path = self.backup_dir / backup_name
            
            # Create backup directory
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Files/directories to backup
            backup_items = [
                "ComBadge.exe",
                "config",
                "knowledge", 
                "data",
                "version.json",
                "update_config.json"
            ]
            
            for item in backup_items:
                source = self.app_directory / item
                if source.exists():
                    if source.is_file():
                        shutil.copy2(source, backup_path)
                    else:
                        shutil.copytree(source, backup_path / item)
            
            # Create backup manifest
            manifest = {
                "backup_date": datetime.now().isoformat(),
                "version": current_version,
                "items": backup_items,
                "app_directory": str(self.app_directory)
            }
            
            with open(backup_path / "backup_manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)
            
            self.logger.info(f"Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            return None
    
    def install_update(self, installer_path: Path, backup_path: Optional[Path] = None) -> UpdateResult:
        """Install downloaded update."""
        self.logger.info(f"Installing update from {installer_path}...")
        
        try:
            current_version = self.get_current_version()
            
            # Run installer with silent installation
            cmd = [str(installer_path), "/S", f"/D={self.app_directory}"]
            
            self.logger.info(f"Running installer: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                # Verify installation
                new_version = self.get_current_version()
                
                # Record successful update
                self._record_update(current_version, new_version, "SUCCESS", str(backup_path))
                
                self.logger.info(f"Update installed successfully: {current_version} -> {new_version}")
                
                return UpdateResult(
                    success=True,
                    message=f"Successfully updated to version {new_version}",
                    version=new_version,
                    backup_path=str(backup_path) if backup_path else None
                )
            else:
                error_msg = f"Installer failed with code {result.returncode}"
                self.logger.error(f"{error_msg}: {result.stderr}")
                
                # Record failed update
                self._record_update(current_version, None, "FAILED", str(backup_path), error_msg)
                
                return UpdateResult(
                    success=False,
                    message="Update installation failed",
                    error_details=result.stderr
                )
                
        except subprocess.TimeoutExpired:
            error_msg = "Update installation timed out"
            self.logger.error(error_msg)
            
            return UpdateResult(
                success=False,
                message=error_msg
            )
            
        except Exception as e:
            error_msg = f"Update installation failed: {e}"
            self.logger.error(error_msg)
            
            return UpdateResult(
                success=False,
                message="Update installation error",
                error_details=str(e)
            )
    
    def rollback_update(self, backup_path: Path) -> UpdateResult:
        """Rollback to previous version from backup."""
        self.logger.info(f"Rolling back from backup: {backup_path}")
        
        try:
            if not backup_path.exists():
                return UpdateResult(
                    success=False,
                    message="Backup not found"
                )
            
            # Load backup manifest
            manifest_file = backup_path / "backup_manifest.json"
            if not manifest_file.exists():
                return UpdateResult(
                    success=False,
                    message="Backup manifest not found"
                )
            
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            current_version = self.get_current_version()
            rollback_version = manifest["version"]
            
            # Stop application if running
            self._stop_application()
            
            # Restore files
            for item in manifest["items"]:
                source = backup_path / item
                target = self.app_directory / item
                
                if source.exists():
                    if target.exists():
                        if target.is_file():
                            target.unlink()
                        else:
                            shutil.rmtree(target)
                    
                    if source.is_file():
                        shutil.copy2(source, target)
                    else:
                        shutil.copytree(source, target)
            
            # Update version info
            self._save_current_version(rollback_version)
            
            # Record rollback
            self._record_update(current_version, rollback_version, "ROLLBACK", str(backup_path))
            
            self.logger.info(f"Rollback successful: {current_version} -> {rollback_version}")
            
            return UpdateResult(
                success=True,
                message=f"Successfully rolled back to version {rollback_version}",
                version=rollback_version
            )
            
        except Exception as e:
            error_msg = f"Rollback failed: {e}"
            self.logger.error(error_msg)
            
            return UpdateResult(
                success=False,
                message="Rollback failed",
                error_details=str(e)
            )
    
    def _stop_application(self):
        """Attempt to gracefully stop the application."""
        try:
            # Try to find and terminate ComBadge processes
            result = subprocess.run([
                'taskkill', '/F', '/IM', 'ComBadge.exe'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("Application stopped successfully")
                time.sleep(2)  # Wait for cleanup
            
        except Exception as e:
            self.logger.warning(f"Could not stop application: {e}")
    
    def _record_update_check(self, current_version: str, latest_version: VersionInfo):
        """Record update check in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO update_checks 
                    (timestamp, current_version, latest_version, update_available, check_result)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    current_version,
                    latest_version.version,
                    1 if self._compare_versions(current_version, latest_version.version) < 0 else 0,
                    "success"
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to record update check: {e}")
    
    def _record_update(self, from_version: Optional[str], to_version: Optional[str], 
                      status: str, backup_path: Optional[str], notes: Optional[str] = None):
        """Record update operation in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO update_history 
                    (timestamp, from_version, to_version, status, backup_path, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    from_version,
                    to_version,
                    status,
                    backup_path,
                    notes
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to record update: {e}")
    
    def get_update_history(self) -> List[Dict]:
        """Get update history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT * FROM update_history 
                    ORDER BY timestamp DESC
                    LIMIT 50
                ''')
                
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to get update history: {e}")
            return []
    
    def cleanup_old_backups(self):
        """Clean up old backup files."""
        try:
            retention_days = self.config["backup_retention_days"]
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            for backup_dir in self.backup_dir.iterdir():
                if backup_dir.is_dir():
                    try:
                        # Parse timestamp from directory name
                        parts = backup_dir.name.split('_')
                        if len(parts) >= 3:
                            date_str = parts[-2] + '_' + parts[-1]
                            backup_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                            
                            if backup_date < cutoff_date:
                                shutil.rmtree(backup_dir)
                                self.logger.info(f"Cleaned up old backup: {backup_dir.name}")
                                
                    except (ValueError, IndexError):
                        # Skip directories that don't match expected format
                        continue
                        
        except Exception as e:
            self.logger.error(f"Backup cleanup failed: {e}")
    
    def auto_update_worker(self):
        """Background worker for automatic updates."""
        while True:
            try:
                if not self.config["auto_check_enabled"]:
                    time.sleep(3600)  # Check every hour if disabled
                    continue
                
                update_available, version_info = self.check_for_updates()
                
                if update_available and version_info:
                    # Handle critical updates
                    if version_info.critical and self.config["critical_updates_auto"]:
                        self.logger.info("Critical update detected, starting automatic installation")
                        self._perform_automatic_update(version_info)
                    
                    # Handle regular auto-updates
                    elif self.config["auto_install_enabled"]:
                        self.logger.info("Update available, starting automatic installation") 
                        self._perform_automatic_update(version_info)
                    
                    # Auto-download only
                    elif self.config["auto_download_enabled"]:
                        self.logger.info("Update available, starting download")
                        self.download_update(version_info)
                
                # Sleep until next check
                sleep_hours = self.config["check_interval_hours"]
                time.sleep(sleep_hours * 3600)
                
            except Exception as e:
                self.logger.error(f"Auto-update worker error: {e}")
                time.sleep(3600)  # Wait an hour before retrying
    
    def _perform_automatic_update(self, version_info: VersionInfo):
        """Perform automatic update installation."""
        try:
            # Download update
            installer_path = self.download_update(version_info)
            if not installer_path:
                return
            
            # Create backup
            backup_path = self.create_backup()
            
            # Install update
            result = self.install_update(installer_path, backup_path)
            
            if result.success:
                self.logger.info("Automatic update completed successfully")
                # Clean up installer
                installer_path.unlink(missing_ok=True)
            else:
                self.logger.error(f"Automatic update failed: {result.message}")
                
        except Exception as e:
            self.logger.error(f"Automatic update error: {e}")


def main():
    """Main entry point for update manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ComBadge Update Manager")
    parser.add_argument("--check", action="store_true", help="Check for updates")
    parser.add_argument("--download", action="store_true", help="Download latest update")
    parser.add_argument("--install", metavar="PATH", help="Install update from path")
    parser.add_argument("--rollback", metavar="BACKUP_PATH", help="Rollback to backup")
    parser.add_argument("--history", action="store_true", help="Show update history")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old backups")
    parser.add_argument("--config", metavar="KEY=VALUE", action="append", help="Set configuration")
    
    args = parser.parse_args()
    
    manager = UpdateManager()
    
    if args.config:
        for config_item in args.config:
            key, value = config_item.split('=', 1)
            # Parse boolean values
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            
            manager.config[key] = value
        
        manager._save_config()
        print(f"Configuration updated: {args.config}")
    
    if args.check:
        update_available, version_info = manager.check_for_updates()
        if update_available:
            print(f"Update available: {version_info.version}")
            print(f"Release notes: {version_info.release_notes}")
        else:
            print("No updates available")
    
    if args.download:
        update_available, version_info = manager.check_for_updates()
        if update_available:
            print(f"Downloading update {version_info.version}...")
            installer_path = manager.download_update(version_info)
            if installer_path:
                print(f"Download completed: {installer_path}")
            else:
                print("Download failed")
        else:
            print("No updates available to download")
    
    if args.install:
        installer_path = Path(args.install)
        if installer_path.exists():
            backup_path = manager.create_backup()
            result = manager.install_update(installer_path, backup_path)
            print(result.message)
        else:
            print("Installer file not found")
    
    if args.rollback:
        backup_path = Path(args.rollback)
        result = manager.rollback_update(backup_path)
        print(result.message)
    
    if args.history:
        history = manager.get_update_history()
        if history:
            print("\nUpdate History:")
            print("-" * 80)
            for record in history:
                print(f"{record['timestamp']}: {record['from_version']} -> {record['to_version']} ({record['status']})")
        else:
            print("No update history found")
    
    if args.cleanup:
        manager.cleanup_old_backups()
        print("Backup cleanup completed")


if __name__ == "__main__":
    main()