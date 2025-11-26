"""
Production Logging System
Structured, high-performance logging with rotation and monitoring
"""

import logging
import logging.handlers
import json
import time
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import threading
import traceback


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for production logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": threading.current_thread().name,
            "process": os.getpid()
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                          'pathname', 'filename', 'module', 'lineno', 
                          'funcName', 'created', 'msecs', 'relativeCreated', 
                          'thread', 'threadName', 'processName', 'process',
                          'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry)


class ProductionLogger:
    """Production-grade logging system with monitoring and alerting"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.log_dir = Path(config.get("log_dir", "logs"))
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup loggers
        self.loggers = {}
        self._setup_main_logger()
        self._setup_specialized_loggers()
        
        # Monitoring
        self.error_count = 0
        self.warning_count = 0
        self.last_alert_time = 0
        self.alert_threshold = config.get("alert_threshold", 10)
        self.alert_cooldown = 300  # 5 minutes
        
        logger.info("Production logging system initialized")
    
    def _setup_main_logger(self):
        """Setup the main application logger"""
        main_logger = logging.getLogger("miner")
        main_logger.setLevel(getattr(logging, self.config.get("level", "INFO")))
        
        # Clear existing handlers
        main_logger.handlers.clear()
        
        # Console handler with simple format
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        main_logger.addHandler(console_handler)
        
        # Structured file handler
        if self.config.get("enable_structured_logging", True):
            structured_file = self.log_dir / "miner.log"
            structured_handler = logging.handlers.RotatingFileHandler(
                structured_file,
                maxBytes=self._parse_size(self.config.get("max_log_size", "50MB")),
                backupCount=self.config.get("backup_count", 5),
                encoding='utf-8'
            )
            structured_handler.setFormatter(StructuredFormatter())
            structured_handler.setLevel(logging.INFO)
            main_logger.addHandler(structured_handler)
        
        # Error-only file handler
        error_file = self.log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=self._parse_size(self.config.get("max_log_size", "50MB")),
            backupCount=self.config.get("backup_count", 5),
            encoding='utf-8'
        )
        error_handler.setFormatter(StructuredFormatter())
        error_handler.setLevel(logging.ERROR)
        main_logger.addHandler(error_handler)
        
        self.loggers["main"] = main_logger
    
    def _setup_specialized_loggers(self):
        """Setup specialized loggers for different components"""
        components = ["mining", "wallet", "performance", "security", "system"]
        
        for component in components:
            logger = logging.getLogger(f"miner.{component}")
            logger.setLevel(logging.INFO)
            
            # Component-specific file handler
            log_file = self.log_dir / f"{component}.log"
            handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self._parse_size(self.config.get("max_log_size", "50MB")),
                backupCount=self.config.get("backup_count", 5),
                encoding='utf-8'
            )
            
            if self.config.get("enable_structured_logging", True):
                handler.setFormatter(StructuredFormatter())
            else:
                handler.setFormatter(logging.Formatter(
                    '%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                ))
            
            logger.addHandler(handler)
            logger.propagate = False
            self.loggers[component] = logger
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '50MB' to bytes"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger by name"""
        if name in self.loggers:
            return self.loggers[name]
        elif name.startswith("miner."):
            component = name.split(".", 1)[1]
            if component in self.loggers:
                return self.loggers[component]
        return self.loggers["main"]
    
    def log_error(self, message: str, component: str = "main", **kwargs):
        """Log an error with monitoring"""
        logger = self.get_logger(component)
        logger.error(message, extra=kwargs)
        
        self.error_count += 1
        self._check_alert_threshold()
    
    def log_warning(self, message: str, component: str = "main", **kwargs):
        """Log a warning with monitoring"""
        logger = self.get_logger(component)
        logger.warning(message, extra=kwargs)
        
        self.warning_count += 1
        self._check_alert_threshold()
    
    def log_performance(self, metric: str, value: float, unit: str = "", **kwargs):
        """Log performance metrics"""
        if self.config.get("enable_performance_logging", True):
            logger = self.get_logger("performance")
            logger.info(
                f"Performance: {metric}={value}{unit}",
                extra={
                    "metric": metric,
                    "value": value,
                    "unit": unit,
                    **kwargs
                }
            )
    
    def log_security_event(self, event: str, severity: str = "INFO", **kwargs):
        """Log security events"""
        logger = self.get_logger("security")
        log_method = getattr(logger, severity.lower(), logger.info)
        log_method(
            f"Security: {event}",
            extra={
                "security_event": event,
                "severity": severity,
                **kwargs
            }
        )
    
    def _check_alert_threshold(self):
        """Check if alert threshold is exceeded"""
        current_time = time.time()
        if (current_time - self.last_alert_time > self.alert_cooldown and
            (self.error_count >= self.alert_threshold or 
             self.warning_count >= self.alert_threshold * 2)):
            
            self.log_error(
                "Alert threshold exceeded",
                component="system",
                error_count=self.error_count,
                warning_count=self.warning_count,
                alert_threshold=self.alert_threshold
            )
            self.last_alert_time = current_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        return {
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "last_alert_time": self.last_alert_time,
            "log_dir": str(self.log_dir),
            "configured_loggers": list(self.loggers.keys())
        }
    
    def cleanup_old_logs(self, days: int = 30):
        """Clean up old log files"""
        cutoff_time = time.time() - (days * 24 * 3600)
        
        for log_file in self.log_dir.rglob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    self.loggers["main"].info(f"Cleaned up old log file: {log_file}")
                except Exception as e:
                    self.loggers["main"].error(f"Failed to clean up {log_file}: {e}")


# Global production logger instance
_production_logger = None


def setup_production_logging(config: Dict[str, Any]) -> ProductionLogger:
    """Setup production logging system"""
    global _production_logger
    _production_logger = ProductionLogger(config)
    return _production_logger


def get_production_logger() -> Optional[ProductionLogger]:
    """Get the production logger instance"""
    return _production_logger


def get_logger(name: str = "main") -> logging.Logger:
    """Get a logger (fallback to standard logging if production not setup)"""
    if _production_logger:
        return _production_logger.get_logger(name)
    return logging.getLogger(f"miner.{name}")
