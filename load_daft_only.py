#!/usr/bin/env python3
"""
Load only Daft listings to test the pipeline
"""

import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from etl.loaders.data_loader import DataLoader

print("🚀 Loading Daft listings...")
loader = DataLoader()
data_dir = Path('data')

daft_files = list(data_dir.glob('daft_listings_*.csv'))
if daft_files:
    latest_daft = sorted(daft_files)[-1]
    print(f"   Loading: {latest_daft.name}")
    df_daft = pd.read_csv(latest_daft)
    print(f"   Found {len(df_daft)} listings")

    records = df_daft.to_dict('records')
    success = loader.load_daft_listings(records)

    if success:
        print(f"✅ Loaded {len(records)} Daft listings successfully!")
        print(f"\nNow run: cd dbt && dbt run --profiles-dir .")
    else:
        print(f"⚠️  Some listings failed")
else:
    print("❌ No Daft listing files found")
