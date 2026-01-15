# Dashboard Sketch — Section 1 (Core KPIs) “Daily Health” Page

Goal: A single Power BI page that **only depends on Section 1 numbered measures (1–8)** from `fabric_monitoring_measures_numbered.dax`, while still being operationally useful.

Measures used (Section 1 only):
- `1 Total Activities`
- `2 Failed Activities`
- `3 Successful Activities`
- `4 Success Rate`
- `5 Failure Rate`
- `6 Active Users`
- `7 Active Workspaces`
- `8 Active Items`

---

## Wireframe (1280×720, Fit to page)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ USF Fabric Monitoring — Daily Health                                         │
│ [Date Range Slicer]  [Environment Slicer]  [Activity Category Slicer]        │
│ (dim_date)           (dim_workspace)       (dim_activity_type)               │
├──────────────────────────────────────────────────────────────────────────────┤
│ KPI STRIP (cards)                                                                
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│ │ Total        │ │ Failed       │ │ Success %    │ │ Failure %    │         │
│ │ [1]          │ │ [2]          │ │ [4]          │ │ [5]          │         │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘         │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│ │ Active       │ │ Active       │ │ Active       │ │ Successful   │         │
│ │ Users [6]    │ │ Workspaces[7]│ │ Items [8]    │ │ [3]          │         │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘         │
├──────────────────────────────────────────────────────────────────────────────┤
│ TREND + WHERE IT’S COMING FROM                                                │
│ ┌─────────────────────────────────────┐ ┌──────────────────────────────────┐ │
│ │ Activity Trend (line/area)          │ │ Top Workspaces by Failures (bar) │ │
│ │ X: dim_date[full_date]              │ │ Y: dim_workspace[workspace_name] │ │
│ │ Y1: [1 Total Activities]            │ │ X: [2 Failed Activities]         │ │
│ │ Y2: [2 Failed Activities]           │ │ Tooltip: [5],[4],[1]             │ │
│ └─────────────────────────────────────┘ └──────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ ┌──────────────────────────────────┐ │
│ │ Top Items by Failures (bar)         │ │ Top Users by Failures (bar)      │ │
│ │ Y: dim_item[item_name]              │ │ Y: dim_user[user_principal_name] │ │
│ │ X: [2 Failed Activities]            │ │ X: [2 Failed Activities]         │ │
│ │ Tooltip: [5],[4],[1]                │ │ Tooltip: [5],[4],[1]             │ │
│ └─────────────────────────────────────┘ └──────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Visual specs (copy/paste into build checklist)

### Slicers (top row)
- Date range slicer: `dim_date[full_date]` (Between)
- Environment slicer: `dim_workspace[environment]` (Dropdown, multi-select)
- Activity category slicer: `dim_activity_type[activity_category]` (Dropdown)

### KPI Cards (8)
- Total: `1 Total Activities`
- Failed: `2 Failed Activities`
- Success rate: `4 Success Rate`
- Failure rate: `5 Failure Rate`
- Active users: `6 Active Users`
- Active workspaces: `7 Active Workspaces`
- Active items: `8 Active Items`
- Successful: `3 Successful Activities`

Recommended formatting:
- Counts: `#,##0`
- Rates: `0.00%`

### Trend chart
- Visual: line chart (or combo chart if you prefer)
- X axis: `dim_date[full_date]`
- Y values:
  - `1 Total Activities` (blue)
  - `2 Failed Activities` (red, secondary axis recommended)

### “Top” breakdown bars
Use **Top N = 10** (or 15 for Items if you have long tails):
- Top Workspaces by Failures
  - Category: `dim_workspace[workspace_name]`
  - Value: `2 Failed Activities`
- Top Items by Failures
  - Category: `dim_item[item_name]`
  - Value: `2 Failed Activities`
- Top Users by Failures
  - Category: `dim_user[user_principal_name]`
  - Value: `2 Failed Activities`

Tooltip fields (all bars):
- `1 Total Activities`
- `2 Failed Activities`
- `5 Failure Rate`
- `4 Success Rate`

---

## Why this satisfies “Section 1” and still feels actionable
- All KPIs + all charts rely on the **Section 1 core measures only**.
- The page still answers “what’s happening?” (trend) and “where is it happening?” (top workspaces/items/users).

---

## Optional (still Section 1 compliant)
If you want a single “health score” card without using non-section measures, you can create it as a *visual-only* KPI by using `4 Success Rate` and setting thresholds in the visual formatting (no new DAX required).
