#!/usr/bin/env python3
"""Entry point for headless mode: python3 headless.py --seed 1 --night 1 --ticks 600 --out run.jsonl"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lantern.headless import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
