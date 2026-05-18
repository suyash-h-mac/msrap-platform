"""
Pytest configuration for MSRAP analytics tests.
Ensures the repo root is on sys.path so imports resolve cleanly.
"""
import sys
import pathlib

# Add repo root (two levels up from analytics/tests/)
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
