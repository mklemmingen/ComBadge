#!/usr/bin/env python3
"""
ComBadge Cleanup Utility

Comprehensive cleanup and maintenance utility for ComBadge installations.
Handles uninstallation, cache cleanup, temporary file removal, and system cleanup.
"""

import os
import sys
import json
import logging
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import tempfile
import sqlite3


class CleanupLevel(Enum):
    """Cleanup intensity levels."""
    LIGHT = "light"          # Temporary files and caches only
    NORMAL = "normal"        # Standard cleanup with logs and temp data
    DEEP = "deep"           # Complete removal including user data
    NUCLEAR = "nuclear"     # Everything including backups and registry


@dataclass
class CleanupItem:
    """Individual cleanup item definition."""
    name: str
    description: str
    path: str
    item_type: str  # file, directory, registry, process
    level: CleanupLevel
    size_bytes: int = 0
    required: bool = False


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    item: CleanupItem
    success: bool
    message: str
    space_freed_bytes: int = 0
    error: Optional[str] = None


class ComBadgeCleanup:
    """Comprehensive cleanup utility for ComBadge."""
    
    def __init__(self, installation_path: Optional[Path] = None):
        """Initialize cleanup utility."""
        self.installation_path = installation_path or self._detect_installation_path()
        
        # Common paths
        self.app_data_path = Path(os.getenv('APPDATA', '')) / "ComBadge" if os.name == 'nt' else Path.home() / ".combadge"
        self.local_app_data_path = Path(os.getenv('LOCALAPPDATA', '')) / "ComBadge" if os.name == 'nt' else Path.home() / ".local/share/combadge"
        self.temp_path = Path(tempfile.gettempdir()) / "ComBadge"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Track cleanup statistics
        self.total_space_freed = 0
        self.items_cleaned = 0
        self.errors_encountered = 0
        
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
    
    def scan_cleanup_items(self, level: CleanupLevel = CleanupLevel.NORMAL) -> List[CleanupItem]:
        """Scan system for cleanup items based on level."""
        self.logger.info(f"Scanning for cleanup items (level: {level.value})...")
        
        items = []
        
        # Temporary files (all levels)
        items.extend(self._scan_temporary_files())
        
        # Cache files (all levels)
        items.extend(self._scan_cache_files())
        
        # Log files (normal and above)
        if level.value in ['normal', 'deep', 'nuclear']:
            items.extend(self._scan_log_files())
        
        # User data (deep and above)
        if level.value in ['deep', 'nuclear']:
            items.extend(self._scan_user_data())
        
        # Application files (nuclear only)
        if level == CleanupLevel.NUCLEAR:
            items.extend(self._scan_application_files())
            items.extend(self._scan_registry_entries())
        
        # Calculate sizes
        for item in items:
            item.size_bytes = self._calculate_item_size(item)
        
        self.logger.info(f"Found {len(items)} cleanup items")
        return items
    
    def _scan_temporary_files(self) -> List[CleanupItem]:
        """Scan for temporary files."""
        items = []
        
        # System temp directory
        temp_dirs = [
            self.temp_path,
            self.installation_path / "temp",
            self.installation_path / "tmp",
            Path(tempfile.gettempdir()) / "combadge_*",
        ]
        
        for temp_dir in temp_dirs:
            if temp_dir.exists():
                items.append(CleanupItem(
                    name=f"temp_dir_{temp_dir.name}",
                    description=f"Temporary directory: {temp_dir}",
                    path=str(temp_dir),
                    item_type="directory",
                    level=CleanupLevel.LIGHT
                ))
        
        # Temporary files in installation directory
        if self.installation_path.exists():
            temp_patterns = ["*.tmp", "*.temp", "*.bak", "*.old", "*.log~"]
            for pattern in temp_patterns:
                for temp_file in self.installation_path.rglob(pattern):
                    items.append(CleanupItem(
                        name=f"temp_file_{temp_file.name}",
                        description=f"Temporary file: {temp_file}",
                        path=str(temp_file),
                        item_type="file",
                        level=CleanupLevel.LIGHT
                    ))
        
        return items
    
    def _scan_cache_files(self) -> List[CleanupItem]:
        """Scan for cache files."""
        items = []
        
        cache_dirs = [
            self.installation_path / "cache",
            self.installation_path / "__pycache__",
            self.local_app_data_path / "cache",
            self.app_data_path / "cache",
        ]
        
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                items.append(CleanupItem(
                    name=f"cache_dir_{cache_dir.name}",
                    description=f"Cache directory: {cache_dir}",
                    path=str(cache_dir),
                    item_type="directory",
                    level=CleanupLevel.LIGHT
                ))
        
        # Python cache files
        if self.installation_path.exists():
            for pycache_dir in self.installation_path.rglob("__pycache__"):
                items.append(CleanupItem(
                    name=f"pycache_{pycache_dir.parent.name}",
                    description=f"Python cache: {pycache_dir}",
                    path=str(pycache_dir),
                    item_type="directory",
                    level=CleanupLevel.LIGHT
                ))
        
        return items
    
    def _scan_log_files(self) -> List[CleanupItem]:
        """Scan for log files."""
        items = []
        
        log_dirs = [
            self.installation_path / "logs",
            self.app_data_path / "logs",
            self.local_app_data_path / "logs",
        ]
        
        for log_dir in log_dirs:
            if log_dir.exists():
                # Add individual log files
                for log_file in log_dir.rglob("*.log"):
                    items.append(CleanupItem(
                        name=f"log_file_{log_file.name}",
                        description=f"Log file: {log_file}",
                        path=str(log_file),
                        item_type="file",
                        level=CleanupLevel.NORMAL
                    ))
                
                # Add log directories if empty after file cleanup
                items.append(CleanupItem(
                    name=f"log_dir_{log_dir.name}",
                    description=f"Log directory: {log_dir}",
                    path=str(log_dir),
                    item_type="directory",
                    level=CleanupLevel.NORMAL
                ))
        
        return items
    
    def _scan_user_data(self) -> List[CleanupItem]:
        """Scan for user data files."""
        items = []
        
        user_data_items = [
            (self.installation_path / "data" / "user_preferences.json", "User preferences"),
            (self.installation_path / "data" / "recent_files.json", "Recent files list"),
            (self.installation_path / "data" / "session_data.db", "Session database"),
            (self.app_data_path, "AppData directory"),
            (self.local_app_data_path, "Local AppData directory"),
        ]
        
        for path, description in user_data_items:
            if path.exists():
                items.append(CleanupItem(
                    name=f"user_data_{path.name}",
                    description=description,
                    path=str(path),
                    item_type="file" if path.is_file() else "directory",
                    level=CleanupLevel.DEEP
                ))
        
        return items
    
    def _scan_application_files(self) -> List[CleanupItem]:
        """Scan for application files (complete uninstall)."""
        items = []
        
        if self.installation_path.exists():
            items.append(CleanupItem(
                name="installation_directory",
                description=f"Complete installation directory: {self.installation_path}",
                path=str(self.installation_path),
                item_type="directory",
                level=CleanupLevel.NUCLEAR
            ))
        
        # Desktop shortcuts
        desktop = Path.home() / "Desktop"
        shortcuts = [
            desktop / "ComBadge.lnk",
            Path(os.getenv('PUBLIC', '')) / "Desktop" / "ComBadge.lnk" if os.name == 'nt' else None
        ]
        
        for shortcut in shortcuts:
            if shortcut and shortcut.exists():
                items.append(CleanupItem(
                    name=f"shortcut_{shortcut.name}",
                    description=f"Desktop shortcut: {shortcut}",
                    path=str(shortcut),
                    item_type="file",
                    level=CleanupLevel.NUCLEAR
                ))
        
        # Start menu shortcuts (Windows)
        if os.name == 'nt':
            start_menu_dirs = [
                Path(os.getenv('APPDATA', '')) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "ComBadge",
                Path(os.getenv('PROGRAMDATA', '')) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "ComBadge"
            ]
            
            for start_dir in start_menu_dirs:
                if start_dir.exists():
                    items.append(CleanupItem(
                        name=f"start_menu_{start_dir.parent.name}",
                        description=f"Start Menu folder: {start_dir}",
                        path=str(start_dir),
                        item_type="directory",
                        level=CleanupLevel.NUCLEAR
                    ))
        
        return items
    
    def _scan_registry_entries(self) -> List[CleanupItem]:
        """Scan for Windows registry entries."""
        items = []
        
        if os.name != 'nt':
            return items
        
        registry_keys = [
            r"HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\ComBadge",
            r"HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\ComBadge.exe",
            r"HKEY_CURRENT_USER\\SOFTWARE\\ComBadge",
            r"HKEY_LOCAL_MACHINE\\SOFTWARE\\ComBadge",
        ]
        
        for reg_key in registry_keys:
            items.append(CleanupItem(
                name=f"registry_{reg_key.split('\\\\')[-1]}",
                description=f"Registry key: {reg_key}",
                path=reg_key,
                item_type="registry",
                level=CleanupLevel.NUCLEAR
            ))
        
        return items
    
    def _calculate_item_size(self, item: CleanupItem) -> int:
        """Calculate size of cleanup item in bytes."""
        try:
            if item.item_type == "registry":
                return 0  # Registry entries don't have meaningful size
            
            path = Path(item.path)
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
    
    def cleanup_item(self, item: CleanupItem, dry_run: bool = False) -> CleanupResult:
        """Clean up a single item."""
        if dry_run:
            return CleanupResult(
                item=item,
                success=True,
                message=f"Would clean: {item.description}",
                space_freed_bytes=item.size_bytes
            )
        
        try:
            if item.item_type == "file":
                return self._cleanup_file(item)
            elif item.item_type == "directory":
                return self._cleanup_directory(item)
            elif item.item_type == "registry":
                return self._cleanup_registry(item)
            elif item.item_type == "process":
                return self._cleanup_process(item)
            else:
                return CleanupResult(
                    item=item,
                    success=False,
                    message=f"Unknown item type: {item.item_type}"
                )
                
        except Exception as e:
            return CleanupResult(
                item=item,
                success=False,
                message=f"Cleanup failed: {str(e)}",
                error=str(e)
            )
    
    def _cleanup_file(self, item: CleanupItem) -> CleanupResult:
        """Clean up a file."""
        file_path = Path(item.path)
        
        if not file_path.exists():
            return CleanupResult(
                item=item,
                success=True,
                message="File already removed",
                space_freed_bytes=0
            )
        
        try:
            size_before = file_path.stat().st_size
            file_path.unlink()
            
            return CleanupResult(
                item=item,
                success=True,
                message=f"File removed: {file_path}",
                space_freed_bytes=size_before
            )
            
        except PermissionError:
            return CleanupResult(
                item=item,
                success=False,
                message="Permission denied",
                error="PermissionError"
            )
        except Exception as e:
            return CleanupResult(
                item=item,
                success=False,
                message=f"Failed to remove file: {e}",
                error=str(e)
            )
    
    def _cleanup_directory(self, item: CleanupItem) -> CleanupResult:
        """Clean up a directory."""
        dir_path = Path(item.path)
        
        if not dir_path.exists():
            return CleanupResult(
                item=item,
                success=True,
                message="Directory already removed",
                space_freed_bytes=0
            )
        
        try:
            size_before = item.size_bytes or self._calculate_item_size(item)
            
            # Try to remove directory
            if dir_path.is_dir():
                shutil.rmtree(dir_path)
            else:
                dir_path.unlink()
            
            return CleanupResult(
                item=item,
                success=True,
                message=f"Directory removed: {dir_path}",
                space_freed_bytes=size_before
            )
            
        except PermissionError:
            return CleanupResult(
                item=item,
                success=False,
                message="Permission denied",
                error="PermissionError"
            )
        except Exception as e:
            return CleanupResult(
                item=item,
                success=False,
                message=f"Failed to remove directory: {e}",
                error=str(e)
            )
    
    def _cleanup_registry(self, item: CleanupItem) -> CleanupResult:
        """Clean up a Windows registry entry."""
        if os.name != 'nt':
            return CleanupResult(
                item=item,
                success=True,
                message="Registry cleanup skipped (non-Windows)",
                space_freed_bytes=0
            )
        
        try:
            # Use reg.exe to delete registry key
            cmd = ['reg', 'delete', item.path, '/f']
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return CleanupResult(
                    item=item,
                    success=True,
                    message=f"Registry key removed: {item.path}",
                    space_freed_bytes=0
                )
            else:
                return CleanupResult(
                    item=item,
                    success=False,
                    message=f"Registry deletion failed: {result.stderr}",
                    error=result.stderr
                )
                
        except subprocess.TimeoutExpired:
            return CleanupResult(
                item=item,
                success=False,
                message="Registry deletion timed out",
                error="Timeout"
            )
        except Exception as e:
            return CleanupResult(
                item=item,
                success=False,
                message=f"Registry cleanup error: {e}",
                error=str(e)
            )
    
    def _cleanup_process(self, item: CleanupItem) -> CleanupResult:
        """Clean up a running process."""
        try:
            if os.name == 'nt':
                # Windows process termination
                cmd = ['taskkill', '/F', '/IM', item.path]
            else:
                # Unix process termination
                cmd = ['pkill', '-f', item.path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return CleanupResult(
                    item=item,
                    success=True,
                    message=f"Process terminated: {item.path}",
                    space_freed_bytes=0
                )
            else:
                return CleanupResult(
                    item=item,
                    success=True,  # Process might not be running
                    message=f"Process not found or already terminated",
                    space_freed_bytes=0
                )
                
        except Exception as e:
            return CleanupResult(
                item=item,
                success=False,
                message=f"Process cleanup error: {e}",
                error=str(e)
            )
    
    def perform_cleanup(self, level: CleanupLevel = CleanupLevel.NORMAL, 
                       dry_run: bool = False, 
                       interactive: bool = True) -> List[CleanupResult]:
        """Perform comprehensive cleanup."""
        self.logger.info(f"Starting cleanup (level: {level.value}, dry_run: {dry_run})...")
        
        # Scan for cleanup items
        items = self.scan_cleanup_items(level)
        
        if not items:
            self.logger.info("No cleanup items found")
            return []
        
        # Calculate total space to be freed
        total_space = sum(item.size_bytes for item in items)
        self.logger.info(f"Found {len(items)} items, {total_space / 1024**2:.1f} MB to be freed")
        
        # Interactive confirmation
        if interactive and not dry_run:
            print("\nCleanup Items:")
            print("-" * 60)
            for i, item in enumerate(items, 1):
                size_mb = item.size_bytes / 1024**2
                print(f"{i:2d}. {item.description} ({size_mb:.1f} MB)")
            
            print(f"\nTotal space to free: {total_space / 1024**2:.1f} MB")
            response = input("\nProceed with cleanup? (y/N): ").lower()
            
            if response != 'y':
                self.logger.info("Cleanup cancelled by user")
                return []
        
        # Stop ComBadge processes before cleanup
        if not dry_run:
            self._stop_combadge_processes()
        
        # Perform cleanup
        results = []
        for item in items:
            self.logger.info(f"Cleaning: {item.description}")
            
            result = self.cleanup_item(item, dry_run)
            results.append(result)
            
            if result.success:
                self.items_cleaned += 1
                self.total_space_freed += result.space_freed_bytes
            else:
                self.errors_encountered += 1
                self.logger.error(f"Failed to clean {item.name}: {result.message}")
        
        # Log summary
        space_freed_mb = self.total_space_freed / 1024**2
        self.logger.info(f"Cleanup completed: {self.items_cleaned} items, {space_freed_mb:.1f} MB freed")
        
        if self.errors_encountered > 0:
            self.logger.warning(f"Encountered {self.errors_encountered} errors during cleanup")
        
        return results
    
    def _stop_combadge_processes(self):
        """Stop all ComBadge processes."""
        try:
            if os.name == 'nt':
                # Stop ComBadge processes on Windows
                subprocess.run(['taskkill', '/F', '/IM', 'ComBadge.exe'], 
                              capture_output=True, timeout=30)
                subprocess.run(['taskkill', '/F', '/IM', 'python.exe', '/FI', 'WINDOWTITLE eq ComBadge*'], 
                              capture_output=True, timeout=30)
            else:
                # Stop ComBadge processes on Unix
                subprocess.run(['pkill', '-f', 'combadge'], 
                              capture_output=True, timeout=30)
            
            # Wait for processes to terminate
            time.sleep(2)
            
        except Exception as e:
            self.logger.warning(f"Could not stop ComBadge processes: {e}")
    
    def generate_cleanup_report(self, results: List[CleanupResult]) -> Dict:
        """Generate comprehensive cleanup report."""
        report = {
            "cleanup_timestamp": time.time(),
            "cleanup_summary": {
                "total_items": len(results),
                "successful_cleanups": sum(1 for r in results if r.success),
                "failed_cleanups": sum(1 for r in results if not r.success),
                "total_space_freed_bytes": sum(r.space_freed_bytes for r in results),
                "total_space_freed_mb": sum(r.space_freed_bytes for r in results) / 1024**2
            },
            "cleanup_details": []
        }
        
        for result in results:
            report["cleanup_details"].append({
                "name": result.item.name,
                "description": result.item.description,
                "path": result.item.path,
                "type": result.item.item_type,
                "level": result.item.level.value,
                "success": result.success,
                "message": result.message,
                "space_freed_bytes": result.space_freed_bytes,
                "error": result.error
            })
        
        return report
    
    def uninstall_combadge(self, keep_user_data: bool = True) -> bool:
        """Complete ComBadge uninstallation."""
        self.logger.info("Starting ComBadge uninstallation...")
        
        try:
            # Stop all processes
            self._stop_combadge_processes()
            
            # Use Windows uninstaller if available
            if os.name == 'nt':
                uninstaller_path = self.installation_path / "uninstall.exe"
                if uninstaller_path.exists():
                    self.logger.info("Running Windows uninstaller...")
                    result = subprocess.run([str(uninstaller_path), '/S'], timeout=300)
                    if result.returncode == 0:
                        self.logger.info("Windows uninstaller completed successfully")
                        return True
            
            # Manual uninstallation
            cleanup_level = CleanupLevel.DEEP if keep_user_data else CleanupLevel.NUCLEAR
            results = self.perform_cleanup(level=cleanup_level, dry_run=False, interactive=False)
            
            success_count = sum(1 for r in results if r.success)
            total_count = len(results)
            
            if success_count == total_count:
                self.logger.info("Manual uninstallation completed successfully")
                return True
            else:
                self.logger.warning(f"Partial uninstallation: {success_count}/{total_count} items removed")
                return False
                
        except Exception as e:
            self.logger.error(f"Uninstallation failed: {e}")
            return False


def main():
    """Main entry point for cleanup utility."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ComBadge Cleanup Utility")
    parser.add_argument("--level", choices=["light", "normal", "deep", "nuclear"],
                       default="normal", help="Cleanup level")
    parser.add_argument("--path", help="Installation path to clean")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cleaned without doing it")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")
    parser.add_argument("--uninstall", action="store_true", help="Complete uninstallation")
    parser.add_argument("--keep-user-data", action="store_true", help="Keep user data during uninstall")
    parser.add_argument("--report", help="Save cleanup report to file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize cleanup utility
    cleanup = ComBadgeCleanup(
        installation_path=Path(args.path) if args.path else None
    )
    
    try:
        if args.uninstall:
            # Complete uninstallation
            if not args.yes:
                response = input("Are you sure you want to uninstall ComBadge? (y/N): ").lower()
                if response != 'y':
                    print("Uninstallation cancelled")
                    sys.exit(0)
            
            success = cleanup.uninstall_combadge(keep_user_data=args.keep_user_data)
            if success:
                print("✅ ComBadge uninstalled successfully")
                sys.exit(0)
            else:
                print("❌ Uninstallation completed with errors")
                sys.exit(1)
        
        else:
            # Regular cleanup
            level = CleanupLevel(args.level)
            interactive = not args.yes
            
            results = cleanup.perform_cleanup(
                level=level,
                dry_run=args.dry_run,
                interactive=interactive
            )
            
            # Generate report
            if args.report:
                report = cleanup.generate_cleanup_report(results)
                with open(args.report, 'w') as f:
                    json.dump(report, f, indent=2)
                print(f"Cleanup report saved to: {args.report}")
            
            # Print summary
            if results:
                successful = sum(1 for r in results if r.success)
                space_freed = sum(r.space_freed_bytes for r in results) / 1024**2
                
                if args.dry_run:
                    print(f"\n📋 Dry run completed: {len(results)} items found, {space_freed:.1f} MB would be freed")
                else:
                    print(f"\n✅ Cleanup completed: {successful}/{len(results)} items cleaned, {space_freed:.1f} MB freed")
                
                if successful < len(results):
                    print("⚠️  Some items could not be cleaned (check logs for details)")
            else:
                print("✨ No cleanup needed - system is clean!")
    
    except KeyboardInterrupt:
        print("\n🛑 Cleanup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()