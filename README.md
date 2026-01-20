# Ireland Housing Data Platform

> Production-ready data pipeline tracking Irish rental markets using dbt + Neon PostgreSQL 17

## Overview

Automated ETL platform that ingests Irish rental listings, official statistics, and economic data to power housing affordability analytics. Built with modern data engineering best practices featuring **smart incremental loading** that automatically detects and loads only new data.

## Quick Start

```bash
# 1. Setup environment
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure database (optional - defaults in .env)
export DB_HOST="your-host"
export DB_NAME="your-db"
export DB_USER="your-user"
export DB_PASSWORD="your-password"

# 3. Create database tables
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f sql/create_raw_tables.sql

# 4. Run smart ETL pipeline
python run_smart_etl.py
```

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────┐
│  Data       │───▶│  PostgreSQL  │───▶│  dbt        │───▶│  Power   │
│  Sources    │    │  Raw Tables  │    │  Transform  │    │  BI      │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────┘
```

**Data Sources:**
- 🏠 **Daft.ie** - Rental listings (all 38 fields captured)
- 📊 **CSO Ireland** - Official statistics (rent index, CPI, population, income)
- 🏘️ **Property Price Register** - Historical sales data
- 💶 **ECB** - Interest rates

**Smart Features:**
- ✅ Automatic full/incremental mode detection
- ✅ Checkpoint-based incremental loading
- ✅ Deduplication at load time
- ✅ Page-by-page database loading (memory efficient)
- ✅ Year-based tracking for CSO data

## Tech Stack

- **Database:** Neon PostgreSQL 17 (serverless)
- **Transformation:** dbt Core 1.11.2
- **ETL:** Python 3.12 + asyncio
- **Web Scraping:** Playwright (Daft.ie), Requests (CSO API)
- **Data Processing:** pandas, sqlalchemy
- **Testing:** 46 dbt data quality tests

## Project Structure

```
ireland_housing_data_platform/
├── etl/
│   ├── config.py                # Configuration management
│   ├── loaders/
│   │   └── data_loader.py       # Database loading with deduplication
│   ├── scrapers/
│   │   ├── smart_daft_scraper.py      # Smart Daft.ie scraper ⭐
│   │   ├── smart_cso_scraper.py       # Smart CSO scraper ⭐
│   │   ├── ecb_scraper.py             # ECB rates (future)
│   │   └── property_price_scraper.py  # PPR data (future)
│   └── utils/
│       ├── database.py          # Database connection & helpers
│       └── logger.py            # Logging configuration
├── dbt/                         # dbt models (11 models)
│   ├── models/
│   │   ├── staging/             # 5 staging views
│   │   └── marts/               # Dimensions + facts + KPIs
│   └── profiles.yml             # Database connection
├── notebooks/                   # Jupyter notebooks for testing
│   ├── smart_etl.ipynb         # Main ETL testing
│   ├── daft_scraper.ipynb      # Daft scraper testing
│   └── cso_scraper.ipynb       # CSO scraper testing
├── sql/
│   └── create_raw_tables.sql    # Raw schema (7 tables)
├── logs/                        # Application logs
├── run_smart_etl.py            # Main ETL runner ⭐
└── README.md                    # This file
```

## Smart ETL Pipeline

### How It Works

The pipeline automatically detects whether to run in **FULL** or **INCREMENTAL** mode:

#### Daft.ie Rental Listings
```python
# First run (empty database) → FULL LOAD
# - Scrapes ALL available pages
# - Loads all historical data
# - Tracks latest publish_date

# Subsequent runs → INCREMENTAL LOAD
# - Scrapes only newest listings (sorted by publishDateDesc)
# - Filters client-side: publish_date > latest_in_db
# - Stops after first empty page (chronological optimization)
```

#### CSO Official Statistics
```python
# First run (empty database) → FULL LOAD
# - Fetches complete dataset via PxStat API
# - Loads all historical years

# Subsequent runs → INCREMENTAL LOAD
# - Fetches complete dataset
# - Filters: year > latest_year_in_db
# - Deduplicates based on unique dimension combinations
```

### Running the Pipeline

```bash
# Run all scrapers (Daft + CSO)
python run_smart_etl.py

# Run only Daft scraper
python run_smart_etl.py --daft-only

# Run only CSO scrapers
python run_smart_etl.py --cso-only

# Force full reload
python run_smart_etl.py --force-full
```

### Example Output

```
======================================================================
🚀 IRELAND HOUSING DATA PLATFORM - SMART ETL
======================================================================
Features:
  ✅ Automatic Full/Incremental mode detection
  ✅ Daft.ie rental listings (all 38 fields)
  ✅ CSO official statistics (rent, CPI, population, income)
  ✅ Smart checkpoint tracking
======================================================================

🏠 Starting Daft.ie Scraper
======================================================================
Database check: 0 existing listings found
🔄 MODE: FULL LOAD - No existing data found
✅ Successfully loaded 15,234 listings to database

📊 Starting CSO Data Collection
======================================================================
[RENT] Database check: 0 existing records
🔄 MODE: FULL LOAD - No existing data found
✅ Successfully loaded 318,444 records
```

## Database Schema

### Raw Tables (7 tables)

1. **raw_daft_listings** - Daft.ie rental listings (38 fields)
2. **raw_cso_rent** - CSO Rent Index (16 fields)
3. **raw_cso_cpi** - Consumer Price Index (12 fields)
4. **raw_cso_population** - Population estimates (14 fields)
5. **raw_cso_income** - Household income (12 fields)
6. **raw_property_sales** - Property price register
7. **raw_ecb_rates** - ECB interest rates

### dbt Models

- **Staging** (5 models): Data cleaning and standardization
- **Dimensions** (2 models): dim_date, dim_county
- **Facts** (3 models): fact_listings, fact_rent_market, fact_cso_rent
- **Analytics** (1 model): rental_affordability_kpis

## Data Quality

- **46 dbt tests** covering:
  - Primary key uniqueness
  - Foreign key relationships
  - NOT NULL constraints
  - Accepted value ranges
  - Data recency checks

## API References

### Daft.ie
- **Method:** Web scraping with Playwright
- **Endpoint:** `https://www.daft.ie/property-for-rent/ireland`
- **Rate Limit:** 2-3 seconds between requests
- **Data Format:** JSON from `__NEXT_DATA__` script tag

### CSO Ireland (Central Statistics Office)
- **Method:** PxStat REST API
- **Base URL:** `https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset`
- **Format:** JSON-stat 2.0
- **Datasets:**
  - **RIA02** - RTB Rent Index
  - **CPM01** - Consumer Price Index
  - **PEA01** - Population Estimates
  - **CIA01** - County Incomes

## Analytics Queries

```sql
-- Latest rental listings by county
SELECT
    county,
    COUNT(*) as listing_count,
    AVG(price) as avg_rent,
    AVG(bedrooms) as avg_bedrooms
FROM raw_daft_listings
WHERE scraped_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY county
ORDER BY avg_rent DESC;

-- Rent trends from CSO
SELECT
    year,
    location_label,
    bedrooms_label,
    AVG(value) as avg_rent
FROM raw_cso_rent
WHERE property_type_label = 'House'
GROUP BY year, location_label, bedrooms_label
ORDER BY year DESC, location_label;

-- Affordability analysis
SELECT * FROM analytics.rental_affordability_kpis
WHERE county IN ('Dublin', 'Cork', 'Galway')
ORDER BY affordability_ratio DESC;
```

## Development

### Adding New Data Sources

1. Create scraper in `etl/scrapers/`
2. Implement checkpoint logic:
   ```python
   def _check_existing_data(self) -> tuple[bool, Optional[int]]:
       # Check latest record in database
       pass

   def _determine_scraping_strategy(self):
       # Decide full vs incremental
       pass
   ```
3. Add loader method in `etl/loaders/data_loader.py`
4. Add database table in `sql/create_raw_tables.sql`
5. Create dbt staging model

### Running Notebooks

```bash
jupyter notebook notebooks/smart_etl.ipynb
```

## Deployment

### Scheduled Runs (cron)

```bash
# Daily at 6 AM
0 6 * * * cd /path/to/project && /path/to/venv/bin/python run_smart_etl.py >> logs/etl.log 2>&1
```

### Docker (optional)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run_smart_etl.py"]
```

## Troubleshooting

### Common Issues

**1. Playwright browser not found**
```bash
playwright install chromium
```

**2. Database connection error**
```bash
# Check .env file or export environment variables
export DB_HOST="your-host"
export DB_PASSWORD="your-password"
```

**3. Memory issues with large datasets**
- The scrapers load data page-by-page to avoid memory issues
- If still problematic, reduce page size in scraper config

**4. Cloudflare blocking Daft scraper**
- The scraper includes anti-detection measures
- Increase delay between requests if needed
- Use residential proxy if blocked (not included)

## Performance

- **Daft Full Load:** ~500 pages, ~10,000 listings in 30-45 minutes
- **Daft Incremental:** ~5-10 pages, ~200 listings in 2-3 minutes
- **CSO Full Load:** ~320K records in 90 seconds
- **CSO Incremental:** <1 second (no new data) or ~10 seconds (new year)
- **dbt Run:** ~45 seconds for all 11 models

## Project Status

✅ **Completed:**
- Smart Daft.ie scraper with incremental loading
- Smart CSO scraper with 4 datasets
- Database schema with 7 raw tables
- Data loader with deduplication
- dbt models (11 models, 46 tests)
- Comprehensive documentation

📋 **In Progress:**
- Power BI dashboard development
- Automated scheduling setup

🔜 **Future:**
- Property Price Register scraper
- ECB interest rates scraper
- Real-time alerting for price changes
- ML-based price predictions

## Contributing

This is a personal portfolio project. Feel free to fork and adapt for your needs.

## License

MIT License - See LICENSE file for details

---

**Last Updated:** 2026-01-13
**Status:** Production Ready
**Database:** Neon PostgreSQL 17
**dbt Models:** 11 models, 46 tests passing
**Smart ETL:** ✅ Fully Operational
