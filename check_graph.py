#!/usr/bin/env python3
"""Diagnostic script to check the graph generation."""
import pandas as pd
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from usf_fabric_monitoring.explorer.graph_builder import GraphBuilder

def main():
    csv_path = "exports/lineage/mirrored_lineage_20260122_121529.csv"
    
    print(f"Reading: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"CSV rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # Check Source Connection column
    source_conn = df['Source Connection'].dropna()
    print(f"\nSource Connection values: {len(source_conn)}")
    print("Sample values:")
    for i, val in enumerate(source_conn.head(5)):
        print(f"  {i+1}. {str(val)[:100]}...")
    
    print("\n--- Building Graph ---")
    builder = GraphBuilder(df)
    graph = builder.build()
    
    print(f"\nTotal Nodes: {len(graph.nodes)}")
    print(f"Total Edges: {len(graph.edges)}")
    
    # Count by type
    by_type = {}
    for n in graph.nodes:
        by_type[n.type] = by_type.get(n.type, 0) + 1
    print(f"By Type: {by_type}")
    
    # Check for bad labels (raw JSON in labels)
    bad_labels = []
    for n in graph.nodes:
        label = str(n.data.label)
        if "'type':" in label or '"type":' in label:
            bad_labels.append(n)
    
    print(f"\nNodes with raw JSON in label: {len(bad_labels)}")
    if bad_labels:
        print("Examples of BAD labels:")
        for n in bad_labels[:5]:
            print(f"  - [{n.type}] {n.data.label[:80]}...")
    
    # Show some external source labels
    ext_sources = [n for n in graph.nodes if n.type == 'externalSource']
    if ext_sources:
        print(f"\nExternal Source Labels ({len(ext_sources)} total):")
        for n in ext_sources[:10]:
            print(f"  - {n.data.label}")
    
    print("\n✅ Diagnostic complete")

if __name__ == "__main__":
    main()
