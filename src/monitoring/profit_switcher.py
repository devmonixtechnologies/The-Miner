"""
Intelligent Profit Switching Algorithm
Automatically switches between algorithms based on profitability
"""

import threading
import time
import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from algorithms.factory import AlgorithmFactory
from utils.logger import get_logger

logger = get_logger(__name__)


class SwitchStrategy(Enum):
    IMMEDIATE = "immediate"
    GRADUAL = "gradual"
    THRESHOLD = "threshold"
    PREDICTIVE = "predictive"


@dataclass
class ProfitabilityData:
    algorithm: str
    hashrate: float
    power_usage: float
    revenue_per_hour: float
    cost_per_hour: float
    profit_per_hour: float
    efficiency: float
    timestamp: float


class ProfitSwitcher:
    """Intelligent profit switching system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False
        self.algorithm_factory = AlgorithmFactory()
        
        # Configuration
        self.switch_strategy = SwitchStrategy(config.get("switch_strategy", "threshold"))
        self.update_interval = config.get("profit_update_interval", 60)  # seconds
        self.switch_threshold = config.get("switch_threshold", 0.1)  # 10% improvement
        self.min_switch_interval = config.get("min_switch_interval", 300)  # 5 minutes
        
        # State
        self.current_algorithm = None
        self.profitability_data: Dict[str, ProfitabilityData] = {}
        self.switch_history: List[Tuple[float, str, str]] = []  # (timestamp, from, to)
        self.last_switch_time = 0
        
        # Threading
        self._lock = threading.Lock()
        self._update_thread = None
        
        # Market data simulation (in real implementation, would use APIs)
        self.market_prices = {
            "BTC": 45000.0,
            "ETH": 3000.0,
            "XMR": 200.0
        }
        
        logger.info("Profit Switcher initialized")
    
    def start(self):
        """Start profit monitoring"""
        if self.running:
            return
        
        self.running = True
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
        
        logger.info("Profit switcher started")
    
    def stop(self):
        """Stop profit monitoring"""
        self.running = False
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=5)
        
        logger.info("Profit switcher stopped")
    
    def get_best_algorithm(self) -> str:
        """Get the currently most profitable algorithm"""
        with self._lock:
            if not self.profitability_data:
                return self._get_default_algorithm()
            
            # Sort by profit per hour
            sorted_algorithms = sorted(
                self.profitability_data.items(),
                key=lambda x: x[1].profit_per_hour,
                reverse=True
            )
            
            best_algorithm = sorted_algorithms[0][0]
            
            # Check if we should switch
            if self._should_switch(best_algorithm):
                return best_algorithm
            else:
                return self.current_algorithm or self._get_default_algorithm()
    
    def _should_switch(self, new_algorithm: str) -> bool:
        """Determine if we should switch to a new algorithm"""
        if not self.current_algorithm:
            return True
        
        if self.current_algorithm == new_algorithm:
            return False
        
        # Check minimum switch interval
        current_time = time.time()
        if current_time - self.last_switch_time < self.min_switch_interval:
            return False
        
        # Get profitability data
        current_data = self.profitability_data.get(self.current_algorithm)
        new_data = self.profitability_data.get(new_algorithm)
        
        if not current_data or not new_data:
            return False
        
        # Apply switching strategy
        if self.switch_strategy == SwitchStrategy.IMMEDIATE:
            return new_data.profit_per_hour > current_data.profit_per_hour
        
        elif self.switch_strategy == SwitchStrategy.THRESHOLD:
            improvement = (new_data.profit_per_hour - current_data.profit_per_hour) / current_data.profit_per_hour
            return improvement >= self.switch_threshold
        
        elif self.switch_strategy == SwitchStrategy.GRADUAL:
            # Consider switching cost and stability
            improvement = (new_data.profit_per_hour - current_data.profit_per_hour) / current_data.profit_per_hour
            return improvement >= self.switch_threshold * 0.5  # Lower threshold for gradual
        
        elif self.switch_strategy == SwitchStrategy.PREDICTIVE:
            # Consider future trends
            return self._predictive_switch_decision(current_data, new_data)
        
        return False
    
    def _predictive_switch_decision(self, current_data: ProfitabilityData, new_data: ProfitabilityData) -> bool:
        """Make predictive switching decision based on trends"""
        # Get historical data for trend analysis
        current_history = self._get_algorithm_history(current_data.algorithm)
        new_history = self._get_algorithm_history(new_data.algorithm)
        
        if len(current_history) < 3 or len(new_history) < 3:
            # Fall back to threshold strategy
            improvement = (new_data.profit_per_hour - current_data.profit_per_hour) / current_data.profit_per_hour
            return improvement >= self.switch_threshold
        
        # Calculate trends
        current_trend = self._calculate_trend(current_history)
        new_trend = self._calculate_trend(new_history)
        
        # Predict future performance
        current_predicted = current_data.profit_per_hour + current_trend * 10  # 10 minutes ahead
        new_predicted = new_data.profit_per_hour + new_trend * 10
        
        # Switch if new algorithm is predicted to be better
        return new_predicted > current_predicted * 1.05  # 5% margin
    
    def _get_algorithm_history(self, algorithm: str, minutes: int = 30) -> List[float]:
        """Get historical profitability data for an algorithm"""
        cutoff_time = time.time() - (minutes * 60)
        history = []
        
        for timestamp, from_algo, to_algo in self.switch_history:
            if timestamp >= cutoff_time and (from_algo == algorithm or to_algo == algorithm):
                data = self.profitability_data.get(algorithm)
                if data:
                    history.append(data.profit_per_hour)
        
        return history
    
    def _calculate_trend(self, history: List[float]) -> float:
        """Calculate trend from historical data"""
        if len(history) < 2:
            return 0.0
        
        # Simple linear regression
        n = len(history)
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(history)
        sum_xy = sum(x[i] * history[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        return slope
    
    def _update_loop(self):
        """Main update loop for profitability data"""
        while self.running:
            try:
                self._update_profitability_data()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error updating profitability data: {e}")
                time.sleep(10)
    
    def _update_profitability_data(self):
        """Update profitability data for all algorithms"""
        algorithms = self.algorithm_factory.get_available_algorithms()
        
        for algorithm_name in algorithms.keys():
            try:
                profit_data = self._calculate_profitability(algorithm_name)
                
                with self._lock:
                    self.profitability_data[algorithm_name] = profit_data
                
            except Exception as e:
                logger.error(f"Error calculating profitability for {algorithm_name}: {e}")
    
    def _calculate_profitability(self, algorithm_name: str) -> ProfitabilityData:
        """Calculate profitability for a specific algorithm"""
        # Simulate hashrate based on algorithm type
        algorithm_info = self.algorithm_factory.get_algorithm_info(algorithm_name)
        algo_type = algorithm_info.get("type", "CPU")
        
        if algo_type == "CPU":
            hashrate = random.uniform(1000, 10000)  # H/s
            power_usage = random.uniform(50, 150)  # Watts
        elif algo_type == "GPU":
            hashrate = random.uniform(100000, 1000000)  # H/s
            power_usage = random.uniform(200, 400)  # Watts
        else:  # ASIC
            hashrate = random.uniform(10000000, 100000000)  # H/s
            power_usage = random.uniform(1000, 2000)  # Watts
        
        # Calculate revenue based on market prices
        if algorithm_name == "sha256":
            coin = "BTC"
            block_reward = 6.25
            difficulty = random.uniform(20000000000000, 30000000000000)
        elif algorithm_name == "ethash":
            coin = "ETH"
            block_reward = 2.0
            difficulty = random.uniform(5000, 15000)
        else:  # randomx
            coin = "XMR"
            block_reward = 0.6
            difficulty = random.uniform(300000000000, 500000000000)
        
        # Simplified profitability calculation
        market_price = self.market_prices.get(coin, 1000)
        blocks_per_hour = 3600 / (difficulty / hashrate) / 1000000  # Simplified
        revenue_per_hour = blocks_per_hour * block_reward * market_price
        
        # Calculate costs
        electricity_cost = 0.12  # $/kWh
        cost_per_hour = (power_usage / 1000) * electricity_cost
        
        # Calculate profit and efficiency
        profit_per_hour = revenue_per_hour - cost_per_hour
        efficiency = hashrate / power_usage if power_usage > 0 else 0
        
        return ProfitabilityData(
            algorithm=algorithm_name,
            hashrate=hashrate,
            power_usage=power_usage,
            revenue_per_hour=revenue_per_hour,
            cost_per_hour=cost_per_hour,
            profit_per_hour=profit_per_hour,
            efficiency=efficiency,
            timestamp=time.time()
        )
    
    def _get_default_algorithm(self) -> str:
        """Get default algorithm"""
        return self.config.get("default_algorithm", "sha256")
    
    def record_switch(self, from_algorithm: str, to_algorithm: str):
        """Record an algorithm switch"""
        with self._lock:
            self.switch_history.append((time.time(), from_algorithm, to_algorithm))
            self.current_algorithm = to_algorithm
            self.last_switch_time = time.time()
            
            # Keep only last 100 switches
            if len(self.switch_history) > 100:
                self.switch_history = self.switch_history[-100:]
        
        logger.info(f"Switched from {from_algorithm} to {to_algorithm}")
    
    def get_profitability_summary(self) -> Dict[str, Any]:
        """Get summary of current profitability data"""
        with self._lock:
            summary = {
                "current_algorithm": self.current_algorithm,
                "last_update": time.time(),
                "algorithms": {}
            }
            
            for algo_name, data in self.profitability_data.items():
                summary["algorithms"][algo_name] = {
                    "hashrate": data.hashrate,
                    "power_usage": data.power_usage,
                    "profit_per_hour": data.profit_per_hour,
                    "efficiency": data.efficiency
                }
            
            return summary
    
    def get_switch_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent switch history"""
        with self._lock:
            history = []
            for timestamp, from_algo, to_algo in self.switch_history[-limit:]:
                history.append({
                    "timestamp": timestamp,
                    "from": from_algo,
                    "to": to_algo
                })
            return history
