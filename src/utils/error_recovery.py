"""
Error Handling and Recovery System
Production-grade error management with automatic recovery
"""

import time
import threading
import traceback
import signal
import sys
import os
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json
import psutil

from utils.production_logger import get_production_logger


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorEvent:
    timestamp: float
    severity: ErrorSeverity
    component: str
    message: str
    exception: Optional[Exception]
    traceback_str: str
    recovery_attempts: int = 0
    resolved: bool = False


class RecoveryAction:
    """Base class for recovery actions"""
    
    def __init__(self, name: str, max_attempts: int = 3, cooldown: float = 60.0):
        self.name = name
        self.max_attempts = max_attempts
        self.cooldown = cooldown
        self.last_attempt = 0.0
        self.success_count = 0
        self.failure_count = 0
    
    def can_attempt(self) -> bool:
        """Check if recovery action can be attempted"""
        return (time.time() - self.last_attempt > self.cooldown and
                self.failure_count < self.max_attempts)
    
    def execute(self, error: ErrorEvent) -> bool:
        """Execute recovery action"""
        if not self.can_attempt():
            return False
        
        self.last_attempt = time.time()
        try:
            success = self._recover(error)
            if success:
                self.success_count += 1
                return True
            else:
                self.failure_count += 1
                return False
        except Exception as e:
            self.failure_count += 1
            raise e
    
    def _recover(self, error: ErrorEvent) -> bool:
        """Override this method to implement specific recovery logic"""
        raise NotImplementedError


class RestartMinerRecovery(RecoveryAction):
    """Recovery action for restarting the miner"""
    
    def __init__(self, miner_instance):
        super().__init__("restart_miner", max_attempts=3, cooldown=30.0)
        self.miner_instance = miner_instance
    
    def _recover(self, error: ErrorEvent) -> bool:
        """Restart the miner"""
        try:
            if self.miner_instance:
                # Stop miner
                if hasattr(self.miner_instance, 'stop'):
                    self.miner_instance.stop()
                    time.sleep(2)
                
                # Start miner
                if hasattr(self.miner_instance, 'start'):
                    self.miner_instance.start()
                    time.sleep(2)
                
                return True
        except Exception as e:
            logger = get_production_logger()
            if logger:
                logger.log_error(f"Failed to restart miner: {e}", component="recovery")
        return False


class ReconnectWalletRecovery(RecoveryAction):
    """Recovery action for reconnecting wallet"""
    
    def __init__(self, wallet_manager):
        super().__init__("reconnect_wallet", max_attempts=5, cooldown=10.0)
        self.wallet_manager = wallet_manager
    
    def _recover(self, error: ErrorEvent) -> bool:
        """Reconnect wallet"""
        try:
            if self.wallet_manager:
                # Reinitialize wallet connection
                if hasattr(self.wallet_manager, 'reconnect'):
                    return self.wallet_manager.reconnect()
            return False
        except Exception as e:
            logger = get_production_logger()
            if logger:
                logger.log_error(f"Failed to reconnect wallet: {e}", component="recovery")
        return False


class ClearCacheRecovery(RecoveryAction):
    """Recovery action for clearing system cache"""
    
    def __init__(self):
        super().__init__("clear_cache", max_attempts=10, cooldown=5.0)
    
    def _recover(self, error: ErrorEvent) -> bool:
        """Clear system cache and garbage collect"""
        try:
            import gc
            gc.collect()
            
            # Clear any file-based caches
            cache_dirs = ["/tmp", "/var/tmp"]
            for cache_dir in cache_dirs:
                if os.path.exists(cache_dir):
                    for file in Path(cache_dir).glob("miner_*"):
                        try:
                            file.unlink()
                        except:
                            pass
            
            return True
        except Exception as e:
            logger = get_production_logger()
            if logger:
                logger.log_error(f"Failed to clear cache: {e}", component="recovery")
        return False


class ReduceResourceUsageRecovery(RecoveryAction):
    """Recovery action for reducing resource usage"""
    
    def __init__(self, miner_instance):
        super().__init__("reduce_resources", max_attempts=3, cooldown=60.0)
        self.miner_instance = miner_instance
    
    def _recover(self, error: ErrorEvent) -> bool:
        """Reduce CPU threads and intensity"""
        try:
            if self.miner_instance and hasattr(self.miner_instance, 'config'):
                config = self.miner_instance.config
                
                # Reduce CPU threads
                if hasattr(config, 'cpu_threads') and config.cpu_threads > 1:
                    config.cpu_threads = max(1, config.cpu_threads // 2)
                
                # Reduce intensity
                if hasattr(config, 'intensity') and config.intensity > 0.5:
                    config.intensity *= 0.8
                
                return True
        except Exception as e:
            logger = get_production_logger()
            if logger:
                logger.log_error(f"Failed to reduce resource usage: {e}", component="recovery")
        return False


class ErrorRecoveryManager:
    """Production-grade error recovery manager"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_production_logger()
        
        # Error tracking
        self.error_history: List[ErrorEvent] = []
        self.max_history = 1000
        self.error_patterns: Dict[str, int] = {}
        
        # Recovery actions
        self.recovery_actions: List[RecoveryAction] = []
        self.component_recoveries: Dict[str, List[RecoveryAction]] = {}
        
        # Monitoring
        self.monitoring_thread = None
        self.running = False
        self.check_interval = 30.0
        
        # Statistics
        self.total_errors = 0
        self.resolved_errors = 0
        self.critical_errors = 0
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        if self.logger:
            self.logger.log_info("Error recovery manager initialized", component="recovery")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    def register_recovery_action(self, action: RecoveryAction, component: str = "general"):
        """Register a recovery action for a component"""
        self.recovery_actions.append(action)
        
        if component not in self.component_recoveries:
            self.component_recoveries[component] = []
        self.component_recoveries[component].append(action)
        
        if self.logger:
            self.logger.log_info(f"Registered recovery action: {action.name} for {component}", 
                              component="recovery")
    
    def handle_error(self, component: str, error: Exception, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        """Handle an error with automatic recovery"""
        self.total_errors += 1
        
        if severity == ErrorSeverity.CRITICAL:
            self.critical_errors += 1
        
        # Create error event
        error_event = ErrorEvent(
            timestamp=time.time(),
            severity=severity,
            component=component,
            message=str(error),
            exception=error,
            traceback_str=traceback.format_exc()
        )
        
        # Track error patterns
        error_type = type(error).__name__
        self.error_patterns[error_type] = self.error_patterns.get(error_type, 0) + 1
        
        # Log error
        if self.logger:
            self.logger.log_error(
                f"Error in {component}: {error}",
                component=component,
                error_type=error_type,
                severity=severity.value,
                traceback=error_event.traceback_str
            )
        
        # Add to history
        self.error_history.append(error_event)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
        
        # Attempt recovery
        if self._should_attempt_recovery(error_event):
            self._attempt_recovery(error_event)
        
        # Check for system-wide issues
        self._check_system_health()
    
    def _should_attempt_recovery(self, error: ErrorEvent) -> bool:
        """Determine if recovery should be attempted"""
        # Don't recover from critical errors immediately
        if error.severity == ErrorSeverity.CRITICAL:
            return False
        
        # Check if too many recent errors
        recent_errors = [e for e in self.error_history 
                        if time.time() - e.timestamp < 300]  # Last 5 minutes
        
        if len(recent_errors) > 10:
            return False
        
        return True
    
    def _attempt_recovery(self, error: ErrorEvent):
        """Attempt recovery for an error"""
        component_actions = self.component_recoveries.get(error.component, [])
        general_actions = self.component_recoveries.get("general", [])
        
        # Try component-specific actions first
        for action in component_actions:
            if action.can_attempt():
                try:
                    if action.execute(error):
                        error.resolved = True
                        self.resolved_errors += 1
                        error.recovery_attempts += 1
                        
                        if self.logger:
                            self.logger.log_info(
                                f"Successfully recovered from error using {action.name}",
                                component="recovery",
                                error_component=error.component,
                                recovery_action=action.name
                            )
                        return
                except Exception as e:
                    if self.logger:
                        self.logger.log_error(f"Recovery action {action.name} failed: {e}", 
                                          component="recovery")
        
        # Try general actions
        for action in general_actions:
            if action.can_attempt():
                try:
                    if action.execute(error):
                        error.resolved = True
                        self.resolved_errors += 1
                        error.recovery_attempts += 1
                        
                        if self.logger:
                            self.logger.log_info(
                                f"Successfully recovered from error using {action.name}",
                                component="recovery",
                                error_component=error.component,
                                recovery_action=action.name
                            )
                        return
                except Exception as e:
                    if self.logger:
                        self.logger.log_error(f"Recovery action {action.name} failed: {e}", 
                                          component="recovery")
    
    def _check_system_health(self):
        """Check overall system health"""
        try:
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                self.handle_error("system", 
                                Exception(f"High memory usage: {memory.percent}%"),
                                ErrorSeverity.HIGH)
            
            # Check CPU usage
            cpu = psutil.cpu_percent(interval=1)
            if cpu > 95:
                self.handle_error("system",
                                Exception(f"High CPU usage: {cpu}%"),
                                ErrorSeverity.HIGH)
            
            # Check disk space
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                self.handle_error("system",
                                Exception(f"Low disk space: {disk.percent}% used"),
                                ErrorSeverity.HIGH)
                
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"System health check failed: {e}", component="recovery")
    
    def start_monitoring(self):
        """Start background monitoring"""
        if self.monitoring_thread is None or not self.monitoring_thread.is_alive():
            self.running = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            if self.logger:
                self.logger.log_info("Error recovery monitoring started", component="recovery")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        if self.logger:
            self.logger.log_info("Error recovery monitoring stopped", component="recovery")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                self._check_system_health()
                time.sleep(self.check_interval)
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Monitoring loop error: {e}", component="recovery")
                time.sleep(60)  # Wait longer on error
    
    def get_stats(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        return {
            "total_errors": self.total_errors,
            "resolved_errors": self.resolved_errors,
            "critical_errors": self.critical_errors,
            "recovery_rate": (self.resolved_errors / max(1, self.total_errors)) * 100,
            "error_patterns": self.error_patterns,
            "recovery_actions": [
                {
                    "name": action.name,
                    "success_count": action.success_count,
                    "failure_count": action.failure_count,
                    "can_attempt": action.can_attempt()
                }
                for action in self.recovery_actions
            ]
        }
    
    def shutdown(self):
        """Graceful shutdown"""
        self.stop_monitoring()
        
        if self.logger:
            self.logger.log_info("Error recovery manager shutdown", component="recovery",
                              stats=self.get_stats())


# Global recovery manager instance
_recovery_manager = None


def setup_error_recovery(config: Dict[str, Any]) -> ErrorRecoveryManager:
    """Setup error recovery system"""
    global _recovery_manager
    _recovery_manager = ErrorRecoveryManager(config)
    return _recovery_manager


def get_recovery_manager() -> Optional[ErrorRecoveryManager]:
    """Get the recovery manager instance"""
    return _recovery_manager


def handle_error(component: str, error: Exception, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """Handle an error (convenience function)"""
    if _recovery_manager:
        _recovery_manager.handle_error(component, error, severity)
