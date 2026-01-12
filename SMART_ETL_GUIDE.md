# Smart ETL Guide - Dynamic Full/Incremental Loading

## Overview

The Ireland Housing Data Platform now features **intelligent ETL** that automatically detects whether to do a full load or incremental update based on what's already in the database.

## How It Works

### Automatic Mode Detection

**For Daft Listings:**
1. Checks `raw_daft_listings` table for existing data
2. Finds the latest `publish_date` in the database
3. Decides mode:
   - **No data found** → FULL LOAD (scrape all available pages)
   - **Data exists** → INCREMENTAL (only scrape listings newer than latest `publish_date`)

**For CSO Data:**
1. Checks respective CSO tables for existing records
2. Finds the latest `year` in each dataset
3. Decides mode:
   - **No data found** → FULL LOAD (fetch all historical data)
   - **Data exists** → INCREMENTAL (only fetch years not in database)

### Full Load Mode

**When triggered:**
- First time running the system
- Database tables are empty
- Using `--force-full` flag

**Behavior for Daft:**
- Scrapes ALL available pages on Daft.ie
- Continues until no more listings found
- Expected: Thousands of listings
- Duration: ~10-15 minutes

**Behavior for CSO:**
- Fetches complete historical datasets via notebook
- All years from earliest to latest
- Expected: Complete time series data

### Incremental Load Mode

**When triggered:**
- Data already exists in database
- Latest checkpoint found

**Behavior for Daft:**
- Only checks first ~5 pages for new listings
- Filters listings where `publish_date > max(publish_date in DB)`
- Stops when no new listings found for 2 consecutive pages
- Expected: 0-50 new listings
- Duration: ~1-2 minutes

**Behavior for CSO:**
- Only fetches data for years not in database
- Compares `year` column to find gaps
- Expected: 0-12 records (only new years)
- Duration: ~30 seconds

## Usage

### Quick Start

```bash
# Test the system (see what mode it will use)
python test_smart_etl.py

# Run full pipeline (automatic mode detection)
python run_smart_etl.py

# Force full refresh
python run_smart_etl.py --force-full

# Only run Daft scraper
python run_smart_etl.py --daft-only

# Only run CSO scraper (manual - use notebook instead)
# CSO data best loaded via notebooks/cso_scraper.ipynb
```

### Typical Workflow

**First Time Setup:**
```bash
# 1. Deploy database
python deploy_tables.py

# 2. Load initial Daft data (FULL LOAD)
python run_smart_etl.py --daft-only

# 3. Load CSO data (use notebook)
jupyter notebook notebooks/cso_scraper.ipynb

# 4. Run dbt models
cd dbt && dbt run --full-refresh --profiles-dir .
```

**Daily Updates:**
```bash
# 1. Scrape new Daft listings (INCREMENTAL)
python run_smart_etl.py --daft-only

# 2. Update dbt models (incremental)
cd dbt && dbt run --profiles-dir .
```

## Testing

```bash
# Test incremental logic
python test_smart_etl.py

# Expected output shows:
# - Current data status
# - Mode that will be used
# - Expected behavior
```

### Example Test Output

**When NO data exists:**
```
📊 Daft Data Status: EMPTY

   → Mode: FULL LOAD
   → Will scrape: ALL available pages until no more listings
   → Expected: Thousands of listings
```

**When data EXISTS:**
```
📊 Daft Data Status:
   Records: 20
   Latest publish_date: 1768089722000

   → Mode: INCREMENTAL
   → Will scrape: listings with publish_date > 1768089722000
   → Will check: ~5 pages for new listings
```

## Technical Details

### Checkpoint Logic

**Daft Scraper** (`smart_daft_scraper.py`):
- Queries: `SELECT MAX(publish_date) FROM raw_daft_listings`
- Comparison: `publish_date > latest_publish_date`
- Early stop: 2 consecutive pages with no new listings

**CSO Scraper** (`smart_cso_scraper.py`):
- Queries: `SELECT MAX(year) FROM raw_cso_*`
- Comparison: `year > latest_year`
- Filter before loading

### Key Functions

```python
def _check_existing_data(self) -> tuple[bool, Optional[int]]:
    """Check if we have existing data in database"""
    # Returns (has_data, latest_checkpoint)

def _determine_scraping_strategy(self):
    """Automatically determine full vs incremental mode"""
    # Sets self.mode = 'full' or 'incremental'
```

## Best Practices

### For Daft Data

1. **First run:** Let it complete full load (may take 10-15 min)
2. **Daily updates:** Run incremental (1-2 min)
3. **After data issues:** Use `--force-full` to rebuild

### For CSO Data

1. **Manual loading recommended:** Use Jupyter notebook
2. **Why?** CSO API requires specific formatting and BOM handling
3. **Frequency:** Quarterly (CSO updates data quarterly)

### Scheduling

**Recommended Schedule:**
```bash
# Daily at 2 AM (cron)
0 2 * * * cd /path/to/project && python run_smart_etl.py --daft-only

# After ETL, run dbt (incremental)
10 2 * * * cd /path/to/project/dbt && dbt run --profiles-dir .
```

## Troubleshooting

### "Mode stuck in FULL LOAD"

**Check:**
```sql
SELECT COUNT(*), MAX(publish_date)
FROM raw_daft_listings;
```

**Solution:** If no `publish_date` values, data might be corrupted. Reload.

### "Incremental mode finds no new listings"

**This is normal!** Means all listings on recent pages are already in DB.

### "Want to force full refresh"

```bash
python run_smart_etl.py --force-full
```

## Performance

### Full Load
- **Daft:** 10-15 minutes, ~5000-10000 listings
- **CSO:** 2-3 minutes (via notebook), ~100K records

### Incremental Load
- **Daft:** 1-2 minutes, ~0-50 new listings
- **CSO:** 30 seconds, ~0-12 new records

### Database Impact
- **Storage:** ~500MB for full dataset
- **Queries:** Optimized with indexes on date columns
- **Incremental:** Minimal I/O, append-only

## Summary

✅ **Automatic detection** - No manual mode selection needed
✅ **Efficient incremental** - Only loads new data
✅ **Smart stopping** - Detects when no more data available
✅ **Checkpoint tracking** - Uses database state as truth
✅ **Production ready** - Handles edge cases and errors

---

**Last Updated:** 2026-01-12
**Status:** ✅ Tested and Working
