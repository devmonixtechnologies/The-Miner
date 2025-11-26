#!/usr/bin/env python3
"""
Test script for API key configuration
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from terminal_gui import TerminalGUI

def test_api_config():
    """Test the API key configuration interface"""
    print("Testing API Key Configuration...")
    
    # Create a mock config
    config = {
        "blockchain": {
            "network": "mainnet",
            "etherscan_api_key": "YourApiKeyHere",
            "infura_project_id": "",
            "mining_wallet_address": "",
            "auto_update_wallet": True
        }
    }
    
    # Create GUI instance
    gui = TerminalGUI(miner_instance=None, config=config)
    
    # Test the API configuration method
    try:
        gui._configure_api_keys()
        print("✅ API Configuration interface works!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_api_config()
