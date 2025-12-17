# GitHub Copilot Instructions for USF Fabric Monitoring

**Version**: 0.3.8 | **Library-first** Microsoft Fabric monitoring/governance toolkit.
Core logic in `src/usf_fabric_monitoring/`; scripts/notebooks are thin wrappers.

## Architecture

### Data Pipeline Flow
```
Monitor Hub API → extraction → Smart Merge (jobs+activities) → Parquet → Star Schema → Analytics
```

1. **Monitor Hub Pipeline** (`core/pipeline.py:MonitorHubPipeline`)
   - Extracts activity events + job details → merges via Smart Merge → writes parquet
   - Output: `exports/monitor_hub_analysis/parquet/activities_*.parquet` (28 columns, source of truth)
   - Legacy CSV: `activities_master_*.csv` (19 columns, incomplete - avoid)

2. **Star Schema Builder** (`core/star_schema_builder.py`)
   - Transforms raw activities → Kimball dimensional model
   - **Critical function**: `build_star_schema_from_pipeline_output()` - use this, NOT `StarSchemaBuilder` directly
   - Output: `exports/star_schema/*.parquet` (dim_date, dim_time, dim_workspace, dim_item, dim_user, dim_activity_type, dim_status, fact_activity, fact_daily_metrics)

3. **Workspace Governance** (`core/workspace_access_enforcer.py`)
   - Enforces security group assignments to workspaces

### Smart Merge Algorithm
The Smart Merge correlates two data sources to enrich activity data:
- **Activity Events API**: High-volume audit log (ReadArtifact, CreateFile) - has `start_time` but no failure details
- **Job History API**: Lower-volume job executions (Pipeline, Refresh) - has `end_time`, `failure_reason`, `duration`

Merge logic in `MonitorHubPipeline._merge_activities()`:
1. Extract activities from Activity Events API (per-day, paginated)
2. Extract job details from Job History API (8-hour cache)
3. Match by `activity_id` or `item_id + timestamp proximity`
4. Enrich with duration, status, failure_reason from job history
5. Write merged result to `parquet/activities_*.parquet`

### Workspace Name Enrichment
The `StarSchemaBuilder` auto-enriches activities with workspace names:
1. `_load_workspace_lookup()` searches for workspace parquet in:
   - Explicit path (if provided)
   - `exports/monitor_hub_analysis/parquet/workspaces_*.parquet`
   - `notebooks/monitor_hub_analysis/parquet/`
2. `_enrich_activities_with_workspace_names()` joins workspace names before dimension build
3. Result: 99%+ of activities get proper workspace names (vs "Unknown" from ID-only data)

### Critical Data Patterns

**Activity Types**: Two sources with different schemas:
- **Audit Log activities** (ReadArtifact, CreateFile, etc.): High volume, always succeed
- **Job History activities** (Pipeline, PipelineRunNotebook, Refresh, Publish): Lower volume, can fail
  - Have `end_time` but NULL `start_time` - star schema uses `end_time` fallback
  - Have `workspace_name` but NULL `workspace_id` - star schema uses name-based lookup

**Counting Pattern** - ALWAYS use `record_count` sum, NOT `activity_id` count:
```python
# ✅ CORRECT - record_count exists for every activity
stats = fact.groupby('workspace_sk').agg(activity_count=('record_count', 'sum'))

# ❌ WRONG - activity_id is NULL for 99% of granular audit log operations
stats = fact.groupby('workspace_sk').agg(activity_count=('activity_id', 'count'))
```

**Dimension Columns** (check schema, not assumptions):
- `dim_time`: `hour_24`, `time_period` (NOT `hour`, `period_of_day`)
- `dim_date`: `month_number` (NOT `month`)
- `dim_status`: `status_code` (NOT `status_name`)

## Environment Setup

**CRITICAL**: Always use the project's conda environment for all Python operations.

```bash
# Create environment (first time only)
make create
# OR: conda env create -f environment.yml

# Activate environment (REQUIRED before any Python command)
conda activate fabric-monitoring

# Verify correct environment
conda env list  # Should show * next to fabric-monitoring

# Install package in editable mode
make install
# OR: conda run -n fabric-monitoring pip install -e .
```

**For terminal commands**, always prefix with the conda environment:
```bash
# ✅ CORRECT - uses project environment
conda run -n fabric-monitoring python script.py
conda run -n fabric-monitoring pytest tests/

# ❌ WRONG - may use wrong Python/packages
python script.py
```

## Workflows

### Primary Commands (via Makefile)
```bash
make create                    # Create conda environment
make install                   # Install package (editable)
make monitor-hub DAYS=7        # Run Monitor Hub extraction
make star-schema               # Build star schema (incremental)
make star-schema FULL_REFRESH=1  # Full rebuild
make validate-config           # Validate config JSONs
make test-smoke                # Quick import tests
```

### CLI Entrypoints (see `pyproject.toml`)
`usf-monitor-hub`, `usf-enforce-access`, `usf-validate-config`, `usf-star-schema`

## Conventions

- **Paths**: Use `core/utils.py:resolve_path()` - auto-resolves to OneLake in Fabric
- **Logging**: Use `core/logger.py:setup_logging` (rotating files under `logs/`)
- **Config**: Business rules in `config/*.json` (inference_rules, workspace_access_targets, etc.)
- **Tests**: Unit tests in `tests/` (offline-safe); integration in `tools/dev_tests/`
- **Notebooks**: `notebooks/Fabric_Star_Schema_Builder.ipynb` - always reload modules with `importlib.reload()`

## Auth/Secrets
- Set `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` in `.env`
- Fallback chain in `core/auth.py`: Fabric `notebookutils` → Azure Identity → fail with clear error

## Star Schema Build (Notebook Pattern)
```python
import importlib
import usf_fabric_monitoring.core.star_schema_builder as ssb_module
importlib.reload(ssb_module)  # Pick up code changes

result = ssb_module.build_star_schema_from_pipeline_output(
    pipeline_output_dir='exports/monitor_hub_analysis',
    output_directory='exports/star_schema',
    incremental=False  # Use False to prevent duplicate accumulation
)
```

## Common Pitfalls
1. **Wrong conda environment**: Always activate `fabric-monitoring` or use `conda run -n fabric-monitoring`
2. **Stale star_schema data**: Delete `exports/star_schema` before rebuilding if data looks wrong
3. **Missing activity types**: `ActivityTypeDimensionBuilder.ACTIVITY_TYPES` is hardcoded - add new types there
4. **Failures showing as Unknown**: Check if activity type exists in dimension; job history types added in v0.3.8
5. **Wrong counts**: Use `('record_count', 'sum')` not `('activity_id', 'count')` - 99% of activity_ids are NULL
