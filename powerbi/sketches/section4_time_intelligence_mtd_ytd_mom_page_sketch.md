# Dashboard Sketch — Section 4 (Time Intelligence) “MTD / YTD / MoM Intelligence” Page

Goal: A single Power BI page that **only depends on Section 4 numbered measures (23–26)** from `fabric_monitoring_measures_numbered.dax`, while still being practical for ops:
- “How much activity so far this month / year?”
- “Are we trending up/down vs last month (as-of the same day-of-month)?”
- “Which workspaces/types/users are driving the month’s volume?”

Measures used (Section 4 only):
- `23 Activities MTD`
- `24 Activities Previous Month`
- `25 Activities YTD`
- `26 MoM Change %`

Important note (model behavior):
- These measures are **relative to an AsOfDate**: `MIN(TODAY(), MAX(dim_date[full_date]))`.
- Practically: they follow the latest selected date (date slicer-aware) but will not drift into future dates.
- `23 Activities MTD` and `25 Activities YTD` behave like “as-of totals” within the current selection.
- `26 MoM Change %` compares **MTD vs previous-month MTD (same day-of-month, capped at prev month end)**.

---

## Wireframe (1280×720, Fit to page)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ USF Fabric Monitoring — MTD / YTD / MoM Intelligence                         │
│ [Date Slicer]*  [Environment]  [Activity Category]  [Workspace]  [User]      │
│ (dim_date)      (dim_workspace) (dim_activity_type) (dim_workspace) (dim_user)│
├──────────────────────────────────────────────────────────────────────────────┤
│ KPI STRIP (cards)                                                            │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│ │ MTD [23]     │ │ Prev Mo [24] │ │ MoM % [26]   │ │ YTD [25]     │         │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘         │
├──────────────────────────────────────────────────────────────────────────────┤
│ MONTH FOCUS: WHAT’S DRIVING MTD?                                             │
│ ┌─────────────────────────────────────┐ ┌──────────────────────────────────┐ │
│ │ MTD by Workspace (Top N)            │ │ MTD by Activity Type (Top N)     │ │
│ │ Y: workspace_name                   │ │ Y: activity_type / category      │ │
│ │ X: [23 Activities MTD]              │ │ X: [23 Activities MTD]           │ │
│ │ Tooltip: [26]                       │ │ Tooltip: [26]                    │ │
│ └─────────────────────────────────────┘ └──────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ ┌──────────────────────────────────┐ │
│ │ MTD by User (Top N)                 │ │ MoM % by Workspace (Top N)       │ │
│ │ Y: user_principal_name              │ │ Y: workspace_name                 │ │
│ │ X: [23 Activities MTD]              │ │ X: [26 MoM Change %]              │ │
│ │ Tooltip: [26]                       │ │ Tooltip: [23],[24]                │ │
│ └─────────────────────────────────────┘ └──────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│ YEAR FOCUS: WHO ARE THE BIGGEST CONTRIBUTORS YTD?                            │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ YTD by Workspace (Top N)                                                   │
│ │ Y: workspace_name   X: [25 Activities YTD]   Tooltip: [23] (optional)      │
│ └──────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘

*Date slicer is optional; these measures anchor to the latest selected date (capped at today).
```

---

## Visual specs (build checklist)

### Slicers (top row)
- Environment slicer: `dim_workspace[environment]` (Dropdown, multi-select)
- Activity category slicer: `dim_activity_type[activity_category]` (Dropdown)
- Workspace slicer: `dim_workspace[workspace_name]` (Dropdown)
- User slicer: `dim_user[user_principal_name]` (Dropdown)
- Optional date slicer: `dim_date[full_date]` (Between)
  - Recommended: helps set AsOfDate (latest selected date).

### KPI Cards
Recommended formatting:
- Counts: `#,##0`
- Percent: `0.00%`

Cards:
- `23 Activities MTD`
- `24 Activities Previous Month`
- `26 MoM Change %`
- `25 Activities YTD`

### “Month focus” visuals
1) MTD by Workspace (Top N)
- Visual: bar chart (horizontal)
- Category: `dim_workspace[workspace_name]`
- Value: `23 Activities MTD`
- Sort: descending by `23`
- Top N: 15
- Tooltip fields:
  - `26 MoM Change %`

2) MTD by Activity Type (Top N)
- Visual: bar chart
- Category: `dim_activity_type[activity_type]` (or `activity_category` if you prefer a higher level)
- Value: `23 Activities MTD`
- Sort: descending by `23`
- Top N: 10–15
- Tooltip fields:
  - `26 MoM Change %`

3) MTD by User (Top N)
- Visual: bar chart
- Category: `dim_user[user_principal_name]`
- Value: `23 Activities MTD`
- Sort: descending by `23`
- Top N: 10–15
- Tooltip fields:
  - `26 MoM Change %`

4) MoM % by Workspace (Top movers)
- Visual: diverging bar chart recommended
- Category: `dim_workspace[workspace_name]`
- Value: `26 MoM Change %`
- Sort: descending by `26` (bookmark a “worst movers” view sorting ascending)
- Top N: 15
- Tooltip fields:
  - `23 Activities MTD`
  - `24 Activities Previous Month`

### “Year focus” visuals
5) YTD by Workspace (Top N)
- Visual: bar chart
- Category: `dim_workspace[workspace_name]`
- Value: `25 Activities YTD`
- Sort: descending by `25`
- Top N: 15
- Tooltip fields:
  - `23 Activities MTD` (optional)

---

## Why this satisfies “Section 4 only” and still works operationally
- KPI strip answers **how much** (MTD/YTD) and **direction** (MoM %).
- The MTD breakdown visuals answer **where the month’s volume comes from** (workspace/type/user).
- The MoM movers visual answers **which workspaces changed most vs last month’s MTD**.
- Everything uses only Section 4 measures (23–26) for values.

---

## Optional enhancements (still Section 4 compliant)
- Add a table “Workspace Month Summary” with columns:
  - `dim_workspace[workspace_name]`, `23`, `24`, `26`, `25`
- Add bookmarks:
  - “Best MoM Movers (↑)” (sort desc by `26`)
  - “Worst MoM Movers (↓)” (sort asc by `26`)
- Add conditional formatting using the `26 MoM Change %` value:
  - Green for positive, red for negative, neutral for blank/zero.
