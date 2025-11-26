#!/usr/bin/env python3

"""
Advanced Cryptocurrency Mining System
Production-ready mining application with monitoring, wallet integration, and auto-scaling
Developed & Maintained by DevMonix Technologies
"""

import sys
import os
import signal
import argparse
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Core imports
from utils.production_logger import setup_production_logging, get_production_logger
from utils.error_recovery import setup_error_recovery, get_recovery_manager, handle_error, ErrorSeverity
from monitoring.resource_monitor import setup_resource_monitor, get_resource_monitor
from security.encryption import setup_security, get_security_manager
from utils.backup_manager import setup_backup_manager, get_backup_manager

# Mining imports
from core.miner import AdvancedMiner
from terminal_gui import start_terminal_gui
from utils.logger import get_logger

# Global production components
logger = None
production_logger = None
recovery_manager = None
resource_monitor = None
security_manager = None
backup_manager = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global logger, production_logger, recovery_manager, resource_monitor, backup_manager
    
    print("\nShutdown signal received. Stopping mining operations...")
    
    try:
        # Stop monitoring
        if resource_monitor:
            resource_monitor.stop_monitoring()
        
        # Stop automated backups
        if backup_manager:
            backup_manager.stop_automated_backups()
        
        # Log shutdown
        if production_logger:
            production_logger.log_info("Application shutdown initiated", component="main")
        
        # Final backup
        if backup_manager:
            backup_manager.backup_configuration("Shutdown backup")
        
        print("Graceful shutdown completed.")
        
    except Exception as e:
        print(f"Error during shutdown: {e}")
    
    sys.exit(0)


def check_system_requirements() -> bool:
    """Check if system meets minimum requirements"""
    try:
        import platform
        import psutil
        
        # Check Python version
        python_version = platform.python_version()
        print(f"Python version: {python_version} ")
        
        # Check memory
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        print(f"Memory: {memory_gb:.1f} GB ")
        
        # Check disk space
        disk = psutil.disk_usage('/')
        disk_gb = disk.free / (1024**3)
        print(f"Disk space: {disk_gb:.1f} GB free ")
        
        # Check CPU
        cpu_cores = psutil.cpu_count()
        print(f"CPU: {cpu_cores} cores ")
        
        # Check for GPU (optional)
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                print(f"GPU: {gpu_count} devices detected ")
            else:
                print("No GPU detected - CPU mining only")
        except ImportError:
            print("No GPU detected - CPU mining only")
        
        print("System requirements met ")
        return True
        
    except Exception as e:
        print(f"System requirements check failed: {e}")
        return False


def initialize_production_systems(config: Dict[str, Any]) -> bool:
    """Initialize all production systems"""
    global logger, production_logger, recovery_manager, resource_monitor, security_manager, backup_manager
    
    try:
        # Setup production logging
        logging_config = config.get("logging", {})
        production_logger = setup_production_logging(logging_config)
        logger = get_production_logger().get_logger("main")
        logger.log_info("Production logging initialized", component="main")
        
        # Setup security
        security_config = config.get("security", {})
        security_manager = setup_security(security_config)
        logger.log_info("Security system initialized", component="main")
        
        # Setup error recovery
        recovery_manager = setup_error_recovery(config)
        logger.log_info("Error recovery system initialized", component="main")
        
        # Setup resource monitoring
        resource_monitor = setup_resource_monitor(config)
        logger.log_info("Resource monitoring initialized", component="main")
        
        # Setup backup manager
        backup_config = config.get("backup", {})
        backup_manager = setup_backup_manager(backup_config)
        logger.log_info("Backup system initialized", component="main")
        
        return True
        
    except Exception as e:
        print(f"Production systems initialization failed: {e}")
        # Don't fail completely, just disable production features
        logger = None
        production_logger = None
        recovery_manager = None
        resource_monitor = None
        security_manager = None
        backup_manager = None
        return False


def initialize_basic_systems(config: Dict[str, Any]) -> bool:
    """Initialize basic systems without production features"""
    global logger, production_logger, recovery_manager, resource_monitor, security_manager, backup_manager
    
    try:
        # Setup basic logging only
        from utils.logger import get_logger as get_basic_logger
        logger = get_basic_logger("main")
        print("Basic logging initialized")
        
        return True
        
    except Exception as e:
        print(f"Basic systems initialization failed: {e}")
        return False


def start_mining_with_monitoring(config: Dict[str, Any]) -> Optional[AdvancedMiner]:
    """Start mining with full production monitoring"""
    global logger, recovery_manager, resource_monitor, backup_manager
    
    try:
        logger.log_info("Starting mining with production monitoring", component="main")
        
        # Create miner instance
        miner = AdvancedMiner(config)
        
        # Register recovery actions
        from utils.error_recovery import (
            RestartMinerRecovery, 
            ReconnectWalletRecovery, 
            ClearCacheRecovery, 
            ReduceResourceUsageRecovery
        )
        
        recovery_manager.register_recovery_action(RestartMinerRecovery(miner), "mining")
        recovery_manager.register_recovery_action(ClearCacheRecovery(), "system")
        recovery_manager.register_recovery_action(ReduceResourceUsageRecovery(miner), "mining")
        
        # Register wallet recovery if available
        if hasattr(miner, 'wallet_manager') and miner.wallet_manager:
            recovery_manager.register_recovery_action(
                ReconnectWalletRecovery(miner.wallet_manager), 
                "wallet"
            )
        
        # Start monitoring
        resource_monitor.start_monitoring(miner)
        recovery_manager.start_monitoring()
        
        # Start automated backups
        if backup_manager.backup_enabled:
            backup_manager.start_automated_backups()
        
        # Start mining
        miner.start()
        
        logger.log_info("Mining started with full monitoring", component="main")
        
        return miner
        
    except Exception as e:
        handle_error("mining", e, ErrorSeverity.CRITICAL)
        return None


def main():
    """Main application entry point"""
    global logger, production_logger, recovery_manager, resource_monitor, backup_manager
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Advanced Cryptocurrency Mining System")
    parser.add_argument("--config", default="config/default.conf", help="Configuration file path")
    parser.add_argument("--terminal", action="store_true", help="Start terminal GUI")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmarks")
    parser.add_argument("--production", action="store_true", help="Enable production mode")
    parser.add_argument("--deploy", action="store_true", help="Run deployment wizard")
    
    args = parser.parse_args()
    
    # Check system requirements
    if not check_system_requirements():
        print("System requirements not met. Exiting.")
        return 1
    
    # Load configuration
    try:
        from config.manager import ConfigManager
        config_manager = ConfigManager(args.config)
        config = config_manager.load_config()
        
        # Use production config if production mode
        if args.production and Path("config/production.conf").exists():
            prod_config_manager = ConfigManager("config/production.conf")
            config = prod_config_manager.load_config()
            print("Using production configuration")
        
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return 1
    
    # Initialize production systems
    if args.production:
        # Use full production systems for production mode
        if not initialize_production_systems(config):
            print("Failed to initialize production systems. Exiting.")
            return 1
    else:
        # Use basic systems for development/terminal mode
        if not initialize_basic_systems(config):
            print("Failed to initialize basic systems. Exiting.")
            return 1
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.deploy:
            # Run deployment wizard
            print("Deployment wizard not yet implemented")
            return 0
        
        elif args.terminal:
            # Start terminal GUI
            print("DEBUG: About to start terminal GUI...")
            print(f"DEBUG: Logger is None: {logger is None}")
            # Skip logger call to avoid hanging
            print("Starting terminal GUI")
            try:
                print("DEBUG: Calling start_terminal_gui...")
                start_terminal_gui(miner_instance=None, config=config)
                print("DEBUG: Terminal GUI completed")
            except Exception as e:
                print(f"ERROR: Terminal GUI failed: {e}")
                import traceback
                traceback.print_exc()
        
        elif args.benchmark:
            # Run benchmarks
            if logger:
                logger.log_info("Running benchmarks", component="main")
            else:
                print("Running benchmarks")
            from utils.benchmark import run_benchmarks
            run_benchmarks(config)
        
        else:
            # Start mining with full production features
            miner = start_mining_with_monitoring(config)
            
            if miner:
                try:
                    # Main mining loop
                    while True:
                        time.sleep(60)  # Check every minute
                        
                        # Log periodic status
                        stats = resource_monitor.get_stats()
                        if stats:
                            logger.log_performance(
                                "mining_status",
                                1,
                                "running",
                                cpu_percent=stats.get("current_metrics", {}).get("cpu_percent", 0),
                                memory_percent=stats.get("current_metrics", {}).get("memory_percent", 0)
                            )
                        
                except KeyboardInterrupt:
                    logger.log_info("Mining stopped by user", component="main")
                
                finally:
                    # Cleanup
                    miner.stop()
                    resource_monitor.stop_monitoring()
                    backup_manager.stop_automated_backups()
                    recovery_manager.stop_monitoring()
                    
                    # Final backup
                    backup_manager.backup_configuration("Mining stopped backup")
                    
                    logger.log_info("Mining cleanup completed", component="main")
            else:
                print("Failed to start miner")
                return 1
    
    except Exception as e:
        handle_error("main", e, ErrorSeverity.CRITICAL)
        return 1
    
    finally:
        # Final cleanup
        if production_logger:
            production_logger.log_info("Application shutdown", component="main")
        
        # Print final statistics
        if resource_monitor:
            stats = resource_monitor.get_stats()
            print(f"\nFinal Statistics:")
            print(f"  Total metrics: {stats.get('total_metrics', 0)}")
            print(f"  Alerts: {stats.get('alert_count', 0)}")
            print(f"  Scale actions: {stats.get('scale_actions', 0)}")
        
        if backup_manager:
            stats = backup_manager.get_stats()
            print(f"  Backups: {stats.get('successful_backups', 0)} successful, {stats.get('failed_backups', 0)} failed")
        
        if recovery_manager:
            stats = recovery_manager.get_stats()
            print(f"  Errors: {stats.get('total_errors', 0)} total, {stats.get('resolved_errors', 0)} resolved")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
