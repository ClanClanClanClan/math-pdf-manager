#!/usr/bin/env python3
"""
Main entry point for Math-PDF Manager
This launcher sets up the correct module path and runs the application.
"""

import sys
from pathlib import Path

# Add project root to Python path so 'src' can be imported as a package
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now import and run the main application
if __name__ == "__main__":
    from src.main import main
    main()