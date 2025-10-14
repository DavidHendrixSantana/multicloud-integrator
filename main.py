#!/usr/bin/env python3
"""
Multi-Cloud File Transfer CLI - Main Entry Point
"""
import sys
import os
from pathlib import Path

# Add src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# Import and run CLI
from cli import cli

if __name__ == "__main__":
    cli()
