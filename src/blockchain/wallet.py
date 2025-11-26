"""
Blockchain Wallet Integration
MetaMask and wallet management for mining earnings
"""

import json
import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from web3 import Web3
import requests

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WalletInfo:
    address: str
    balance_eth: float
    balance_usd: float
    network: str
    chain_id: int
    connected: bool


@dataclass
class TransactionInfo:
    hash: str
    from_address: str
    to_address: str
    amount_eth: float
    amount_usd: float
    gas_price: float
    timestamp: int
    status: str


class MetaMaskIntegration:
    """MetaMask wallet integration for mining earnings"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Web3 configuration
        self.infura_project_id = config.get("infura_project_id", "")
        self.network = config.get("network", "mainnet")
        self.chain_id = self._get_chain_id()
        
        # Web3 connection
        self.w3 = None
        self.connected = False
        
        # Wallet information
        self.wallet_info = None
        self.transactions = []
        
        # Mining earnings
        self.mining_address = config.get("mining_wallet_address", "")
        self.earnings = 0.0
        
        # Price tracking
        self.eth_price_usd = 0.0
        self.last_price_update = 0
        
        self._setup_web3()
    
    def _get_chain_id(self) -> int:
        """Get chain ID for selected network"""
        networks = {
            "mainnet": 1,
            "goerli": 5,
            "sepolia": 11155111,
            "polygon": 137,
            "arbitrum": 42161,
            "optimism": 10
        }
        return networks.get(self.network, 1)
    
    def _setup_web3(self):
        """Setup Web3 connection"""
        try:
            if self.infura_project_id:
                # Use Infura for reliable connection
                rpc_url = f"https://{self.network}.infura.io/v3/{self.infura_project_id}"
                self.w3 = Web3(Web3.HTTPProvider(rpc_url))
            else:
                # Use public RPC endpoint
                rpc_urls = {
                    "mainnet": "https://ethereum.publicnode.com",
                    "goerli": "https://ethereum-goerli.publicnode.com",
                    "polygon": "https://polygon-rpc.com",
                    "arbitrum": "https://arb1.arbitrum.io/rpc",
                    "optimism": "https://mainnet.optimism.io"
                }
                rpc_url = rpc_urls.get(self.network, rpc_urls["mainnet"])
                self.w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            # Add POA middleware for testnets (skip for now due to import issues)
            # if self.network in ["goerli", "sepolia"]:
            #     try:
            #         from web3.middleware import geth_poa_middleware
            #         self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            #     except ImportError:
            #         logger.warning("POA middleware not available, continuing without it")
            
            if self.w3.is_connected():
                self.connected = True
                logger.info(f"Connected to {self.network} blockchain")
                self._update_eth_price()
            else:
                logger.error("Failed to connect to blockchain")
                
        except Exception as e:
            logger.error(f"Web3 setup error: {e}")
    
    def connect_wallet(self, address: str) -> bool:
        """Connect to MetaMask wallet"""
        try:
            if not self.connected:
                logger.error("Not connected to blockchain")
                return False
            
            # Validate address format
            if not self.w3.is_address(address):
                logger.error("Invalid wallet address format")
                return False
            
            # Convert to checksum address
            checksum_address = self.w3.to_checksum_address(address)
            
            # Get wallet balance
            balance_wei = self.w3.eth.get_balance(checksum_address)
            balance_eth = self.w3.from_wei(balance_wei, 'ether')
            
            # Update wallet info
            self.wallet_info = WalletInfo(
                address=checksum_address,
                balance_eth=float(balance_eth),
                balance_usd=float(balance_eth) * self.eth_price_usd,
                network=self.network,
                chain_id=self.chain_id,
                connected=True
            )
            
            logger.info(f"Connected to wallet: {checksum_address[:10]}...")
            return True
            
        except Exception as e:
            logger.error(f"Wallet connection error: {e}")
            return False
    
    def get_wallet_info(self) -> Optional[WalletInfo]:
        """Get current wallet information"""
        return self.wallet_info
    
    def get_balance(self) -> Dict[str, float]:
        """Get wallet balance in ETH and USD"""
        if not self.wallet_info:
            return {"eth": 0.0, "usd": 0.0}
        
        # Update balance
        try:
            balance_wei = self.w3.eth.get_balance(self.wallet_info.address)
            balance_eth = float(self.w3.from_wei(balance_wei, 'ether'))
            balance_usd = balance_eth * self.eth_price_usd
            
            self.wallet_info.balance_eth = balance_eth
            self.wallet_info.balance_usd = balance_usd
            
            return {"eth": balance_eth, "usd": balance_usd}
            
        except Exception as e:
            logger.error(f"Balance update error: {e}")
            return {"eth": self.wallet_info.balance_eth, "usd": self.wallet_info.balance_usd}
    
    def get_transactions(self, limit: int = 10) -> List[TransactionInfo]:
        """Get recent transactions"""
        if not self.wallet_info:
            return []
        
        try:
            # Use Etherscan API for transaction history
            api_key = self.config.get("etherscan_api_key", "")
            if not api_key:
                logger.warning("No Etherscan API key configured")
                return self._get_mock_transactions()
            
            base_url = "https://api.etherscan.io/api"
            params = {
                "module": "account",
                "action": "txlist",
                "address": self.wallet_info.address,
                "startblock": 0,
                "endblock": 99999999,
                "page": 1,
                "offset": limit,
                "sort": "desc",
                "apikey": api_key
            }
            
            response = requests.get(base_url, params=params)
            data = response.json()
            
            if data["status"] == "1":
                transactions = []
                for tx in data["result"]:
                    tx_info = TransactionInfo(
                        hash=tx["hash"],
                        from_address=tx["from"],
                        to_address=tx["to"],
                        amount_eth=float(self.w3.from_wei(int(tx["value"]), 'ether')),
                        amount_usd=float(self.w3.from_wei(int(tx["value"]), 'ether')) * self.eth_price_usd,
                        gas_price=float(self.w3.from_wei(int(tx["gasPrice"]), 'gwei')),
                        timestamp=int(tx["timeStamp"]),
                        status="confirmed" if tx["isError"] == "0" else "failed"
                    )
                    transactions.append(tx_info)
                
                self.transactions = transactions
                return transactions
            else:
                logger.warning("Etherscan API error")
                return self._get_mock_transactions()
                
        except Exception as e:
            logger.error(f"Transaction fetch error: {e}")
            return self._get_mock_transactions()
    
    def _get_mock_transactions(self) -> List[TransactionInfo]:
        """Get mock transactions for demo"""
        import random
        
        mock_txs = [
            TransactionInfo(
                hash="0x1234567890abcdef1234567890abcdef12345678",
                from_address="0xabcdef1234567890abcdef1234567890abcdef12",
                to_address=self.wallet_info.address if self.wallet_info else "0x1234567890abcdef1234567890abcdef12345678",
                amount_eth=random.uniform(0.01, 1.0),
                amount_usd=random.uniform(20, 2000),
                gas_price=random.uniform(10, 100),
                timestamp=int(time.time()) - random.randint(0, 86400 * 30),
                status="confirmed"
            )
            for _ in range(5)
        ]
        
        return mock_txs
    
    def _update_eth_price(self):
        """Update ETH price in USD"""
        try:
            # Use CoinGecko API for price
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {"ids": "ethereum", "vs_currencies": "usd"}
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            self.eth_price_usd = data["ethereum"]["usd"]
            self.last_price_update = time.time()
            
            logger.info(f"ETH price updated: ${self.eth_price_usd:.2f}")
            
        except Exception as e:
            logger.error(f"Price update error: {e}")
            # Use fallback price
            self.eth_price_usd = 2000.0
    
    def add_mining_earnings(self, amount_eth: float):
        """Add mining earnings to wallet"""
        self.earnings += amount_eth
        logger.info(f"Added mining earnings: {amount_eth:.6f} ETH (${amount_eth * self.eth_price_usd:.2f})")
    
    def get_mining_stats(self) -> Dict[str, Any]:
        """Get mining earnings statistics"""
        return {
            "total_earnings_eth": self.earnings,
            "total_earnings_usd": self.earnings * self.eth_price_usd,
            "current_balance_eth": self.wallet_info.balance_eth if self.wallet_info else 0.0,
            "current_balance_usd": self.wallet_info.balance_usd if self.wallet_info else 0.0,
            "eth_price_usd": self.eth_price_usd,
            "last_price_update": self.last_price_update
        }
    
    def create_mining_contract(self) -> Optional[str]:
        """Create a simple mining contract (demo)"""
        try:
            # Simple mining contract bytecode (for demo purposes)
            mining_contract_code = """
            // Simple Mining Contract
            pragma solidity ^0.8.0;
            
            contract MiningPool {
                address public owner;
                mapping(address => uint256) public balances;
                
                function deposit() external payable {
                    balances[msg.sender] += msg.value;
                }
                
                function withdraw(uint256 amount) external {
                    require(balances[msg.sender] >= amount, "Insufficient balance");
                    balances[msg.sender] -= amount;
                    payable(msg.sender).transfer(amount);
                }
            }
            """
            
            # In a real implementation, you would compile and deploy this
            logger.info("Mining contract creation (demo mode)")
            return "0x0000000000000000000000000000000000000000"
            
        except Exception as e:
            logger.error(f"Contract creation error: {e}")
            return None
    
    def validate_address(self, address: str) -> bool:
        """Validate Ethereum address"""
        try:
            return self.w3.is_address(address) if self.w3 else False
        except:
            return False
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        if not self.connected:
            return {"connected": False}
        
        try:
            latest_block = self.w3.eth.block_number
            gas_price = self.w3.eth.gas_price
            
            return {
                "connected": True,
                "network": self.network,
                "chain_id": self.chain_id,
                "latest_block": latest_block,
                "gas_price": float(self.w3.from_wei(gas_price, 'gwei')),
                "eth_price_usd": self.eth_price_usd
            }
        except Exception as e:
            logger.error(f"Network info error: {e}")
            return {"connected": False, "error": str(e)}


class WalletManager:
    """High-level wallet management for mining operations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metamask = MetaMaskIntegration(config)
        self.connected = False
        self.auto_update = config.get("auto_update_wallet", True)
        
        if self.auto_update:
            self._start_auto_update()
    
    def _start_auto_update(self):
        """Start automatic wallet updates"""
        def update_loop():
            while True:
                try:
                    if self.connected:
                        self.metamask.get_balance()
                        self.metamask._update_eth_price()
                    time.sleep(30)  # Update every 30 seconds
                except Exception as e:
                    logger.error(f"Auto update error: {e}")
                    time.sleep(60)
        
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
    
    def connect_wallet(self, address: str) -> bool:
        """Connect wallet and start management"""
        if self.metamask.connect_wallet(address):
            self.connected = True
            logger.info("Wallet manager connected")
            return True
        return False
    
    def disconnect_wallet(self):
        """Disconnect wallet"""
        self.connected = False
        self.metamask.wallet_info = None
        logger.info("Wallet manager disconnected")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all wallet data for dashboard"""
        if not self.connected:
            return {"connected": False}
        
        return {
            "connected": True,
            "wallet": self.metamask.get_wallet_info(),
            "balance": self.metamask.get_balance(),
            "transactions": self.metamask.get_transactions()[:5],
            "mining_stats": self.metamask.get_mining_stats(),
            "network": self.metamask.get_network_info()
        }
