#!/usr/bin/env python3
"""
Test script for terminal GUI
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_terminal_gui():
    """Test terminal GUI functionality"""
    try:
        # Test imports
        from terminal_gui import TerminalGUI, start_terminal_gui
        print("✓ Terminal GUI imports successful")
        
        # Test GUI creation
        gui = TerminalGUI()
        print("✓ Terminal GUI created successfully")
        
        # Test menu display
        print("\n--- MENU TEST ---")
        gui._show_menu()
        print("✓ Menu displayed successfully")
        
        # Test API key configuration
        print("\n--- API KEY CONFIGURATION TEST ---")
        gui._configure_api_keys()
        print("✓ API key configuration works")
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_terminal_gui()
    sys.exit(0 if success else 1)
