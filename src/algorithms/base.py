"""
Base Algorithm Class
Foundation for all mining algorithms
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time
import threading


class BaseAlgorithm(ABC):
    """Base class for all mining algorithms"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.running = False
        self.start_time = 0
        self.total_hashes = 0
        self.performance_data = {}
        self._lock = threading.Lock()
        
        # Algorithm-specific initialization
        self._initialize()
    
    @abstractmethod
    def _initialize(self):
        """Initialize algorithm-specific parameters"""
        pass
    
    @abstractmethod
    def mine(self, work_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute mining algorithm on work data
        Returns result if valid share/block found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_algorithm_type(self) -> str:
        """Return algorithm type (CPU, GPU, ASIC)"""
        pass
    
    def start(self):
        """Start the algorithm"""
        self.running = True
        self.start_time = time.time()
        self.total_hashes = 0
        self._on_start()
    
    def stop(self):
        """Stop the algorithm"""
        self.running = False
        self._on_stop()
    
    def _on_start(self):
        """Called when algorithm starts"""
        pass
    
    def _on_stop(self):
        """Called when algorithm stops"""
        pass
    
    def record_hash(self, count: int = 1):
        """Record hash attempts"""
        with self._lock:
            self.total_hashes += count
    
    def get_performance(self) -> Dict[str, Any]:
        """Get performance metrics"""
        with self._lock:
            uptime = time.time() - self.start_time if self.start_time > 0 else 0
            hashrate = self.total_hashes / uptime if uptime > 0 else 0
            
            return {
                "hashrate": hashrate,
                "total_hashes": self.total_hashes,
                "uptime": uptime,
                "algorithm_type": self.get_algorithm_type(),
                "custom_data": self.performance_data
            }
    
    def update_performance_data(self, key: str, value: Any):
        """Update algorithm-specific performance data"""
        with self._lock:
            self.performance_data[key] = value
    
    @property
    def algorithm_type(self) -> str:
        """Alias for get_algorithm_type()"""
        return self.get_algorithm_type()
