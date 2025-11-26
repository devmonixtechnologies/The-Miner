"""
SHA-256 Mining Algorithm
Bitcoin and other SHA-256 based cryptocurrencies
"""

import hashlib
import time
from typing import Dict, Any, Optional

from .base import BaseAlgorithm


class SHA256Algorithm(BaseAlgorithm):
    """SHA-256 mining algorithm implementation"""
    
    def _initialize(self):
        """Initialize SHA-256 specific parameters"""
        self.target_difficulty = self.config.get("difficulty", 1.0)
        self.max_nonce = 2**32 - 1
        self.batch_size = self.config.get("batch_size", 1000)
        
    def get_algorithm_type(self) -> str:
        """Return algorithm type"""
        return "CPU"
    
    def mine(self, work_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Mine using SHA-256 algorithm
        Returns valid share if found
        """
        if not self.running:
            return None
        
        data = work_data.get("data", "")
        target = work_data.get("target", "00000000")
        difficulty = work_data.get("difficulty", self.target_difficulty)
        
        # Convert target to integer for comparison
        try:
            target_int = int(target, 16)
        except ValueError:
            target_int = self._get_target_from_difficulty(difficulty)
        
        # Mine in batches for efficiency
        for batch_start in range(0, self.batch_size, 100):
            if not self.running:
                return None
            
            for i in range(100):
                nonce = batch_start + i
                if nonce > self.max_nonce:
                    return None
                
                # Create block header
                block_header = f"{data}{nonce:08x}".encode()
                
                # Double SHA-256
                hash_result = hashlib.sha256(hashlib.sha256(block_header).digest()).hexdigest()
                
                self.record_hash()
                
                # Check if hash meets target
                hash_int = int(hash_result, 16)
                if hash_int < target_int:
                    return {
                        "valid": True,
                        "nonce": nonce,
                        "hash": hash_result,
                        "difficulty": difficulty,
                        "algorithm": "SHA-256",
                        "timestamp": time.time()
                    }
        
        return None
    
    def _get_target_from_difficulty(self, difficulty: float) -> int:
        """Calculate target from difficulty"""
        # Standard Bitcoin difficulty calculation
        max_target = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
        return int(max_target / difficulty)
    
    def _on_start(self):
        """Called when algorithm starts"""
        self.update_performance_data("optimization", "standard")
        self.update_performance_data("vectorized", False)
    
    def _on_stop(self):
        """Called when algorithm stops"""
        pass
