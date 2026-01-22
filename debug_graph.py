import pandas as pd
import json
import os
import glob
from pathlib import Path
import sys

# Add src to sys.path
sys.path.insert(0, os.path.abspath('src'))

from usf_fabric_monitoring.explorer.graph_builder import GraphBuilder

def debug():
    # Force the large real file
    file_path = "exports/lineage/mirrored_lineage_20260122_121529.csv"
    print(f"Reading {file_path}")
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        return

    df = pd.read_csv(file_path)
    print(f"DataFrame Shape: {df.shape}")
    
    builder = GraphBuilder(df)
    graph = builder.build()
    
    # Stats
    print(f"Total Nodes: {len(graph.nodes)}")
    print(f"Total Edges: {len(graph.edges)}")
    
    workspaces = [n for n in graph.nodes if n.type == 'workspace']
    items = [n for n in graph.nodes if n.type == 'item']
    sources = [n for n in graph.nodes if n.type == 'externalSource']
    
    print(f"Workspaces: {len(workspaces)}")
    print(f"Items: {len(items)}")
    print(f"External Sources: {len(sources)}")
    
    # Check parent relationships
    items_with_parent = [n for n in items if n.parentNode]
    print(f"Items with Parent: {len(items_with_parent)}")
    
    # Dump a few source labels
    print("\nSample External Source Labels:")
    for n in sources[:10]:
        print(f" - {n.data.label} (ID: {n.id[:8]}...)")

    print("\nSample Workspace Labels:")
    for n in workspaces[:5]:
        print(f" - {n.data.label}")

    print("\nSample Edges:")
    for e in graph.edges[:5]:
        print(f" - {e.source} -> {e.target} ({e.label})")

if __name__ == "__main__":
    debug()
