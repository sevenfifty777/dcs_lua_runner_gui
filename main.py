#!/usr/bin/env python3
"""
DCS Lua Runner GUI - Main Entry Point

A standalone Windows GUI application for executing Lua code in DCS World.
Based on the DCS Fiddle project and DCS Lua Runner VSCode extension.

Author: Generated for DCS Lua Runner GUI
License: MIT (following original DCS Fiddle licensing)
"""

import sys
import os

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def check_dependencies():
    """Check if required dependencies are installed."""
    missing_deps = []
    
    try:
        import requests
    except ImportError:
        missing_deps.append("requests")
    
    try:
        import pygments
    except ImportError:
        missing_deps.append("pygments")
    
    if missing_deps:
        print("Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nPlease install them using:")
        print(f"pip install {' '.join(missing_deps)}")
        print("\nOr install all dependencies with:")
        print("pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Main entry point for the DCS Lua Runner GUI application."""
    print("DCS Lua Runner GUI v1.0.0")
    print("Based on DCS Fiddle project")
    print("-" * 40)
    
    # Check dependencies
    if not check_dependencies():
        input("Press Enter to exit...")
        sys.exit(1)
    
    try:
        # Import and create the main window
        from gui.main_window import MainWindow
        
        print("Starting application...")
        app = MainWindow()
        app.run()
        
    except ImportError as e:
        print(f"Failed to import application modules: {e}")
        print("Make sure you're running this script from the correct directory.")
        input("Press Enter to exit...")
        sys.exit(1)
        
    except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
