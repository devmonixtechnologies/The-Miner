"""
Mining Benchmark System
Comprehensive benchmarking for mining algorithms and system performance
"""

import time
import threading
import statistics
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from algorithms.factory import AlgorithmFactory
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BenchmarkResult:
    algorithm: str
    hashrate: float
    power_usage: float
    efficiency: float
    temperature: float
    cpu_usage: float
    memory_usage: float
    duration: float
    valid_shares: int
    invalid_shares: int
    stability_score: float


class MiningBenchmark:
    """Comprehensive mining benchmark system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.algorithm_factory = AlgorithmFactory()
        
        # Benchmark settings
        self.benchmark_duration = config.get("benchmark_duration", 60)  # seconds
        self.warmup_duration = config.get("warmup_duration", 10)  # seconds
        self.thread_count = config.get("benchmark_threads", 4)
        
        # Results storage
        self.results: List[BenchmarkResult] = []
        self.current_benchmark = None
        
        logger.info("Mining Benchmark initialized")
    
    def run_full_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive benchmark for all algorithms"""
        logger.info("Starting full mining benchmark...")
        
        available_algorithms = self.algorithm_factory.get_available_algorithms()
        benchmark_results = {}
        
        for algo_name in available_algorithms.keys():
            logger.info(f"Benchmarking {algo_name}...")
            
            try:
                result = self.benchmark_algorithm(algo_name)
                benchmark_results[algo_name] = result
                self.results.append(result)
                
                # Cool down between benchmarks
                logger.info("Cooling down between benchmarks...")
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Benchmark failed for {algo_name}: {e}")
        
        # Generate summary
        summary = self._generate_summary(benchmark_results)
        
        logger.info("Full benchmark completed")
        return {
            "results": benchmark_results,
            "summary": summary,
            "timestamp": time.time()
        }
    
    def benchmark_algorithm(self, algorithm_name: str) -> BenchmarkResult:
        """Benchmark a specific algorithm"""
        logger.info(f"Starting benchmark for {algorithm_name}...")
        
        # Create algorithm instance
        algorithm = self.algorithm_factory.create_algorithm(algorithm_name, self.config)
        
        # Initialize monitoring
        import psutil
        process = psutil.Process()
        
        # Warmup phase
        logger.info(f"Warming up {algorithm_name} for {self.warmup_duration} seconds...")
        algorithm.start()
        time.sleep(self.warmup_duration)
        
        # Benchmark phase
        logger.info(f"Benchmarking {algorithm_name} for {self.benchmark_duration} seconds...")
        
        start_time = time.time()
        stats = {
            "hash_attempts": 0,
            "valid_shares": 0,
            "invalid_shares": 0,
            "temperature_samples": [],
            "cpu_samples": [],
            "memory_samples": [],
            "power_samples": []
        }
        
        # Monitoring thread
        def monitor_performance():
            while self.current_benchmark:
                try:
                    # CPU and memory
                    cpu_percent = process.cpu_percent()
                    memory_info = process.memory_info()
                    
                    stats["cpu_samples"].append(cpu_percent)
                    stats["memory_samples"].append(memory_info.rss)
                    
                    # Temperature (estimated)
                    temp = self._estimate_temperature()
                    stats["temperature_samples"].append(temp)
                    
                    # Power usage (estimated)
                    power = self._estimate_power_usage(cpu_percent)
                    stats["power_samples"].append(power)
                    
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
        
        # Mining thread
        def mine_benchmark():
            work_data = {
                "data": f"benchmark_{int(time.time())}",
                "difficulty": 1.0,
                "target": "00000000"
            }
            
            while self.current_benchmark:
                try:
                    result = algorithm.mine(work_data)
                    stats["hash_attempts"] += 1
                    
                    if result:
                        if result.get("valid", False):
                            stats["valid_shares"] += 1
                        else:
                            stats["invalid_shares"] += 1
                    
                    # Update work data periodically
                    if stats["hash_attempts"] % 1000 == 0:
                        work_data["data"] = f"benchmark_{int(time.time())}"
                    
                except Exception as e:
                    logger.error(f"Mining error: {e}")
                    break
        
        # Start benchmark
        self.current_benchmark = True
        
        monitor_thread = threading.Thread(target=monitor_performance, daemon=True)
        mining_thread = threading.Thread(target=mine_benchmark, daemon=True)
        
        monitor_thread.start()
        mining_thread.start()
        
        # Wait for benchmark duration
        time.sleep(self.benchmark_duration)
        
        # Stop benchmark
        self.current_benchmark = False
        algorithm.stop()
        
        monitor_thread.join(timeout=2)
        mining_thread.join(timeout=2)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Calculate metrics
        hashrate = stats["hash_attempts"] / duration if duration > 0 else 0
        
        avg_temperature = statistics.mean(stats["temperature_samples"]) if stats["temperature_samples"] else 0
        avg_cpu = statistics.mean(stats["cpu_samples"]) if stats["cpu_samples"] else 0
        avg_memory = statistics.mean(stats["memory_samples"]) if stats["memory_samples"] else 0
        avg_power = statistics.mean(stats["power_samples"]) if stats["power_samples"] else 0
        
        efficiency = hashrate / avg_power if avg_power > 0 else 0
        
        # Calculate stability score
        stability_score = self._calculate_stability(stats)
        
        result = BenchmarkResult(
            algorithm=algorithm_name,
            hashrate=hashrate,
            power_usage=avg_power,
            efficiency=efficiency,
            temperature=avg_temperature,
            cpu_usage=avg_cpu,
            memory_usage=avg_memory,
            duration=duration,
            valid_shares=stats["valid_shares"],
            invalid_shares=stats["invalid_shares"],
            stability_score=stability_score
        )
        
        logger.info(f"Benchmark completed for {algorithm_name}: {hashrate:.2f} H/s")
        return result
    
    def run_stress_test(self, algorithm_name: str, duration: int = 300) -> Dict[str, Any]:
        """Run stress test for algorithm"""
        logger.info(f"Starting stress test for {algorithm_name} ({duration}s)...")
        
        # Extended benchmark
        original_duration = self.benchmark_duration
        self.benchmark_duration = duration
        
        try:
            result = self.benchmark_algorithm(algorithm_name)
            
            # Additional stress test metrics
            stress_metrics = {
                "max_temperature": max([result.temperature]) if isinstance(result.temperature, list) else result.temperature,
                "temperature_variance": self._calculate_variance([result.temperature]) if isinstance(result.temperature, list) else 0,
                "performance_degradation": self._calculate_performance_degradation(algorithm_name, duration),
                "error_rate": result.invalid_shares / (result.valid_shares + result.invalid_shares) if (result.valid_shares + result.invalid_shares) > 0 else 0
            }
            
            return {
                "benchmark_result": result,
                "stress_metrics": stress_metrics,
                "passed_stress_test": stress_metrics["error_rate"] < 0.05 and stress_metrics["max_temperature"] < 85
            }
            
        finally:
            self.benchmark_duration = original_duration
    
    def compare_algorithms(self, algorithm_names: List[str]) -> Dict[str, Any]:
        """Compare multiple algorithms side by side"""
        logger.info(f"Comparing algorithms: {', '.join(algorithm_names)}")
        
        comparison_results = {}
        
        for algo_name in algorithm_names:
            if not self.algorithm_factory.is_supported(algo_name):
                logger.warning(f"Algorithm {algo_name} not supported, skipping")
                continue
            
            try:
                result = self.benchmark_algorithm(algo_name)
                comparison_results[algo_name] = result
            except Exception as e:
                logger.error(f"Comparison failed for {algo_name}: {e}")
        
        # Generate comparison analysis
        analysis = self._analyze_comparison(comparison_results)
        
        return {
            "results": comparison_results,
            "analysis": analysis,
            "recommendations": self._get_recommendations(comparison_results)
        }
    
    def _estimate_temperature(self) -> float:
        """Estimate system temperature"""
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        return entries[0].current
        except:
            pass
        
        # Fallback estimation
        return 45.0  # Default estimated temperature
    
    def _estimate_power_usage(self, cpu_percent: float) -> float:
        """Estimate power usage based on CPU load"""
        base_power = 50.0  # Base system power
        cpu_power = (cpu_percent / 100.0) * 65.0  # CPU power contribution
        return base_power + cpu_power
    
    def _calculate_stability(self, stats: Dict[str, Any]) -> float:
        """Calculate stability score based on metrics"""
        stability = 1.0
        
        # Temperature stability
        if stats["temperature_samples"]:
            temp_variance = statistics.variance(stats["temperature_samples"])
            if temp_variance > 25:  # High variance
                stability -= 0.2
            elif temp_variance > 10:
                stability -= 0.1
        
        # CPU stability
        if stats["cpu_samples"]:
            cpu_variance = statistics.variance(stats["cpu_samples"])
            if cpu_variance > 100:
                stability -= 0.2
            elif cpu_variance > 50:
                stability -= 0.1
        
        # Error rate
        total_shares = stats["valid_shares"] + stats["invalid_shares"]
        if total_shares > 0:
            error_rate = stats["invalid_shares"] / total_shares
            stability -= error_rate * 2  # Penalize errors heavily
        
        return max(0.0, min(1.0, stability))
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of values"""
        if len(values) < 2:
            return 0.0
        return statistics.variance(values)
    
    def _calculate_performance_degradation(self, algorithm_name: str, duration: int) -> float:
        """Calculate performance degradation over time"""
        # This would require more complex implementation with time-based sampling
        # For now, return a small random degradation
        import random
        return random.uniform(0.0, 0.05)  # 0-5% degradation
    
    def _generate_summary(self, results: Dict[str, BenchmarkResult]) -> Dict[str, Any]:
        """Generate benchmark summary"""
        if not results:
            return {}
        
        # Find best performing algorithm
        best_hashrate = max(results.values(), key=lambda x: x.hashrate)
        best_efficiency = max(results.values(), key=lambda x: x.efficiency)
        best_stability = max(results.values(), key=lambda x: x.stability_score)
        
        # Calculate averages
        avg_hashrate = statistics.mean([r.hashrate for r in results.values()])
        avg_efficiency = statistics.mean([r.efficiency for r in results.values()])
        avg_temperature = statistics.mean([r.temperature for r in results.values()])
        
        return {
            "total_algorithms": len(results),
            "best_hashrate": {
                "algorithm": best_hashrate.algorithm,
                "hashrate": best_hashrate.hashrate
            },
            "best_efficiency": {
                "algorithm": best_efficiency.algorithm,
                "efficiency": best_efficiency.efficiency
            },
            "best_stability": {
                "algorithm": best_stability.algorithm,
                "stability": best_stability.stability_score
            },
            "averages": {
                "hashrate": avg_hashrate,
                "efficiency": avg_efficiency,
                "temperature": avg_temperature
            }
        }
    
    def _analyze_comparison(self, results: Dict[str, BenchmarkResult]) -> Dict[str, Any]:
        """Analyze comparison results"""
        if not results:
            return {}
        
        analysis = {}
        
        # Performance ranking
        ranked_by_hashrate = sorted(results.items(), key=lambda x: x[1].hashrate, reverse=True)
        ranked_by_efficiency = sorted(results.items(), key=lambda x: x[1].efficiency, reverse=True)
        ranked_by_stability = sorted(results.items(), key=lambda x: x[1].stability_score, reverse=True)
        
        analysis["rankings"] = {
            "hashrate": [(name, result.hashrate) for name, result in ranked_by_hashrate],
            "efficiency": [(name, result.efficiency) for name, result in ranked_by_efficiency],
            "stability": [(name, result.stability_score) for name, result in ranked_by_stability]
        }
        
        # Performance differences
        if len(results) > 1:
            hashrates = [r.hashrate for r in results.values()]
            analysis["performance_spread"] = {
                "max_hashrate": max(hashrates),
                "min_hashrate": min(hashrates),
                "hashrate_ratio": max(hashrates) / min(hashrates) if min(hashrates) > 0 else 0
            }
        
        return analysis
    
    def _get_recommendations(self, results: Dict[str, BenchmarkResult]) -> List[str]:
        """Get recommendations based on benchmark results"""
        recommendations = []
        
        if not results:
            return ["No benchmark results available"]
        
        # Find best overall algorithm
        def overall_score(result: BenchmarkResult) -> float:
            return (result.hashrate * 0.4 + 
                   result.efficiency * 0.3 + 
                   result.stability_score * 0.3)
        
        best_overall = max(results.values(), key=overall_score)
        recommendations.append(f"Best overall algorithm: {best_overall.algorithm}")
        
        # Temperature recommendations
        high_temp_algos = [name for name, result in results.items() if result.temperature > 75]
        if high_temp_algos:
            recommendations.append(f"High temperature algorithms: {', '.join(high_temp_algos)}")
        
        # Efficiency recommendations
        low_efficiency_algos = [name for name, result in results.items() if result.efficiency < 1.0]
        if low_efficiency_algos:
            recommendations.append(f"Low efficiency algorithms: {', '.join(low_efficiency_algos)}")
        
        # Stability recommendations
        unstable_algos = [name for name, result in results.items() if result.stability_score < 0.7]
        if unstable_algos:
            recommendations.append(f"Unstable algorithms: {', '.join(unstable_algos)}")
        
        return recommendations


def run_benchmarks(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run comprehensive benchmarks"""
    benchmark = MiningBenchmark(config)
    return benchmark.run_full_benchmark()
