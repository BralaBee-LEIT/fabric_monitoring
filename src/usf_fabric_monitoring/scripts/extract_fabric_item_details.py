"""
Fabric Item Details Extraction Script

Extracts detailed information about Fabric items including:
- Job instances for ALL supported item types (Pipelines, Notebooks, Dataflows, etc.)
- Lakehouse tables (maintenance status)

Usage:
    python extract_fabric_item_details.py
    python extract_fabric_item_details.py --workspace <workspace_id>
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parents[2]))

from usf_fabric_monitoring.core.auth import create_authenticator_from_env
from usf_fabric_monitoring.core.extractor import FabricDataExtractor
from usf_fabric_monitoring.core.fabric_item_details import FabricItemDetailExtractor
from usf_fabric_monitoring.core.logger import setup_logging

def parse_args(args=None):
    parser = argparse.ArgumentParser(description="Extract Fabric item details")
    parser.add_argument("--workspace", help="Filter by specific workspace ID")
    parser.add_argument("--output-dir", default="exports/fabric_item_details", help="Output directory")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    return parser.parse_args(args)

def save_json(data: Any, filepath: Path):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

def get_last_processed_time(output_dir: Path) -> datetime:
    """Finds the latest endTimeUtc from existing job JSON files."""
    max_time = None
    if not output_dir.exists():
        return None
    
    # Check only the most recent files to avoid scanning everything
    # Sort files by modification time, newest first
    files = sorted(output_dir.glob("jobs_*.json"), key=os.path.getmtime, reverse=True)
    
    # Scan up to 5 most recent files
    for file_path in files[:5]:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                for job in data:
                    end_time_str = job.get("endTimeUtc")
                    if end_time_str:
                        # Handle ISO format with 'Z'
                        end_time_str = end_time_str.replace('Z', '+00:00')
                        try:
                            dt = datetime.fromisoformat(end_time_str)
                            if max_time is None or dt > max_time:
                                max_time = dt
                        except ValueError:
                            pass
        except Exception:
            continue
            
    return max_time

def main(argv=None):
    load_dotenv()
    args = parse_args(argv)
    
    logger = setup_logging(name="fabric_item_details", level=getattr(logging, args.log_level.upper()))
    
    try:
        authenticator = create_authenticator_from_env()
        extractor = FabricDataExtractor(authenticator)
        detail_extractor = FabricItemDetailExtractor(authenticator)
        
        output_dir = Path(args.output_dir)
        last_processed_time = get_last_processed_time(output_dir)
        
        if last_processed_time:
            logger.info(f"Incremental run: Fetching jobs completed after {last_processed_time}")
        else:
            logger.info("Full run: No previous job data found or unable to determine last run time")

        # Get workspaces
        logger.info("Fetching workspaces...")
        workspaces = extractor.get_workspaces(tenant_wide=False, exclude_personal=True)
        
        if args.workspace:
            workspaces = [ws for ws in workspaces if ws.get("id") == args.workspace]
            logger.info(f"Filtered to workspace: {args.workspace}")
            
        logger.info(f"Found {len(workspaces)} workspaces to process")
        
        all_details = {
            "jobs": [],
            "lakehouses": []
        }
        
        for ws in workspaces:
            workspace_id = ws.get("id")
            workspace_name = ws.get("displayName")
            logger.info(f"Processing workspace: {workspace_name} ({workspace_id})")
            
            items = extractor.get_workspace_items(workspace_id)
            
            for item in items:
                item_id = item.get("id")
                item_type = item.get("type")
                item_name = item.get("displayName")
                
                if item_type == "Lakehouse":
                    logger.info(f"  Fetching tables for Lakehouse: {item_name}")
                    tables = detail_extractor.get_lakehouse_tables(workspace_id, item_id)
                    for table in tables:
                        table["_workspace_name"] = workspace_name
                        table["_item_name"] = item_name
                        table["_item_type"] = item_type
                        all_details["lakehouses"].append(table)
                else:
                    # Try to fetch jobs for all other item types (Pipelines, Notebooks, Dataflows, etc.)
                    # This ensures we capture any item type that supports the job instances API
                    try:
                        jobs = detail_extractor.get_item_job_instances(workspace_id, item_id)
                        if jobs:
                            # Filter jobs if incremental run
                            if last_processed_time:
                                new_jobs = []
                                for job in jobs:
                                    end_time_str = job.get("endTimeUtc")
                                    if end_time_str:
                                        try:
                                            dt = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                                            if dt > last_processed_time:
                                                new_jobs.append(job)
                                        except ValueError:
                                            # If date parsing fails, include it to be safe
                                            new_jobs.append(job)
                                    else:
                                        # If no end time, include it (might be running)
                                        new_jobs.append(job)
                                jobs = new_jobs

                            if jobs:
                                logger.info(f"  Found {len(jobs)} new jobs for {item_type}: {item_name}")
                                for job in jobs:
                                    job["_workspace_name"] = workspace_name
                                    job["_item_name"] = item_name
                                    job["_item_type"] = item_type
                                    all_details["jobs"].append(job)
                    except Exception as e:
                        # Log debug to avoid noise for items that don't support jobs
                        logger.debug(f"  Could not fetch jobs for {item_type} {item_name}: {str(e)}")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(args.output_dir)
        
        if all_details["jobs"]:
            save_json(all_details["jobs"], output_dir / f"jobs_{timestamp}.json")
            logger.info(f"Saved {len(all_details['jobs'])} jobs (all types)")
            
        if all_details["lakehouses"]:
            save_json(all_details["lakehouses"], output_dir / f"lakehouses_{timestamp}.json")
            logger.info(f"Saved {len(all_details['lakehouses'])} lakehouse tables")
            
        logger.info("Extraction complete")
        
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
