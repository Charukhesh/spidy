"""Athena Everyday Desktop Companion Runner Script.
Run this script to launch your Athena AI Desktop Companion.
"""

import sys
import os

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from athena.main import main

if __name__ == "__main__":
    main()

