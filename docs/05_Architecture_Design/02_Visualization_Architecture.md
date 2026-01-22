# Proposed Architecture: Fabric Lineage Explorer

**Status**: Proposal  
**Date**: 2026-01-22  
**Goal**: Create a standalone, best-in-class visualization tool for Microsoft Fabric lineage and topology.

---

## 1. Executive Summary
The current CSV-based visualization (`visualize_lineage.py`) is a good proof-of-concept but lacks the interactivity required for "Deep Dive" analysis of complex enterprise topologies. We propose moving to a dedicated sub-project (`fabric-lineage-explorer`) utilizing a modern web stack.

## 2. Technical Stack Recommendation

| Component | Technology | Reasoning |
| :--- | :--- | :--- |
| **Frontend Framework** | **React (Vite) + TypeScript** | Industry standard for complex, interactive UIs. |
| **Visualization Library** | **React Flow** | Best-in-class support for "Sub-Flows" (nesting Items inside Workspaces). |
| **Layout Engine** | **Dagre.js** or **Elkjs** | Essential for auto-arranging thousands of nodes without overlap. |
| **Backend / CLI** | **FastAPI** | Lightweight Python server to parse local data and serve the UI. |
| **Data Format** | **JSON (Graph Schema)** | Replaces CSV. Standard nodes/edges format optimized for frontend parsing. |

## 3. Data Structure (The "Graph JSON")

Move away from tabular CSV to a hierarchical Graph JSON format. This allows representing the "Compound Graph" nature of Fabric (Items live *inside* Workspaces).

```json
{
  "nodes": [
    {
      "id": "workspace_A",
      "type": "workspaceGroup",
      "data": { "label": "Finance Workspace", "capacity": "F64" },
      "position": { "x": 0, "y": 0 },
      "style": { "width": 500, "height": 300 } # Container size
    },
    {
      "id": "lakehouse_1",
      "type": "fabricItem",
      "parentNode": "workspace_A", # Critical: This item lives inside the workspace
      "extent": "parent",
      "data": { "label": "Revenue Data", "itemType": "Lakehouse" }
    },
    {
      "id": "external_adls",
      "type": "externalSource",
      "data": { "label": "Azure Data Lake Gen2", "connection": "abfss://..." }
    }
  ],
  "edges": [
    {
      "id": "e1",
      "source": "lakehouse_1",
      "target": "external_adls",
      "label": "Shortcut",
      "animated": true
    }
  ]
}
```

## 4. Key Features Roadmap

### Phase 1: The Explorer (MVP)
*   **Interactive Canvas**: Infinite panning and zooming.
*   **Semantic Zooming**: Zoom out to see only Workspace clusters; zoom in to see individual Items.
*   **Search**: Instant search for any Item or Shortcut.

### Phase 2: The Analyst (Impact Analysis)
*   **Upstream/Downstream Highlighting**: Click a Lakehouse to see exactly where data comes from and where it goes.
*   **Orphan Detection**: Visual highlight of items with no connections.
*   **Cross-Workspace Dependencies**: Special coloring for edges that cross workspace boundaries (governance risk).

### Phase 3: The Operator (Live Status)
*   **Status Overlay**: Integration with `Monitor Hub` to color-code items red/green based on the last run status.
*   **Metadata Side-Panel**: Click an item to view Owner, Sensitivity Label, and Endorsement status.

## 5. Deployment Strategy
The tool will be packaged as a single CLI command within the existing repository:

```bash
# User command
fabric-lineage explore

# Action
1. Parses local audit/lineage data.
2. Generates `graph.json`.
3. Launches local server at http://localhost:8080.
```
