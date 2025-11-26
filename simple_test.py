#!/usr/bin/env python3
"""
Simple test for terminal GUI
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    print("Starting simple terminal test...")
    
    try:
        # Load config
        from config.manager import ConfigManager
        config_manager = ConfigManager("config/default.conf")
        config = config_manager.load_config()
        print("✓ Configuration loaded")
        
        # Create terminal GUI
        from terminal_gui import TerminalGUI
        gui = TerminalGUI(miner_instance=None, config=config)
        print("✓ Terminal GUI created")
        
        # Show menu once
        print("\n--- SHOWING MENU ---")
        gui._show_menu()
        print("✓ Menu displayed")
        
        # Get input
        print("\nGetting input...")
        choice = input("Enter choice: ")
        print(f"✓ User entered: {choice}")
        
        print("\n✅ Simple test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
