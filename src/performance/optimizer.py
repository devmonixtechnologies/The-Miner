"""
Performance Optimization and Memory Management
Production-grade performance tuning and resource optimization
"""

import gc
import threading
import time
import psutil
import os
import resource
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from pathlib import Path
import weakref
import tracemalloc

from utils.production_logger import get_production_logger


@dataclass
class PerformanceMetrics:
    timestamp: float
    memory_usage_mb: float
    memory_percent: float
    cpu_percent: float
    gc_collections: int
    objects_count: int
    file_descriptors: int
    threads_count: int
    response_time_ms: float


class MemoryPool:
    """Memory pool for efficient object allocation"""
    
    def __init__(self, pool_size: int = 1000):
        self.pool_size = pool_size
        self.available_objects = []
        self.used_objects = set()
        self.total_allocated = 0
        self.lock = threading.Lock()
    
    def get_object(self, object_type: type, *args, **kwargs):
        """Get object from pool or create new one"""
        with self.lock:
            # Try to reuse existing object
            for obj in self.available_objects:
                if isinstance(obj, object_type):
                    self.available_objects.remove(obj)
                    self.used_objects.add(obj)
                    return obj
            
            # Create new object if pool not full
            if self.total_allocated < self.pool_size:
                obj = object_type(*args, **kwargs)
                self.used_objects.add(obj)
                self.total_allocated += 1
                return obj
            
            # Pool full, create temporary object
            return object_type(*args, **kwargs)
    
    def return_object(self, obj):
        """Return object to pool"""
        with self.lock:
            if obj in self.used_objects:
                self.used_objects.remove(obj)
                self.available_objects.append(obj)
    
    def cleanup(self):
        """Clean up unused objects"""
        with self.lock:
            self.available_objects.clear()
            self.used_objects.clear()
            self.total_allocated = 0


class PerformanceOptimizer:
    """Production-grade performance optimization system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_production_logger()
        
        # Performance settings
        self.enable_optimization = config.get("performance", {}).get("enable_memory_optimization", True)
        self.gc_interval = config.get("performance", {}).get("gc_interval", 300)
        self.max_memory_usage = self._parse_size(config.get("performance", {}).get("max_memory_usage", "2048MB"))
        self.enable_cpu_affinity = config.get("performance", {}).get("enable_cpu_affinity", True)
        self.priority_class = config.get("performance", {}).get("priority_class", "normal")
        
        # Memory management
        self.memory_pools: Dict[type, MemoryPool] = {}
        self.weak_refs: List[weakref.ref] = []
        
        # Performance tracking
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history = 3600  # 1 hour at 1-second intervals
        
        # Optimization thread
        self.optimization_thread = None
        self.running = False
        
        # Statistics
        self.gc_runs = 0
        self.memory_cleanups = 0
        self.optimizations_applied = 0
        
        # Initialize performance monitoring
        self._initialize_monitoring()
        
        # Apply initial optimizations
        if self.enable_optimization:
            self._apply_initial_optimizations()
        
        if self.logger:
            self.logger.log_info("Performance optimizer initialized", component="performance")
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '2048MB' to bytes"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def _initialize_monitoring(self):
        """Initialize performance monitoring"""
        try:
            # Start memory tracing
            tracemalloc.start()
            
            # Set resource limits
            if self.max_memory_usage:
                # Set memory limit (soft limit)
                try:
                    resource.setrlimit(resource.RLIMIT_AS, (self.max_memory_usage, self.max_memory_usage))
                except (ValueError, OSError):
                    # May not be available on all systems
                    pass
            
            # Set process priority
            self._set_process_priority()
            
            # Set CPU affinity if enabled
            if self.enable_cpu_affinity:
                self._set_cpu_affinity()
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Performance monitoring initialization failed: {e}", component="performance")
    
    def _set_process_priority(self):
        """Set process priority based on configuration"""
        try:
            priority_map = {
                "low": psutil.BELOW_NORMAL_PRIORITY_CLASS if hasattr(psutil, 'BELOW_NORMAL_PRIORITY_CLASS') else 10,
                "normal": psutil.NORMAL_PRIORITY_CLASS if hasattr(psutil, 'NORMAL_PRIORITY_CLASS') else 0,
                "high": psutil.HIGH_PRIORITY_CLASS if hasattr(psutil, 'HIGH_PRIORITY_CLASS') else -5,
                "realtime": psutil.REALTIME_PRIORITY_CLASS if hasattr(psutil, 'REALTIME_PRIORITY_CLASS') else -10
            }
            
            priority = priority_map.get(self.priority_class, 0)
            current_process = psutil.Process()
            
            if hasattr(current_process, 'nice'):
                current_process.nice(priority)
            elif hasattr(current_process, 'set_nice'):
                current_process.set_nice(priority)
            
            if self.logger:
                self.logger.log_info(f"Set process priority to {self.priority_class}", component="performance")
                
        except Exception as e:
            if self.logger:
                self.logger.log_warning(f"Failed to set process priority: {e}", component="performance")
    
    def _set_cpu_affinity(self):
        """Set CPU affinity to optimize performance"""
        try:
            current_process = psutil.Process()
            cpu_count = psutil.cpu_count()
            
            # Use all available CPUs for mining
            cpu_list = list(range(cpu_count))
            current_process.cpu_affinity(cpu_list)
            
            if self.logger:
                self.logger.log_info(f"Set CPU affinity to {cpu_count} cores", component="performance")
                
        except Exception as e:
            if self.logger:
                self.logger.log_warning(f"Failed to set CPU affinity: {e}", component="performance")
    
    def _apply_initial_optimizations(self):
        """Apply initial performance optimizations"""
        try:
            # Optimize garbage collection
            gc.set_threshold(700, 10, 10)
            
            # Enable aggressive garbage collection
            gc.collect()
            
            # Optimize file descriptor limits
            try:
                soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
                resource.setrlimit(resource.RLIMIT_NOFILE, (max(soft, 4096), hard))
            except (ValueError, OSError):
                pass
            
            if self.logger:
                self.logger.log_info("Applied initial performance optimizations", component="performance")
                
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Failed to apply initial optimizations: {e}", component="performance")
    
    def start_optimization(self):
        """Start performance optimization thread"""
        if self.running:
            return
        
        self.running = True
        self.optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self.optimization_thread.start()
        
        if self.logger:
            self.logger.log_info("Performance optimization started", component="performance")
    
    def stop_optimization(self):
        """Stop performance optimization thread"""
        self.running = False
        if self.optimization_thread:
            self.optimization_thread.join(timeout=5)
        
        if self.logger:
            self.logger.log_info("Performance optimization stopped", component="performance")
    
    def _optimization_loop(self):
        """Main optimization loop"""
        while self.running:
            try:
                start_time = time.time()
                
                # Collect performance metrics
                metrics = self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # Limit history size
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history.pop(0)
                
                # Perform optimizations
                self._perform_optimizations(metrics)
                
                # Log performance metrics
                self._log_performance_metrics(metrics)
                
                # Sleep for interval
                elapsed = time.time() - start_time
                sleep_time = max(1, self.gc_interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Optimization loop error: {e}", component="performance")
                time.sleep(60)  # Wait longer on error
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        try:
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_usage_mb = memory.used / (1024 * 1024)
            memory_percent = memory.percent
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Garbage collection
            gc_stats = gc.get_stats()
            gc_collections = sum(stat.get('collections', 0) for stat in gc_stats)
            
            # Object count
            objects_count = len(gc.get_objects())
            
            # File descriptors
            try:
                file_descriptors = len(psutil.Process().open_files())
            except:
                file_descriptors = 0
            
            # Thread count
            threads_count = threading.active_count()
            
            # Response time (simulated)
            response_time_ms = 0.0
            
            return PerformanceMetrics(
                timestamp=time.time(),
                memory_usage_mb=memory_usage_mb,
                memory_percent=memory_percent,
                cpu_percent=cpu_percent,
                gc_collections=gc_collections,
                objects_count=objects_count,
                file_descriptors=file_descriptors,
                threads_count=threads_count,
                response_time_ms=response_time_ms
            )
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Failed to collect performance metrics: {e}", component="performance")
            
            # Return default metrics
            return PerformanceMetrics(
                timestamp=time.time(),
                memory_usage_mb=0.0,
                memory_percent=0.0,
                cpu_percent=0.0,
                gc_collections=0,
                objects_count=0,
                file_descriptors=0,
                threads_count=0,
                response_time_ms=0.0
            )
    
    def _perform_optimizations(self, metrics: PerformanceMetrics):
        """Perform performance optimizations based on metrics"""
        optimizations_applied = 0
        
        # Memory optimization
        if metrics.memory_usage_mb > self.max_memory_usage / (1024 * 1024):
            self._optimize_memory_usage()
            optimizations_applied += 1
        
        # Garbage collection optimization
        if metrics.objects_count > 100000:  # Too many objects
            self._optimize_garbage_collection()
            optimizations_applied += 1
        
        # File descriptor optimization
        if metrics.file_descriptors > 900:  # Approaching limit
            self._optimize_file_descriptors()
            optimizations_applied += 1
        
        # Thread optimization
        if metrics.threads_count > 50:  # Too many threads
            self._optimize_threads()
            optimizations_applied += 1
        
        if optimizations_applied > 0:
            self.optimizations_applied += optimizations_applied
            
            if self.logger:
                self.logger.log_info(
                    f"Applied {optimizations_applied} performance optimizations",
                    component="performance",
                    memory_mb=metrics.memory_usage_mb,
                    objects_count=metrics.objects_count,
                    file_descriptors=metrics.file_descriptors,
                    threads_count=metrics.threads_count
                )
    
    def _optimize_memory_usage(self):
        """Optimize memory usage"""
        try:
            # Aggressive garbage collection
            collected = gc.collect()
            self.gc_runs += 1
            
            # Clean up memory pools
            for pool in self.memory_pools.values():
                pool.cleanup()
            
            # Clear weak references
            self.weak_refs = [ref for ref in self.weak_refs if ref() is not None]
            
            self.memory_cleanups += 1
            
            if self.logger:
                self.logger.log_performance(
                    "memory_cleanup",
                    collected,
                    "objects",
                    memory_cleanups=self.memory_cleanups
                )
                
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Memory optimization failed: {e}", component="performance")
    
    def _optimize_garbage_collection(self):
        """Optimize garbage collection"""
        try:
            # Run garbage collection
            collected = gc.collect()
            self.gc_runs += 1
            
            # Adjust GC thresholds for better performance
            if len(self.metrics_history) > 10:
                recent_metrics = self.metrics_history[-10:]
                avg_objects = sum(m.objects_count for m in recent_metrics) / len(recent_metrics)
                
                if avg_objects > 50000:
                    # More aggressive GC
                    gc.set_threshold(500, 5, 5)
                elif avg_objects < 10000:
                    # Less aggressive GC
                    gc.set_threshold(1000, 15, 15)
            
            if self.logger:
                self.logger.log_performance(
                    "garbage_collection",
                    collected,
                    "objects",
                    gc_runs=self.gc_runs
                )
                
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Garbage collection optimization failed: {e}", component="performance")
    
    def _optimize_file_descriptors(self):
        """Optimize file descriptor usage"""
        try:
            current_process = psutil.Process()
            open_files = current_process.open_files()
            
            # Close unnecessary file descriptors
            for file_info in open_files:
                try:
                    if file_info.path.endswith('.tmp') or '/tmp/' in file_info.path:
                        # Close temporary files
                        fd = file_info.fd
                        os.close(fd)
                except:
                    pass
            
            if self.logger:
                self.logger.log_performance(
                    "file_descriptor_cleanup",
                    len(open_files),
                    "descriptors"
                )
                
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"File descriptor optimization failed: {e}", component="performance")
    
    def _optimize_threads(self):
        """Optimize thread usage"""
        try:
            # This is a placeholder for thread optimization
            # In practice, you might want to identify and join zombie threads
            
            active_threads = threading.enumerate()
            
            # Log thread count for monitoring
            if self.logger:
                self.logger.log_performance(
                    "thread_count",
                    len(active_threads),
                    "threads"
                )
                
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Thread optimization failed: {e}", component="performance")
    
    def _log_performance_metrics(self, metrics: PerformanceMetrics):
        """Log performance metrics"""
        if self.logger:
            self.logger.log_performance("memory_usage_mb", metrics.memory_usage_mb, "MB")
            self.logger.log_performance("memory_percent", metrics.memory_percent, "percent")
            self.logger.log_performance("cpu_percent", metrics.cpu_percent, "percent")
            self.logger.log_performance("objects_count", metrics.objects_count, "objects")
            self.logger.log_performance("file_descriptors", metrics.file_descriptors, "descriptors")
            self.logger.log_performance("threads_count", metrics.threads_count, "threads")
    
    def get_memory_pool(self, object_type: type, pool_size: int = 1000) -> MemoryPool:
        """Get or create memory pool for object type"""
        if object_type not in self.memory_pools:
            self.memory_pools[object_type] = MemoryPool(pool_size)
        return self.memory_pools[object_type]
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the most recent performance metrics"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_average_metrics(self, duration_minutes: int = 5) -> Optional[Dict[str, float]]:
        """Get average performance metrics over the specified duration"""
        if not self.metrics_history:
            return None
        
        cutoff_time = time.time() - (duration_minutes * 60)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return None
        
        return {
            "memory_usage_mb": sum(m.memory_usage_mb for m in recent_metrics) / len(recent_metrics),
            "memory_percent": sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
            "cpu_percent": sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
            "objects_count": sum(m.objects_count for m in recent_metrics) / len(recent_metrics),
            "file_descriptors": sum(m.file_descriptors for m in recent_metrics) / len(recent_metrics),
            "threads_count": sum(m.threads_count for m in recent_metrics) / len(recent_metrics),
            "sample_count": len(recent_metrics)
        }
    
    def get_memory_usage_report(self) -> Dict[str, Any]:
        """Get detailed memory usage report"""
        try:
            # Get memory snapshot
            snapshot = tracemalloc.take_snapshot()
            
            # Get top statistics
            top_stats = snapshot.statistics('lineno')
            
            # Get memory traceback
            memory_report = {
                "current_usage_mb": psutil.virtual_memory().used / (1024 * 1024),
                "peak_usage_mb": max(m.memory_usage_mb for m in self.metrics_history) if self.metrics_history else 0,
                "gc_runs": self.gc_runs,
                "memory_cleanups": self.memory_cleanups,
                "pools_count": len(self.memory_pools),
                "top_allocations": [
                    {
                        "file": str(stat.traceback[0].filename),
                        "line": stat.traceback[0].lineno,
                        "size_mb": stat.size / (1024 * 1024),
                        "count": stat.count
                    }
                    for stat in top_stats[:10]
                ]
            }
            
            return memory_report
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Failed to generate memory report: {e}", component="performance")
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance optimization statistics"""
        current = self.get_current_metrics()
        
        return {
            "optimization_active": self.running,
            "gc_runs": self.gc_runs,
            "memory_cleanups": self.memory_cleanups,
            "optimizations_applied": self.optimizations_applied,
            "memory_pools": len(self.memory_pools),
            "current_metrics": current.__dict__ if current else None,
            "max_memory_usage_mb": self.max_memory_usage / (1024 * 1024),
            "gc_interval": self.gc_interval,
            "cpu_affinity_enabled": self.enable_cpu_affinity,
            "priority_class": self.priority_class
        }


# Global performance optimizer instance
_performance_optimizer = None


def setup_performance_optimizer(config: Dict[str, Any]) -> PerformanceOptimizer:
    """Setup performance optimization system"""
    global _performance_optimizer
    _performance_optimizer = PerformanceOptimizer(config)
    return _performance_optimizer


def get_performance_optimizer() -> Optional[PerformanceOptimizer]:
    """Get the performance optimizer instance"""
    return _performance_optimizer
