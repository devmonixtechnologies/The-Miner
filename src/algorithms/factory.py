"""
Algorithm Factory
Creates and manages mining algorithm instances
"""

from typing import Dict, Any, Type
from .base import BaseAlgorithm
from .sha256 import SHA256Algorithm
from .ethash import EthashAlgorithm
from .randomx import RandomXAlgorithm


class AlgorithmFactory:
    """Factory for creating mining algorithm instances"""
    
    def __init__(self):
        self._algorithms: Dict[str, Type[BaseAlgorithm]] = {
            "sha256": SHA256Algorithm,
            "ethash": EthashAlgorithm,
            "randomx": RandomXAlgorithm,
        }
        
        self._algorithm_info = {
            "sha256": {
                "name": "SHA-256",
                "description": "Bitcoin and SHA-256 based cryptocurrencies",
                "type": "CPU",
                "difficulty": "Low",
                "power_usage": "Medium",
                "efficiency": "High"
            },
            "ethash": {
                "name": "Ethash",
                "description": "Ethereum and Ethash based cryptocurrencies",
                "type": "GPU",
                "difficulty": "Medium",
                "power_usage": "High",
                "efficiency": "Medium"
            },
            "randomx": {
                "name": "RandomX",
                "description": "Monero and RandomX based cryptocurrencies",
                "type": "CPU",
                "difficulty": "High",
                "power_usage": "Medium",
                "efficiency": "Low"
            }
        }
    
    def create_algorithm(self, algorithm_name: str, config: Dict[str, Any]) -> BaseAlgorithm:
        """
        Create an algorithm instance
        
        Args:
            algorithm_name: Name of the algorithm to create
            config: Configuration parameters
            
        Returns:
            Algorithm instance
            
        Raises:
            ValueError: If algorithm is not supported
        """
        algorithm_name = algorithm_name.lower()
        
        if algorithm_name not in self._algorithms:
            raise ValueError(f"Unsupported algorithm: {algorithm_name}")
        
        algorithm_class = self._algorithms[algorithm_name]
        return algorithm_class(algorithm_name, config)
    
    def get_available_algorithms(self) -> Dict[str, Dict[str, str]]:
        """Get information about all available algorithms"""
        return self._algorithm_info.copy()
    
    def get_algorithm_info(self, algorithm_name: str) -> Dict[str, str]:
        """Get information about a specific algorithm"""
        algorithm_name = algorithm_name.lower()
        
        if algorithm_name not in self._algorithm_info:
            raise ValueError(f"Unsupported algorithm: {algorithm_name}")
        
        return self._algorithm_info[algorithm_name].copy()
    
    def register_algorithm(self, algorithm_name: str, algorithm_class: Type[BaseAlgorithm], 
                          info: Dict[str, str]):
        """
        Register a new algorithm
        
        Args:
            algorithm_name: Name of the algorithm
            algorithm_class: Algorithm class
            info: Algorithm information
        """
        algorithm_name = algorithm_name.lower()
        
        self._algorithms[algorithm_name] = algorithm_class
        self._algorithm_info[algorithm_name] = info
    
    def is_supported(self, algorithm_name: str) -> bool:
        """Check if an algorithm is supported"""
        return algorithm_name.lower() in self._algorithms
    
    def get_algorithms_by_type(self, algorithm_type: str) -> Dict[str, Dict[str, str]]:
        """Get algorithms filtered by type (CPU, GPU, ASIC)"""
        filtered = {}
        
        for name, info in self._algorithm_info.items():
            if info.get("type", "").upper() == algorithm_type.upper():
                filtered[name] = info
        
        return filtered
