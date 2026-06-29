"""Pytest bootstrap: put the repo root on sys.path so `import fireflyverify`
resolves without an install, and force UTF-8 stdout for cross-platform output."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
