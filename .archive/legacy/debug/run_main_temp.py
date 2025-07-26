#!/usr/bin/env python3
"""Temporary runner script to bypass environment issues"""
import sys
import os

# Remove the corrupted venv from Python path
sys.path = [p for p in sys.path if '.venv' not in p]

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import and run main
from cli.commands import main

if __name__ == "__main__":
    # Pass through command line arguments
    sys.argv[0] = 'main.py'  # Make it look like we're running main.py
    main()