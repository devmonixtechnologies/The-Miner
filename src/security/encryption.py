"""
Security and Encryption Module
Production-grade security with API key encryption and access control
"""

import os
import json
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import secrets
import time

from utils.production_logger import get_production_logger


class SecurityManager:
    """Production-grade security manager for API keys and sensitive data"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_production_logger()
        
        # Security settings
        self.enable_encryption = config.get("security", {}).get("enable_api_key_encryption", True)
        self.max_failed_attempts = config.get("security", {}).get("max_failed_attempts", 3)
        self.require_wallet_auth = config.get("security", {}).get("require_wallet_auth", False)
        
        # Security paths
        self.security_dir = Path.home() / ".miner" / "security"
        self.security_dir.mkdir(parents=True, exist_ok=True)
        self.key_file = self.security_dir / "encryption.key"
        self.encrypted_config = self.security_dir / "encrypted.conf"
        self.auth_file = self.security_dir / "auth.json"
        
        # Failed attempts tracking
        self.failed_attempts = 0
        self.lockout_time = 0
        self.lockout_duration = 300  # 5 minutes
        
        # Initialize encryption
        self.fernet = None
        if self.enable_encryption:
            self._initialize_encryption()
        
        # Load authentication data
        self.auth_data = self._load_auth_data()
        
        if self.logger:
            self.logger.log_security_event("Security manager initialized", severity="INFO")
    
    def _initialize_encryption(self):
        """Initialize encryption key"""
        try:
            if self.key_file.exists():
                # Load existing key
                with open(self.key_file, 'rb') as f:
                    key = f.read()
                self.fernet = Fernet(key)
            else:
                # Generate new key
                key = Fernet.generate_key()
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                self.fernet = Fernet(key)
                
                # Set restrictive permissions
                os.chmod(self.key_file, 0o600)
                
                if self.logger:
                    self.logger.log_security_event("Generated new encryption key", severity="INFO")
        except Exception as e:
            if self.logger:
                self.logger.log_security_event(f"Encryption initialization failed: {e}", severity="CRITICAL")
            raise
    
    def _load_auth_data(self) -> Dict[str, Any]:
        """Load authentication data"""
        try:
            if self.auth_file.exists():
                with open(self.auth_file, 'r') as f:
                    return json.load(f)
            else:
                # Create default auth data
                auth_data = {
                    "session_tokens": {},
                    "failed_attempts": {},
                    "last_activity": {},
                    "created_at": time.time()
                }
                self._save_auth_data(auth_data)
                return auth_data
        except Exception as e:
            if self.logger:
                self.logger.log_security_event(f"Failed to load auth data: {e}", severity="WARNING")
            return {}
    
    def _save_auth_data(self, auth_data: Dict[str, Any]):
        """Save authentication data"""
        try:
            with open(self.auth_file, 'w') as f:
                json.dump(auth_data, f, indent=2)
            os.chmod(self.auth_file, 0o600)
        except Exception as e:
            if self.logger:
                self.logger.log_security_event(f"Failed to save auth data: {e}", severity="WARNING")
    
    def encrypt_api_keys(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt API keys in configuration"""
        if not self.enable_encryption or not self.fernet:
            return config
        
        encrypted_config = config.copy()
        sensitive_keys = [
            "etherscan_api_key",
            "infura_project_id",
            "mining_wallet_private_key"
        ]
        
        # Encrypt blockchain section
        if "blockchain" in encrypted_config:
            blockchain_config = encrypted_config["blockchain"].copy()
            
            for key in sensitive_keys:
                if key in blockchain_config and blockchain_config[key]:
                    try:
                        # Encrypt the value
                        encrypted_value = self.fernet.encrypt(blockchain_config[key].encode())
                        blockchain_config[key] = encrypted_value.decode()
                        
                        if self.logger:
                            self.logger.log_security_event(f"Encrypted API key: {key}", severity="INFO")
                    except Exception as e:
                        if self.logger:
                            self.logger.log_security_event(f"Failed to encrypt {key}: {e}", severity="WARNING")
            
            encrypted_config["blockchain"] = blockchain_config
        
        return encrypted_config
    
    def decrypt_api_keys(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt API keys in configuration"""
        if not self.enable_encryption or not self.fernet:
            return config
        
        decrypted_config = config.copy()
        sensitive_keys = [
            "etherscan_api_key",
            "infura_project_id",
            "mining_wallet_private_key"
        ]
        
        # Decrypt blockchain section
        if "blockchain" in decrypted_config:
            blockchain_config = decrypted_config["blockchain"].copy()
            
            for key in sensitive_keys:
                if key in blockchain_config and blockchain_config[key]:
                    try:
                        # Try to decrypt (might already be decrypted)
                        if isinstance(blockchain_config[key], str):
                            value = blockchain_config[key].encode()
                            try:
                                decrypted_value = self.fernet.decrypt(value).decode()
                                blockchain_config[key] = decrypted_value
                            except Exception:
                                # Already decrypted or invalid format
                                pass
                    except Exception as e:
                        if self.logger:
                            self.logger.log_security_event(f"Failed to decrypt {key}: {e}", severity="WARNING")
            
            decrypted_config["blockchain"] = blockchain_config
        
        return decrypted_config
    
    def save_encrypted_config(self, config: Dict[str, Any]):
        """Save configuration with encrypted API keys"""
        if not self.enable_encryption:
            return
        
        try:
            # Encrypt sensitive data
            encrypted_config = self.encrypt_api_keys(config)
            
            # Save to file
            with open(self.encrypted_config, 'w') as f:
                json.dump(encrypted_config, f, indent=2)
            
            os.chmod(self.encrypted_config, 0o600)
            
            if self.logger:
                self.logger.log_security_event("Saved encrypted configuration", severity="INFO")
        except Exception as e:
            if self.logger:
                self.logger.log_security_event(f"Failed to save encrypted config: {e}", severity="WARNING")
    
    def load_encrypted_config(self) -> Dict[str, Any]:
        """Load and decrypt configuration"""
        if not self.enable_encryption or not self.encrypted_config.exists():
            return {}
        
        try:
            with open(self.encrypted_config, 'r') as f:
                encrypted_config = json.load(f)
            
            # Decrypt sensitive data
            decrypted_config = self.decrypt_api_keys(encrypted_config)
            
            if self.logger:
                self.logger.log_security_event("Loaded encrypted configuration", severity="INFO")
            
            return decrypted_config
        except Exception as e:
            if self.logger:
                self.logger.log_security_event(f"Failed to load encrypted config: {e}", severity="WARNING")
            return {}
    
    def generate_session_token(self, user_id: str, duration: int = 3600) -> str:
        """Generate a secure session token"""
        try:
            # Generate random token
            token_data = f"{user_id}:{time.time()}:{secrets.token_urlsafe(32)}"
            token_hash = hashlib.sha256(token_data.encode()).hexdigest()
            
            # Store token data
            self.auth_data["session_tokens"][token_hash] = {
                "user_id": user_id,
                "created_at": time.time(),
                "expires_at": time.time() + duration,
                "last_activity": time.time()
            }
            
            self._save_auth_data(self.auth_data)
            
            if self.logger:
                self.logger.log_security_event(f"Generated session token for {user_id}", severity="INFO")
            
            return token_hash
        except Exception as e:
            if self.logger:
                self.logger.log_security_event(f"Failed to generate session token: {e}", severity="WARNING")
            return ""
    
    def validate_session_token(self, token: str) -> bool:
        """Validate a session token"""
        try:
            if token not in self.auth_data["session_tokens"]:
                return False
            
            token_data = self.auth_data["session_tokens"][token]
            current_time = time.time()
            
            # Check expiration
            if current_time > token_data["expires_at"]:
                del self.auth_data["session_tokens"][token]
                self._save_auth_data(self.auth_data)
                return False
            
            # Update last activity
            token_data["last_activity"] = current_time
            self._save_auth_data(self.auth_data)
            
            return True
        except Exception as e:
            if self.logger:
                self.logger.log_security_event(f"Failed to validate session token: {e}", severity="WARNING")
            return False
    
    def check_failed_attempts(self, identifier: str) -> bool:
        """Check if identifier is locked due to failed attempts"""
        current_time = time.time()
        
        # Reset lockout if duration has passed
        if self.lockout_time > 0 and current_time > self.lockout_time + self.lockout_duration:
            self.failed_attempts = 0
            self.lockout_time = 0
            if identifier in self.auth_data["failed_attempts"]:
                del self.auth_data["failed_attempts"][identifier]
        
        # Check if currently locked out
        if self.lockout_time > 0 and current_time < self.lockout_time + self.lockout_duration:
            return False
        
        # Check identifier-specific failed attempts
        if identifier in self.auth_data["failed_attempts"]:
            attempts = self.auth_data["failed_attempts"][identifier]
            if attempts >= self.max_failed_attempts:
                return False
        
        return True
    
    def record_failed_attempt(self, identifier: str):
        """Record a failed attempt"""
        self.failed_attempts += 1
        
        if identifier not in self.auth_data["failed_attempts"]:
            self.auth_data["failed_attempts"][identifier] = 0
        
        self.auth_data["failed_attempts"][identifier] += 1
        
        # Check for lockout
        if self.auth_data["failed_attempts"][identifier] >= self.max_failed_attempts:
            self.lockout_time = time.time()
            
            if self.logger:
                self.logger.log_security_event(
                    f"Account locked for {identifier} due to {self.max_failed_attempts} failed attempts",
                    severity="WARNING"
                )
        
        self._save_auth_data(self.auth_data)
    
    def record_successful_attempt(self, identifier: str):
        """Record a successful attempt and reset failed attempts"""
        if identifier in self.auth_data["failed_attempts"]:
            del self.auth_data["failed_attempts"][identifier]
        
        self.auth_data["last_activity"][identifier] = time.time()
        self._save_auth_data(self.auth_data)
        
        if self.logger:
            self.logger.log_security_event(f"Successful authentication for {identifier}", severity="INFO")
    
    def validate_wallet_address(self, address: str) -> bool:
        """Validate Ethereum wallet address format"""
        try:
            # Basic length check
            if not address or len(address) != 42:
                return False
            
            # Check if it starts with 0x
            if not address.startswith('0x'):
                return False
            
            # Check if the rest is hexadecimal
            hex_part = address[2:]
            if not all(c in '0123456789abcdefABCDEF' for c in hex_part):
                return False
            
            # Checksum validation (basic)
            try:
                # Convert to lowercase and hash
                address_lower = address.lower()
                address_hash = hashlib.sha256(address_lower.encode()).hexdigest()
                
                # Check checksum
                for i, c in enumerate(address[2:]):
                    if c.isupper():
                        # Should be uppercase if corresponding hash character >= 8
                        if int(address_hash[i], 16) < 8:
                            return False
                    else:
                        # Should be lowercase if corresponding hash character < 8
                        if int(address_hash[i], 16) >= 8:
                            return False
                
                return True
            except:
                # If checksum validation fails, still accept if format is correct
                return True
                
        except Exception as e:
            if self.logger:
                self.logger.log_security_event(f"Wallet address validation error: {e}", severity="WARNING")
            return False
    
    def sanitize_input(self, input_string: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not input_string:
            return ""
        
        # Remove dangerous characters
        dangerous_chars = ['<', '>', '&', '"', "'", ';', '|', '`', '$', '(', ')', '{', '}']
        sanitized = input_string
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Limit length
        sanitized = sanitized[:1000]
        
        return sanitized.strip()
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get security system status"""
        return {
            "encryption_enabled": self.enable_encryption,
            "key_file_exists": self.key_file.exists(),
            "encrypted_config_exists": self.encrypted_config.exists(),
            "failed_attempts": self.failed_attempts,
            "is_locked_out": time.time() < self.lockout_time + self.lockout_duration,
            "active_sessions": len(self.auth_data.get("session_tokens", {})),
            "security_dir": str(self.security_dir),
            "auth_required": self.require_wallet_auth
        }
    
    def cleanup_expired_sessions(self):
        """Clean up expired session tokens"""
        current_time = time.time()
        expired_tokens = []
        
        for token, data in self.auth_data.get("session_tokens", {}).items():
            if current_time > data["expires_at"]:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self.auth_data["session_tokens"][token]
        
        if expired_tokens:
            self._save_auth_data(self.auth_data)
            
            if self.logger:
                self.logger.log_security_event(
                    f"Cleaned up {len(expired_tokens)} expired sessions",
                    severity="INFO"
                )


# Global security manager instance
_security_manager = None


def setup_security(config: Dict[str, Any]) -> SecurityManager:
    """Setup security system"""
    global _security_manager
    _security_manager = SecurityManager(config)
    return _security_manager


def get_security_manager() -> Optional[SecurityManager]:
    """Get the security manager instance"""
    return _security_manager
