#!/usr/bin/env python3
"""Play the game: python3 main.py [--seed N]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lantern.client import main  # noqa: E402

if __name__ == "__main__":
    main()
