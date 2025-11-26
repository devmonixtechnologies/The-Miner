"""
Backup and Recovery Manager
Production-grade backup system with automated scheduling and recovery
"""

import os
import json
import gzip
import shutil
import tarfile
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import hashlib
import sqlite3

from utils.production_logger import get_production_logger
from security.encryption import get_security_manager


@dataclass
class BackupMetadata:
    timestamp: float
    backup_type: str
    size_bytes: int
    compressed_size: int
    checksum: str
    description: str
    files_count: int
    encrypted: bool = False


class BackupManager:
    """Production-grade backup and recovery system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_production_logger()
        self.security_manager = get_security_manager()
        
        # Backup configuration
        self.backup_enabled = config.get("backup", {}).get("enable_auto_backup", True)
        self.backup_interval = config.get("backup", {}).get("backup_interval", 86400)  # 24 hours
        self.backup_retention = config.get("backup", {}).get("backup_retention", 7)  # days
        self.backup_dir = Path(config.get("backup", {}).get("backup_dir", "backups"))
        self.compress_backups = config.get("backup", {}).get("compress_backups", True)
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Database for backup tracking
        self.db_path = self.backup_dir / "backups.db"
        self._init_database()
        
        # Backup thread
        self.backup_thread = None
        self.running = False
        
        # Statistics
        self.total_backups = 0
        self.successful_backups = 0
        self.failed_backups = 0
        self.last_backup_time = 0
        
        if self.logger:
            self.logger.log_info("Backup manager initialized", component="backup")
    
    def _init_database(self):
        """Initialize backup tracking database"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS backups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        backup_type TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        compressed_size INTEGER NOT NULL,
                        checksum TEXT NOT NULL,
                        description TEXT,
                        files_count INTEGER,
                        encrypted BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON backups(timestamp)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_backup_type ON backups(backup_type)
                ''')
                
                conn.commit()
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Failed to initialize backup database: {e}", component="backup")
    
    def _record_backup(self, metadata: BackupMetadata, filename: str):
        """Record backup in database"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    INSERT INTO backups 
                    (timestamp, backup_type, filename, size_bytes, compressed_size, 
                     checksum, description, files_count, encrypted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metadata.timestamp,
                    metadata.backup_type,
                    filename,
                    metadata.size_bytes,
                    metadata.compressed_size,
                    metadata.checksum,
                    metadata.description,
                    metadata.files_count,
                    metadata.encrypted
                ))
                conn.commit()
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Failed to record backup: {e}", component="backup")
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _create_backup_filename(self, backup_type: str) -> str:
        """Generate backup filename with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"backup_{backup_type}_{timestamp}.tar.gz"
    
    def backup_configuration(self, description: str = "Manual configuration backup") -> bool:
        """Backup configuration files"""
        try:
            timestamp = time.time()
            filename = self._create_backup_filename("config")
            backup_path = self.backup_dir / filename
            
            # Files to backup
            files_to_backup = []
            config_files = [
                "config/default.conf",
                "config/production.conf"
            ]
            
            for config_file in config_files:
                file_path = Path(config_file)
                if file_path.exists():
                    files_to_backup.append(file_path)
            
            # Include encrypted config if exists
            if self.security_manager:
                encrypted_config = self.security_manager.encrypted_config
                if encrypted_config.exists():
                    files_to_backup.append(encrypted_config)
            
            if not files_to_backup:
                if self.logger:
                    self.logger.log_warning("No configuration files found to backup", component="backup")
                return False
            
            # Create tar archive
            with tarfile.open(backup_path, "w:gz" if self.compress_backups else "w") as tar:
                for file_path in files_to_backup:
                    arcname = file_path.name
                    tar.add(file_path, arcname=arcname)
            
            # Calculate metadata
            original_size = sum(f.stat().st_size for f in files_to_backup)
            compressed_size = backup_path.stat().st_size
            checksum = self._calculate_checksum(backup_path)
            
            metadata = BackupMetadata(
                timestamp=timestamp,
                backup_type="config",
                size_bytes=original_size,
                compressed_size=compressed_size,
                checksum=checksum,
                description=description,
                files_count=len(files_to_backup),
                encrypted=self.security_manager is not None
            )
            
            # Record backup
            self._record_backup(metadata, filename)
            
            self.total_backups += 1
            self.successful_backups += 1
            self.last_backup_time = timestamp
            
            if self.logger:
                self.logger.log_info(
                    f"Configuration backup completed: {filename}",
                    component="backup",
                    backup_type="config",
                    size_bytes=original_size,
                    compressed_size=compressed_size,
                    compression_ratio=compressed_size/original_size if original_size > 0 else 0
                )
            
            return True
            
        except Exception as e:
            self.failed_backups += 1
            if self.logger:
                self.logger.log_error(f"Configuration backup failed: {e}", component="backup")
            return False
    
    def backup_earnings_data(self, description: str = "Earnings data backup") -> bool:
        """Backup earnings and wallet data"""
        try:
            timestamp = time.time()
            filename = self._create_backup_filename("earnings")
            backup_path = self.backup_dir / filename
            
            # Files to backup
            files_to_backup = []
            
            # Earnings data
            earnings_files = [
                "data/earnings.json",
                "data/wallet_data.json",
                "data/mining_stats.json"
            ]
            
            for earnings_file in earnings_files:
                file_path = Path(earnings_file)
                if file_path.exists():
                    files_to_backup.append(file_path)
            
            # Logs (recent ones only)
            log_dir = Path("logs")
            if log_dir.exists():
                # Get logs from last 7 days
                cutoff_time = time.time() - (7 * 24 * 3600)
                for log_file in log_dir.glob("*.log"):
                    if log_file.stat().st_mtime > cutoff_time:
                        files_to_backup.append(log_file)
            
            if not files_to_backup:
                if self.logger:
                    self.logger.log_warning("No earnings data found to backup", component="backup")
                return False
            
            # Create tar archive
            with tarfile.open(backup_path, "w:gz" if self.compress_backups else "w") as tar:
                for file_path in files_to_backup:
                    arcname = str(file_path)
                    tar.add(file_path, arcname=arcname)
            
            # Calculate metadata
            original_size = sum(f.stat().st_size for f in files_to_backup)
            compressed_size = backup_path.stat().st_size
            checksum = self._calculate_checksum(backup_path)
            
            metadata = BackupMetadata(
                timestamp=timestamp,
                backup_type="earnings",
                size_bytes=original_size,
                compressed_size=compressed_size,
                checksum=checksum,
                description=description,
                files_count=len(files_to_backup),
                encrypted=self.security_manager is not None
            )
            
            # Record backup
            self._record_backup(metadata, filename)
            
            self.total_backups += 1
            self.successful_backups += 1
            self.last_backup_time = timestamp
            
            if self.logger:
                self.logger.log_info(
                    f"Earnings backup completed: {filename}",
                    component="backup",
                    backup_type="earnings",
                    size_bytes=original_size,
                    compressed_size=compressed_size
                )
            
            return True
            
        except Exception as e:
            self.failed_backups += 1
            if self.logger:
                self.logger.log_error(f"Earnings backup failed: {e}", component="backup")
            return False
    
    def backup_full_system(self, description: str = "Full system backup") -> bool:
        """Complete system backup"""
        try:
            timestamp = time.time()
            filename = self._create_backup_filename("full")
            backup_path = self.backup_dir / filename
            
            # Files to backup
            files_to_backup = []
            
            # Configuration files
            config_files = [
                "config/default.conf",
                "config/production.conf",
                "main.py",
                "requirements.txt",
                "README.md"
            ]
            
            # Source code
            src_dir = Path("src")
            if src_dir.exists():
                for src_file in src_dir.rglob("*.py"):
                    files_to_backup.append(src_file)
            
            # Data files
            data_dir = Path("data")
            if data_dir.exists():
                for data_file in data_dir.rglob("*"):
                    if data_file.is_file():
                        files_to_backup.append(data_file)
            
            # Security files
            if self.security_manager:
                security_dir = Path.home() / ".miner" / "security"
                if security_dir.exists():
                    for security_file in security_dir.rglob("*"):
                        if security_file.is_file():
                            files_to_backup.append(security_file)
            
            # Recent logs
            log_dir = Path("logs")
            if log_dir.exists():
                cutoff_time = time.time() - (7 * 24 * 3600)
                for log_file in log_dir.glob("*.log*"):
                    if log_file.stat().st_mtime > cutoff_time:
                        files_to_backup.append(log_file)
            
            if not files_to_backup:
                if self.logger:
                    self.logger.log_warning("No files found for full backup", component="backup")
                return False
            
            # Create tar archive
            with tarfile.open(backup_path, "w:gz" if self.compress_backups else "w") as tar:
                for file_path in files_to_backup:
                    # Calculate relative path from current directory
                    try:
                        arcname = str(file_path.relative_to(Path.cwd()))
                    except ValueError:
                        arcname = file_path.name
                    tar.add(file_path, arcname=arcname)
            
            # Calculate metadata
            original_size = sum(f.stat().st_size for f in files_to_backup)
            compressed_size = backup_path.stat().st_size
            checksum = self._calculate_checksum(backup_path)
            
            metadata = BackupMetadata(
                timestamp=timestamp,
                backup_type="full",
                size_bytes=original_size,
                compressed_size=compressed_size,
                checksum=checksum,
                description=description,
                files_count=len(files_to_backup),
                encrypted=self.security_manager is not None
            )
            
            # Record backup
            self._record_backup(metadata, filename)
            
            self.total_backups += 1
            self.successful_backups += 1
            self.last_backup_time = timestamp
            
            if self.logger:
                self.logger.log_info(
                    f"Full system backup completed: {filename}",
                    component="backup",
                    backup_type="full",
                    size_bytes=original_size,
                    compressed_size=compressed_size,
                    files_count=len(files_to_backup)
                )
            
            return True
            
        except Exception as e:
            self.failed_backups += 1
            if self.logger:
                self.logger.log_error(f"Full system backup failed: {e}", component="backup")
            return False
    
    def restore_backup(self, backup_id: int, target_dir: Optional[Path] = None) -> bool:
        """Restore backup from ID"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute('''
                    SELECT filename, backup_type, checksum 
                    FROM backups 
                    WHERE id = ?
                ''', (backup_id,))
                
                result = cursor.fetchone()
                if not result:
                    if self.logger:
                        self.logger.log_error(f"Backup ID {backup_id} not found", component="backup")
                    return False
                
                filename, backup_type, expected_checksum = result
                backup_path = self.backup_dir / filename
                
                if not backup_path.exists():
                    if self.logger:
                        self.logger.log_error(f"Backup file {filename} not found", component="backup")
                    return False
                
                # Verify checksum
                actual_checksum = self._calculate_checksum(backup_path)
                if actual_checksum != expected_checksum:
                    if self.logger:
                        self.logger.log_error(
                            f"Backup checksum mismatch for {filename}",
                            component="backup",
                            expected=expected_checksum,
                            actual=actual_checksum
                        )
                    return False
                
                # Extract backup
                restore_dir = target_dir or Path.cwd()
                with tarfile.open(backup_path, "r:gz" if self.compress_backups else "r") as tar:
                    tar.extractall(restore_dir)
                
                if self.logger:
                    self.logger.log_info(
                        f"Backup {backup_id} restored successfully",
                        component="backup",
                        backup_type=backup_type,
                        restore_dir=str(restore_dir)
                    )
                
                return True
                
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Backup restore failed: {e}", component="backup")
            return False
    
    def list_backups(self, backup_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List available backups"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                query = '''
                    SELECT id, timestamp, backup_type, filename, size_bytes, 
                           compressed_size, description, files_count, encrypted
                    FROM backups
                '''
                params = []
                
                if backup_type:
                    query += ' WHERE backup_type = ?'
                    params.append(backup_type)
                
                query += ' ORDER BY timestamp DESC LIMIT ?'
                params.append(limit)
                
                cursor = conn.execute(query, params)
                
                backups = []
                for row in cursor.fetchall():
                    backup = {
                        "id": row[0],
                        "timestamp": row[1],
                        "datetime": datetime.fromtimestamp(row[1]).strftime("%Y-%m-%d %H:%M:%S"),
                        "backup_type": row[2],
                        "filename": row[3],
                        "size_bytes": row[4],
                        "size_mb": row[4] / (1024 * 1024),
                        "compressed_size": row[5],
                        "compressed_mb": row[5] / (1024 * 1024),
                        "description": row[6],
                        "files_count": row[7],
                        "encrypted": bool(row[8])
                    }
                    backups.append(backup)
                
                return backups
                
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Failed to list backups: {e}", component="backup")
            return []
    
    def cleanup_old_backups(self):
        """Remove old backups based on retention policy"""
        try:
            cutoff_time = time.time() - (self.backup_retention * 24 * 3600)
            
            with sqlite3.connect(str(self.db_path)) as conn:
                # Get old backups
                cursor = conn.execute('''
                    SELECT id, filename FROM backups 
                    WHERE timestamp < ?
                ''', (cutoff_time,))
                
                old_backups = cursor.fetchall()
                removed_count = 0
                
                for backup_id, filename in old_backups:
                    backup_path = self.backup_dir / filename
                    
                    # Delete file
                    if backup_path.exists():
                        backup_path.unlink()
                    
                    # Delete from database
                    conn.execute('DELETE FROM backups WHERE id = ?', (backup_id,))
                    removed_count += 1
                
                conn.commit()
                
                if removed_count > 0 and self.logger:
                    self.logger.log_info(
                        f"Cleaned up {removed_count} old backups",
                        component="backup",
                        cutoff_days=self.backup_retention
                    )
                
                return removed_count
                
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Backup cleanup failed: {e}", component="backup")
            return 0
    
    def start_automated_backups(self):
        """Start automated backup scheduling"""
        if self.backup_thread is None or not self.backup_thread.is_alive():
            self.running = True
            self.backup_thread = threading.Thread(target=self._backup_loop, daemon=True)
            self.backup_thread.start()
            
            if self.logger:
                self.logger.log_info("Automated backups started", component="backup")
    
    def stop_automated_backups(self):
        """Stop automated backup scheduling"""
        self.running = False
        if self.backup_thread:
            self.backup_thread.join(timeout=5)
        
        if self.logger:
            self.logger.log_info("Automated backups stopped", component="backup")
    
    def _backup_loop(self):
        """Main backup scheduling loop"""
        while self.running:
            try:
                current_time = time.time()
                
                # Check if it's time for a backup
                if current_time - self.last_backup_time >= self.backup_interval:
                    # Perform different types of backups in rotation
                    backup_cycle = int(current_time / self.backup_interval) % 3
                    
                    if backup_cycle == 0:
                        self.backup_configuration("Scheduled configuration backup")
                    elif backup_cycle == 1:
                        self.backup_earnings_data("Scheduled earnings backup")
                    else:
                        self.backup_full_system("Scheduled full system backup")
                    
                    # Cleanup old backups
                    self.cleanup_old_backups()
                
                # Sleep for a short interval
                time.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Backup loop error: {e}", component="backup")
                time.sleep(3600)  # Wait longer on error
    
    def get_stats(self) -> Dict[str, Any]:
        """Get backup statistics"""
        return {
            "total_backups": self.total_backups,
            "successful_backups": self.successful_backups,
            "failed_backups": self.failed_backups,
            "success_rate": (self.successful_backups / max(1, self.total_backups)) * 100,
            "last_backup_time": self.last_backup_time,
            "last_backup_datetime": datetime.fromtimestamp(self.last_backup_time).strftime("%Y-%m-%d %H:%M:%S") if self.last_backup_time > 0 else None,
            "backup_enabled": self.backup_enabled,
            "automated_running": self.running,
            "backup_dir": str(self.backup_dir),
            "total_backups_size": sum(f.stat().st_size for f in self.backup_dir.glob("*.tar.gz"))
        }


# Global backup manager instance
_backup_manager = None


def setup_backup_manager(config: Dict[str, Any]) -> BackupManager:
    """Setup backup system"""
    global _backup_manager
    _backup_manager = BackupManager(config)
    return _backup_manager


def get_backup_manager() -> Optional[BackupManager]:
    """Get the backup manager instance"""
    return _backup_manager
