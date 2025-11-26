"""
System Resource Monitoring and Auto-Scaling
Production-grade resource management with intelligent scaling
"""

import time
import threading
import psutil
import os
import gc
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

from utils.production_logger import get_production_logger


class ResourceStatus(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    OVERLOADED = "overloaded"


@dataclass
class ResourceMetrics:
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    disk_free_gb: float
    network_io: Dict[str, float]
    process_count: int
    load_average: List[float]
    temperature: float
    status: ResourceStatus


class ScalingPolicy:
    """Base class for scaling policies"""
    
    def __init__(self, name: str, threshold: float, cooldown: float = 300.0):
        self.name = name
        self.threshold = threshold
        self.cooldown = cooldown
        self.last_action = 0.0
        self.action_count = 0
    
    def should_scale(self, metrics: ResourceMetrics) -> bool:
        """Check if scaling should be triggered"""
        if time.time() - self.last_action < self.cooldown:
            return False
        return self._evaluate_condition(metrics)
    
    def _evaluate_condition(self, metrics: ResourceMetrics) -> bool:
        """Override this method to implement scaling logic"""
        raise NotImplementedError
    
    def execute_scale(self, metrics: ResourceMetrics) -> bool:
        """Execute scaling action"""
        if self.should_scale(metrics):
            success = self._scale_action(metrics)
            if success:
                self.last_action = time.time()
                self.action_count += 1
            return success
        return False
    
    def _scale_action(self, metrics: ResourceMetrics) -> bool:
        """Override this method to implement scaling action"""
        raise NotImplementedError


class CPUScalingPolicy(ScalingPolicy):
    """CPU-based scaling policy"""
    
    def __init__(self, miner_instance, max_threads: int = 16):
        super().__init__("cpu_scaling", threshold=85.0, cooldown=120.0)
        self.miner_instance = miner_instance
        self.max_threads = max_threads
        self.original_threads = None
    
    def _evaluate_condition(self, metrics: ResourceMetrics) -> bool:
        return metrics.cpu_percent > self.threshold
    
    def _scale_action(self, metrics: ResourceMetrics) -> bool:
        """Reduce CPU threads if CPU usage is high"""
        try:
            if self.miner_instance and hasattr(self.miner_instance, 'config'):
                config = self.miner_instance.config
                
                # Store original thread count
                if self.original_threads is None:
                    self.original_threads = getattr(config, 'cpu_threads', 4)
                
                current_threads = getattr(config, 'cpu_threads', 4)
                new_threads = max(1, current_threads - 1)
                
                if new_threads != current_threads:
                    setattr(config, 'cpu_threads', new_threads)
                    
                    logger = get_production_logger()
                    if logger:
                        logger.log_performance(
                            "cpu_threads_scaled_down",
                            new_threads,
                            "threads",
                            old_threads=current_threads,
                            cpu_percent=metrics.cpu_percent
                        )
                    
                    return True
        except Exception as e:
            logger = get_production_logger()
            if logger:
                logger.log_error(f"CPU scaling failed: {e}", component="scaling")
        return False


class MemoryScalingPolicy(ScalingPolicy):
    """Memory-based scaling policy"""
    
    def __init__(self):
        super().__init__("memory_scaling", threshold=80.0, cooldown=180.0)
    
    def _evaluate_condition(self, metrics: ResourceMetrics) -> bool:
        return metrics.memory_percent > self.threshold
    
    def _scale_action(self, metrics: ResourceMetrics) -> bool:
        """Perform garbage collection and cache clearing"""
        try:
            # Force garbage collection
            collected = gc.collect()
            
            # Clear caches
            if hasattr(gc, 'collect'):
                gc.collect()
            
            logger = get_production_logger()
            if logger:
                logger.log_performance(
                    "memory_cleanup",
                    collected,
                    "objects",
                    memory_percent=metrics.memory_percent,
                    memory_used_mb=metrics.memory_used_mb
                )
            
            return True
        except Exception as e:
            logger = get_production_logger()
            if logger:
                logger.log_error(f"Memory scaling failed: {e}", component="scaling")
        return False


class IntensityScalingPolicy(ScalingPolicy):
    """Mining intensity scaling policy"""
    
    def __init__(self, miner_instance):
        super().__init__("intensity_scaling", threshold=75.0, cooldown=240.0)
        self.miner_instance = miner_instance
        self.original_intensity = None
    
    def _evaluate_condition(self, metrics: ResourceMetrics) -> bool:
        # Scale if CPU or memory is high
        return metrics.cpu_percent > self.threshold or metrics.memory_percent > self.threshold
    
    def _scale_action(self, metrics: ResourceMetrics) -> bool:
        """Reduce mining intensity"""
        try:
            if self.miner_instance and hasattr(self.miner_instance, 'config'):
                config = self.miner_instance.config
                
                # Store original intensity
                if self.original_intensity is None:
                    self.original_intensity = getattr(config, 'intensity', 0.8)
                
                current_intensity = getattr(config, 'intensity', 0.8)
                new_intensity = max(0.3, current_intensity * 0.9)
                
                if new_intensity != current_intensity:
                    setattr(config, 'intensity', new_intensity)
                    
                    logger = get_production_logger()
                    if logger:
                        logger.log_performance(
                            "intensity_scaled_down",
                            new_intensity,
                            "ratio",
                            old_intensity=current_intensity,
                            cpu_percent=metrics.cpu_percent,
                            memory_percent=metrics.memory_percent
                        )
                    
                    return True
        except Exception as e:
            logger = get_production_logger()
            if logger:
                logger.log_error(f"Intensity scaling failed: {e}", component="scaling")
        return False


class ResourceMonitor:
    """Production-grade resource monitoring system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_production_logger()
        
        # Monitoring settings
        self.monitoring_interval = config.get("monitoring", {}).get("performance_update_interval", 1.0)
        self.enable_auto_scaling = config.get("monitoring", {}).get("enable_auto_scaling", True)
        self.max_cpu_usage = config.get("monitoring", {}).get("max_cpu_usage", 85.0)
        self.max_memory_usage = config.get("performance", {}).get("max_memory_usage", "2048MB")
        
        # Metrics storage
        self.metrics_history: List[ResourceMetrics] = []
        self.max_history = 3600  # 1 hour at 1-second intervals
        
        # Scaling policies
        self.scaling_policies: List[ScalingPolicy] = []
        
        # Monitoring thread
        self.monitoring_thread = None
        self.running = False
        
        # Alerts
        self.alert_thresholds = {
            "cpu": 90.0,
            "memory": 85.0,
            "disk": 90.0,
            "temperature": 75.0
        }
        
        # Statistics
        self.total_metrics = 0
        self.alert_count = 0
        self.scale_actions = 0
        
        if self.logger:
            self.logger.log_info("Resource monitor initialized", component="monitoring")
    
    def add_scaling_policy(self, policy: ScalingPolicy):
        """Add a scaling policy"""
        self.scaling_policies.append(policy)
        
        if self.logger:
            self.logger.log_info(f"Added scaling policy: {policy.name}", component="monitoring")
    
    def start_monitoring(self, miner_instance=None):
        """Start resource monitoring"""
        if self.running:
            return
        
        # Add default scaling policies if auto-scaling is enabled
        if self.enable_auto_scaling and miner_instance:
            self.scaling_policies.append(CPUScalingPolicy(miner_instance))
            self.scaling_policies.append(MemoryScalingPolicy())
            self.scaling_policies.append(IntensityScalingPolicy(miner_instance))
        
        self.running = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(miner_instance,),
            daemon=True
        )
        self.monitoring_thread.start()
        
        if self.logger:
            self.logger.log_info("Resource monitoring started", component="monitoring")
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        if self.logger:
            self.logger.log_info("Resource monitoring stopped", component="monitoring")
    
    def _monitoring_loop(self, miner_instance=None):
        """Main monitoring loop"""
        while self.running:
            try:
                metrics = self._collect_metrics()
                self._process_metrics(metrics, miner_instance)
                time.sleep(self.monitoring_interval)
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Monitoring loop error: {e}", component="monitoring")
                time.sleep(5)  # Wait longer on error
    
    def _collect_metrics(self) -> ResourceMetrics:
        """Collect system resource metrics"""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        load_avg = list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_used_mb = memory.used / (1024 * 1024)
        memory_available_mb = memory.available / (1024 * 1024)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_free_gb = disk.free / (1024 * 1024 * 1024)
        
        # Network metrics
        network = psutil.net_io_counters()
        network_io = {
            "bytes_sent": network.bytes_sent,
            "bytes_recv": network.bytes_recv,
            "packets_sent": network.packets_sent,
            "packets_recv": network.packets_recv
        }
        
        # Process count
        process_count = len(psutil.pids())
        
        # Temperature (if available)
        temperature = 0.0
        try:
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if temps:
                    # Get average temperature from all sensors
                    temp_values = []
                    for name, entries in temps.items():
                        for entry in entries:
                            if entry.current:
                                temp_values.append(entry.current)
                    if temp_values:
                        temperature = sum(temp_values) / len(temp_values)
        except:
            pass
        
        # Determine status
        status = self._determine_status(cpu_percent, memory.percent, disk.percent, temperature)
        
        return ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory_used_mb,
            memory_available_mb=memory_available_mb,
            disk_percent=disk.percent,
            disk_free_gb=disk_free_gb,
            network_io=network_io,
            process_count=process_count,
            load_average=load_avg,
            temperature=temperature,
            status=status
        )
    
    def _determine_status(self, cpu: float, memory: float, disk: float, temp: float) -> ResourceStatus:
        """Determine overall system status"""
        if (cpu > 95 or memory > 95 or disk > 95 or temp > 85):
            return ResourceStatus.OVERLOADED
        elif (cpu > 85 or memory > 85 or disk > 85 or temp > 75):
            return ResourceStatus.CRITICAL
        elif (cpu > 70 or memory > 70 or disk > 70 or temp > 60):
            return ResourceStatus.WARNING
        else:
            return ResourceStatus.NORMAL
    
    def _process_metrics(self, metrics: ResourceMetrics, miner_instance=None):
        """Process collected metrics"""
        self.total_metrics += 1
        
        # Add to history
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history.pop(0)
        
        # Log performance metrics
        if self.logger:
            self.logger.log_performance("cpu_usage", metrics.cpu_percent, "percent")
            self.logger.log_performance("memory_usage", metrics.memory_percent, "percent")
            self.logger.log_performance("disk_usage", metrics.disk_percent, "percent")
            if metrics.temperature > 0:
                self.logger.log_performance("temperature", metrics.temperature, "celsius")
        
        # Check for alerts
        self._check_alerts(metrics)
        
        # Execute scaling policies
        if self.enable_auto_scaling:
            self._execute_scaling_policies(metrics)
    
    def _check_alerts(self, metrics: ResourceMetrics):
        """Check for alert conditions"""
        alerts = []
        
        if metrics.cpu_percent > self.alert_thresholds["cpu"]:
            alerts.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
        
        if metrics.memory_percent > self.alert_thresholds["memory"]:
            alerts.append(f"High memory usage: {metrics.memory_percent:.1f}%")
        
        if metrics.disk_percent > self.alert_thresholds["disk"]:
            alerts.append(f"Low disk space: {metrics.disk_percent:.1f}% used")
        
        if metrics.temperature > 0 and metrics.temperature > self.alert_thresholds["temperature"]:
            alerts.append(f"High temperature: {metrics.temperature:.1f}°C")
        
        if alerts and self.logger:
            self.alert_count += 1
            self.logger.log_warning(
                f"System alerts: {'; '.join(alerts)}",
                component="monitoring",
                alerts=alerts,
                metrics=metrics.__dict__
            )
    
    def _execute_scaling_policies(self, metrics: ResourceMetrics):
        """Execute scaling policies"""
        for policy in self.scaling_policies:
            try:
                if policy.execute_scale(metrics):
                    self.scale_actions += 1
                    
                    if self.logger:
                        self.logger.log_info(
                            f"Scaling policy executed: {policy.name}",
                            component="monitoring",
                            policy=policy.name,
                            action_count=policy.action_count
                        )
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Scaling policy {policy.name} failed: {e}", component="monitoring")
    
    def get_current_metrics(self) -> Optional[ResourceMetrics]:
        """Get the most recent metrics"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_average_metrics(self, duration_minutes: int = 5) -> Optional[Dict[str, float]]:
        """Get average metrics over the specified duration"""
        if not self.metrics_history:
            return None
        
        cutoff_time = time.time() - (duration_minutes * 60)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return None
        
        return {
            "cpu_percent": sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
            "memory_percent": sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
            "disk_percent": sum(m.disk_percent for m in recent_metrics) / len(recent_metrics),
            "temperature": sum(m.temperature for m in recent_metrics if m.temperature > 0) / 
                          len([m for m in recent_metrics if m.temperature > 0]) or 0,
            "sample_count": len(recent_metrics)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        current = self.get_current_metrics()
        
        return {
            "total_metrics": self.total_metrics,
            "alert_count": self.alert_count,
            "scale_actions": self.scale_actions,
            "current_metrics": current.__dict__ if current else None,
            "scaling_policies": [
                {
                    "name": policy.name,
                    "action_count": policy.action_count,
                    "last_action": policy.last_action
                }
                for policy in self.scaling_policies
            ],
            "monitoring_active": self.running,
            "auto_scaling_enabled": self.enable_auto_scaling
        }


# Global resource monitor instance
_resource_monitor = None


def setup_resource_monitor(config: Dict[str, Any]) -> ResourceMonitor:
    """Setup resource monitoring system"""
    global _resource_monitor
    _resource_monitor = ResourceMonitor(config)
    return _resource_monitor


def get_resource_monitor() -> Optional[ResourceMonitor]:
    """Get the resource monitor instance"""
    return _resource_monitor
