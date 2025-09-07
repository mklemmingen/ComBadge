#!/usr/bin/env python3
"""
ComBadge Backup Manager

Comprehensive backup and restore system for ComBadge configurations,
user data, knowledge base, and complete system snapshots.
"""

import os
import sys
import json
import logging
import shutil
import zipfile
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import tempfile
import sqlite3
import threading


@dataclass
class BackupItem:
    """Individual backup item definition."""
    name: str
    source_path: str
    item_type: str  # file, directory, database
    priority: str   # critical, important, optional
    size_bytes: int = 0
    checksum: str = ""


@dataclass
class BackupSet:
    """Complete backup set information."""
    backup_id: str
    timestamp: str
    version: str
    backup_type: str  # full, incremental, differential
    description: str
    items: List[BackupItem]
    total_size_bytes: int
    compressed_size_bytes: int
    checksum: str
    metadata: Dict[str, Any]


@dataclass
class BackupResult:
    """Result of a backup operation."""
    backup_set: BackupSet
    success: bool
    message: str
    backup_path: Optional[str] = None
    duration_seconds: float = 0.0
    error: Optional[str] = None


class BackupManager:
    """Comprehensive backup management for ComBadge."""
    
    def __init__(self, installation_path: Optional[Path] = None, backup_root: Optional[Path] = None):
        """Initialize backup manager."""
        self.installation_path = installation_path or self._detect_installation_path()
        self.backup_root = backup_root or self.installation_path / "backups"
        
        # Create backup directories
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.full_backup_dir = self.backup_root / "full"
        self.incremental_backup_dir = self.backup_root / "incremental"
        self.config_backup_dir = self.backup_root / "config"
        
        for backup_dir in [self.full_backup_dir, self.incremental_backup_dir, self.config_backup_dir]:
            backup_dir.mkdir(exist_ok=True)
        
        # Database for backup tracking
        self.db_path = self.backup_root / "backup_history.db"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup database
        self._setup_database()
        
    def _detect_installation_path(self) -> Path:
        """Detect ComBadge installation path."""
        possible_paths = [
            Path("C:\\Program Files\\ComBadge"),
            Path("C:\\Program Files (x86)\\ComBadge"),
            Path(os.path.expanduser("~\\AppData\\Local\\ComBadge")),
            Path.cwd(),
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "ComBadge.exe").exists():
                return path
                
        return Path.cwd()
    
    def _setup_database(self):
        """Setup SQLite database for backup tracking."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS backup_sets (
                        backup_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        version TEXT,
                        backup_type TEXT NOT NULL,
                        description TEXT,
                        backup_path TEXT NOT NULL,
                        total_size_bytes INTEGER,
                        compressed_size_bytes INTEGER,
                        checksum TEXT,
                        metadata TEXT,
                        status TEXT DEFAULT 'completed'
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS backup_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        backup_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        source_path TEXT NOT NULL,
                        item_type TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        size_bytes INTEGER,
                        checksum TEXT,
                        FOREIGN KEY (backup_id) REFERENCES backup_sets (backup_id)
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS restore_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        backup_id TEXT NOT NULL,
                        restore_path TEXT NOT NULL,
                        status TEXT NOT NULL,
                        notes TEXT
                    )
                ''')
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to setup backup database: {e}")
    
    def identify_backup_items(self, backup_type: str = "full") -> List[BackupItem]:
        """Identify items to include in backup."""
        items = []
        
        # Critical items (always included)
        critical_items = [
            ("executable", str(self.installation_path / "ComBadge.exe"), "file"),
            ("main_config", str(self.installation_path / "config" / "default_config.yaml"), "file"),
            ("user_preferences", str(self.installation_path / "config" / "user_preferences.yaml"), "file"),
        ]
        
        # Important items
        important_items = [
            ("config_directory", str(self.installation_path / "config"), "directory"),
            ("knowledge_base", str(self.installation_path / "knowledge"), "directory"),
            ("data_directory", str(self.installation_path / "data"), "directory"),
            ("documentation", str(self.installation_path / "docs"), "directory"),
        ]
        
        # Optional items (full backup only)
        optional_items = [
            ("logs", str(self.installation_path / "logs"), "directory"),
            ("cache", str(self.installation_path / "cache"), "directory"),
            ("temp", str(self.installation_path / "temp"), "directory"),
            ("backup_history", str(self.db_path), "database"),
        ]
        
        # Add items based on backup type
        all_items = critical_items + important_items
        if backup_type == "full":
            all_items.extend(optional_items)
        
        for name, path, item_type in all_items:
            source_path = Path(path)
            if source_path.exists():
                priority = "critical" if (name, path, item_type) in critical_items else \
                          "important" if (name, path, item_type) in important_items else "optional"
                
                item = BackupItem(
                    name=name,
                    source_path=str(source_path),
                    item_type=item_type,
                    priority=priority
                )
                
                # Calculate size and checksum
                item.size_bytes = self._calculate_item_size(source_path)
                item.checksum = self._calculate_item_checksum(source_path)
                
                items.append(item)
        
        return items
    
    def _calculate_item_size(self, path: Path) -> int:
        """Calculate size of item in bytes."""
        try:
            if not path.exists():
                return 0
            
            if path.is_file():
                return path.stat().st_size
            elif path.is_dir():
                total_size = 0
                for file_path in path.rglob("*"):
                    if file_path.is_file():
                        try:
                            total_size += file_path.stat().st_size
                        except (OSError, PermissionError):
                            continue
                return total_size
        except (OSError, PermissionError):
            pass
        
        return 0
    
    def _calculate_item_checksum(self, path: Path) -> str:
        """Calculate checksum of item."""
        try:
            if not path.exists():
                return ""
            
            hasher = hashlib.sha256()
            
            if path.is_file():
                with open(path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
            elif path.is_dir():
                # Hash directory structure and file contents
                for file_path in sorted(path.rglob("*")):
                    if file_path.is_file():
                        # Add file path to hash
                        hasher.update(str(file_path.relative_to(path)).encode())
                        
                        # Add file content to hash
                        try:
                            with open(file_path, 'rb') as f:
                                for chunk in iter(lambda: f.read(4096), b""):
                                    hasher.update(chunk)
                        except (OSError, PermissionError):
                            continue
            
            return hasher.hexdigest()
            
        except (OSError, PermissionError):
            return ""
    
    def create_backup(self, backup_type: str = "full", description: str = "",
                     compression: bool = True, verify: bool = True) -> BackupResult:
        """Create a backup of ComBadge installation."""
        self.logger.info(f"Starting {backup_type} backup...")
        start_time = time.time()
        
        try:
            # Generate backup ID
            timestamp = datetime.now()
            backup_id = f"combadge_{backup_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            # Get current version
            version = self._get_current_version()
            
            # Identify backup items
            items = self.identify_backup_items(backup_type)
            
            if not items:
                return BackupResult(
                    backup_set=None,
                    success=False,
                    message="No items found to backup"
                )
            
            # Calculate total size
            total_size = sum(item.size_bytes for item in items)
            
            # Create backup directory
            backup_dir = self.full_backup_dir if backup_type == "full" else self.incremental_backup_dir
            backup_path = backup_dir / f"{backup_id}.zip"
            
            self.logger.info(f"Creating backup: {backup_path}")
            self.logger.info(f"Backing up {len(items)} items ({total_size / 1024**2:.1f} MB)")
            
            # Create backup archive
            compressed_size = self._create_backup_archive(items, backup_path, compression)
            
            # Verify backup if requested
            if verify and not self._verify_backup(backup_path, items):
                return BackupResult(
                    backup_set=None,
                    success=False,
                    message="Backup verification failed"
                )
            
            # Calculate archive checksum
            archive_checksum = self._calculate_item_checksum(backup_path)
            
            # Create backup set
            backup_set = BackupSet(
                backup_id=backup_id,
                timestamp=timestamp.isoformat(),
                version=version,
                backup_type=backup_type,
                description=description or f"Automatic {backup_type} backup",
                items=items,
                total_size_bytes=total_size,
                compressed_size_bytes=compressed_size,
                checksum=archive_checksum,
                metadata={
                    "installation_path": str(self.installation_path),
                    "backup_tool_version": "1.0.0",
                    "compression": compression,
                    "verified": verify
                }
            )
            
            # Record backup in database
            self._record_backup(backup_set, str(backup_path))
            
            duration = time.time() - start_time
            compression_ratio = (1 - compressed_size / total_size) * 100 if total_size > 0 else 0
            
            self.logger.info(f"Backup completed in {duration:.1f}s")
            self.logger.info(f"Compression: {compression_ratio:.1f}% reduction")
            
            return BackupResult(
                backup_set=backup_set,
                success=True,
                message=f"Backup completed successfully",
                backup_path=str(backup_path),
                duration_seconds=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Backup failed after {duration:.1f}s: {e}")
            
            return BackupResult(
                backup_set=None,
                success=False,
                message=f"Backup failed: {str(e)}",
                duration_seconds=duration,
                error=str(e)
            )
    
    def _create_backup_archive(self, items: List[BackupItem], backup_path: Path, 
                             compression: bool = True) -> int:
        """Create backup archive from items."""
        compression_type = zipfile.ZIP_DEFLATED if compression else zipfile.ZIP_STORED
        
        with zipfile.ZipFile(backup_path, 'w', compression_type, compresslevel=6) as zipf:
            # Add backup manifest
            manifest = {
                "backup_timestamp": datetime.now().isoformat(),
                "installation_path": str(self.installation_path),
                "items": [asdict(item) for item in items]
            }
            
            zipf.writestr("backup_manifest.json", json.dumps(manifest, indent=2))
            
            # Add each item
            for item in items:
                source_path = Path(item.source_path)
                
                if not source_path.exists():
                    self.logger.warning(f"Skipping missing item: {source_path}")
                    continue
                
                try:
                    if source_path.is_file():
                        # Add single file
                        arcname = f"data/{item.name}/{source_path.name}"
                        zipf.write(source_path, arcname)
                        
                    elif source_path.is_dir():
                        # Add directory contents
                        for file_path in source_path.rglob("*"):
                            if file_path.is_file():
                                relative_path = file_path.relative_to(source_path)
                                arcname = f"data/{item.name}/{relative_path}"
                                zipf.write(file_path, arcname)
                                
                except Exception as e:
                    self.logger.error(f"Failed to add {item.name} to backup: {e}")
                    continue
        
        return backup_path.stat().st_size
    
    def _verify_backup(self, backup_path: Path, items: List[BackupItem]) -> bool:
        """Verify backup archive integrity."""
        try:
            self.logger.info("Verifying backup integrity...")
            
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Test archive integrity
                test_result = zipf.testzip()
                if test_result:
                    self.logger.error(f"Archive corruption detected: {test_result}")
                    return False
                
                # Verify manifest
                try:
                    manifest_data = zipf.read("backup_manifest.json")
                    manifest = json.loads(manifest_data)
                    
                    if len(manifest["items"]) != len(items):
                        self.logger.error("Manifest item count mismatch")
                        return False
                        
                except Exception as e:
                    self.logger.error(f"Manifest verification failed: {e}")
                    return False
                
                # Verify critical items exist
                critical_items = [item for item in items if item.priority == "critical"]
                for item in critical_items:
                    item_files = [name for name in zipf.namelist() if name.startswith(f"data/{item.name}/")]
                    if not item_files:
                        self.logger.error(f"Critical item missing from backup: {item.name}")
                        return False
            
            self.logger.info("Backup verification successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Backup verification failed: {e}")
            return False
    
    def _get_current_version(self) -> str:
        """Get current ComBadge version."""
        try:
            version_file = self.installation_path / "version.json"
            if version_file.exists():
                with open(version_file, 'r') as f:
                    version_data = json.load(f)
                    return version_data.get('version', '1.0.0')
            
            # Try to get from executable
            exe_path = self.installation_path / "ComBadge.exe"
            if exe_path.exists():
                import subprocess
                result = subprocess.run([str(exe_path), "--version"], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    return result.stdout.strip()
        except:
            pass
        
        return "unknown"
    
    def _record_backup(self, backup_set: BackupSet, backup_path: str):
        """Record backup in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Insert backup set
                conn.execute('''
                    INSERT INTO backup_sets 
                    (backup_id, timestamp, version, backup_type, description, backup_path,
                     total_size_bytes, compressed_size_bytes, checksum, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    backup_set.backup_id,
                    backup_set.timestamp,
                    backup_set.version,
                    backup_set.backup_type,
                    backup_set.description,
                    backup_path,
                    backup_set.total_size_bytes,
                    backup_set.compressed_size_bytes,
                    backup_set.checksum,
                    json.dumps(backup_set.metadata)
                ))
                
                # Insert backup items
                for item in backup_set.items:
                    conn.execute('''
                        INSERT INTO backup_items
                        (backup_id, name, source_path, item_type, priority, size_bytes, checksum)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        backup_set.backup_id,
                        item.name,
                        item.source_path,
                        item.item_type,
                        item.priority,
                        item.size_bytes,
                        item.checksum
                    ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to record backup in database: {e}")
    
    def list_backups(self, backup_type: Optional[str] = None) -> List[Dict]:
        """List available backups."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if backup_type:
                    cursor = conn.execute('''
                        SELECT * FROM backup_sets 
                        WHERE backup_type = ? 
                        ORDER BY timestamp DESC
                    ''', (backup_type,))
                else:
                    cursor = conn.execute('''
                        SELECT * FROM backup_sets 
                        ORDER BY timestamp DESC
                    ''')
                
                columns = [description[0] for description in cursor.description]
                backups = []
                
                for row in cursor.fetchall():
                    backup_info = dict(zip(columns, row))
                    
                    # Parse metadata
                    if backup_info['metadata']:
                        backup_info['metadata'] = json.loads(backup_info['metadata'])
                    
                    backups.append(backup_info)
                
                return backups
                
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            return []
    
    def restore_backup(self, backup_id: str, restore_path: Optional[Path] = None,
                      selective_restore: Optional[List[str]] = None) -> bool:
        """Restore from backup."""
        self.logger.info(f"Starting restore from backup: {backup_id}")
        
        try:
            # Get backup information
            backup_info = self._get_backup_info(backup_id)
            if not backup_info:
                self.logger.error(f"Backup not found: {backup_id}")
                return False
            
            backup_path = Path(backup_info['backup_path'])
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Default restore path
            if restore_path is None:
                restore_path = self.installation_path
            
            self.logger.info(f"Restoring to: {restore_path}")
            
            # Stop ComBadge processes
            self._stop_combadge_processes()
            
            # Extract backup
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Load manifest
                manifest_data = zipf.read("backup_manifest.json")
                manifest = json.loads(manifest_data)
                
                # Extract items
                for item_info in manifest['items']:
                    item_name = item_info['name']
                    
                    # Skip if selective restore and item not selected
                    if selective_restore and item_name not in selective_restore:
                        continue
                    
                    self.logger.info(f"Restoring: {item_name}")
                    
                    # Extract item files
                    item_files = [name for name in zipf.namelist() 
                                 if name.startswith(f"data/{item_name}/")]
                    
                    for file_path in item_files:
                        # Calculate destination path
                        relative_path = file_path[len(f"data/{item_name}/"):]
                        dest_path = restore_path / item_name / relative_path
                        
                        # Create parent directories
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Extract file
                        with zipf.open(file_path) as src, open(dest_path, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
            
            # Record restore in database
            self._record_restore(backup_id, str(restore_path), "success")
            
            self.logger.info("Restore completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            self._record_restore(backup_id, str(restore_path or ""), "failed", str(e))
            return False
    
    def _get_backup_info(self, backup_id: str) -> Optional[Dict]:
        """Get backup information from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT * FROM backup_sets WHERE backup_id = ?
                ''', (backup_id,))
                
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                
        except Exception as e:
            self.logger.error(f"Failed to get backup info: {e}")
        
        return None
    
    def _record_restore(self, backup_id: str, restore_path: str, status: str, notes: str = ""):
        """Record restore operation in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO restore_history
                    (timestamp, backup_id, restore_path, status, notes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    backup_id,
                    restore_path,
                    status,
                    notes
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to record restore: {e}")
    
    def _stop_combadge_processes(self):
        """Stop ComBadge processes before restore."""
        try:
            import subprocess
            
            if os.name == 'nt':
                subprocess.run(['taskkill', '/F', '/IM', 'ComBadge.exe'], 
                              capture_output=True, timeout=30)
            else:
                subprocess.run(['pkill', '-f', 'combadge'], 
                              capture_output=True, timeout=30)
            
            time.sleep(2)  # Wait for processes to terminate
            
        except Exception as e:
            self.logger.warning(f"Could not stop ComBadge processes: {e}")
    
    def cleanup_old_backups(self, retention_days: int = 30, keep_min: int = 5):
        """Clean up old backup files."""
        self.logger.info(f"Cleaning up backups older than {retention_days} days...")
        
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            with sqlite3.connect(self.db_path) as conn:
                # Get backups to clean
                cursor = conn.execute('''
                    SELECT backup_id, backup_path, timestamp FROM backup_sets
                    ORDER BY timestamp DESC
                ''')
                
                all_backups = cursor.fetchall()
                
                # Keep minimum number of backups
                backups_to_check = all_backups[keep_min:]
                
                deleted_count = 0
                freed_space = 0
                
                for backup_id, backup_path, timestamp_str in backups_to_check:
                    backup_time = datetime.fromisoformat(timestamp_str)
                    
                    if backup_time < cutoff_date:
                        backup_file = Path(backup_path)
                        
                        if backup_file.exists():
                            file_size = backup_file.stat().st_size
                            backup_file.unlink()
                            freed_space += file_size
                            
                        # Remove from database
                        conn.execute('DELETE FROM backup_items WHERE backup_id = ?', (backup_id,))
                        conn.execute('DELETE FROM backup_sets WHERE backup_id = ?', (backup_id,))
                        
                        deleted_count += 1
                        self.logger.info(f"Deleted old backup: {backup_id}")
                
                conn.commit()
                
                if deleted_count > 0:
                    self.logger.info(f"Cleanup completed: {deleted_count} backups removed, {freed_space / 1024**2:.1f} MB freed")
                else:
                    self.logger.info("No backups to clean up")
                    
        except Exception as e:
            self.logger.error(f"Backup cleanup failed: {e}")
    
    def schedule_automatic_backup(self, backup_type: str = "incremental", 
                                 interval_hours: int = 24):
        """Schedule automatic backups (runs in background thread)."""
        def backup_worker():
            while True:
                try:
                    time.sleep(interval_hours * 3600)
                    
                    self.logger.info(f"Running scheduled {backup_type} backup...")
                    result = self.create_backup(
                        backup_type=backup_type,
                        description=f"Scheduled automatic {backup_type} backup",
                        compression=True,
                        verify=True
                    )
                    
                    if result.success:
                        self.logger.info("Scheduled backup completed successfully")
                    else:
                        self.logger.error(f"Scheduled backup failed: {result.message}")
                        
                except Exception as e:
                    self.logger.error(f"Scheduled backup error: {e}")
        
        # Start background thread
        backup_thread = threading.Thread(target=backup_worker, daemon=True)
        backup_thread.start()
        
        self.logger.info(f"Scheduled automatic {backup_type} backups every {interval_hours} hours")


def main():
    """Main entry point for backup manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ComBadge Backup Manager")
    parser.add_argument("--path", help="Installation path")
    parser.add_argument("--backup-dir", help="Backup directory")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create backup
    backup_parser = subparsers.add_parser('create', help='Create backup')
    backup_parser.add_argument('--type', choices=['full', 'incremental'], 
                              default='full', help='Backup type')
    backup_parser.add_argument('--description', help='Backup description')
    backup_parser.add_argument('--no-compression', action='store_true', help='Disable compression')
    backup_parser.add_argument('--no-verify', action='store_true', help='Skip verification')
    
    # List backups
    list_parser = subparsers.add_parser('list', help='List backups')
    list_parser.add_argument('--type', help='Filter by backup type')
    
    # Restore backup
    restore_parser = subparsers.add_parser('restore', help='Restore backup')
    restore_parser.add_argument('backup_id', help='Backup ID to restore')
    restore_parser.add_argument('--path', help='Restore path')
    restore_parser.add_argument('--items', nargs='+', help='Selective restore items')
    
    # Cleanup backups
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old backups')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Retention days')
    cleanup_parser.add_argument('--keep', type=int, default=5, help='Minimum backups to keep')
    
    args = parser.parse_args()
    
    # Initialize backup manager
    manager = BackupManager(
        installation_path=Path(args.path) if args.path else None,
        backup_root=Path(args.backup_dir) if args.backup_dir else None
    )
    
    if args.command == 'create':
        result = manager.create_backup(
            backup_type=args.type,
            description=args.description or "",
            compression=not args.no_compression,
            verify=not args.no_verify
        )
        
        if result.success:
            print(f"✅ Backup created: {result.backup_path}")
            print(f"   Duration: {result.duration_seconds:.1f}s")
            print(f"   Size: {result.backup_set.compressed_size_bytes / 1024**2:.1f} MB")
        else:
            print(f"❌ Backup failed: {result.message}")
            sys.exit(1)
    
    elif args.command == 'list':
        backups = manager.list_backups(args.type)
        
        if backups:
            print(f"\n📦 Available Backups ({len(backups)} found):")
            print("-" * 80)
            
            for backup in backups:
                timestamp = datetime.fromisoformat(backup['timestamp'])
                size_mb = backup['compressed_size_bytes'] / 1024**2
                
                print(f"ID: {backup['backup_id']}")
                print(f"   Type: {backup['backup_type']}")
                print(f"   Date: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Size: {size_mb:.1f} MB")
                print(f"   Description: {backup['description']}")
                print()
        else:
            print("No backups found")
    
    elif args.command == 'restore':
        success = manager.restore_backup(
            backup_id=args.backup_id,
            restore_path=Path(args.path) if args.path else None,
            selective_restore=args.items
        )
        
        if success:
            print("✅ Restore completed successfully")
        else:
            print("❌ Restore failed")
            sys.exit(1)
    
    elif args.command == 'cleanup':
        manager.cleanup_old_backups(
            retention_days=args.days,
            keep_min=args.keep
        )
        print("✅ Backup cleanup completed")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()