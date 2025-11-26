"""
Advanced Logging System
Comprehensive logging with multiple outputs and levels
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.theme import Theme
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    import colorama
    from colorama import Fore, Back, Style
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class MiningLogger:
    """Advanced logging system for mining operations"""
    
    def __init__(self, name: str = "miner", log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Logger setup
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Setup handlers
        self._setup_console_handler()
        self._setup_file_handlers()
        
        # Mining-specific loggers
        self.mining_logger = self._create_specialized_logger("mining")
        self.performance_logger = self._create_specialized_logger("performance")
        self.profit_logger = self._create_specialized_logger("profit")
        self.error_logger = self._create_specialized_logger("errors", level=logging.ERROR)
        
        # Initialize performance logger with CSV handler
        perf_log = self.log_dir / "performance.log"
        perf_handler = logging.handlers.RotatingFileHandler(
            perf_log, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
        )
        perf_handler.setFormatter(CSVDetailedFormatter())
        perf_handler.setLevel(logging.INFO)
        self.performance_logger.addHandler(perf_handler)
        
        # Statistics
        self.log_stats = {
            "total_logs": 0,
            "errors": 0,
            "warnings": 0,
            "shares_found": 0
        }
    
    def _setup_console_handler(self):
        """Setup console logging with colors"""
        if RICH_AVAILABLE:
            console = Console(theme=Theme({
                "info": "cyan",
                "warning": "yellow",
                "error": "red",
                "critical": "bold red",
                "debug": "dim white"
            }))
            
            handler = RichHandler(
                console=console,
                show_time=True,
                show_path=False,
                markup=True,
                rich_tracebacks=True
            )
        else:
            handler = logging.StreamHandler(sys.stdout)
            
            if COLORAMA_AVAILABLE:
                colorama.init()
                formatter = ColoredFormatter()
            else:
                formatter = SimpleFormatter()
            
            handler.setFormatter(formatter)
        
        handler.setLevel(logging.INFO)
        self.logger.addHandler(handler)
    
    def _setup_file_handlers(self):
        """Setup file logging with rotation"""
        # Main log file with rotation
        main_log = self.log_dir / f"{self.name}.log"
        main_handler = logging.handlers.RotatingFileHandler(
            main_log, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        main_handler.setFormatter(DetailedFormatter())
        main_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(main_handler)
        
        # Error-only log file
        error_log = self.log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
        )
        error_handler.setFormatter(DetailedFormatter())
        error_handler.setLevel(logging.ERROR)
        self.logger.addHandler(error_handler)
    
    def _create_specialized_logger(self, suffix: str, level: int = logging.DEBUG) -> logging.Logger:
        """Create specialized logger for specific components"""
        logger_name = f"{self.name}.{suffix}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        
        # Add file handler
        log_file = self.log_dir / f"{suffix}.log"
        handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
        )
        handler.setFormatter(DetailedFormatter())
        logger.addHandler(handler)
        
        return logger
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, extra=kwargs)
        self.log_stats["total_logs"] += 1
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, extra=kwargs)
        self.log_stats["total_logs"] += 1
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, extra=kwargs)
        self.log_stats["warnings"] += 1
        self.log_stats["total_logs"] += 1
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, extra=kwargs)
        self.log_stats["errors"] += 1
        self.log_stats["total_logs"] += 1
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, extra=kwargs)
        self.log_stats["errors"] += 1
        self.log_stats["total_logs"] += 1
    
    def mining_event(self, event_type: str, details: Dict[str, Any]):
        """Log mining-specific events"""
        message = f"[MINING] {event_type}: {details}"
        self.mining_logger.info(message)
        
        if event_type == "share_found":
            self.log_stats["shares_found"] += 1
    
    def performance_metric(self, metric_name: str, value: Any, unit: str = ""):
        """Log performance metrics"""
        message = f"{metric_name}={value}{unit}"
        self.performance_logger.info(message)
    
    def profit_update(self, algorithm: str, profit: float, hashrate: float):
        """Log profit updates"""
        message = f"Algorithm: {algorithm}, Profit: ${profit:.4f}/hr, Hashrate: {hashrate:.2f} H/s"
        self.profit_logger.info(message)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        return self.log_stats.copy()
    
    def get_recent_logs(self, count: int = 50, level: Optional[str] = None) -> list:
        """Get recent log entries"""
        log_file = self.log_dir / f"{self.name}.log"
        
        if not log_file.exists():
            return []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Filter by level if specified
            if level:
                level_filter = level.upper()
                lines = [line for line in lines if level_filter in line]
            
            # Return last N lines
            return lines[-count:]
            
        except Exception as e:
            self.error(f"Error reading log file: {e}")
            return []
    
    def clear_logs(self):
        """Clear all log files"""
        try:
            for log_file in self.log_dir.glob("*.log"):
                log_file.unlink()
            
            # Reset stats
            self.log_stats = {
                "total_logs": 0,
                "errors": 0,
                "warnings": 0,
                "shares_found": 0
            }
            
            self.info("All logs cleared")
            
        except Exception as e:
            self.error(f"Error clearing logs: {e}")


class DetailedFormatter(logging.Formatter):
    """Detailed formatter for file logs"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


class CSVDetailedFormatter(logging.Formatter):
    """CSV formatter for performance logs"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s,%(levelname)s,%(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


class SimpleFormatter(logging.Formatter):
    """Simple formatter for console"""
    
    def __init__(self):
        super().__init__('%(levelname)s: %(message)s')


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE
    }
    
    def __init__(self):
        super().__init__('%(levelname)s: %(message)s')
    
    def format(self, record):
        if COLORAMA_AVAILABLE:
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        
        return super().format(record)


# Global logger instance
_global_logger = None


def setup_logging(verbose: bool = False, log_dir: str = "logs") -> MiningLogger:
    """Setup global logging system"""
    global _global_logger
    
    _global_logger = MiningLogger("miner", log_dir)
    
    if verbose:
        # Set console handler to DEBUG level
        for handler in _global_logger.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(logging.DEBUG)
    
    return _global_logger


def get_logger(name: str = None) -> MiningLogger:
    """Get logger instance"""
    global _global_logger
    
    if _global_logger is None:
        setup_logging()
    
    if name:
        return MiningLogger(name)
    
    return _global_logger


def log_system_info():
    """Log system information at startup"""
    logger = get_logger()
    
    import platform
    import psutil
    
    logger.info("=" * 50)
    logger.info("ADVANCED CRYPTOCURRENCY MINING SYSTEM")
    logger.info("=" * 50)
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Python: {platform.python_version()}")
    logger.info(f"CPU: {platform.processor()}")
    logger.info(f"Cores: {psutil.cpu_count()}")
    logger.info(f"Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    logger.info(f"Disk: {psutil.disk_usage('/').total / (1024**3):.1f} GB")
    logger.info("=" * 50)
