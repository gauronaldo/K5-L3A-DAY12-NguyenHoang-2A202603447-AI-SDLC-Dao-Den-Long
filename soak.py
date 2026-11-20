#!/usr/bin/env python3
"""Soak test entry point: python3 soak.py --seed 7 --nights 10 --out soak.json"""
import os
import sys

if not getattr(sys, "frozen", False):   # packaged builds have no __file__ and already contain the package
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lantern.soak import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
