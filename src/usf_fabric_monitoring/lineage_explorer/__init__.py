"""
Fabric Lineage Explorer
-----------------------
A minimalist, intelligent visualization tool for Microsoft Fabric lineage data.

Key Design Principles:
1. Graph-native data model (no CSV intermediate)
2. Clean, minimalist UI with intuitive interactions
3. Smart filtering by workspace, item type, source type
4. Responsive design for business and technical users

Usage:
    # Option 1: CLI
    python -m usf_fabric_monitoring.lineage_explorer
    
    # Option 2: Import
    from usf_fabric_monitoring.lineage_explorer import run_server
    run_server(csv_path="path/to/lineage.csv", port=8000)
"""

__version__ = "1.0.0"

from .server import run_server
from .graph_builder import build_graph_from_csv, compute_graph_stats, export_graph_to_json
from .models import LineageGraph, Workspace, FabricItem, ExternalSource, LineageEdge

__all__ = [
    "run_server",
    "build_graph_from_csv",
    "compute_graph_stats",
    "export_graph_to_json",
    "LineageGraph",
    "Workspace",
    "FabricItem", 
    "ExternalSource",
    "LineageEdge",
]
