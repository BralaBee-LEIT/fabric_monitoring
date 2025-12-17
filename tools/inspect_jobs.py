#!/usr/bin/env python3
"""Inspect job details to see failures."""

import json
from pathlib import Path

def main():
    # Load all job files and merge
    jobs_dir = Path('exports/monitor_hub_analysis/fabric_item_details')
    all_jobs = []
    
    for job_file in sorted(jobs_dir.glob('jobs_*.json')):
        print(f'Loading: {job_file.name}')
        with open(job_file) as f:
            jobs = json.load(f)
            print(f'  - {len(jobs)} jobs')
            all_jobs.extend(jobs)
    
    print()
    print('=' * 60)
    print(f'TOTAL JOBS LOADED: {len(all_jobs):,}')
    print('=' * 60)
    
    if not all_jobs:
        print('No jobs found!')
        return
    
    # Show structure
    print()
    print('SAMPLE JOB KEYS:')
    print(list(all_jobs[0].keys()))
    
    # Count by status
    print()
    print('=' * 60)
    print('JOBS BY STATUS:')
    print('=' * 60)
    status_counts = {}
    for job in all_jobs:
        status = job.get('status', 'Unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        print(f'  {status}: {count:,}')
    
    # Show failed job sample
    failed_jobs = [j for j in all_jobs if j.get('status') == 'Failed']
    print()
    print('=' * 60)
    print(f'FAILED JOBS: {len(failed_jobs):,}')
    print('=' * 60)
    
    if failed_jobs:
        print()
        print('SAMPLE FAILED JOB:')
        print(json.dumps(failed_jobs[0], indent=2, default=str))

if __name__ == '__main__':
    main()
