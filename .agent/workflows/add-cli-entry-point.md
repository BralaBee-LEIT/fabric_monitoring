---
description: How to add a new CLI script/entry point to the project
---

# Adding a New CLI Entry Point

This workflow describes how to properly add a new CLI command to the usf_fabric_monitoring project following the industry-standard src layout.

## Steps

### 1. Create the Script Module

Create a new Python file in `src/usf_fabric_monitoring/scripts/`:

```python
# src/usf_fabric_monitoring/scripts/my_new_command.py
"""
Description of what this command does.
"""
import argparse
from dotenv import load_dotenv

from usf_fabric_monitoring.core.some_module import SomeClass


def main():
    """Entry point for the CLI command."""
    load_dotenv()
    parser = argparse.ArgumentParser(description="My new command")
    # Add arguments...
    args = parser.parse_args()
    # Implementation...
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Important**: Do NOT use `sys.path.insert()` hacks - the script is inside the package.

### 2. Update `__init__.py`

Add the new module to `src/usf_fabric_monitoring/scripts/__init__.py`:

```python
from . import (
    monitor_hub_pipeline,
    # ... other modules ...
    my_new_command,  # ADD THIS
)

__all__ = [
    "monitor_hub_pipeline",
    # ... other modules ...
    "my_new_command",  # ADD THIS
]
```

### 3. Add Entry Point to `pyproject.toml`

Add a new entry point in `pyproject.toml`:

```toml
[project.scripts]
usf-monitor-hub = "usf_fabric_monitoring.scripts.monitor_hub_pipeline:main"
# ... other entry points ...
usf-my-command = "usf_fabric_monitoring.scripts.my_new_command:main"  # ADD THIS
```

### 4. Reinstall the Package

// turbo
```bash
conda run -n fabric-monitoring pip install -e .
```

### 5. Verify the Entry Point Works

// turbo
```bash
conda run -n fabric-monitoring usf-my-command --help
```

### 6. Add Makefile Target (Optional)

Add a convenience target in `Makefile`:

```makefile
my-command:
	@echo "$(GREEN)Running my command$(NC)"
	@if conda env list | grep -q "^$(ENV_NAME) "; then \
		conda run --no-capture-output -n $(ENV_NAME) python -m usf_fabric_monitoring.scripts.my_new_command; \
	fi
```

### 7. Add Tests

Create tests in `tests/test_my_new_command.py`.

---

## Verification Checklist

- [ ] Script has `main()` function that returns exit code
- [ ] Script has `if __name__ == "__main__":` block
- [ ] No `sys.path` hacks in the script
- [ ] Module added to `scripts/__init__.py`
- [ ] Entry point added to `pyproject.toml`
- [ ] Package reinstalled with `pip install -e .`
- [ ] Entry point works: `usf-my-command --help`
- [ ] All tests pass: `pytest tests/ -v`
