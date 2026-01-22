"""
CLI entry point for Lineage Explorer.

Usage:
    python -m usf_fabric_monitoring.lineage_explorer [OPTIONS]
    
Options:
    --csv PATH      Path to lineage CSV file
    --port PORT     Server port (default: 8000)
    --host HOST     Server host (default: 127.0.0.1)
"""

import argparse
import sys
from pathlib import Path

# Find the default CSV if exists
def find_default_csv():
    """Look for the most recent lineage CSV."""
    # Get the module directory and navigate up to project root
    module_dir = Path(__file__).parent
    # Go up: lineage_explorer -> usf_fabric_monitoring -> src -> usf_fabric_monitoring (root)
    project_root = module_dir.parent.parent.parent
    
    lineage_dir = project_root / "exports" / "lineage"
    
    # Also check relative to current working directory
    cwd_lineage = Path.cwd() / "exports" / "lineage"
    
    for search_dir in [lineage_dir, cwd_lineage]:
        if search_dir.exists():
            csv_files = sorted(search_dir.glob("mirrored_lineage_*.csv"), reverse=True)
            if csv_files:
                return str(csv_files[0])
    
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Fabric Lineage Explorer - Interactive lineage visualization"
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=find_default_csv(),
        help="Path to lineage CSV file (auto-detects if not specified)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Server host (default: 127.0.0.1)"
    )
    
    args = parser.parse_args()
    
    if not args.csv:
        print("Error: No lineage CSV file found.")
        print("Please specify with --csv PATH")
        sys.exit(1)
    
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)
    
    print(f"🔗 Loading lineage data from: {csv_path}")
    print(f"🚀 Starting server at http://{args.host}:{args.port}")
    
    from .server import run_server
    run_server(csv_path=str(csv_path), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
