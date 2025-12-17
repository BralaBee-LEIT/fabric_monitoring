# Deploying Star Schema Builder in Microsoft Fabric

This guide explains how to use the star schema builder within Microsoft Fabric.

## Option 1: Fabric Notebook (Recommended)

The simplest approach is to run the star schema builder in a Fabric Notebook connected to a Lakehouse.

### Setup Steps

1. **Upload the module to Fabric Files**
   ```
   Lakehouse/Files/
   └── usf_fabric_monitoring/
       └── core/
           └── star_schema_builder.py
   ```

2. **Create a Notebook with the following cells:**

```python
# Cell 1: Setup paths for Fabric environment
import sys
from pathlib import Path

# Add custom module path
sys.path.insert(0, "/lakehouse/default/Files/usf_fabric_monitoring")

# Import the builder
from core.star_schema_builder import (
    StarSchemaBuilder,
    build_star_schema_from_parquet,
    ALL_STAR_SCHEMA_DDLS
)
```

```python
# Cell 2: Define Fabric-aware paths
INPUT_DIR = "/lakehouse/default/Files/monitor_hub_analysis/parquet"
OUTPUT_DIR = "/lakehouse/default/Files/star_schema"

# Or use Tables for Delta format
OUTPUT_DIR_DELTA = "/lakehouse/default/Tables"
```

```python
# Cell 3: Load activities from Lakehouse
import pandas as pd
from pathlib import Path

# Find latest activities file
activities_files = sorted(Path(INPUT_DIR).glob("activities_*.parquet"), reverse=True)
if activities_files:
    activities_df = pd.read_parquet(activities_files[0])
    print(f"Loaded {len(activities_df):,} activities from {activities_files[0].name}")
else:
    raise FileNotFoundError("No activities parquet files found")
```

```python
# Cell 4: Build star schema
builder = StarSchemaBuilder(output_directory=OUTPUT_DIR)
results = builder.build_complete_schema(
    activities=activities_df.to_dict(orient="records"),
    incremental=True  # Set to False for full refresh
)

print(f"Build completed in {results['duration_seconds']:.2f}s")
print(f"Fact records: {results['facts_built'].get('fact_activity', 0):,}")
```

```python
# Cell 5: Convert to Delta tables (optional - for SQL endpoint access)
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

# Convert each parquet to Delta table
for parquet_file in Path(OUTPUT_DIR).glob("*.parquet"):
    table_name = parquet_file.stem
    df = spark.read.parquet(str(parquet_file))
    df.write.mode("overwrite").format("delta").saveAsTable(table_name)
    print(f"Created Delta table: {table_name}")
```

---

## Option 2: Create Delta Tables Directly

Use the DDL statements to create managed Delta tables, then use Spark to populate:

```python
# Cell 1: Create dimension tables using DDL
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

# Create dim_date table
spark.sql("""
CREATE TABLE IF NOT EXISTS dim_date (
    date_sk INT NOT NULL,
    full_date DATE NOT NULL,
    day_of_week INT,
    day_of_week_name STRING,
    day_of_month INT,
    day_of_year INT,
    week_of_year INT,
    month_number INT,
    month_name STRING,
    quarter INT,
    year INT,
    is_weekend BOOLEAN,
    is_weekday BOOLEAN,
    fiscal_year INT,
    fiscal_quarter INT
) USING DELTA
""")

# Create fact_activity table (partitioned by date for performance)
spark.sql("""
CREATE TABLE IF NOT EXISTS fact_activity (
    activity_id STRING,
    date_sk INT NOT NULL,
    time_sk INT NOT NULL,
    workspace_sk BIGINT,
    item_sk BIGINT,
    user_sk BIGINT,
    activity_type_sk INT NOT NULL,
    status_sk INT NOT NULL,
    duration_seconds DOUBLE,
    duration_minutes DOUBLE,
    duration_hours DOUBLE,
    is_failed INT,
    is_success INT,
    is_long_running INT,
    record_count INT DEFAULT 1,
    source_system STRING,
    extracted_at TIMESTAMP
) USING DELTA
PARTITIONED BY (activity_date DATE)
""")

# Repeat for other tables...
```

---

## Option 3: Fabric Data Pipeline

Create an automated pipeline that:

1. **Runs daily** after Monitor Hub extraction
2. **Calls a Notebook** with the star schema builder
3. **Writes to Delta tables** in a Lakehouse

### Pipeline Steps:
```
[Schedule Trigger: Daily 6 AM]
    ↓
[Notebook Activity: Extract Monitor Hub Data]
    ↓
[Notebook Activity: Build Star Schema]
    ↓
[Notebook Activity: Write to Delta Tables]
    ↓
[Refresh Semantic Model (optional)]
```

---

## Option 4: Semantic Model Integration

Once the star schema is in Delta tables, create a Direct Lake semantic model:

### Model Structure:
```
Tables:
├── dim_date (Role-Playing: Activity Date, Extract Date)
├── dim_time
├── dim_workspace
├── dim_item
├── dim_user
├── dim_activity_type
├── dim_status
├── fact_activity
└── fact_daily_metrics

Relationships:
├── fact_activity[date_sk] → dim_date[date_sk]
├── fact_activity[time_sk] → dim_time[time_sk]
├── fact_activity[workspace_sk] → dim_workspace[workspace_sk]
├── fact_activity[item_sk] → dim_item[item_sk]
├── fact_activity[user_sk] → dim_user[user_sk]
├── fact_activity[activity_type_sk] → dim_activity_type[activity_type_sk]
└── fact_activity[status_sk] → dim_status[status_sk]
```

### Key Measures:
```dax
Total Activities = COUNTROWS(fact_activity)

Success Rate = 
DIVIDE(
    CALCULATE(COUNTROWS(fact_activity), fact_activity[is_success] = 1),
    COUNTROWS(fact_activity)
)

Avg Duration Minutes = AVERAGE(fact_activity[duration_minutes])

Unique Users = DISTINCTCOUNT(fact_activity[user_sk])

Activities by Workspace = 
SUMMARIZE(
    fact_activity,
    dim_workspace[workspace_name],
    "Activity Count", COUNTROWS(fact_activity)
)
```

---

## File Paths in Fabric

| Local Path | Fabric Lakehouse Path |
|------------|----------------------|
| `exports/monitor_hub_analysis/parquet/` | `/lakehouse/default/Files/monitor_hub_analysis/parquet/` |
| `exports/star_schema/` | `/lakehouse/default/Files/star_schema/` |
| Delta tables | `/lakehouse/default/Tables/` |

---

## Environment Variables in Fabric

Set these in your Notebook or Pipeline parameters:

```python
import os

# For Fabric Lakehouse
os.environ["EXPORT_DIRECTORY"] = "/lakehouse/default/Files/monitor_hub_analysis"
os.environ["STAR_SCHEMA_OUTPUT_DIR"] = "/lakehouse/default/Files/star_schema"

# Or use workspace-level environment variables in Fabric Settings
```

---

## Sample Fabric Notebook

A complete notebook is available at:
`notebooks/Fabric_Star_Schema_Builder.ipynb`

This notebook:
1. Checks for existing Monitor Hub data
2. Runs incremental star schema build
3. Converts to Delta tables
4. Validates relationships
5. Optionally refreshes semantic model
