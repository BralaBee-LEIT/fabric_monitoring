# Fabric Monitoring System Makefile
# CRUD operations for conda environment management

# Environment variables
ENV_NAME = fabric-monitoring
ENV_FILE = environment.yml
REQ_FILE = requirements.txt
PYTHON_VERSION = 3.11

# Colors for output
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

.PHONY: help create update delete status install test clean lint format check-env

# Default target
help:
	@echo "$(GREEN)Fabric Monitoring System - Environment Management$(NC)"
	@echo ""
	@echo "$(YELLOW)Available commands:$(NC)"
	@echo "  $(GREEN)create$(NC)      - Create conda environment from environment.yml"
	@echo "  $(GREEN)update$(NC)      - Update existing environment with new dependencies"
	@echo "  $(GREEN)delete$(NC)      - Delete the conda environment"
	@echo "  $(GREEN)status$(NC)      - Show environment status and info"
	@echo "  $(GREEN)install$(NC)     - Install additional pip dependencies from requirements.txt"
	@echo "  $(GREEN)activate$(NC)    - Show activation command"
	@echo "  $(GREEN)test$(NC)        - Run tests in the environment"
	@echo "  $(GREEN)lint$(NC)        - Run linting checks"
	@echo "  $(GREEN)format$(NC)      - Format code with black"
	@echo "  $(GREEN)clean$(NC)       - Clean cache and temporary files"
	@echo "  $(GREEN)export$(NC)      - Export current environment to new yml file"
	@echo ""
	@echo "$(YELLOW)Usage examples:$(NC)"
	@echo "  make create       # Create new environment"
	@echo "  make update       # Update existing environment"
	@echo "  make delete       # Remove environment"
	@echo "  make status       # Check environment status"

# CREATE: Create new conda environment
create:
	@echo "$(GREEN)Creating conda environment: $(ENV_NAME)$(NC)"
	@if conda env list | grep -q "^$(ENV_NAME) "; then \
		echo "$(YELLOW)Environment $(ENV_NAME) already exists. Use 'make update' to update it.$(NC)"; \
	else \
		conda env create -f $(ENV_FILE) && \
		echo "$(GREEN)✅ Environment $(ENV_NAME) created successfully!$(NC)" && \
		echo "$(YELLOW)Activate with: conda activate $(ENV_NAME)$(NC)"; \
	fi

# READ: Show environment status and information
status:
	@echo "$(GREEN)Environment Status: $(ENV_NAME)$(NC)"
	@echo "----------------------------------------"
	@if conda env list | grep -q "^$(ENV_NAME) "; then \
		echo "$(GREEN)✅ Environment exists$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Environment details:$(NC)"; \
		conda env list | grep "^$(ENV_NAME) "; \
		echo ""; \
		echo "$(YELLOW)Python version:$(NC)"; \
		conda run -n $(ENV_NAME) python --version; \
		echo ""; \
		echo "$(YELLOW)Installed packages:$(NC)"; \
		conda run -n $(ENV_NAME) pip list | head -10; \
		echo "... (showing first 10 packages)"; \
		echo ""; \
		echo "$(YELLOW)To see all packages:$(NC) conda run -n $(ENV_NAME) conda list"; \
	else \
		echo "$(RED)❌ Environment $(ENV_NAME) does not exist$(NC)"; \
		echo "$(YELLOW)Create it with: make create$(NC)"; \
	fi

# UPDATE: Update existing environment
update:
	@echo "$(GREEN)Updating conda environment: $(ENV_NAME)$(NC)"
	@if conda env list | grep -q "^$(ENV_NAME) "; then \
		conda env update -f $(ENV_FILE) --prune && \
		echo "$(GREEN)✅ Environment $(ENV_NAME) updated successfully!$(NC)"; \
	else \
		echo "$(RED)❌ Environment $(ENV_NAME) does not exist$(NC)"; \
		echo "$(YELLOW)Create it first with: make create$(NC)"; \
	fi

# DELETE: Remove conda environment
delete:
	@echo "$(RED)Deleting conda environment: $(ENV_NAME)$(NC)"
	@echo "$(YELLOW)⚠️  This will permanently delete the environment!$(NC)"
	@read -p "Are you sure? (y/N): " confirm && \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		conda env remove -n $(ENV_NAME) && \
		echo "$(GREEN)✅ Environment $(ENV_NAME) deleted successfully!$(NC)"; \
	else \
		echo "$(YELLOW)Deletion cancelled.$(NC)"; \
	fi

# INSTALL: Install additional pip dependencies
install:
	@echo "$(GREEN)Installing additional pip dependencies$(NC)"
	@if conda env list | grep -q "^$(ENV_NAME) "; then \
		conda run -n $(ENV_NAME) pip install -r $(REQ_FILE) && \
		echo "$(GREEN)✅ Additional dependencies installed!$(NC)"; \
	else \
		echo "$(RED)❌ Environment $(ENV_NAME) does not exist$(NC)"; \
		echo "$(YELLOW)Create it first with: make create$(NC)"; \
	fi

# Show activation command
activate:
	@echo "$(GREEN)To activate the environment, run:$(NC)"
	@echo "$(YELLOW)conda activate $(ENV_NAME)$(NC)"

# EXPORT: Export current environment to new file
export:
	@echo "$(GREEN)Exporting environment to environment_exported.yml$(NC)"
	@if conda env list | grep -q "^$(ENV_NAME) "; then \
		conda env export -n $(ENV_NAME) > environment_exported.yml && \
		echo "$(GREEN)✅ Environment exported to environment_exported.yml$(NC)"; \
	else \
		echo "$(RED)❌ Environment $(ENV_NAME) does not exist$(NC)"; \
	fi

# Development commands
test:
	@echo "$(GREEN)Running tests$(NC)"
	@if conda env list | grep -q "^$(ENV_NAME) "; then \
		conda run -n $(ENV_NAME) python -m pytest tests/ -v --cov=src/; \
	else \
		echo "$(RED)❌ Environment $(ENV_NAME) does not exist$(NC)"; \
	fi

lint:
	@echo "$(GREEN)Running linting checks$(NC)"
	@if conda env list | grep -q "^$(ENV_NAME) "; then \
		conda run -n $(ENV_NAME) flake8 src/ && \
		conda run -n $(ENV_NAME) mypy src/; \
	else \
		echo "$(RED)❌ Environment $(ENV_NAME) does not exist$(NC)"; \
	fi

format:
	@echo "$(GREEN)Formatting code with black$(NC)"
	@if conda env list | grep -q "^$(ENV_NAME) "; then \
		conda run -n $(ENV_NAME) black src/ tests/; \
	else \
		echo "$(RED)❌ Environment $(ENV_NAME) does not exist$(NC)"; \
	fi

clean:
	@echo "$(GREEN)Cleaning cache and temporary files$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✅ Cache and temporary files cleaned$(NC)"

# Check if environment exists (utility function)
check-env:
	@if conda env list | grep -q "^$(ENV_NAME) "; then \
		echo "$(GREEN)✅ Environment $(ENV_NAME) exists$(NC)"; \
	else \
		echo "$(RED)❌ Environment $(ENV_NAME) does not exist$(NC)"; \
		exit 1; \
	fi

# Development workflow shortcuts
dev-setup: create install
	@echo "$(GREEN)✅ Development environment setup complete!$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. conda activate $(ENV_NAME)"
	@echo "  2. Start developing!"

dev-check: lint test
	@echo "$(GREEN)✅ Development checks passed!$(NC)"

# Quick commands
.PHONY: c u d s
c: create
u: update  
d: delete
s: status