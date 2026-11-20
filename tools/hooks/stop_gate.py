#!/usr/bin/env python3
"""Claude Code Stop hook: refuse to finish while unit tests are red.

Exit 2 + stderr -> the agent is told to keep working. On the second consecutive
block (stop_hook_active) we still report but let it stop, to avoid an endless loop.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    payload = json.load(sys.stdin)
except Exception:
    payload = {}

proc = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "verify.py"), "--quick"],
                      capture_output=True, text=True, cwd=ROOT)
if proc.returncode == 0:
    sys.exit(0)

tail = "\n".join((proc.stderr + proc.stdout).strip().splitlines()[-25:])
sys.stderr.write("Unit tests are failing - fix them (or explain why) before finishing:\n" + tail + "\n")
sys.exit(0 if payload.get("stop_hook_active") else 2)
