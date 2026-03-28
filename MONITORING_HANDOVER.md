# USF Fabric Monitoring - Operational Handover Document

| Field | Value |
|:------|:------|
| **Document Title** | USF Fabric Monitoring - Operational Handover & Deployment Guide |
| **Version** | 1.0 |
| **Date** | 28 March 2026 |
| **Classification** | Internal - Confidential |
| **Client** | Ricoh Europe PLC |
| **Author** | Sanmi Ibitoye |
| **Companion Document** | `PROJECT_RHICO_HANDOVER_DOCUMENT.md` (cross-repo handover) |

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture & Data Flow](#2-architecture--data-flow)
3. [Repository Structure](#3-repository-structure)
4. [Core Modules Reference](#4-core-modules-reference)
5. [Deployment: Local to Microsoft Fabric](#5-deployment-local-to-microsoft-fabric)
6. [Fabric Workspace Layout (FUAM_Monitoring_Admin)](#6-fabric-workspace-layout)
7. [Scheduled Pipeline Operation](#7-scheduled-pipeline-operation)
8. [Notebook Cell Reference](#8-notebook-cell-reference)
9. [Star Schema & Semantic Model](#9-star-schema--semantic-model)
10. [Lineage Explorer Deployment](#10-lineage-explorer-deployment)
11. [Authentication & Credentials](#11-authentication--credentials)
12. [Configuration Files](#12-configuration-files)
13. [CLI Commands](#13-cli-commands)
14. [Makefile Quick Reference](#14-makefile-quick-reference)
15. [Testing & CI/CD](#15-testing--cicd)
16. [Operational Procedures](#16-operational-procedures)
17. [Recommended CI/CD Lifecycle](#17-recommended-cicd-lifecycle)
18. [Known Limitations & Technical Debt](#18-known-limitations--technical-debt)
19. [Troubleshooting](#19-troubleshooting)

---

## 1. System Overview

The USF Fabric Monitoring platform (`usf_fabric_monitoring` v0.3.37) provides:

- **Tenant-wide activity monitoring**: Extracts and analyses Microsoft Fabric activity events (28-day rolling window) with Smart Merge technology that recovers 100% of missing duration data
- **Workspace access governance**: Audits and enforces security group assignments across all workspaces
- **Data lineage extraction**: Discovers Lakehouse shortcuts, mirrored databases, and item connections with hybrid extraction (iterative or Admin Scanner API)
- **Interactive lineage visualisation**: Neo4j-powered graph explorer with D3.js frontend (6 views, detail panels, blast radius analysis)
- **Star schema analytics**: Kimball-style dimensional model (8 dimensions, 3 fact tables) with incremental load and SCD Type 2

The system operates in two modes:
1. **Local CLI**: Direct command-line execution with Service Principal credentials
2. **Microsoft Fabric**: `.whl` package installed as custom library, notebooks run via Fabric scheduler

---

## 2. Architecture & Data Flow

### 2.1 End-to-End Pipeline Flow

```
Fabric APIs                    Local / Fabric Notebook              Outputs
─────────────────              ─────────────────────              ──────────────

Power BI Activity     ──►  extract_historical_data.py  ──►  raw_data/daily/
Events API (28-day)            (daily CSV per day)           fabric_activities_YYYYMMDD.csv

Fabric Job Instance   ──►  extract_fabric_item_details.py ──►  fabric_item_details/
API                            (job history JSON)              detailed_jobs_*.json

                                       │
                                       ▼

                            pipeline.py (Smart Merge)
                            ├── Load daily CSVs (data_loader.py)
                            ├── Rename columns (Id→event_id, etc.)
                            ├── Backfill activity_id from event_id
                            ├── merge_asof(activities, jobs,
                            │     by=item_id, tolerance=5min)
                            └── Enrichment (duration recovery)
                                       │
                                       ▼

                            monitor_hub_reporter_clean.py
                            ├── activities_master_YYYYMMDD_HHMMSS.csv  (26 columns)
                            ├── key_measurables_summary_*.csv
                            ├── user_performance_analysis_*.csv
                            ├── domain_performance_analysis_*.csv
                            ├── failure_analysis_*.csv
                            ├── daily_trends_analysis_*.csv
                            └── compute_analysis_*.csv
                                       │
                                       ▼

                            parquet/ (Source of Truth)
                            ├── activities_YYYYMMDD_HHMMSS.parquet
                            ├── items_YYYYMMDD_HHMMSS.parquet
                            └── workspaces_YYYYMMDD_HHMMSS.parquet
                                       │
                                       ▼

                            star_schema_builder.py
                            ├── dim_date, dim_time, dim_workspace
                            ├── dim_item, dim_user, dim_activity_type
                            ├── dim_status
                            ├── fact_activity
                            └── fact_daily_metrics
                                       │
                                       ▼

                            Semantic Model (Power BI)
                            └── Direct Lake or Import mode
```

### 2.2 Key Data Volumes (as validated)

| Metric | Value |
|:-------|:------|
| Total activities (single pipeline run) | ~888,000 |
| Unique workspaces | ~512 |
| Observed activity types | 46 (69 defined in code) |
| Daily extraction volume | ~30,000-85,000 events/day |
| Job instance records (merge source) | ~8,000-70,000 per run |
| activity_id population (pre-fix) | 11% |
| activity_id population (post-fix v0.3.37) | 100% |
| invoke_type population | ~8% (only job-type activities have this) |

### 2.3 The 26-Column Schema (v0.3.37)

The `activities_master` CSV contains these columns:

```
event_id, activity_id, workspace_id, workspace_name, item_id, item_name,
item_type, activity_type, status, invoke_type, start_time, end_time,
date, hour, duration_seconds, duration_minutes, submitted_by, created_by,
last_updated_by, domain, location, object_url, failure_reason, error_message,
root_activity_id, job_instance_id
```

Columns added in v0.3.37: `event_id`, `invoke_type`, `root_activity_id`, `job_instance_id`

> **Note**: The reporter template (`monitor_hub_reporter_clean.py`) defines 28 columns in its `column_order` list, which additionally includes `is_simulated` and `error_code`. These are conditionally included — they only appear in the output if present in the source data. Current pipeline output produces 26 columns. The notebook validation cell expects 26.

---

## 3. Repository Structure

```
usf_fabric_monitoring/
├── src/usf_fabric_monitoring/          # Installable Python package
│   ├── __init__.py                     # Version: 0.3.37
│   ├── core/                           # Business logic (20 modules)
│   │   ├── admin_scanner.py            # Admin Scanner API client
│   │   ├── api_resilience.py           # Circuit breaker, retry, backoff
│   │   ├── auth.py                     # FabricAuthenticator (SP + DefaultAzureCredential)
│   │   ├── config_validation.py        # JSON schema validation
│   │   ├── csv_exporter.py             # CSV export utilities
│   │   ├── data_loader.py             # Load + rename daily CSVs, backfill activity_id
│   │   ├── enrichment.py              # Activity enrichment (domain, location, duration)
│   │   ├── env_detection.py           # Detect Local vs Fabric Notebook vs Fabric Pipeline
│   │   ├── extractor.py              # FabricDataExtractor (Activity Events + Admin APIs)
│   │   ├── fabric_item_details.py    # Detailed item metadata + job history extraction
│   │   ├── historical_analyzer.py    # Comprehensive analysis engine (7 report types)
│   │   ├── item_connections.py       # Item-to-item connection extraction
│   │   ├── logger.py                 # Centralised logging config
│   │   ├── monitor_hub_reporter_clean.py  # CSV report generator (26-col activities_master)
│   │   ├── pipeline.py               # MonitorHubPipeline (orchestrator, Smart Merge)
│   │   ├── schema.py                 # DDL definitions for all tables
│   │   ├── star_schema_builder.py    # Kimball dimensional model builder
│   │   ├── type_safety.py            # Defensive data handling (11 functions)
│   │   ├── utils.py                  # resolve_path, is_fabric_environment re-export
│   │   └── workspace_access_enforcer.py  # Access policy enforcement
│   └── scripts/                        # CLI entry points (packaged in .whl)
│       ├── build_star_schema.py
│       ├── enforce_workspace_access.py
│       ├── extract_lineage.py
│       ├── monitor_hub_pipeline.py
│       └── validate_config.py
│
├── scripts/                            # Repo-level scripts (NOT in .whl)
│   ├── extract_historical_data.py      # Daily activity extraction from API
│   ├── extract_fabric_item_details.py  # Job history extraction from API
│   ├── extract_lineage.py              # Lineage extraction (hybrid mode)
│   ├── analyze_fabric_items.py         # Item analysis utilities
│   ├── audit_sp_access.py             # Service Principal access audit
│   ├── build_star_schema.py           # Star schema CLI wrapper
│   ├── enforce_workspace_access.py    # Access enforcement CLI wrapper
│   ├── extract_daily_data.py          # Single-day extraction helper
│   ├── fabric_workspace_report.py     # Workspace summary report generator
│   ├── generate_reports_manual.py     # Manual report generation
│   ├── monitor_hub_pipeline.py        # Pipeline CLI wrapper
│   ├── run_full_pipeline.py           # Full pipeline orchestrator
│   ├── run_lineage_explorer.py        # Start Lineage Explorer server
│   └── validate_config.py            # Config validation CLI wrapper
│
├── notebooks/
│   └── 1_Monitor_Hub_Analysis.ipynb   # Primary analysis notebook (19 cells)
│
├── lineage_explorer/                  # Standalone web application
│   ├── server.py                      # FastAPI application
│   ├── api_extended.py               # 25 query functions, 119 Cypher statements
│   ├── graph_builder.py              # CSV → Neo4j graph loader
│   ├── graph_database/
│   │   ├── data_loader.py            # Neo4j data loader
│   │   └── queries.py                # Cypher query library
│   ├── static/                        # D3.js frontend (6 views)
│   │   ├── index.html                 # Main Graph view
│   │   ├── elements_graph.html        # Elements Graph view
│   │   ├── tables_graph.html          # Tables Graph view
│   │   ├── table_impact.html          # Table Impact / Blast Radius
│   │   ├── dashboard.html             # Table Health Dashboard
│   │   └── query_explorer.html        # Query Explorer
│   ├── docker-compose.yml            # Neo4j container config
│   └── README.md
│
├── config/                            # Configuration files
│   ├── inference_rules.json          # Activity type inference rules
│   ├── workspace_access_targets.json # Access enforcement targets
│   └── workspace_access_suppressions.json  # Enforcement exclusions
│
├── tests/                             # 205 test functions across 17 files
├── dist/                              # Built wheel (.whl) for Fabric deployment
├── exports/                           # Local output directory (gitignored)
├── docs/                              # 14 documentation files across 8 categories
├── pyproject.toml                     # Package config, entry points, dependencies
├── Makefile                           # 25+ automation targets
├── CHANGELOG.md                       # Release history
└── SECURITY.md                        # Security policy
```

### Critical distinction: `src/...scripts/` vs `scripts/`

| Directory | In `.whl`? | Purpose |
|:----------|:-----------|:--------|
| `src/usf_fabric_monitoring/scripts/` | Yes | CLI entry points (Typer commands) registered in pyproject.toml |
| `scripts/` (repo root) | **No** | Standalone extraction scripts that make API calls. Imported dynamically by `pipeline.py` via `_find_scripts_dir()` |

The repo-level `scripts/` are **not** needed in Fabric when running via notebook — the notebook's extraction cell (Cell 6) calls `MonitorHubPipeline` which uses the 8-hour cache. The actual API extraction is handled by a **scheduled Fabric pipeline** that runs independently (see Section 7).

---

## 4. Core Modules Reference

### 4.1 Pipeline Orchestration

| Module | Class/Function | Purpose |
|:-------|:---------------|:--------|
| `pipeline.py` | `MonitorHubPipeline` | Main orchestrator: extract → merge → report → parquet |
| `pipeline.py` | `_find_scripts_dir()` | Multi-environment script discovery (repo/cwd/Lakehouse/env var) |
| `pipeline.py` | `_merge_activities()` | Smart Merge via `merge_asof(by=item_id, tolerance=5min)` |
| `data_loader.py` | `load_activities_from_directory()` | Load daily CSVs, rename columns, backfill `activity_id` |
| `data_loader.py` | `RENAME_MAP` | Maps API camelCase fields to snake_case |

### 4.2 Extraction

| Module | Class/Function | Purpose |
|:-------|:---------------|:--------|
| `extractor.py` | `FabricDataExtractor` | Activity Events API + workspace/item enumeration |
| `fabric_item_details.py` | `run_item_details_extraction()` | Job Instance API (invokeType, rootActivityId, duration) |
| `admin_scanner.py` | `AdminScannerClient` | Batch metadata extraction (lineage, datasources) |
| `auth.py` | `FabricAuthenticator` | SP credentials → token with proactive refresh (5-min buffer) |

### 4.3 Analysis & Reporting

| Module | Class/Function | Purpose |
|:-------|:---------------|:--------|
| `historical_analyzer.py` | `HistoricalAnalysisEngine` | 7 analysis categories (measurables, trends, failures, users, domains) |
| `monitor_hub_reporter_clean.py` | `MonitorHubCSVReporter` | Generate 7 CSV reports with 26-column activities_master |
| `star_schema_builder.py` | `StarSchemaBuilder` | Kimball model: 7 dimensions + 2 fact tables |
| `enrichment.py` | Activity enrichment | Domain, location, duration, URL building |

### 4.4 Governance

| Module | Class/Function | Purpose |
|:-------|:---------------|:--------|
| `workspace_access_enforcer.py` | `WorkspaceAccessEnforcer` | Assess or enforce security group assignments |
| `config_validation.py` | JSON schema validation | Validate inference_rules, access targets, suppressions |

### 4.5 Infrastructure

| Module | Purpose |
|:-------|:--------|
| `api_resilience.py` | Circuit breaker, exponential backoff, rate limiting |
| `env_detection.py` | Detect runtime: Local / Fabric Notebook / Fabric Pipeline / DevOps |
| `type_safety.py` | 11 defensive data handling functions |
| `utils.py` | `resolve_path()` (auto-prefixes `/lakehouse/default/Files/` in Fabric) |

---

## 5. Deployment: Local to Microsoft Fabric

This section documents the **manual deployment process** for getting code changes from the local development environment into Microsoft Fabric. There is currently no automated CI/CD for this — see Section 17 for recommendations.

### 5.1 Prerequisites

| Requirement | Detail |
|:------------|:-------|
| Local conda env | `fabric-monitoring` (Python 3.11) |
| Fabric workspace | `FUAM_Monitoring_Admin` (or equivalent) |
| Fabric capacity | Active Fabric capacity assigned to workspace |
| Service Principal | With Power BI Admin API access and workspace membership |
| `.env` file | `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` |

### 5.2 Step-by-Step: Deploying a Code Change

#### Phase 1: Local Development & Testing

```bash
# 1. Activate environment
conda activate fabric-monitoring

# 2. Make code changes in src/usf_fabric_monitoring/

# 3. Run tests
make test

# 4. Run lint
make lint

# 5. Verify locally (if pipeline changes)
python -c "
from usf_fabric_monitoring.core.pipeline import MonitorHubPipeline
# Dry-run validation
"
```

#### Phase 2: Build the Wheel

```bash
# 6. Update version in pyproject.toml and src/__init__.py (if releasing)
# 7. Build wheel
python -m build --wheel

# Output: dist/usf_fabric_monitoring-X.Y.Z-py3-none-any.whl
```

#### Phase 3: Git Commit & Push

```bash
# 8. Commit on feature branch
git checkout -b feature/<description>
git add <changed-files>
git commit -m "fix: description of change"
git push -u origin feature/<description>

# 9. Create PR, review, merge
gh pr create --title "fix: description" --body "..."
gh pr merge <number> --squash --delete-branch

# 10. Sync to all remotes
git checkout main && git pull origin main
git push abba-replc main
gh auth switch --user Bralabee
git push bralabee main
gh auth switch --user BralaBee-LEIT
```

#### Phase 4: Upload to Fabric

```
11. Open Microsoft Fabric portal → FUAM_Monitoring_Admin workspace

12. Upload .whl:
    → Workspace Settings → Library management
    → Remove old .whl (usf_fabric_monitoring-<old_version>-py3-none-any.whl)
    → Upload new .whl from dist/
    → Wait for environment to rebuild (~2-5 minutes)

13. Upload notebook (if changed):
    → Navigate to the notebook item (1_Monitor_Hub_Analysis)
    → Import or manually update changed cells
    → For minor changes: edit cells directly in Fabric UI
    → For major changes: download → replace → re-upload

14. Verify installation:
    → Open notebook → Run package verification cell
    → Should show: usf_fabric_monitoring version: X.Y.Z
```

#### Phase 5: Verify in Fabric

```
15. Run the extraction cell (if cache expired) or regeneration cell
16. Check activities_master has expected column count (26)
17. Run analysis cells to verify reports generate correctly
18. Run star schema cell if dimensional model needs updating
```

### 5.3 What Gets Uploaded vs What Already Exists

| Artifact | Upload Method | Frequency |
|:---------|:-------------|:----------|
| `.whl` package | Workspace Library management | On every code change to `src/` |
| Notebook | Direct edit or import | On notebook cell changes |
| `.env` credentials | Lakehouse Files (`dot_env_files/.env`) | On credential rotation |
| Config files | Lakehouse Files (if needed) | Rarely |
| Repo-level `scripts/` | **Not uploaded** — extraction happens via scheduled pipeline | Never |

### 5.4 Environment Variable Configuration in Fabric

The notebook reads credentials from `.env` files in this order:

1. `/lakehouse/default/Files/dot_env_files/.env` (Fabric Lakehouse)
2. `.env` in working directory (fallback)

Required variables:

```env
AZURE_CLIENT_ID=<service-principal-app-id>
AZURE_CLIENT_SECRET=<service-principal-secret>
AZURE_TENANT_ID=<azure-ad-tenant-id>
TENANT_WIDE=1
DEFAULT_ANALYSIS_DAYS=7
MAX_HISTORICAL_DAYS=28
EXPORT_DIRECTORY=exports/monitor_hub_analysis
```

---

## 6. Fabric Workspace Layout

### 6.1 FUAM_Monitoring_Admin Workspace

The monitoring platform runs in the `FUAM_Monitoring_Admin` workspace in Microsoft Fabric. This workspace contains approximately 48 artifacts managed via Fabric Git Sync.

### 6.2 Key Lakehouse Structure

```
Lakehouse/
├── Files/
│   ├── dot_env_files/
│   │   └── .env                           # Service Principal credentials
│   ├── exports/
│   │   └── monitor_hub_analysis/
│   │       ├── raw_data/
│   │       │   └── daily/                 # Daily activity CSVs
│   │       │       ├── fabric_activities_20260101.csv
│   │       │       ├── fabric_activities_20260102.csv
│   │       │       └── ...
│   │       ├── parquet/                   # Merged snapshots (Source of Truth)
│   │       │   ├── activities_YYYYMMDD_HHMMSS.parquet
│   │       │   ├── items_YYYYMMDD_HHMMSS.parquet
│   │       │   └── workspaces_YYYYMMDD_HHMMSS.parquet
│   │       ├── activities_master_*.csv    # 26-column report outputs
│   │       ├── failure_analysis_*.csv
│   │       ├── user_performance_analysis_*.csv
│   │       ├── domain_performance_analysis_*.csv
│   │       ├── daily_trends_analysis_*.csv
│   │       ├── compute_analysis_*.csv
│   │       ├── key_measurables_summary_*.csv
│   │       └── pipeline_summary_*.json    # Cached pipeline results
│   └── star_schema/                       # Dimensional model outputs
│       ├── dim_date.parquet
│       ├── dim_time.parquet
│       ├── dim_workspace.parquet
│       ├── dim_item.parquet
│       ├── dim_user.parquet
│       ├── dim_activity_type.parquet
│       ├── dim_status.parquet
│       ├── fact_activity.parquet
│       ├── fact_daily_metrics.parquet
│       └── fact_user_metrics.parquet
│
└── Tables/                                # Delta tables (for SQL endpoint / Semantic Model)
    ├── dim_date/
    ├── dim_workspace/
    ├── fact_activity/
    └── ...
```

---

## 7. Scheduled Pipeline Operation

### 7.1 How the Monitoring Runs Automatically

A **Fabric Data Pipeline** (or scheduled notebook) runs the Monitor Hub notebook daily at approximately **03:00 UTC**. This:

1. Installs/uses the `.whl` package from the workspace environment
2. Executes the extraction cell which calls `MonitorHubPipeline.run_complete_analysis()`
3. Extracts the last 7 days of activity data from the Power BI Activity Events API
4. Merges with Job Instance API data (Smart Merge)
5. Generates 7 CSV reports + Parquet snapshots
6. Stores outputs in the Lakehouse `Files/exports/monitor_hub_analysis/`

### 7.2 Cache Behaviour

The notebook has an **8-hour cache** mechanism:
- If `activities_master_*.csv` exists and is less than 8 hours old, extraction is skipped
- This prevents duplicate API calls when running the notebook interactively during business hours
- The 3am scheduled run always creates fresh data
- Override with `FORCE_REFRESH=1` environment variable

### 7.3 Data Retention

As of v0.3.37, a housekeeping cell runs before extraction and removes raw data files older than **180 days** (configurable via `DATA_RETENTION_DAYS` env var):
- `raw_data/daily/fabric_activities_YYYYMMDD.csv`
- `parquet/activities_YYYYMMDD_HHMMSS.parquet`
- `parquet/items_YYYYMMDD_HHMMSS.parquet`
- `parquet/workspaces_YYYYMMDD_HHMMSS.parquet`

Aggregated report CSVs (`activities_master_*`, etc.) are **not** cleaned by this cell.

---

## 8. Notebook Cell Reference

### `1_Monitor_Hub_Analysis.ipynb` (19 cells)

| Cell | Title / Purpose | Run Order |
|:-----|:----------------|:----------|
| 0 | **Notebook Information** (markdown) | - |
| 1 | **Setup Local Path** — adds `src/` to sys.path for local dev | Always |
| 2 | **Package Verification** — checks `usf_fabric_monitoring` is installed | Always |
| 3 | **Credential Management** — loads `.env`, verifies SP, inspects token | Always |
| 4 | **Run Configuration** — sets `DAYS_TO_ANALYZE`, `TENANT_WIDE`, `OUTPUT_DIR` | Always |
| 5 | **Data Housekeeping** — removes raw files older than 180 days | Always |
| 6 | **Smart Data Extraction** — 8-hour cache check, runs pipeline if expired | Scheduled runs |
| 7 | **Regenerate from Parquet** — rebuild 26-col reports without API calls | Manual use only |
| 8 | **Spark Analysis Header** (markdown) | - |
| 9 | **Spark Setup** — initialise SparkSession, import functions | Always (analysis) |
| 10 | **26-Column Schema Validation** — load activities_master CSVs, validate schema | Always (analysis) |
| 11 | **Data Validation & Column Check** | Analysis |
| 12 | **Overall Statistics Summary** | Analysis |
| 13 | **Workspace Activity Analysis** | Analysis |
| 14 | **Failure Analysis by Workspace** | Analysis |
| 15 | **User Activity & Failure Analysis** | Analysis |
| 16 | **Error & Failure Reason Analysis** | Analysis |
| 17 | **Time-Based Analysis** | Analysis |
| 18 | **Star Schema Builder** — import schema, build dimensional model | As needed |

### Cell 7: When to Use the Regeneration Cell

Use this cell when:
- The `.whl` has been updated with column mapping fixes (e.g., v0.3.37)
- You need to produce new 26-column reports from existing parquet data
- You don't want to (or can't) re-extract from APIs
- The scheduled pipeline hasn't run since the `.whl` update

It reads the latest `activities_YYYYMMDD_HHMMSS.parquet`, applies the column renames and backfills, and calls `MonitorHubCSVReporter` to produce all 7 reports.

---

## 9. Star Schema & Semantic Model

### 9.1 Dimensional Model

| Table | Type | Description | Key Columns |
|:------|:-----|:------------|:------------|
| `dim_date` | Dimension | Calendar date attributes | date_sk, full_date, year, quarter, month, day, day_of_week, is_weekend |
| `dim_time` | Dimension | Hour-of-day dimension | time_sk, hour, period (Morning/Afternoon/Evening/Night) |
| `dim_workspace` | Dimension | Workspace attributes | workspace_sk, workspace_id, workspace_name |
| `dim_item` | Dimension | Fabric item attributes | item_sk, item_id, item_name, item_type |
| `dim_user` | Dimension | User attributes | user_sk, submitted_by, created_by, last_updated_by |
| `dim_activity_type` | Dimension | Activity type attributes | activity_type_sk, activity_type, category |
| `dim_status` | Dimension | Activity status | status_sk, status, is_success |
| `fact_activity` | Fact | One row per activity event | activity_sk, event_id, activity_id, invoke_type, root_activity_id, job_instance_id, duration_seconds, + all dimension FKs |
| `fact_daily_metrics` | Fact | Aggregated daily metrics | date_sk, workspace_sk, total_activities, failed_count, avg_duration |
| `fact_user_metrics` | Fact | Aggregated user metrics | date_sk, user_sk, workspace_sk, total_activities, failed_count |

### 9.2 Building the Star Schema

**From the notebook** (Cell 18):
```python
from usf_fabric_monitoring.core.star_schema_builder import StarSchemaBuilder
builder = StarSchemaBuilder(output_directory="exports/star_schema")
results = builder.build_complete_schema(activities=activities, incremental=True)
```

**From CLI**:
```bash
usf-star-schema --input-dir exports/monitor_hub_analysis/parquet --output-dir exports/star_schema
```

### 9.3 Loading into Fabric Delta Tables

After star schema parquet files are generated, convert to Delta tables for the SQL endpoint:

```python
for parquet_file in Path("exports/star_schema").glob("*.parquet"):
    table_name = parquet_file.stem
    df = spark.read.parquet(str(parquet_file))
    df.write.mode("overwrite").format("delta").saveAsTable(table_name)
```

### 9.4 Updating the Semantic Model

After Delta tables are refreshed:
1. Open the Semantic Model in Fabric
2. Tables should auto-reflect Delta table schema changes
3. Add new columns (`invoke_type`, `root_activity_id`, etc.) to the model if not auto-detected
4. Create measures as needed for the new fields (e.g., `Scheduled Run Count = CALCULATE(COUNTROWS(fact_activity), fact_activity[invoke_type] = "Scheduled")`)

---

## 10. Lineage Explorer Deployment

### 10.1 Components

| Component | Technology | Purpose |
|:----------|:-----------|:--------|
| `server.py` | FastAPI + Uvicorn | REST API serving lineage data |
| `api_extended.py` | Python | ~44 query functions/endpoints |
| `graph_database/queries.py` | Python | Cypher query library (~140 statements across both files) |
| `graph_builder.py` | Python | Loads CSV/Parquet lineage data into Neo4j |
| `static/*.html` | D3.js | 5 interactive graph views |
| `docker-compose.yml` | Docker | Neo4j Community container |

### 10.2 Setup & Run

```bash
# 1. Extract lineage data
usf-extract-lineage --mode auto

# 2. Start Neo4j
cd lineage_explorer
docker-compose up -d
# Requires NEO4J_PASSWORD env var (no default)

# 3. Load data into Neo4j
make lineage-explorer
# Or: python graph_builder.py

# 4. Start API server
uvicorn server:app --host 127.0.0.1 --port 8000

# 5. Open browser
open http://127.0.0.1:8000
```

### 10.3 Views

| View | URL | Purpose |
|:-----|:----|:--------|
| Main Graph | `/` (`index.html`) | Force-directed graph of all Fabric items with detail panels |
| Elements Graph | `/static/elements_graph.html` | Item-level graph with connection tracking |
| Tables Graph | `/static/tables_graph.html` | Table-level graph with status and sync metadata |
| Table Impact | `/static/table_impact.html` | Blast radius analysis for table changes |
| Dashboard | `/static/dashboard.html` | Table health KPIs, source breakdown, pattern detection |
| Query Explorer | `/static/query_explorer.html` | Ad-hoc Cypher query execution (8+ pre-built queries) |

---

## 11. Authentication & Credentials

### 11.1 Credential Chain

The system resolves credentials in priority order:

1. **Environment variables** (`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`)
2. **`.env` file** (loaded via `python-dotenv`)
3. **DefaultAzureCredential** (fallback for Managed Identity in Fabric)

### 11.2 Token Management

- `FabricAuthenticator` in `auth.py` manages token lifecycle
- Proactive refresh: tokens refreshed **5 minutes** before expiry
- Scopes: `https://api.fabric.microsoft.com/.default` (Fabric) and `https://analysis.windows.net/powerbi/api/.default` (Power BI)

### 11.3 Required Permissions

| API | Permission Required |
|:----|:--------------------|
| Power BI Activity Events | Power BI Admin (Fabric Administrator role) |
| Fabric Admin Scanner | Fabric Administrator or delegated admin |
| Workspace management | Workspace Admin or Member role |
| Job Instance API | Workspace member with read access |

---

## 12. Configuration Files

### `config/inference_rules.json`

Maps activity types to human-readable categories and severity levels. Used by the enrichment module.

### `config/workspace_access_targets.json`

Defines required security groups and roles per workspace pattern:

```json
{
  "targets": [
    {
      "workspace_pattern": ".*\\[DEV\\]$",
      "required_principals": [
        {"display_name": "...", "principal_type": "Group", "role": "Admin"}
      ]
    }
  ]
}
```

### `config/workspace_access_suppressions.json`

Workspaces to exclude from access enforcement:

```json
{
  "suppressions": [
    {"workspace_name": "Personal Workspace", "reason": "User workspace"}
  ]
}
```

---

## 13. CLI Commands

| Command | Purpose | Key Flags |
|:--------|:--------|:----------|
| `usf-monitor-hub` | Run full monitoring pipeline | `--days`, `--output-dir`, `--member-only` |
| `usf-enforce-access` | Audit or enforce workspace access | `--mode assess\|enforce`, `--confirm` |
| `usf-extract-lineage` | Extract data lineage | `--mode auto\|iterative\|scanner` |
| `usf-star-schema` | Build dimensional model | `--input-dir`, `--output-dir`, `--incremental` |
| `usf-validate-config` | Validate JSON config files | `--config`, `--schema` |

---

## 14. Makefile Quick Reference

| Target | Purpose |
|:-------|:--------|
| `make install` | Install package in editable mode |
| `make build` | Build `.whl` package |
| `make test` | Run all tests with pytest |
| `make lint` | Run ruff linter |
| `make format` | Run ruff formatter |
| `make clean` | Remove build artifacts |
| `make monitor-hub` | Run monitor hub pipeline |
| `make enforce-access` | Run access enforcement |
| `make extract-lineage` | Run lineage extraction |
| `make lineage-explorer` | Load data + start Lineage Explorer |
| `make dev-setup` | Create conda env + install |
| `make dev-check` | Lint + test |
| `make check-env` | Verify environment configuration |

---

## 15. Testing & CI/CD

### 15.1 Test Suite

- **205 tests** across **17 test files**
- Run with: `make test` or `pytest`
- Key test files:
  - `test_pipeline.py` — Pipeline orchestration
  - `test_auth.py` — Authentication flows
  - `test_lineage_extraction.py` — Lineage extraction
  - `test_star_schema_builder.py` — Dimensional model building
  - `test_workspace_access_enforcer.py` — Access enforcement
  - `test_api_resilience.py` — Circuit breaker and retry logic

### 15.2 CI Pipeline (`.github/workflows/ci.yml`)

Runs on push to main and PRs:

1. **Lint**: `ruff check src/ tests/ scripts/`
2. **Type check**: `mypy src/` (continue-on-error, 112 pre-existing errors)
3. **Tests**: `pytest` with coverage
4. **Build**: `python -m build --wheel` (validates package builds)

---

## 16. Operational Procedures

### 16.1 Weekly: Review Activity Reports

```bash
conda activate fabric-monitoring
usf-monitor-hub --days 7
# Review: exports/monitor_hub_analysis/activities_master_*.csv
# Key metrics: failure rate, top failing items, user activity patterns
```

Or in Fabric: run the notebook (Cells 1-6 for extraction, Cells 8-17 for analysis).

### 16.2 Monthly: Access Compliance Audit

```bash
usf-enforce-access --mode assess
# Review output CSV for compliance gaps
# If gaps found:
usf-enforce-access --mode enforce --confirm
```

### 16.3 On Code Change: Deploy to Fabric

Follow Section 5.2 (Phase 1-5) above.

### 16.4 On Credential Rotation

1. Generate new SP credential in Azure portal
2. Update locally: edit `.env` file
3. Update in Fabric: upload new `.env` to `/lakehouse/default/Files/dot_env_files/.env`
4. No code changes needed

### 16.5 On Schema Change (New Columns)

When adding new columns to the pipeline output:

1. Update `data_loader.py` — add to `RENAME_MAP` if renaming API fields
2. Update `pipeline.py` — add to `job_rename_map` if from Job Instance API
3. Update `monitor_hub_reporter_clean.py` — add to `column_order` list
4. Update `schema.py` — add to DDL definitions
5. Update `star_schema_builder.py` — add to fact builder `.get()` calls
6. Update notebook Cell 10 — update `expected_columns` list and `22`→`N` references
7. Build new `.whl`, deploy to Fabric (Section 5.2)
8. Run regeneration cell (Cell 7) or wait for next scheduled extraction

### 16.6 Quarterly: Lineage Refresh

```bash
usf-extract-lineage --mode auto
cd lineage_explorer
docker-compose up -d
make lineage-explorer
```

---

## 17. Recommended CI/CD Lifecycle

The current deployment process is manual (Section 5). Below is the recommended automation path.

### 17.1 Phase 1: Automated Build & Test (Immediate)

**Already in place** via `.github/workflows/ci.yml`. Ensures every PR is linted, typed, tested, and builds successfully.

### 17.2 Phase 2: Automated Wheel Publishing (Short-term)

Add a release workflow that:
1. Triggers on Git tag (`v*`)
2. Builds the `.whl`
3. Publishes to a private PyPI (Azure Artifacts or GitHub Packages)
4. Creates a GitHub Release with the `.whl` as an artifact

```yaml
# .github/workflows/release.yml (proposed)
on:
  push:
    tags: ['v*']
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install build
      - run: python -m build --wheel
      - uses: actions/upload-artifact@v4
        with: { name: wheel, path: dist/*.whl }
      - run: gh release create ${{ github.ref_name }} dist/*.whl --generate-notes
        env: { GH_TOKEN: ${{ secrets.GITHUB_TOKEN }} }
```

### 17.3 Phase 3: Fabric Environment Automation (Medium-term)

Use the **Fabric REST API** to automate library uploads:

1. **Upload `.whl` to Lakehouse** via OneLake API (`PUT /Files/...`)
2. **Update workspace environment** via Fabric Environment API
3. **Trigger notebook run** via Fabric Job Scheduler API

This would enable a fully automated pipeline:
```
git push tag → CI builds wheel → API uploads to Lakehouse → API updates environment → API triggers notebook
```

### 17.4 Phase 4: Git Sync for Notebooks (Long-term)

Configure **Fabric Git Sync** on the `FUAM_Monitoring_Admin` workspace to sync notebooks directly from the repository. This eliminates manual notebook uploads.

Requirements:
- Workspace must be Git-connected to the monitoring repo
- Notebook format must be compatible with Fabric's `.ipynb` flavour
- Directory mapping: `notebooks/` → workspace notebook items

### 17.5 Phase 5: Full Lifecycle Automation

The end-state CI/CD would look like:

```
Developer pushes code
        │
        ▼
CI: lint → type check → test → build wheel
        │
        ▼
Release: tag → publish wheel → GitHub Release
        │
        ▼
Deploy: OneLake API uploads .whl + notebook
        │
        ▼
Environment: Fabric API installs .whl into workspace environment
        │
        ▼
Verify: Fabric API triggers notebook run → check exit status
        │
        ▼
Monitor: Scheduled pipeline runs daily at 03:00 UTC
```

---

## 18. Known Limitations & Technical Debt

| Limitation | Impact | Workaround | Resolution Path |
|:-----------|:-------|:-----------|:----------------|
| Activity Events API 28-day limit | Cannot analyse activity older than 28 days from API | Run daily, accumulate parquet files | Incremental Delta Lake archival |
| Pipeline/Dataflow lineage not extracted | Incomplete lineage graph | Focus on Lakehouse and Mirrored DB | Pending Admin API improvements |
| No real-time alerting | No proactive failure notifications | Review reports on schedule | Teams/Email integration |
| MyPy 112 pre-existing type errors | Reduced type safety confidence | `continue-on-error` in CI | Dedicated type annotation sprint |
| Manual Fabric deployment | Risk of human error, slow iteration | Follow Section 5.2 checklist | Implement Phase 2-4 (Section 17) |
| Notebook not Git-synced | Manual upload required for changes | Edit directly in Fabric UI for minor changes | Implement Phase 4 (Section 17) |
| Old 22-column CSVs in Lakehouse | Noise in validation output | Validation cell skips them correctly | Will age out via 180-day retention |
| `scripts/` not in `.whl` | Pipeline extraction fails if scripts not found | Notebook uses 8-hour cache from scheduled run | Include scripts in package or refactor |
| pandas SettingWithCopyWarning | Warning noise in logs | Harmless, use `.loc[]` | Low-priority fix in historical_analyzer.py |

---

## 19. Troubleshooting

| Symptom | Cause | Resolution |
|:--------|:------|:-----------|
| `Script not found: .../scripts/extract_historical_data.py` | Pipeline trying to import repo-level scripts from `.whl` install | Use 8-hour cache (run within 8hrs of scheduled extraction), or use Cell 7 regeneration |
| `activities_master has 22 columns (expected 26)` | Old CSV generated before v0.3.37 | Run Cell 6 (extraction) or Cell 7 (regeneration) to produce new 26-col output |
| `No valid CSV files found with expected 26-column schema` | No 26-col files exist yet | Run extraction or regeneration cell first |
| `Pipeline failed: Authentication failed` | SP credentials expired or missing | Check `.env` in Lakehouse, rotate credentials |
| `KeyError: 'analysis_period'` | Using regeneration cell without required dict keys | Cell 7 includes this — ensure you're using the latest notebook |
| Package version mismatch | Old `.whl` still installed | Remove old wheel from workspace library, upload new one, wait for environment rebuild |
| Spark can't read CSV in Fabric | Path format issue | `convert_to_spark_path()` in Cell 10 handles this — ensure notebook is up to date |
| `FORCE_REFRESH` not working | Env var not set | Add `FORCE_REFRESH=1` in Cell 4 config or set in `.env` |
| Star schema build fails | Empty activities list | Ensure activities_master has data before running star schema cell |
| Neo4j connection refused | Docker not running | `cd lineage_explorer && docker-compose up -d` |

---

*Document generated: 28 March 2026*
*Based on: `usf_fabric_monitoring` v0.3.37, commit `f72e748`*
