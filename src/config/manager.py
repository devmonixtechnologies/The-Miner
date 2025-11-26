"""
Configuration Management System
Handles loading, saving, and validating configuration
"""

import configparser
import json
import os
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MiningConfig:
    # Core mining settings
    default_algorithm: str = "sha256"
    mining_mode: str = "smart"  # solo, pool, smart
    difficulty: float = 1.0
    target: str = "00000000"
    
    # Performance settings
    cpu_threads: int = 4
    gpu_devices: list = None
    intensity: float = 0.8
    
    # Profit switching
    switch_strategy: str = "threshold"
    profit_update_interval: int = 60
    switch_threshold: float = 0.1
    min_switch_interval: int = 300
    enable_profit_switching: bool = True
    
    # Monitoring
    performance_update_interval: float = 1.0
    optimal_cpu_usage: float = 80.0
    optimal_temperature: float = 75.0
    max_temperature: float = 85.0
    
    # Pool settings
    pool_url: str = ""
    pool_user: str = ""
    pool_password: str = ""
    
    # Algorithm-specific settings
    sha256_batch_size: int = 1000
    ethash_cache_size: int = 33554432  # 32MB
    ethash_dataset_size: int = 4294967296  # 4GB
    randomx_dataset_size: int = 2147483648  # 2GB
    
    def __post_init__(self):
        if self.gpu_devices is None:
            self.gpu_devices = []


class ConfigManager:
    """Advanced configuration management system"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/default.conf"
        self.config = MiningConfig()
        self._config_format = "ini"  # ini, json
        
        logger.info(f"Config Manager initialized with path: {self.config_path}")
    
    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from file"""
        if config_path:
            self.config_path = config_path
        
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file not found: {self.config_path}. Creating default.")
            self.save_config()
            return self._load_ini_config()  # Return raw config dict
        
        try:
            # Determine file format
            if self.config_path.endswith('.json'):
                self._config_format = "json"
                config_dict = self._load_json_config()
            else:
                self._config_format = "ini"
                config_dict = self._load_ini_config()
            
            # Update config object
            self._update_config_from_dict(config_dict)
            
            # Validate configuration
            self._validate_config()
            
            logger.info(f"Configuration loaded from {self.config_path}")
            return config_dict  # Return raw config dict
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            logger.info("Using default configuration")
            return self._load_ini_config()  # Return raw config dict
    
    def save_config(self, config_path: Optional[str] = None) -> bool:
        """Save configuration to file"""
        if config_path:
            self.config_path = config_path
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            config_dict = asdict(self.config)
            
            if self._config_format == "json":
                self._save_json_config(config_dict)
            else:
                self._save_ini_config(config_dict)
            
            logger.info(f"Configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def get_config(self) -> MiningConfig:
        """Get current configuration object"""
        return self.config
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return asdict(self.config)
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update configuration with new values"""
        try:
            for key, value in updates.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                else:
                    logger.warning(f"Unknown config key: {key}")
            
            # Validate after update
            self._validate_config()
            
            logger.info("Configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return False
    
    def reset_to_defaults(self):
        """Reset configuration to default values"""
        self.config = MiningConfig()
        logger.info("Configuration reset to defaults")
    
    def _load_ini_config(self) -> Dict[str, Any]:
        """Load configuration from INI file"""
        parser = configparser.ConfigParser()
        parser.read(self.config_path)
        
        config_dict = {}
        
        # Parse each section
        for section_name in parser.sections():
            section_dict = {}
            for key, value in parser[section_name].items():
                # Try to parse as different types
                section_dict[key] = self._parse_config_value(value)
            config_dict[section_name] = section_dict
        
        return config_dict
    
    def _load_json_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def _save_ini_config(self, config_dict: Dict[str, Any]):
        """Save configuration to INI file"""
        parser = configparser.ConfigParser()
        
        # Group settings by category
        sections = {
            "mining": [
                "default_algorithm", "mining_mode", "difficulty", "target",
                "cpu_threads", "gpu_devices", "intensity"
            ],
            "blockchain": [
                "network", "infura_project_id", "etherscan_api_key", 
                "mining_wallet_address", "auto_update_wallet",
                "pool_address", "pool_fee", "payout_threshold"
            ],
            "profit_switching": [
                "switch_strategy", "profit_update_interval", "switch_threshold",
                "min_switch_interval", "enable_profit_switching"
            ],
            "monitoring": [
                "performance_update_interval", "optimal_cpu_usage",
                "optimal_temperature", "max_temperature"
            ],
            "pool": [
                "pool_url", "pool_user", "pool_password"
            ],
            "algorithms": [
                "sha256_batch_size", "ethash_cache_size", "ethash_dataset_size",
                "randomx_dataset_size"
            ]
        }
        
        # Create sections and add settings
        for section_name, keys in sections.items():
            parser.add_section(section_name)
            for key in keys:
                if key in config_dict:
                    value = config_dict[key]
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value)
                    parser.set(section_name, key, str(value))
        
        # Write to file
        with open(self.config_path, 'w') as f:
            parser.write(f)
    
    def _save_json_config(self, config_dict: Dict[str, Any]):
        """Save configuration to JSON file"""
        with open(self.config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def _update_config_from_dict(self, config_dict: Dict[str, Any]):
        """Update config object from dictionary"""
        # Handle INI format (nested sections)
        if "mining" in config_dict:
            for key, value in config_dict["mining"].items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        
        if "profit_switching" in config_dict:
            for key, value in config_dict["profit_switching"].items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        
        if "monitoring" in config_dict:
            for key, value in config_dict["monitoring"].items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        
        if "pool" in config_dict:
            for key, value in config_dict["pool"].items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        
        if "algorithms" in config_dict:
            for key, value in config_dict["algorithms"].items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        
        # Handle flat JSON format
        for key, value in config_dict.items():
            if hasattr(self.config, key) and not isinstance(value, dict):
                setattr(self.config, key, value)
    
    def _parse_config_value(self, value: str) -> Union[str, int, float, bool, list]:
        """Parse configuration value to appropriate type"""
        # Try boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Try JSON (for lists and dicts)
        try:
            return json.loads(value)
        except ValueError:
            pass
        
        # Default to string
        return value
    
    def _validate_config(self):
        """Validate configuration values"""
        # Validate algorithm
        valid_algorithms = ["sha256", "ethash", "randomx"]
        if self.config.default_algorithm not in valid_algorithms:
            logger.warning(f"Invalid algorithm: {self.config.default_algorithm}")
            self.config.default_algorithm = "sha256"
        
        # Validate mining mode
        valid_modes = ["solo", "pool", "smart"]
        if self.config.mining_mode not in valid_modes:
            logger.warning(f"Invalid mining mode: {self.config.mining_mode}")
            self.config.mining_mode = "smart"
        
        # Validate switch strategy
        valid_strategies = ["immediate", "gradual", "threshold", "predictive"]
        if self.config.switch_strategy not in valid_strategies:
            logger.warning(f"Invalid switch strategy: {self.config.switch_strategy}")
            self.config.switch_strategy = "threshold"
        
        # Validate ranges
        if not 0.0 <= self.config.intensity <= 1.0:
            logger.warning("Invalid intensity value, setting to 0.8")
            self.config.intensity = 0.8
        
        if self.config.cpu_threads < 1:
            self.config.cpu_threads = 1
        
        if self.config.max_temperature <= self.config.optimal_temperature:
            logger.warning("Max temperature should be higher than optimal")
            self.config.max_temperature = self.config.optimal_temperature + 10
    
    def create_profile(self, profile_name: str, description: str = "") -> bool:
        """Create a configuration profile"""
        try:
            profiles_dir = "config/profiles"
            os.makedirs(profiles_dir, exist_ok=True)
            
            profile_path = os.path.join(profiles_dir, f"{profile_name}.json")
            
            profile_data = {
                "name": profile_name,
                "description": description,
                "config": asdict(self.config),
                "created_at": str(os.path.getmtime(self.config_path) if os.path.exists(self.config_path) else 0)
            }
            
            with open(profile_path, 'w') as f:
                json.dump(profile_data, f, indent=2)
            
            logger.info(f"Profile created: {profile_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating profile: {e}")
            return False
    
    def load_profile(self, profile_name: str) -> bool:
        """Load a configuration profile"""
        try:
            profile_path = f"config/profiles/{profile_name}.json"
            
            if not os.path.exists(profile_path):
                logger.error(f"Profile not found: {profile_name}")
                return False
            
            with open(profile_path, 'r') as f:
                profile_data = json.load(f)
            
            config_dict = profile_data.get("config", {})
            self._update_config_from_dict(config_dict)
            self._validate_config()
            
            logger.info(f"Profile loaded: {profile_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading profile: {e}")
            return False
    
    def list_profiles(self) -> Dict[str, str]:
        """List available configuration profiles"""
        profiles = {}
        profiles_dir = "config/profiles"
        
        if os.path.exists(profiles_dir):
            for filename in os.listdir(profiles_dir):
                if filename.endswith('.json'):
                    profile_name = filename[:-5]  # Remove .json extension
                    try:
                        with open(os.path.join(profiles_dir, filename), 'r') as f:
                            profile_data = json.load(f)
                            profiles[profile_name] = profile_data.get("description", "")
                    except:
                        profiles[profile_name] = "Error loading description"
        
        return profiles
