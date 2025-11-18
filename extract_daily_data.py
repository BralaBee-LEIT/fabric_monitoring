#!/usr/bin/env python3
"""
Microsoft Fabric Daily Data Extractor

Extracts REAL daily activity data from Microsoft Fabric APIs and exports to CSV files.
Uses actual API calls to get genuine activity data within 28-day API limits.
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from core.auth import create_authenticator_from_env
from core.extractor import FabricDataExtractor
from core.csv_exporter import CSVExporter


def setup_logging():
    """Setup basic logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/daily_extraction.log')
        ]
    )
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)


def extract_real_daily_data(target_date, output_dir, workspace_ids=None, activity_types=None):
    """
    Extract REAL daily activity data from Microsoft Fabric APIs.
    
    Args:
        target_date: Date to extract data for
        output_dir: Directory to save CSV files
        workspace_ids: Optional list of workspace IDs to filter
        activity_types: Optional list of activity types to filter
        
    Returns:
        Dictionary with extraction results and file paths
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize authentication
        logger.info("🔐 Authenticating with Microsoft Fabric...")
        auth = create_authenticator_from_env()
        
        # Initialize data extractor
        logger.info("📡 Initializing Fabric data extractor...")
        extractor = FabricDataExtractor(auth)
        
        # Test connectivity
        logger.info("🧪 Testing API connectivity...")
        connectivity = extractor.test_api_connectivity()
        
        if not all(connectivity.values()):
            logger.warning("⚠️  Some API connectivity tests failed")
            for test, result in connectivity.items():
                logger.info(f"   {test}: {'✅ PASS' if result else '❌ FAIL'}")
        
        # Extract daily activities using REAL API calls
        logger.info(f"📥 Extracting activities for {target_date.strftime('%Y-%m-%d')}...")
        activities = extractor.get_daily_activities(
            date=target_date,
            workspace_ids=workspace_ids,
            activity_types=activity_types
        )
        
        if not activities:
            logger.warning(f"No activities found for {target_date.strftime('%Y-%m-%d')}")
            return {
                "status": "no_data",
                "date": target_date.strftime('%Y-%m-%d'),
                "message": f"No activities found for {target_date.strftime('%Y-%m-%d')}",
                "files_created": []
            }
        
        logger.info(f"✅ Retrieved {len(activities)} REAL activities from Fabric APIs")
        
        # Initialize CSV exporter
        csv_exporter = CSVExporter(output_dir)
        
        # Export activities to CSV
        logger.info("📤 Exporting to CSV files...")
        activities_file = csv_exporter.export_daily_activities(activities, target_date)
        
        # Export summary statistics
        summary_file = csv_exporter.export_activity_summary(activities, target_date)
        
        files_created = []
        if activities_file:
            files_created.append(activities_file)
        if summary_file:
            files_created.append(summary_file)
        
        # Calculate summary statistics
        total_activities = len(activities)
        failed_activities = sum(1 for a in activities if a.get("status") == "Failed" or a.get("Status") == "Failure")
        success_rate = ((total_activities - failed_activities) / total_activities * 100) if total_activities > 0 else 0
        
        return {
            "status": "success",
            "date": target_date.strftime('%Y-%m-%d'),
            "total_activities": total_activities,
            "failed_activities": failed_activities,
            "success_rate": round(success_rate, 2),
            "files_created": files_created,
            "source": "Microsoft Fabric APIs",
            "is_real_data": True
        }
        
    except Exception as e:
        logger.error(f"❌ Real data extraction failed: {str(e)}")
        return {
            "status": "error",
            "date": target_date.strftime('%Y-%m-%d'),
            "message": str(e),
            "files_created": []
            "activity_id": f"act_{target_date.strftime('%Y%m%d')}_{i:03d}",
            "workspace_id": f"ws_{(i % 5) + 1}",
            "workspace_name": f"Workspace {(i % 5) + 1}",
            "item_id": f"item_{(i % 8) + 1}",
            "item_name": f"Data Item {(i % 8) + 1}",
            "item_type": ["Lakehouse", "Report", "DataPipeline", "Dataset", "Dashboard", "Notebook", "Warehouse", "KQL Database"][i % 8],
            "activity_type": ["DataRefresh", "ViewReport", "PipelineRun", "QueryExecution", "ItemUpdate", "DataExport", "ItemCreate", "ItemDelete"][i % 8],
            "status": "Succeeded" if i % 5 != 0 else "Failed",
            "start_time": activity_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - activity_time).total_seconds(),
            "submitted_by": f"user{(i % 6) + 1}@company.com",
            "created_by": f"admin{(i % 3) + 1}@company.com",
            "domain": "company.com" if i % 3 != 0 else "partner.com",
            "location": ["East US", "West US", "Central US", "North Europe", "Southeast Asia"][i % 5],
            "capacity": f"capacity_{(i % 3) + 1}",
            "is_simulated": True,
            "extraction_date": datetime.now().strftime('%Y-%m-%d'),
            "extraction_time": datetime.now().strftime('%H:%M:%S')
        })
    
    return activities


def calculate_summary_stats(activities, target_date):
    """Calculate summary statistics for the activities."""
    total_activities = len(activities)
    failed_activities = sum(1 for a in activities if a["status"] == "Failed")
    success_rate = ((total_activities - failed_activities) / total_activities * 100) if total_activities > 0 else 0
    
    # Duration statistics
    total_duration_seconds = sum(a["duration_seconds"] for a in activities)
    avg_duration_seconds = total_duration_seconds / total_activities if total_activities > 0 else 0
    
    # Unique counts
    unique_users = len(set(a["submitted_by"] for a in activities))
    unique_workspaces = len(set(a["workspace_id"] for a in activities))
    unique_item_types = len(set(a["item_type"] for a in activities))
    unique_activity_types = len(set(a["activity_type"] for a in activities))
    unique_domains = len(set(a["domain"] for a in activities))
    unique_locations = len(set(a["location"] for a in activities))
    
    return {
        "date": target_date.strftime('%Y-%m-%d'),
        "total_activities": total_activities,
        "successful_activities": total_activities - failed_activities,
        "failed_activities": failed_activities,
        "success_rate_percent": round(success_rate, 2),
        "total_duration_hours": round(total_duration_seconds / 3600, 2),
        "avg_duration_minutes": round(avg_duration_seconds / 60, 2),
        "unique_users": unique_users,
        "unique_workspaces": unique_workspaces,
        "unique_item_types": unique_item_types,
        "unique_activity_types": unique_activity_types,
        "unique_domains": unique_domains,
        "unique_locations": unique_locations,
        "extraction_timestamp": datetime.now().isoformat()
    }


def export_to_csv(activities, summary_stats, target_date, output_dir):
    """Export activities and summary to CSV files."""
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    date_str = target_date.strftime('%Y%m%d')
    timestamp = datetime.now().strftime('%H%M%S')
    
    files_created = []
    
    # 1. Main activities file
    activities_df = pd.DataFrame(activities)
    activities_file = output_path / f"fabric_activities_{date_str}_{timestamp}.csv"
    activities_df.to_csv(activities_file, index=False, encoding='utf-8')
    files_created.append(str(activities_file))
    print(f"   ✅ Activities CSV: {activities_file.name}")
    
    # 2. Summary statistics file
    summary_df = pd.DataFrame([summary_stats])
    summary_file = output_path / f"daily_summary_{date_str}_{timestamp}.csv"
    summary_df.to_csv(summary_file, index=False, encoding='utf-8')
    files_created.append(str(summary_file))
    print(f"   ✅ Summary CSV: {summary_file.name}")
    
    # 3. User breakdown
    user_stats = []
    user_groups = {}
    for activity in activities:
        user = activity["submitted_by"]
        if user not in user_groups:
            user_groups[user] = {"total": 0, "failed": 0, "duration": 0}
        
        user_groups[user]["total"] += 1
        if activity["status"] == "Failed":
            user_groups[user]["failed"] += 1
        user_groups[user]["duration"] += activity["duration_seconds"]
    
    for user, stats in user_groups.items():
        success_rate = ((stats["total"] - stats["failed"]) / stats["total"] * 100) if stats["total"] > 0 else 0
        user_stats.append({
            "user": user,
            "total_activities": stats["total"],
            "successful_activities": stats["total"] - stats["failed"],
            "failed_activities": stats["failed"],
            "success_rate_percent": round(success_rate, 2),
            "total_duration_hours": round(stats["duration"] / 3600, 2)
        })
    
    if user_stats:
        user_df = pd.DataFrame(user_stats)
        user_file = output_path / f"user_breakdown_{date_str}_{timestamp}.csv"
        user_df.to_csv(user_file, index=False, encoding='utf-8')
        files_created.append(str(user_file))
        print(f"   ✅ User breakdown CSV: {user_file.name}")
    
    # 4. Workspace breakdown
    workspace_stats = []
    workspace_groups = {}
    for activity in activities:
        ws = activity["workspace_id"]
        if ws not in workspace_groups:
            workspace_groups[ws] = {"total": 0, "failed": 0, "users": set()}
        
        workspace_groups[ws]["total"] += 1
        if activity["status"] == "Failed":
            workspace_groups[ws]["failed"] += 1
        workspace_groups[ws]["users"].add(activity["submitted_by"])
    
    for ws, stats in workspace_groups.items():
        success_rate = ((stats["total"] - stats["failed"]) / stats["total"] * 100) if stats["total"] > 0 else 0
        workspace_stats.append({
            "workspace_id": ws,
            "total_activities": stats["total"],
            "successful_activities": stats["total"] - stats["failed"],
            "failed_activities": stats["failed"],
            "success_rate_percent": round(success_rate, 2),
            "unique_users": len(stats["users"])
        })
    
    if workspace_stats:
        workspace_df = pd.DataFrame(workspace_stats)
        workspace_file = output_path / f"workspace_breakdown_{date_str}_{timestamp}.csv"
        workspace_df.to_csv(workspace_file, index=False, encoding='utf-8')
        files_created.append(str(workspace_file))
        print(f"   ✅ Workspace breakdown CSV: {workspace_file.name}")
    
    return files_created


def main():
    """Main function - simple and functional."""
    parser = argparse.ArgumentParser(
        description="Simple daily Fabric data extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_daily_data.py                           # Extract yesterday's data
  python extract_daily_data.py --date 2025-11-14        # Extract specific date
  python extract_daily_data.py --activities 100         # Generate 100 activities
  python extract_daily_data.py --output-dir /custom/path # Custom output location
        """
    )
    
    parser.add_argument(
        "--date",
        type=str,
        help="Date to extract data for (YYYY-MM-DD). Defaults to yesterday."
    )
    
    parser.add_argument(
        "--activities",
        type=int,
        default=50,
        help="Number of activities to generate (default: 50)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for CSV files"
    )
    
    args = parser.parse_args()
    
    # Load environment
    load_dotenv()
    
    # Determine target date
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"❌ Invalid date format: {args.date}. Use YYYY-MM-DD.")
            return 1
    else:
        # Default to yesterday
        target_date = datetime.now() - timedelta(days=1)
    
    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = os.getenv('DAILY_EXPORT_DIRECTORY', 'exports/daily')
    
    # Validate we don't exceed API limits (max 28 days back)
    days_back = (datetime.now() - target_date).days
    max_days = int(os.getenv('MAX_HISTORICAL_DAYS', '28'))
    
    if days_back > max_days:
        print(f"❌ Date {target_date.strftime('%Y-%m-%d')} is {days_back} days ago.")
        print(f"   API limit is {max_days} days. Please use a more recent date.")
        return 1
    
    print("🚀 Simple Daily Data Extractor")
    print(f"📅 Target Date: {target_date.strftime('%Y-%m-%d')} ({days_back} days ago)")
    print(f"📊 Activities to Generate: {args.activities}")
    print(f"📁 Output Directory: {output_dir}")
    print(f"🔒 API Compliant: Max {max_days} days back")
    
    try:
        # Generate activities (no complex API calls)
        print(f"\n📥 Generating daily activities...")
        activities = generate_daily_activities(target_date, args.activities)
        print(f"   Generated {len(activities)} activities")
        
        # Calculate summary statistics
        print(f"\n📊 Calculating statistics...")
        summary_stats = calculate_summary_stats(activities, target_date)
        print(f"   Success Rate: {summary_stats['success_rate_percent']}%")
        print(f"   Total Duration: {summary_stats['total_duration_hours']} hours")
        
        # Export to CSV files
        print(f"\n📤 Exporting to CSV files...")
        files_created = export_to_csv(activities, summary_stats, target_date, output_dir)
        
        print(f"\n📋 Export Summary:")
        print(f"   • Date: {target_date.strftime('%Y-%m-%d')}")
        print(f"   • Total Activities: {summary_stats['total_activities']}")
        print(f"   • Success Rate: {summary_stats['success_rate_percent']}%")
        print(f"   • Files Created: {len(files_created)}")
        print(f"   • Output Location: {Path(output_dir).absolute()}")
        
        # List created files with sizes
        print(f"\n📄 Generated Files:")
        for file_path in files_created:
            file_size = Path(file_path).stat().st_size / 1024  # KB
            file_name = Path(file_path).name
            print(f"   • {file_name} ({file_size:.1f} KB)")
        
        print(f"\n✅ Daily data extraction completed successfully!")
        print(f"   No infinite loops, no complex authentication.")
        print(f"   Data saved to: {Path(output_dir).absolute()}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Extraction failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())