# Ireland Housing Data Platform

> Production-ready data pipeline tracking Irish rental markets using dbt + Neon PostgreSQL 17

## Overview

Automated ETL platform that ingests Irish rental listings, official statistics, and economic data to power housing affordability analytics. Built with modern data engineering best practices.

## Quick Start

**See [RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md) for detailed setup guide.**

```bash
# 1. Setup environment
python -m venv venv && source venv/bin/activate
pip install dbt-core dbt-postgres pandas python-dotenv sqlalchemy loguru

# 2. Deploy database tables
python deploy_tables.py

# 3. Load data
python load_daft_only.py

# 4. Run dbt models
cd dbt
export DB_HOST="ep-nameless-cherry-abn7j2cl-pooler.eu-west-2.aws.neon.tech"
export DB_NAME="neondb"
export DB_USER="neondb_owner"
export DB_PASSWORD="npg_e3y6gIFNHsaD"
dbt run --full-refresh --profiles-dir .
dbt test --profiles-dir .
```

## Architecture

```
Raw Data (PostgreSQL) → Staging (dbt views) → Marts (dbt tables) → Analytics (KPIs)
```

**Data Sources:**
- Daft.ie rental listings (38 fields captured)
- CSO official statistics (rent, CPI, population, income)
- Property Price Register
- ECB interest rates

**dbt Models:**
- 5 staging models (data cleaning)
- 2 dimension models (date, county)
- 3 incremental fact models (listings, market aggregations, CSO rent)
- 1 analytics KPI model (affordability metrics)

## Tech Stack

- **Database:** Neon PostgreSQL 17 (serverless)
- **Transformation:** dbt Core 1.11.2
- **ETL:** Python 3.12 (pandas, sqlalchemy)
- **Scraping:** Playwright, BeautifulSoup
- **Testing:** 46 dbt data quality tests

## Project Structure

```
ireland_housing_data_platform/
├── dbt/                          # dbt models (11 models)
│   ├── models/
│   │   ├── staging/              # 5 staging views
│   │   └── marts/                # Dimensions + facts + KPIs
│   ├── profiles.yml              # Database connection
│   └── dbt_project.yml
├── etl/
│   ├── loaders/                  # Data loading logic
│   └── scrapers/                 # Daft.ie scraper
├── sql/
│   └── create_raw_tables.sql     # Raw schema (7 tables)
├── data/                         # CSV data files
├── deploy_tables.py              # Setup script
├── load_daft_only.py             # Data loader
└── RUN_INSTRUCTIONS.md           # Detailed guide
```

## Key Features

✅ **All 38 Daft listing fields captured** - Complete data extraction
✅ **Incremental dbt models** - Efficient data processing
✅ **46 data quality tests** - Comprehensive validation
✅ **Star schema design** - Optimized for analytics
✅ **Production-ready** - Tested and validated

## Data Pipeline

1. **Extract:** Scrape Daft.ie + fetch CSO APIs
2. **Load:** Insert raw data into PostgreSQL
3. **Transform:** dbt models clean and structure data
4. **Serve:** Analytics views ready for BI tools

## Analytics Outputs

Query these tables for insights:

```sql
-- Individual listings
SELECT * FROM marts.fact_listings;

-- Market aggregations (by county/bedroom/property type)
SELECT * FROM marts.fact_rent_market;

-- Affordability KPIs
SELECT * FROM analytics.rental_affordability_kpis;
```

## Database Connection

```
postgresql://neondb_owner:npg_e3y6gIFNHsaD@ep-nameless-cherry-abn7j2cl-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require
```

## Development Status

✅ **Completed:**
- Raw table schemas (7 tables)
- ETL loaders with complete field mapping
- dbt models (11 models built)
- Data quality tests (46 tests passing)
- Documentation

📋 **Next Steps:**
- Set up automated daily scraping
- Build Power BI dashboard
- Add more data sources

## Contributing

This is a personal portfolio project demonstrating data engineering skills.

## License

MIT

---

**Last Updated:** 2026-01-11
**Status:** Production Ready
**dbt Models:** 11 models, 46 tests passing
