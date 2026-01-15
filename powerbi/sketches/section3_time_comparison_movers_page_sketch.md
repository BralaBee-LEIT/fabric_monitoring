# Dashboard Sketch — Section 3 (Time Comparison) “Time Comparison & Movers” Page

Goal: A single Power BI page that **only depends on Section 3 numbered measures (16–22)** from `fabric_monitoring_measures_numbered.dax`, while still being operationally useful (spot *what changed* and *where*).

Measures used (Section 3 only):
- `16 Activities Today`
- `17 Activities Yesterday`
- `18 Activities Last 7 Days`
- `19 Activities Last 28 Days`
- `20 Activities Previous 7 Days`
- `21 DoD Change %`
- `22 WoW Change %`

Important note (model behavior):
- These measures are **relative to an AsOfDate**: `MIN(TODAY(), MAX(dim_date[full_date]))`.
- Practically: they follow the latest selected date (date slicer-aware) but will not drift into future dates.
- They work best to compare “current vs previous” and to rank/sort **by workspace / item / user / type**.

---

## Wireframe (1280×720, Fit to page)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ USF Fabric Monitoring — Time Comparison & Movers                             │
│ [Date Range Slicer]*  [Environment]  [Activity Category]  [Workspace]        │
│ (dim_date)            (dim_workspace) (dim_activity_type)   (dim_workspace)  │
├──────────────────────────────────────────────────────────────────────────────┤
│ KPI STRIP (cards)                                                            │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│ │ Today [16]   │ │ Yesterday[17]│ │ DoD % [21]   │ │ Last 7 [18]  │         │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘         │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                         │
│ │ Prev 7 [20]  │ │ WoW % [22]   │ │ Last 28 [19] │                         │
│ └──────────────┘ └──────────────┘ └──────────────┘                         │
├──────────────────────────────────────────────────────────────────────────────┤
│ WHERE DID IT CHANGE? (TOP MOVERS)                                            │
│ ┌─────────────────────────────────────┐ ┌──────────────────────────────────┐ │
│ │ WoW % by Workspace (Top N)          │ │ DoD % by Workspace (Top N)       │ │
│ │ Y: dim_workspace[workspace_name]    │ │ Y: dim_workspace[workspace_name] │ │
│ │ X: [22 WoW Change %]                │ │ X: [21 DoD Change %]             │ │
│ │ Tooltip: [18],[20]                  │ │ Tooltip: [16],[17]               │ │
│ └─────────────────────────────────────┘ └──────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ ┌──────────────────────────────────┐ │
│ │ Last 7 Days by Activity Type        │ │ Last 7 Days by User (Top N)      │ │
│ │ Y: dim_activity_type[activity_type] │ │ Y: dim_user[user_principal_name] │ │
│ │ X: [18 Activities Last 7 Days]      │ │ X: [18 Activities Last 7 Days]   │ │
│ │ Tooltip: [22] (optional)            │ │ Tooltip: [22] (optional)         │ │
│ └─────────────────────────────────────┘ └──────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘

*Date slicer can remain for consistency; Section 3 measures use the latest selected date (capped at today).
```

---

## Visual specs (build checklist)

### Slicers (top row)
- Environment slicer: `dim_workspace[environment]` (Dropdown, multi-select)
- Activity category slicer: `dim_activity_type[activity_category]` (Dropdown)
- Workspace slicer: `dim_workspace[workspace_name]` (Dropdown)
- Optional date slicer: `dim_date[full_date]` (Between)
  - Recommended: Section 3 measures are slicer-aware and anchor to the latest selected date.

### KPI Cards
Recommended formatting:
- Counts: `#,##0`
- Percent: `0.00%`

Cards:
- `16 Activities Today`
- `17 Activities Yesterday`
- `21 DoD Change %`
- `18 Activities Last 7 Days`
- `20 Activities Previous 7 Days`
- `22 WoW Change %`
- `19 Activities Last 28 Days`

### “Top Movers” charts
1) WoW % by Workspace (diverging bar recommended)
- Category: `dim_workspace[workspace_name]`
- Value: `22 WoW Change %`
- Sort: descending by `22` (or ascending to show worst movers)
- Top N: 15
- Tooltip fields: `18 Activities Last 7 Days`, `20 Activities Previous 7 Days`

2) DoD % by Workspace (diverging bar recommended)
- Category: `dim_workspace[workspace_name]`
- Value: `21 DoD Change %`
- Sort: descending by `21`
- Top N: 15
- Tooltip fields: `16 Activities Today`, `17 Activities Yesterday`

3) Last 7 Days by Activity Type
- Category: `dim_activity_type[activity_type]`
- Value: `18 Activities Last 7 Days`
- Sort: descending by `18`
- Top N: 10–15
- Tooltip fields: `22 WoW Change %` (optional), `19 Activities Last 28 Days` (optional)

4) Last 7 Days by User (Top N)
- Category: `dim_user[user_principal_name]`
- Value: `18 Activities Last 7 Days`
- Sort: descending by `18`
- Top N: 10–15
- Tooltip fields: `22 WoW Change %` (optional)

---

## Why this satisfies “Section 3” and is better than a basic snapshot
- The KPI strip answers **“what changed?”** using DoD/WoW measures.
- The movers visuals answer **“where did it change?”** by ranking workspaces/users/types by change and recent activity.
- Everything uses only Section 3 measures (16–22) for values.

---

## Optional enhancements (still Section 3 compliant)
- Add a table named “Workspace Movers” with columns:
  - `dim_workspace[workspace_name]`, `18`, `20`, `22`, `16`, `17`, `21`
- Add bookmarks:
  - “Best Movers (WoW ↑)” (sort desc)
  - “Worst Movers (WoW ↓)” (sort asc)
