# Dashboard Sketch — Section 2 (Duration) “Duration & Performance” Page

Goal: A single Power BI page that **only depends on Section 2 numbered measures (9–15)** from `fabric_monitoring_measures_numbered.dax`, while still enabling practical performance analysis.

Measures used (Section 2 only):
- `9 Total Duration Hours`
- `10 Total Duration Minutes`
- `11 Avg Duration Minutes`
- `12 Avg Duration Seconds`
- `13 Max Duration Hours`
- `14 Long Running Activities`
- `15 Long Running Rate`

---

## Wireframe (1280×720, Fit to page)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ USF Fabric Monitoring — Duration & Performance                               │
│ [Date Range]  [Environment]  [Activity Category]  [Item Type]                │
│ (dim_date)    (dim_workspace) (dim_activity_type) (dim_item)                 │
├──────────────────────────────────────────────────────────────────────────────┤
│ KPI STRIP (cards)                                                            │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│ │ Total Hrs    │ │ Avg (min)    │ │ Max (hrs)    │ │ Long-Run #   │         │
│ │ [9]          │ │ [11]         │ │ [13]         │ │ [14]         │         │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘         │
│ ┌──────────────┐ ┌──────────────┐                                           │
│ │ Long-Run %   │ │ Total (min)  │                                           │
│ │ [15]         │ │ [10]         │                                           │
│ └──────────────┘ └──────────────┘                                           │
├──────────────────────────────────────────────────────────────────────────────┤
│ WHERE IS THE DURATION COMING FROM?                                            │
│ ┌─────────────────────────────────────┐ ┌──────────────────────────────────┐ │
│ │ Total Duration by Activity Type     │ │ Avg Duration by Activity Type     │ │
│ │ Y: dim_activity_type[activity_type] │ │ Y: dim_activity_type[activity_type]│
│ │ X: [9 Total Duration Hours]         │ │ X: [11 Avg Duration Minutes]      │ │
│ │ Tooltip: [13],[15],[14]             │ │ Tooltip: [13],[15],[14]           │ │
│ └─────────────────────────────────────┘ └──────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ ┌──────────────────────────────────┐ │
│ │ Total Duration by Workspace (Top N) │ │ Long-Running Hotspots (Top N)     │ │
│ │ Y: dim_workspace[workspace_name]    │ │ Y: dim_item[item_name]            │ │
│ │ X: [9 Total Duration Hours]         │ │ X: [14 Long Running Activities]   │ │
│ │ Tooltip: [11],[13],[15]             │ │ Tooltip: [13],[9],[15]            │ │
│ └─────────────────────────────────────┘ └──────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Visual specs (build checklist)

### Slicers (top row)
- Date range slicer: `dim_date[full_date]` (Between)
- Environment slicer: `dim_workspace[environment]` (Dropdown, multi-select)
- Activity category slicer: `dim_activity_type[activity_category]` (Dropdown)
- Item type slicer: `dim_item[item_type]` (Dropdown)

### KPI Cards
Recommended formatting:
- Hours: `#,##0.0`
- Minutes/Seconds: `#,##0.0`
- Long-running rate: `0.00%`

Cards:
- Total duration: `9 Total Duration Hours`
- Avg duration: `11 Avg Duration Minutes`
- Max duration: `13 Max Duration Hours`
- Long-running count: `14 Long Running Activities`
- Long-running rate: `15 Long Running Rate`
- Total duration (minutes): `10 Total Duration Minutes`

### Charts
1) Total Duration by Activity Type (bar)
- Category: `dim_activity_type[activity_type]`
- Value: `9 Total Duration Hours`
- Sort: descending by `9`
- Top N: 10
- Tooltip fields: `11 Avg Duration Minutes`, `13 Max Duration Hours`, `15 Long Running Rate`

2) Avg Duration by Activity Type (bar)
- Category: `dim_activity_type[activity_type]`
- Value: `11 Avg Duration Minutes`
- Sort: descending by `11`
- Top N: 10
- Tooltip fields: `9 Total Duration Hours`, `13 Max Duration Hours`, `15 Long Running Rate`

3) Total Duration by Workspace (bar)
- Category: `dim_workspace[workspace_name]`
- Value: `9 Total Duration Hours`
- Sort: descending by `9`
- Top N: 10
- Tooltip fields: `11 Avg Duration Minutes`, `13 Max Duration Hours`, `15 Long Running Rate`

4) Long-Running Hotspots (bar)
- Category: `dim_item[item_name]`
- Value: `14 Long Running Activities`
- Sort: descending by `14`
- Top N: 15
- Tooltip fields: `13 Max Duration Hours`, `9 Total Duration Hours`, `15 Long Running Rate`

---

## Why this satisfies “Section 2” and still works operationally
- Every KPI and chart uses only **duration + long-running** measures (9–15).
- The page highlights both:
  - **load** (total duration),
  - **efficiency** (average duration),
  - **risk** (long-running rate + max duration),
  - and **where to act** (workspace/item hotspots).

---

## Optional enhancements (still Section 2 compliant)
- Add a tooltip page (tooltip-only, no new DAX) showing: `9`, `11`, `13`, `14`, `15` for the hovered item/workspace/type.
- Use visual-level filters to default to `dim_activity_type[activity_category] IN {Pipeline, Notebook, Dataflow}` if you want this page to focus on scheduled executions (no new measures required).
