# Ireland Housing Data Platform - Quick Start Guide

## Prerequisites

- Python 3.12+ installed (use `pyenv` if needed)
- Git installed
- Internet connection for Neon PostgreSQL

## Step 1: Environment Setup

```bash
# Navigate to project directory
cd ireland_housing_data_platform

# Create Python virtual environment (Python 3.12 recommended)
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows

# Install dbt and dependencies
pip install dbt-core dbt-postgres pandas python-dotenv sqlalchemy loguru
```

## Step 2: Database Setup

The project uses **Neon PostgreSQL 17** (serverless PostgreSQL).

**Connection Details:**
```
Host: ep-nameless-cherry-abn7j2cl-pooler.eu-west-2.aws.neon.tech
Port: 5432
Database: neondb
User: neondb_owner
Password: npg_e3y6gIFNHsaD
SSL: Required
```

**Deploy tables:**
```bash
python deploy_tables.py
```

This creates:
- 7 raw tables (daft_listings, cso_rent, cso_cpi, cso_population, cso_income, property_sales, ecb_rates)
- 3 dbt schemas (staging, marts, analytics)

## Step 3: Load Sample Data

```bash
# Load Daft listings (if you have CSV files in data/ directory)
python load_daft_only.py
```

Expected: Loads 20 Daft listings with all 38 fields into `raw_daft_listings`

## Step 4: Run dbt Models

```bash
cd dbt

# Set environment variables
export DB_HOST="ep-nameless-cherry-abn7j2cl-pooler.eu-west-2.aws.neon.tech"
export DB_NAME="neondb"
export DB_USER="neondb_owner"
export DB_PASSWORD="npg_e3y6gIFNHsaD"

# Install dbt packages
dbt deps --profiles-dir .

# Test connection
dbt debug --profiles-dir .

# Run all models (first time)
dbt run --full-refresh --profiles-dir .

# Run tests
dbt test --profiles-dir .
```

Expected output:
```
✅ 11 models built successfully
✅ 46 tests passed
```

## Step 5: Incremental ETL Loading

The pipeline now supports **smart incremental loading** for Daft data:

### Initial Full Load (One-time)
```bash
# First run - gets ALL available Daft listings
python etl/main.py
```
- **Automatically scrapes ALL available pages** until no more listings found
- Gets complete historical dataset (potentially thousands of listings)
- Creates checkpoint for future incremental loads

### Ongoing Incremental Updates
```bash
# Subsequent runs - gets only new listings
python etl/main.py
```
- Automatically detects existing data and checkpoints
- Scrapes only recent pages (3 pages) and filters for new listings
- Uses `publish_date` and `property_id` for incremental filtering

### Manual Control
```bash
# Force full refresh (if needed)
python etl/main.py extract  # Scrapers only, no loading
```

**How it works:**
- **Checkpoint table** (`scraping_checkpoints`) tracks last successful scrape
- **Smart detection** automatically switches between full/incremental modes
- **Date filtering** ensures only newer listings than last checkpoint are processed
- **Dynamic page detection** stops when no more listings are available

## Step 6: Incremental dbt Updates

After ETL loading, update dbt models incrementally:

```bash
cd dbt
export DB_HOST="ep-nameless-cherry-abn7j2cl-pooler.eu-west-2.aws.neon.tech"
export DB_NAME="neondb"
export DB_USER="neondb_owner"
export DB_PASSWORD="npg_e3y6gIFNHsaD"

# Run only new/changed data
dbt run --profiles-dir .
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│ RAW LAYER (PostgreSQL Tables)                       │
│ - raw_daft_listings (38 fields)                     │
│ - raw_cso_rent, raw_cso_cpi, raw_cso_population     │
│ - raw_cso_income, raw_property_sales, raw_ecb_rates │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ STAGING LAYER (dbt Views)                           │
│ - stg_daft_listings (cleaned + calculated fields)   │
│ - stg_cso_rent, stg_cso_cpi, stg_cso_population     │
│ - stg_cso_income                                     │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ MARTS LAYER (dbt Tables - Incremental)              │
│ Dimensions:                                          │
│ - dim_date (10,227 rows)                            │
│ - dim_county (counties with province/tier)          │
│                                                      │
│ Facts (Incremental):                                │
│ - fact_listings (individual listings)               │
│ - fact_rent_market (aggregated by county/bedroom)   │
│ - fact_cso_rent (official CSO statistics)           │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ ANALYTICS LAYER (dbt Views)                         │
│ - rental_affordability_kpis (comprehensive metrics) │
└─────────────────────────────────────────────────────┘
```

## Key Tables for Analysis

Query these tables for insights:

```sql
-- Individual listings with all details
SELECT * FROM marts.fact_listings LIMIT 100;

-- Market aggregations by county/bedroom/property type
SELECT * FROM marts.fact_rent_market;

-- Comprehensive affordability metrics
SELECT * FROM analytics.rental_affordability_kpis;
```

## Data Refresh Workflow

### Daily Updates

1. Run Daft scraper (automated)
2. Load new data: `python load_daft_only.py`
3. Run dbt incrementally: `cd dbt && dbt run --profiles-dir .`

### Manual CSO Data Updates

1. Run CSO scraper: `jupyter notebook notebooks/cso_scraper.ipynb`
2. Load CSO data using data loader
3. Run dbt: `dbt run --profiles-dir .`

## Troubleshooting

### dbt Connection Issues

```bash
# Check if database is accessible
python deploy_tables.py

# Verify dbt configuration
cd dbt
dbt debug --profiles-dir .
```

### No Data in fact_listings

- Check if raw_daft_listings has data: `SELECT count(*) FROM raw_daft_listings;`
- Re-run dbt: `dbt run --select fact_listings --profiles-dir .`

### Tests Failing

```bash
# Run tests with verbose output
cd dbt
dbt test --profiles-dir . --debug
```

## Project Structure

```
ireland_housing_data_platform/
├── dbt/                          # dbt project
│   ├── models/
│   │   ├── staging/              # 5 staging models
│   │   └── marts/
│   │       ├── core/             # 5 core models (dims + facts)
│   │       └── kpis/             # 1 KPI model
│   ├── profiles.yml              # Database connection
│   └── dbt_project.yml           # dbt configuration
├── etl/
│   ├── loaders/                  # Data loaders
│   └── scrapers/                 # Daft scraper
├── sql/
│   └── create_raw_tables.sql     # Raw table schemas
├── data/                         # CSV data files
├── deploy_tables.py              # Database setup script
└── load_daft_only.py             # Data loading script
```

## Success Criteria

✅ All 7 raw tables created
✅ All 11 dbt models built
✅ All 46 dbt tests passing
✅ Data flowing through pipeline

## Support

For issues:
1. Check database connection
2. Verify Python environment (Python 3.12)
3. Ensure all dependencies installed
4. Check dbt logs: `dbt/logs/dbt.log`

## Database Connection String

```
postgresql://neondb_owner:npg_e3y6gIFNHsaD@ep-nameless-cherry-abn7j2cl-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require
```

Use this for:
- Power BI / Tableau connections
- Python scripts (sqlalchemy)
- Direct psql access

---

**Last Updated:** 2026-01-11
**Status:** ✅ Production Ready
