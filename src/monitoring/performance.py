"""
System Performance Monitor
Monitors CPU, GPU, memory, temperature and power consumption
"""

import threading
import time
import psutil
import platform
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False

try:
    import cpuinfo
    CPUINFO_AVAILABLE = True
except ImportError:
    CPUINFO_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SystemStats:
    cpu_percent: float
    cpu_count: int
    cpu_freq: float
    memory_percent: float
    memory_used: int
    memory_total: int
    disk_usage: float
    gpu_stats: List[Dict[str, Any]]
    temperature: float
    power_usage: float
    timestamp: float


class PerformanceMonitor:
    """Advanced system performance monitoring"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False
        self.update_interval = config.get("performance_update_interval", 1.0)
        
        # Performance tracking
        self.hash_attempts = 0
        self.hash_start_time = time.time()
        self.current_hashrate = 0.0
        self.max_hashrate = 0.0
        self.avg_hashrate = 0.0
        self.hashrate_history = []
        
        # System monitoring
        self.current_stats = SystemStats(
            cpu_percent=0.0,
            cpu_count=0,
            cpu_freq=0.0,
            memory_percent=0.0,
            memory_used=0,
            memory_total=0,
            disk_usage=0.0,
            gpu_stats=[],
            temperature=0.0,
            power_usage=0.0,
            timestamp=0.0
        )
        
        # Optimization parameters
        self.optimal_cpu_usage = config.get("optimal_cpu_usage", 80.0)
        self.optimal_temp = config.get("optimal_temperature", 75.0)
        self.max_temp = config.get("max_temperature", 85.0)
        
        # Threading
        self._lock = threading.Lock()
        self._monitor_thread = None
        
        # System info
        self.system_info = self._get_system_info()
        
        logger.info("Performance Monitor initialized")
    
    def start(self):
        """Start performance monitoring"""
        if self.running:
            return
        
        self.running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("Performance monitoring started")
    
    def stop(self):
        """Stop performance monitoring"""
        self.running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        
        logger.info("Performance monitoring stopped")
    
    def record_hash_attempt(self, count: int = 1):
        """Record hash attempts for hashrate calculation"""
        with self._lock:
            self.hash_attempts += count
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        with self._lock:
            return {
                "hashrate": self.current_hashrate,
                "max_hashrate": self.max_hashrate,
                "avg_hashrate": self.avg_hashrate,
                "hash_attempts": self.hash_attempts,
                "power_usage": self.current_stats.power_usage,
                "temperature": self.current_stats.temperature,
                "cpu_percent": self.current_stats.cpu_percent,
                "memory_percent": self.current_stats.memory_percent,
                "gpu_stats": self.current_stats.gpu_stats,
                "timestamp": self.current_stats.timestamp
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get detailed system information"""
        return self.system_info
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get performance optimization recommendations"""
        recommendations = []
        
        with self._lock:
            stats = self.current_stats
            
            # CPU usage recommendations
            if stats.cpu_percent > 90:
                recommendations.append("CPU usage is very high. Consider reducing mining threads.")
            elif stats.cpu_percent < 50:
                recommendations.append("CPU usage is low. Consider increasing mining threads.")
            
            # Temperature recommendations
            if stats.temperature > self.max_temp:
                recommendations.append(f"Temperature ({stats.temperature:.1f}°C) exceeds maximum. Reduce intensity.")
            elif stats.temperature > self.optimal_temp:
                recommendations.append(f"Temperature ({stats.temperature:.1f}°C) is high. Monitor closely.")
            
            # Memory recommendations
            if stats.memory_percent > 90:
                recommendations.append("Memory usage is very high. Close other applications.")
            
            # GPU recommendations
            for gpu in stats.gpu_stats:
                gpu_temp = gpu.get("temperature", 0)
                gpu_load = gpu.get("load", 0)
                
                if gpu_temp > 85:
                    recommendations.append(f"GPU {gpu.get('id')} temperature ({gpu_temp}°C) is too high.")
                elif gpu_load < 70:
                    recommendations.append(f"GPU {gpu.get('id')} usage ({gpu_load}%) is low. Optimize settings.")
            
            # Power recommendations
            if stats.power_usage > 500:  # High power usage
                recommendations.append("Power consumption is high. Consider efficiency optimization.")
            
            # Hashrate recommendations
            if self.current_hashrate < self.max_hashrate * 0.8:
                recommendations.append("Hashrate has decreased. Check system load and cooling.")
        
        return recommendations
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._update_system_stats()
                self._update_hashrate()
                self._check_optimization()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)
    
    def _update_system_stats(self):
        """Update system statistics"""
        try:
            # CPU stats
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq().current if psutil.cpu_freq() else 0.0
            
            # Memory stats
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used
            memory_total = memory.total
            
            # Disk stats
            disk_usage = psutil.disk_usage('/').percent
            
            # GPU stats
            gpu_stats = self._get_gpu_stats()
            
            # Temperature (estimated)
            temperature = self._estimate_temperature()
            
            # Power usage (estimated)
            power_usage = self._estimate_power_usage()
            
            # Update stats
            with self._lock:
                self.current_stats = SystemStats(
                    cpu_percent=cpu_percent,
                    cpu_count=cpu_count,
                    cpu_freq=cpu_freq,
                    memory_percent=memory_percent,
                    memory_used=memory_used,
                    memory_total=memory_total,
                    disk_usage=disk_usage,
                    gpu_stats=gpu_stats,
                    temperature=temperature,
                    power_usage=power_usage,
                    timestamp=time.time()
                )
        
        except Exception as e:
            logger.error(f"Error updating system stats: {e}")
    
    def _update_hashrate(self):
        """Update hashrate calculations"""
        with self._lock:
            current_time = time.time()
            elapsed_time = current_time - self.hash_start_time
            
            if elapsed_time > 0:
                self.current_hashrate = self.hash_attempts / elapsed_time
                
                # Update max hashrate
                if self.current_hashrate > self.max_hashrate:
                    self.max_hashrate = self.current_hashrate
                
                # Update history
                self.hashrate_history.append({
                    "timestamp": current_time,
                    "hashrate": self.current_hashrate
                })
                
                # Keep only last 1000 entries
                if len(self.hashrate_history) > 1000:
                    self.hashrate_history = self.hashrate_history[-1000:]
                
                # Calculate average hashrate
                if self.hashrate_history:
                    total_hashrate = sum(entry["hashrate"] for entry in self.hashrate_history)
                    self.avg_hashrate = total_hashrate / len(self.hashrate_history)
    
    def _check_optimization(self):
        """Check if optimization is needed"""
        with self._lock:
            stats = self.current_stats
            
            # Temperature protection
            if stats.temperature > self.max_temp:
                logger.warning(f"Temperature too high: {stats.temperature:.1f}°C")
                self._trigger_emergency_cooling()
            
            # CPU overload protection
            if stats.cpu_percent > 95:
                logger.warning(f"CPU usage too high: {stats.cpu_percent:.1f}%")
                self._reduce_intensity()
    
    def _trigger_emergency_cooling(self):
        """Trigger emergency cooling measures"""
        logger.critical("Emergency cooling triggered!")
        # In real implementation, this would reduce mining intensity
    
    def _reduce_intensity(self):
        """Reduce mining intensity"""
        logger.info("Reducing mining intensity due to system load")
        # In real implementation, this would adjust mining parameters
    
    def _get_gpu_stats(self) -> List[Dict[str, Any]]:
        """Get GPU statistics"""
        gpu_stats = []
        
        if GPUTIL_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                for gpu in gpus:
                    gpu_stats.append({
                        "id": gpu.id,
                        "name": gpu.name,
                        "load": gpu.load * 100,
                        "memory_used": gpu.memoryUsed,
                        "memory_total": gpu.memoryTotal,
                        "temperature": gpu.temperature,
                        "uuid": gpu.uuid
                    })
            except Exception as e:
                logger.error(f"Error getting GPU stats: {e}")
        
        return gpu_stats
    
    def _estimate_temperature(self) -> float:
        """Estimate system temperature"""
        # Try to get actual temperature
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        # Use the first temperature reading
                        return entries[0].current
        except:
            pass
        
        # Estimate based on CPU usage
        with self._lock:
            cpu_load = self.current_stats.cpu_percent
        
        # Simple estimation: higher CPU usage = higher temperature
        base_temp = 40.0  # Base temperature at idle
        temp_increase = (cpu_load / 100.0) * 30.0  # Up to 30°C increase
        return base_temp + temp_increase
    
    def _estimate_power_usage(self) -> float:
        """Estimate power usage"""
        base_power = 50.0  # Base system power
        
        with self._lock:
            # CPU power contribution
            cpu_power = (self.current_stats.cpu_percent / 100.0) * 65.0  # Up to 65W for CPU
            
            # GPU power contribution
            gpu_power = 0.0
            for gpu in self.current_stats.gpu_stats:
                gpu_load = gpu.get("load", 0) / 100.0
                gpu_power += gpu_load * 200.0  # Up to 200W per GPU
        
        return base_power + cpu_power + gpu_power
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get detailed system information"""
        info = {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "architecture": platform.architecture()[0],
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "disk_total": psutil.disk_usage('/').total
        }
        
        # Add CPU info if available
        if CPUINFO_AVAILABLE:
            try:
                cpu_info = cpuinfo.get_cpu_info()
                info.update({
                    "cpu_brand": cpu_info.get("brand_raw", "Unknown"),
                    "cpu_freq": cpu_info.get("hz_advertised_friendly", "Unknown"),
                    "cpu_cores": cpu_info.get("count", 0)
                })
            except:
                pass
        
        # Add GPU info
        if GPUTIL_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                info["gpu_count"] = len(gpus)
                info["gpus"] = [
                    {
                        "name": gpu.name,
                        "memory": gpu.memoryTotal,
                        "driver": gpu.driver
                    }
                    for gpu in gpus
                ]
            except:
                info["gpu_count"] = 0
        
        return info
