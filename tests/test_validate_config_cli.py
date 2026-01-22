from __future__ import annotations

import sys
from pathlib import Path


# Add src to path for testing (mirrors other tests)
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))


def test_validate_config_cli_returns_zero_for_repo_config():
    from usf_fabric_monitoring.scripts.validate_config import main

    repo_root = Path(__file__).resolve().parents[1]
    config_dir = repo_root / "config"

    exit_code = main([str(config_dir), "--json"])
    assert exit_code == 0
