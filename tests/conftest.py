"""
Pytest configuration and fixtures for test suite.
"""
import sys
from pathlib import Path

# Add the project root and scripts directory to the Python path
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_project_root / "scripts"))
