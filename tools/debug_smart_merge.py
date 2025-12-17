#!/usr/bin/env python3
"""Debug Smart Merge correlation issues."""

import json
import pandas as pd
from pathlib import Path

def main():
    print("=" * 70)
    print("SMART MERGE DEBUG ANALYSIS")
    print("=" * 70)
    
    # 1. Load job details
    jobs_dir = Path('exports/monitor_hub_analysis/fabric_item_details')
    all_jobs = []
    for job_file in jobs_dir.glob('jobs_*.json'):
        with open(job_file) as f:
            all_jobs.extend(json.load(f))
    
    print(f"\n1. Jobs Loaded: {len(all_jobs):,}")
    
    # Get unique item_ids from jobs
    job_item_ids = set()
    for job in all_jobs:
        item_id = job.get('itemId')
        if item_id:
            job_item_ids.add(str(item_id))
    
    print(f"   Unique item_ids in jobs: {len(job_item_ids):,}")
    
    # Failed job item_ids
    failed_job_item_ids = set()
    for job in all_jobs:
        if job.get('status') == 'Failed':
            item_id = job.get('itemId')
            if item_id:
                failed_job_item_ids.add(str(item_id))
    
    print(f"   Unique item_ids with failures: {len(failed_job_item_ids):,}")
    
    # 2. Load activities parquet
    parquet_dir = Path('exports/monitor_hub_analysis/parquet')
    latest_parquet = sorted(parquet_dir.glob('activities_*.parquet'), reverse=True)[0]
    df_activities = pd.read_parquet(latest_parquet)
    
    print(f"\n2. Activities in Parquet: {len(df_activities):,}")
    
    # Get unique item_ids from activities
    activity_item_ids = set(df_activities['item_id'].dropna().astype(str).unique())
    print(f"   Unique item_ids in activities: {len(activity_item_ids):,}")
    
    # 3. Check overlap
    overlap = job_item_ids.intersection(activity_item_ids)
    print(f"\n3. OVERLAP ANALYSIS:")
    print(f"   Item IDs in BOTH jobs AND activities: {len(overlap):,}")
    
    failed_overlap = failed_job_item_ids.intersection(activity_item_ids)
    print(f"   Failed job item_ids that exist in activities: {len(failed_overlap):,}")
    
    # 4. Sample comparison
    if failed_overlap:
        sample_item = list(failed_overlap)[0]
        print(f"\n4. SAMPLE ANALYSIS (item_id: {sample_item[:20]}...):")
        
        # Find this item in jobs
        sample_jobs = [j for j in all_jobs if str(j.get('itemId')) == sample_item]
        print(f"   Jobs for this item: {len(sample_jobs)}")
        if sample_jobs:
            failed_sample = [j for j in sample_jobs if j.get('status') == 'Failed']
            print(f"   Failed jobs: {len(failed_sample)}")
            if failed_sample:
                job = failed_sample[0]
                print(f"   Sample failed job time: {job.get('startTimeUtc')}")
        
        # Find in activities
        sample_activities = df_activities[df_activities['item_id'].astype(str) == sample_item]
        print(f"   Activities for this item: {len(sample_activities)}")
        if len(sample_activities) > 0:
            print(f"   Activity status values: {sample_activities['status'].value_counts().to_dict()}")
            print(f"   Activity time range: {sample_activities['start_time'].min()} to {sample_activities['start_time'].max()}")
    
    # 5. Check if parquet has Smart Merge columns
    print(f"\n5. SMART MERGE COLUMNS IN PARQUET:")
    smart_cols = ['job_status', 'job_failure_reason', 'failure_reason', 'error_message']
    for col in smart_cols:
        exists = col in df_activities.columns
        print(f"   {col}: {'EXISTS' if exists else 'MISSING'}")
    
    # 6. The real issue - check status in parquet vs raw data
    print(f"\n6. STATUS IN PARQUET:")
    print(df_activities['status'].value_counts())

if __name__ == '__main__':
    main()
