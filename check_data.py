import pandas as pd
import glob
import os

# Path to data
path = "/home/sanmi/Documents/J'TOYE_DIGITAL/LEIT_TEKSYSTEMS/1_Project_Rhico/usf_fabric_monitoring/exports/monitor_hub_analysis/raw_data/daily/*.csv"
files = glob.glob(path)

print(f"Found {len(files)} files.")

unique_statuses = set()
unique_item_types = set()

# Read a sample of files to check statuses
for f in files[:5]: # Check first 5 files
    try:
        df = pd.read_csv(f)
        if 'Status' in df.columns:
            unique_statuses.update(df['Status'].unique())
        if 'ItemType' in df.columns:
            unique_item_types.update(df['ItemType'].unique())
    except Exception as e:
        print(f"Error reading {f}: {e}")

print(f"Unique Statuses found: {unique_statuses}")
print(f"Unique Item Types found: {unique_item_types}")
