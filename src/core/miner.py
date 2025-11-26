"""
Core Mining Engine
Advanced cryptocurrency mining system with multi-algorithm support
"""

import threading
import time
import hashlib
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from algorithms.factory import AlgorithmFactory
from monitoring.performance import PerformanceMonitor
from monitoring.profit_switcher import ProfitSwitcher
from utils.logger import get_logger

logger = get_logger(__name__)


class MiningMode(Enum):
    SOLO = "solo"
    POOL = "pool"
    SMART = "smart"


@dataclass
class MiningStats:
    hashrate: float
    accepted_shares: int
    rejected_shares: int
    uptime: float
    power_usage: float
    temperature: float
    efficiency: float


class AdvancedMiner:
    """Advanced mining system with intelligent features"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False
        self.paused = False
        
        # Initialize components
        self.algorithm_factory = AlgorithmFactory()
        self.performance_monitor = PerformanceMonitor(config)
        self.profit_switcher = ProfitSwitcher(config)
        
        # Mining state
        self.current_algorithm = None
        self.mining_threads = []
        self.stats = MiningStats(
            hashrate=0.0,
            accepted_shares=0,
            rejected_shares=0,
            uptime=0.0,
            power_usage=0.0,
            temperature=0.0,
            efficiency=0.0
        )
        
        # Threading locks
        self._stats_lock = threading.Lock()
        self._control_lock = threading.Lock()
        
        logger.info("Advanced Miner initialized")
    
    def start(self):
        """Start the mining operation"""
        with self._control_lock:
            if self.running:
                logger.warning("Mining already running")
                return
            
            self.running = True
            logger.info("Starting advanced mining operation")
            
            # Start monitoring threads
            self.performance_monitor.start()
            self.profit_switcher.start()
            
            # Start main mining thread
            mining_thread = threading.Thread(target=self._mining_loop, daemon=True)
            mining_thread.start()
            self.mining_threads.append(mining_thread)
            
            # Start stats collection thread
            stats_thread = threading.Thread(target=self._stats_loop, daemon=True)
            stats_thread.start()
            self.mining_threads.append(stats_thread)
    
    def stop(self):
        """Stop the mining operation"""
        with self._control_lock:
            if not self.running:
                return
            
            self.running = False
            logger.info("Stopping mining operation")
            
            # Stop components
            self.performance_monitor.stop()
            self.profit_switcher.stop()
            
            # Wait for threads to finish
            for thread in self.mining_threads:
                if thread.is_alive():
                    thread.join(timeout=5)
            
            logger.info("Mining operation stopped")
    
    def pause(self):
        """Pause mining temporarily"""
        self.paused = True
        logger.info("Mining paused")
    
    def resume(self):
        """Resume mining after pause"""
        self.paused = False
        logger.info("Mining resumed")
    
    def _mining_loop(self):
        """Main mining loop"""
        start_time = time.time()
        
        while self.running:
            if self.paused:
                time.sleep(1)
                continue
            
            try:
                # Get best algorithm from profit switcher
                best_algorithm = self.profit_switcher.get_best_algorithm()
                
                if best_algorithm != self.current_algorithm:
                    self._switch_algorithm(best_algorithm)
                
                if self.current_algorithm:
                    # Mine one block/share
                    self._mine_iteration()
                
                # Small delay to prevent CPU overload
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in mining loop: {e}")
                time.sleep(1)
        
        # Update final uptime
        with self._stats_lock:
            self.stats.uptime = time.time() - start_time
    
    def _mine_iteration(self):
        """Execute one mining iteration"""
        if not self.current_algorithm:
            return
        
        try:
            # Generate work data
            work_data = self._generate_work_data()
            
            # Execute mining algorithm
            result = self.current_algorithm.mine(work_data)
            
            if result:
                # Process found share/block
                self._process_share(result)
            
            # Update hashrate
            self.performance_monitor.record_hash_attempt()
            
        except Exception as e:
            logger.error(f"Mining iteration error: {e}")
    
    def _generate_work_data(self) -> Dict[str, Any]:
        """Generate work data for mining"""
        return {
            "data": f"block_{int(time.time())}_{random.randint(0, 1000000)}",
            "difficulty": self.config.get("difficulty", 1.0),
            "target": self.config.get("target", "00000000"),
            "nonce": random.randint(0, 2**32 - 1)
        }
    
    def _process_share(self, result: Dict[str, Any]):
        """Process a found share/block"""
        with self._stats_lock:
            if result.get("valid", False):
                self.stats.accepted_shares += 1
                logger.info(f"Valid share found! Nonce: {result.get('nonce')}")
            else:
                self.stats.rejected_shares += 1
                logger.warning(f"Invalid share rejected: {result.get('nonce')}")
    
    def _switch_algorithm(self, new_algorithm_name: str):
        """Switch to a different mining algorithm"""
        try:
            logger.info(f"Switching to algorithm: {new_algorithm_name}")
            
            # Create new algorithm instance
            new_algorithm = self.algorithm_factory.create_algorithm(
                new_algorithm_name, self.config
            )
            
            # Stop current algorithm if running
            if self.current_algorithm:
                self.current_algorithm.stop()
            
            # Start new algorithm
            self.current_algorithm = new_algorithm
            self.current_algorithm.start()
            
            logger.info(f"Successfully switched to {new_algorithm_name}")
            
        except Exception as e:
            logger.error(f"Failed to switch algorithm: {e}")
    
    def _stats_loop(self):
        """Statistics collection loop"""
        while self.running:
            try:
                # Update performance metrics
                perf_data = self.performance_monitor.get_current_stats()
                
                with self._stats_lock:
                    self.stats.hashrate = perf_data.get("hashrate", 0.0)
                    self.stats.power_usage = perf_data.get("power_usage", 0.0)
                    self.stats.temperature = perf_data.get("temperature", 0.0)
                    
                    # Calculate efficiency (hashes per watt)
                    if self.stats.power_usage > 0:
                        self.stats.efficiency = self.stats.hashrate / self.stats.power_usage
                    else:
                        self.stats.efficiency = 0.0
                
                # Log stats every 30 seconds
                if int(time.time()) % 30 == 0:
                    self._log_stats()
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Stats loop error: {e}")
                time.sleep(5)
    
    def _log_stats(self):
        """Log current mining statistics"""
        with self._stats_lock:
            logger.info(
                f"Stats - Hashrate: {self.stats.hashrate:.2f} H/s | "
                f"Accepted: {self.stats.accepted_shares} | "
                f"Rejected: {self.stats.rejected_shares} | "
                f"Power: {self.stats.power_usage:.1f}W | "
                f"Temp: {self.stats.temperature:.1f}°C | "
                f"Efficiency: {self.stats.efficiency:.2f} H/W"
            )
    
    def get_stats(self) -> MiningStats:
        """Get current mining statistics"""
        with self._stats_lock:
            return MiningStats(**self.stats.__dict__)
    
    def is_running(self) -> bool:
        """Check if mining is running"""
        return self.running
    
    def get_algorithm_info(self) -> Optional[Dict[str, Any]]:
        """Get information about current algorithm"""
        if self.current_algorithm:
            return {
                "name": self.current_algorithm.name,
                "type": self.current_algorithm.algorithm_type,
                "performance": self.current_algorithm.get_performance()
            }
        return None
