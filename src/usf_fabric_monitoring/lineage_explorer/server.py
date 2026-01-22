"""
Lineage Explorer API Server
---------------------------
FastAPI backend serving the lineage graph data and static frontend.

Endpoints:
- GET /api/graph - Full lineage graph
- GET /api/stats - Graph statistics
- GET /api/workspaces - List of workspaces
- GET /api/health - Health check
- POST /api/refresh - Refresh graph from CSV
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import pandas as pd
import glob
import os
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from .graph_builder import (
    build_graph_from_csv, 
    compute_graph_stats, export_graph_to_json
)
from .models import LineageGraph, GraphStats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Path Configuration
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[2]  # usf_fabric_monitoring root
EXPORT_DIR = PROJECT_ROOT / "exports" / "lineage"
FRONTEND_DIR = BASE_DIR / "static"


class GraphCache:
    """In-memory cache for the lineage graph."""
    
    def __init__(self, ttl_seconds: int = 300):
        self.graph: Optional[LineageGraph] = None
        self.stats: Optional[GraphStats] = None
        self.loaded_at: Optional[datetime] = None
        self.source_file: Optional[str] = None
        self.source_mtime: Optional[float] = None
        self.ttl_seconds = ttl_seconds
        self.load_time_ms: float = 0
    
    def is_valid(self) -> bool:
        if self.graph is None or self.source_file is None:
            return False
        
        try:
            current_mtime = os.path.getmtime(self.source_file)
            if current_mtime != self.source_mtime:
                logger.info("Source file modified, cache invalidated")
                return False
        except OSError:
            return False
        
        if self.loaded_at:
            age = (datetime.now() - self.loaded_at).total_seconds()
            if age > self.ttl_seconds:
                logger.info(f"Cache TTL expired ({age:.0f}s > {self.ttl_seconds}s)")
                return False
        
        return True
    
    def set(self, graph: LineageGraph, stats: GraphStats, source_file: str, load_time_ms: float):
        self.graph = graph
        self.stats = stats
        self.source_file = source_file
        self.source_mtime = os.path.getmtime(source_file)
        self.loaded_at = datetime.now()
        self.load_time_ms = load_time_ms
        logger.info(f"Cache updated: {graph.total_items} items, {graph.total_connections} edges (loaded in {load_time_ms:.0f}ms)")
    
    def clear(self):
        self.graph = None
        self.stats = None
        self.loaded_at = None
        logger.info("Cache cleared")


# Global cache
_cache = GraphCache(ttl_seconds=300)


def find_lineage_csv() -> Path:
    """Find the most recent lineage CSV file."""
    search_paths = [EXPORT_DIR]
    
    cwd_export = Path("exports/lineage")
    if cwd_export.exists():
        search_paths.append(cwd_export)
    
    for search_path in search_paths:
        if not search_path.exists():
            continue
        
        csv_files = glob.glob(str(search_path / "mirrored_lineage_*.csv"))
        if not csv_files:
            csv_files = glob.glob(str(search_path / "*.csv"))
        
        if csv_files:
            # Use largest file (real data is larger than test files)
            return Path(max(csv_files, key=os.path.getsize))
    
    raise FileNotFoundError(f"No lineage CSV found in: {search_paths}")


def load_graph(force_refresh: bool = False) -> tuple[LineageGraph, GraphStats]:
    """Load graph data, using cache when available."""
    global _cache
    
    if not force_refresh and _cache.is_valid():
        return _cache.graph, _cache.stats
    
    start_time = time.time()
    
    csv_path = find_lineage_csv()
    logger.info(f"Loading: {csv_path} ({os.path.getsize(csv_path)} bytes)")
    
    graph = build_graph_from_csv(csv_path)
    stats = compute_graph_stats(graph)
    
    load_time_ms = (time.time() - start_time) * 1000
    _cache.set(graph, stats, str(csv_path), load_time_ms)
    
    return graph, stats


# FastAPI App
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-load cache on startup."""
    logger.info("Starting Fabric Lineage Explorer")
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info(f"Export dir: {EXPORT_DIR}")
    
    try:
        load_graph()
        logger.info("Initial cache loaded successfully")
    except Exception as e:
        logger.warning(f"Could not pre-load cache: {e}")
    
    yield
    
    logger.info("Shutting down Fabric Lineage Explorer")


app = FastAPI(
    title="Fabric Lineage Explorer",
    description="Interactive visualization of Microsoft Fabric lineage relationships",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Endpoints
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "cached": _cache.graph is not None,
        "loaded_at": _cache.loaded_at.isoformat() if _cache.loaded_at else None,
        "source_file": _cache.source_file
    }


@app.get("/api/graph")
async def get_graph():
    """Get the full lineage graph."""
    try:
        graph, _ = load_graph()
        return graph.model_dump(mode='json')
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error loading graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error loading graph: {str(e)}")


@app.get("/api/stats")
async def get_stats():
    """Get graph statistics."""
    try:
        _, stats = load_graph()
        return stats.model_dump()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error computing stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspaces")
async def list_workspaces():
    """List all workspaces with item counts."""
    try:
        graph, _ = load_graph()
        
        # Count items per workspace
        item_counts = {}
        for item in graph.items:
            ws_id = item.workspace_id
            item_counts[ws_id] = item_counts.get(ws_id, 0) + 1
        
        workspaces = [
            {
                "id": ws.id,
                "name": ws.name,
                "item_count": item_counts.get(ws.id, 0)
            }
            for ws in sorted(graph.workspaces, key=lambda w: w.name)
        ]
        
        return {"workspaces": workspaces}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/refresh")
async def refresh_graph():
    """Force refresh the graph from CSV."""
    try:
        _cache.clear()
        graph, stats = load_graph(force_refresh=True)
        return {
            "status": "refreshed",
            "items": graph.total_items,
            "edges": graph.total_connections,
            "load_time_ms": _cache.load_time_ms
        }
    except Exception as e:
        logger.error(f"Error refreshing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Serve static frontend
@app.get("/")
async def serve_frontend():
    """Serve the frontend application."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Frontend not found")


# Mount static files if directory exists
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# Allow overriding CSV path
_override_csv_path: Optional[str] = None


def set_csv_path(path: str):
    """Set the CSV path to use (for programmatic use)."""
    global _override_csv_path
    _override_csv_path = path


# Monkey patch find_lineage_csv to check override
_original_find_lineage_csv = find_lineage_csv

def _find_lineage_csv_with_override() -> Path:
    if _override_csv_path:
        return Path(_override_csv_path)
    return _original_find_lineage_csv()

# Replace the function
find_lineage_csv = _find_lineage_csv_with_override


def run_server(csv_path: Optional[str] = None, host: str = "127.0.0.1", port: int = 8000):
    """
    Run the Lineage Explorer server.
    
    Args:
        csv_path: Optional path to lineage CSV file. Auto-detects if not provided.
        host: Server host (default: 127.0.0.1)
        port: Server port (default: 8000)
    """
    import uvicorn
    
    if csv_path:
        set_csv_path(csv_path)
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
