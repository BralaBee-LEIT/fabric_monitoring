#!/usr/bin/env python3
"""Inspect parquet file to verify Smart Merge fields."""

import pandas as pd
from pathlib import Path

def main():
    # Load latest parquet
    parquet_dir = Path('exports/monitor_hub_analysis/parquet')
    latest = sorted(parquet_dir.glob('activities_*.parquet'), reverse=True)[0]
    df = pd.read_parquet(latest)
    
    print('=' * 60)
    print(f'Latest parquet: {latest.name}')
    print(f'Total records: {len(df):,}')
    print(f'Columns ({len(df.columns)}):')
    print('=' * 60)
    for col in sorted(df.columns):
        print(f'  - {col}')
    
    print()
    print('=' * 60)
    print('STATUS DISTRIBUTION:')
    print('=' * 60)
    print(df['status'].value_counts())
    
    # Check if Smart Merge fields exist
    smart_merge_fields = ['job_status', 'job_failure_reason', 'failure_reason', 'job_invoker', 'job_end_time']
    print()
    print('=' * 60)
    print('SMART MERGE FIELDS CHECK:')
    print('=' * 60)
    for field in smart_merge_fields:
        if field in df.columns:
            non_null = df[field].notna().sum()
            print(f'  {field}: EXISTS ({non_null:,} non-null)')
        else:
            print(f'  {field}: MISSING')
    
    # Check for failure_reason content
    if 'failure_reason' in df.columns:
        print()
        print('=' * 60)
        print('FAILURE REASON SAMPLES (if any):')
        print('=' * 60)
        failures = df[df['failure_reason'].notna()]['failure_reason'].head(5)
        for i, reason in enumerate(failures, 1):
            print(f'  {i}. {str(reason)[:100]}...' if len(str(reason)) > 100 else f'  {i}. {reason}')
    
    # Check status vs job_status discrepancies
    if 'job_status' in df.columns:
        print()
        print('=' * 60)
        print('STATUS VS JOB_STATUS ANALYSIS:')
        print('=' * 60)
        # Records where status says Completed but job_status says Failed
        discrepancy = df[(df['status'] == 'Completed') & (df['job_status'] == 'Failed')]
        print(f'  Records with status=Completed but job_status=Failed: {len(discrepancy):,}')
        
        # Records where status was corrected to Failed
        corrected = df[df['status'] == 'Failed']
        print(f'  Total records with status=Failed: {len(corrected):,}')

if __name__ == '__main__':
    main()
