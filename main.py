#!/usr/bin/env python3
"""Play: python3 main.py · Bench: python3 main.py --bench --seed 42 --duration 30 --out bench.json
· Leaderboard: python3 main.py --export-leaderboard out.json"""
import os
import sys

if not getattr(sys, "frozen", False):   # packaged builds have no __file__ and already contain the package
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lantern.client import main  # noqa: E402

if __name__ == "__main__":
    main()
