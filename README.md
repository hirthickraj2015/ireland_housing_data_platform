# Ireland Housing Data Platform

> End-to-end data analytics platform for Irish rental market intelligence, featuring automated ETL, data warehousing, and interactive dashboards.

## Project Overview

This platform collects, transforms, and visualizes Irish housing market data to provide actionable insights for renters, investors, and policymakers. It demonstrates production-grade data engineering practices including:

- **Automated ETL** with smart incremental loading
- **Data Warehouse** with medallion architecture (Bronze → Silver → Gold)
- **Star Schema** modeling for analytics
- **Interactive Dashboards** in Power BI
- **Data Quality** enforcement with 37 automated dbt tests

## Quick Start

```bash
# 1. Clone and setup environment
git clone <repository-url>
cd ireland_housing_data_platform
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 2. Configure database credentials
cp .env.example .env
# Edit .env with your Neon PostgreSQL credentials

# 3. Create database schema
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f sql/create_raw_tables.sql

# 4. Run ETL pipeline
python run_smart_etl.py

# 5. Deploy data warehouse
python deploy_warehouse.py

# 6. Run dbt transformations
cd dbt && dbt run --profiles-dir . && dbt test --profiles-dir .
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IRELAND HOUSING DATA PLATFORM                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DATA SOURCES              ETL LAYER                  DATA WAREHOUSE        │
│  ───────────              ─────────                  ──────────────         │
│                                                                             │
│  ┌─────────────┐      ┌─────────────────┐      ┌─────────────────────────┐  │
│  │  Daft.ie    │─────▶│  Smart Daft     │      │      BRONZE LAYER       │  │
│  │  Rentals    │      │  Scraper        │─────▶│  (raw_daft_listings)    │  │
│  └─────────────┘      │  (Playwright)   │      │                         │  │
│                       └─────────────────┘      │  raw_cso_rent           │  │
│  ┌─────────────┐      ┌─────────────────┐      │  raw_cso_cpi            │  │
│  │  CSO.ie     │─────▶│  Smart CSO      │─────▶│  raw_cso_population     │  │
│  │  Statistics │      │  Scraper        │      │  raw_cso_income         │  │
│  └─────────────┘      │  (PxStat API)   │      └───────────┬─────────────┘  │
│                       └─────────────────┘                  │                │
│                                                            ▼                │
│                                                ┌─────────────────────────┐  │
│                                                │      SILVER LAYER       │  │
│                                                │  (Cleaned & Validated)  │  │
│                                                │                         │  │
│                                                │  stg_daft_listings      │  │
│                                                │  stg_cso_rent_index     │  │
│                                                │  stg_economic_indicators│  │
│                                                └───────────┬─────────────┘  │
│                                                            │                │
│                                                            ▼                │
│                                                ┌─────────────────────────┐  │
│  ┌─────────────┐                               │       GOLD LAYER        │  │
│  │  Power BI   │◀──────────────────────────────│    (Star Schema)        │  │
│  │  Dashboard  │                               │                         │  │
│  └─────────────┘                               │  DIMENSIONS:            │  │
│                                                │  - dim_date             │  │
│                                                │  - dim_county           │  │
│                                                │  - dim_property_type    │  │
│                                                │  - dim_market_segment   │  │
│                                                │                         │  │
│                                                │  FACTS:                 │  │
│                                                │  - fact_rental_listings │  │
│                                                │  - fact_market_summary  │  │
│                                                │  - fact_affordability   │  │
│                                                │  - fact_economic_ind... │  │
│                                                │  - fact_price_movements │  │
│                                                └─────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Database | Neon PostgreSQL 17 | Serverless cloud database |
| ETL | Python 3.12 + asyncio | Data extraction and loading |
| Web Scraping | Playwright | Daft.ie with Cloudflare bypass |
| API Client | Requests | CSO PxStat API (JSON-stat 2.0) |
| Transformation | dbt Core | SQL-based data modeling |
| Visualization | Power BI | Interactive dashboards |
| CI/CD | GitHub Actions | Automated daily ETL at 2 AM UTC |
| Data Processing | pandas, SQLAlchemy | Data manipulation |

## Data Sources

### 1. Daft.ie Rental Listings
- **Method:** Web scraping with Playwright (handles Cloudflare)
- **Frequency:** Daily incremental updates
- **Fields Captured:** 38 fields including price, bedrooms, BER rating, coordinates, seller info
- **Volume:** ~2,000+ active listings per scrape

### 2. CSO Ireland Official Statistics
- **Method:** PxStat REST API (JSON-stat 2.0 format)
- **Datasets:**
  | Code  | Dataset    | Description              | Years     |
  |-------|------------|--------------------------|-----------|
  | RIA02 | Rent Index | RTB Average Monthly Rent | 2008-2024 |
  | CPM01 | CPI        | Consumer Price Index     | 1975-2024 |
  | PEA01 | Population | Population Estimates     | 1950-2024 |
  | CIA01 | Income     | County Household Income  | 2000-2022 |

## Data Warehouse Design

### Medallion Architecture

**Bronze Layer (Raw Data)**
- Exact copy of source data with minimal transformation
- 5 active tables: `raw_daft_listings`, `raw_cso_rent`, `raw_cso_cpi`, `raw_cso_population`, `raw_cso_income`
- 2 future tables: `raw_property_sales`, `raw_ecb_rates` (schema ready, scrapers planned)

**Silver Layer (Cleaned & Validated)**
- Standardized column names and data types
- County name normalization (handles variations like "Co. Dublin" → "Dublin")
- Data quality flags (outlier detection, completeness scores)
- Views: `silver.stg_daft_listings`, `silver.stg_cso_rent_index`, `silver.stg_economic_indicators`

**Gold Layer (Star Schema)**
- Optimized for analytics and reporting
- 4 Dimension tables + 5 Fact tables
- Supports time-series analysis, geographic drill-down, and cross-dataset joins

### Star Schema Design

```
                    ┌─────────────────┐
                    │    dim_date     │
                    │  (2000-2030)    │
                    │  date_key (PK)  │
                    └────────┬────────┘
                             │
┌─────────────────┐          │          ┌──────────────────┐
│   dim_county    │          │          │ dim_property_type│
│  county_key(PK) │          │          │ property_type_key│
│  county_name    │          │          │ property_category│
│  province       │          │          └────────┬─────────┘
│  is_commuter    │          │                   │
└────────┬────────┘          │                   │
         │                   │                   │
         │    ┌──────────────┴──────────────┐    │
         │    │   fact_rental_listings      │    │
         └────┤   listing_key (PK)          ├────┘
              │   date_key (FK)             │
              │   county_key (FK)           │
              │   property_type_key (FK)    │
              │   price_monthly             │
              │   bedrooms                  │
              │   ber_rating                │
              └─────────────────────────────┘
```

## Project Structure

```
ireland_housing_data_platform/
├── etl/
│   ├── config.py                    # Environment configuration
│   ├── __init__.py
│   ├── scrapers/
│   │   ├── smart_daft_scraper.py    # Playwright-based Daft scraper
│   │   └── smart_cso_scraper.py     # CSO PxStat API client
│   ├── loaders/
│   │   └── data_loader.py           # Database loading with deduplication
│   └── utils/
│       ├── database.py              # PostgreSQL connection utilities
│       └── logger.py                # Structured logging
├── sql/
│   ├── create_raw_tables.sql        # Bronze layer DDL
│   ├── 01_create_silver_layer.sql   # Silver layer views
│   ├── 02_create_gold_dimensions.sql # Dimension tables
│   └── 03_create_gold_facts.sql     # Fact tables
├── dbt/
│   ├── dbt_project.yml              # dbt configuration
│   ├── profiles.yml                 # Database connection
│   └── models/
│       ├── staging/                 # 5 staging models
│       └── marts/core/              # Dimension & fact models
├── powerbi/
│   └── ireland_rent_analysis.pbix   # Power BI dashboard
├── .github/workflows/
│   └── daily_etl.yml                # Automated daily runs
├── run_smart_etl.py                 # Main ETL entry point
├── deploy_warehouse.py              # Data warehouse deployment
├── requirements.txt                 # Python dependencies
├── Makefile                         # Common commands
└── README.md                        # This file
```

## Smart ETL Pipeline

The ETL pipeline automatically detects whether to perform a full or incremental load based on existing data:

### Daft.ie Scraper
```
First Run (empty database):
  → FULL LOAD: Scrapes all available pages (~500+ pages)
  → Loads data page-by-page to database (memory efficient)

Subsequent Runs:
  → INCREMENTAL LOAD: Only fetches listings newer than last run
  → Uses publishDateDesc sort for chronological optimization
  → Stops after first empty page (all remaining are older)
```

### CSO Scraper
```
First Run (empty database):
  → FULL LOAD: Fetches complete dataset from PxStat API

Subsequent Runs:
  → INCREMENTAL LOAD: Filters year > latest_year_in_db
  → Deduplicates at database level (ON CONFLICT DO NOTHING)
```

### Running the Pipeline

```bash
# Run complete pipeline (recommended)
python run_smart_etl.py

# Run only Daft scraper
python run_smart_etl.py --daft-only

# Run only CSO scrapers
python run_smart_etl.py --cso-only

# Force full refresh (re-scrape everything)
python run_smart_etl.py --force-full

# Or use Makefile
make run-etl        # Run ETL
make run-dbt        # Run dbt models
make all            # Run ETL + dbt
```

## Power BI Dashboard

The Power BI dashboard (`powerbi/ireland_rent_analysis.pbix`) connects directly to the Gold layer and provides:

### Key Metrics (KPIs)
| Metric              | Description                                   |
|---------------------|-----------------------------------------------|
| Total Listings      | Count of active rental properties             |
| Median Monthly Rent | Middle market rent (less skewed than average) |
| Dublin Premium %    | How much more Dublin costs vs national average|
| Data Quality Score  | % of listings with images AND BER rating      |

### Dashboard Pages
1. **Executive Overview** - KPI cards, price histogram, top 5 counties, property type distribution
2. **Geographic Analysis** - County map, province breakdown, Dublin vs commuter belt comparison
3. **Affordability Analysis** - Price percentiles, affordable housing gauge, bedroom vs price trends
4. **Data Quality** - BER coverage, image coverage, completeness metrics

### Connecting Power BI
1. Open `powerbi/ireland_rent_analysis.pbix`
2. Go to Home → Transform Data → Data Source Settings
3. Update PostgreSQL connection with your Neon credentials
4. Refresh data

## Data Quality

### Automated Tests (37 dbt tests)
- **Uniqueness:** Primary keys, natural keys
- **Referential Integrity:** Foreign key relationships
- **Not Null:** Required fields
- **Accepted Values:** Valid BER ratings, property types, provinces
- **Data Freshness:** Recent data checks

### Quality Flags in Silver Layer
```sql
-- Listings with quality issues are flagged
SELECT
    is_price_outlier,      -- Price outside €500-€10,000 range
    is_complete_record,    -- Has all required fields
    listing_quality_score  -- 0-100 composite score
FROM silver.stg_daft_listings;
```

### Known Data Quality Issues
| Issue | Impact | Mitigation |
|-------|--------|------------|
| Bedroom outliers (0-123) | <1% of listings | Filter bedrooms > 10 in reports |
| Price outliers (<€200, >€10,000) | <2% of listings | is_price_outlier flag |
| Single snapshot date | No time-series yet | Run scraper weekly to accumulate history |

## Sample Queries

```sql
-- Current rental prices by county
SELECT
    c.county_name,
    c.province,
    COUNT(*) as listing_count,
    ROUND(AVG(f.price_monthly), 0) as avg_rent,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.price_monthly), 0) as median_rent
FROM gold.fact_rental_listings f
JOIN gold.dim_county c ON f.county_key = c.county_key
GROUP BY c.county_name, c.province
ORDER BY median_rent DESC;

-- Affordability by bedroom count
SELECT
    bedrooms,
    COUNT(*) as listings,
    ROUND(AVG(price_monthly), 0) as avg_rent,
    ROUND(AVG(price_per_bedroom), 0) as avg_per_bedroom
FROM gold.fact_rental_listings
WHERE bedrooms BETWEEN 0 AND 5
GROUP BY bedrooms
ORDER BY bedrooms;

-- Market summary with YoY change
SELECT
    county_name,
    avg_price_current,
    price_change_yoy_pct,
    trend_classification
FROM gold.fact_price_movements pm
JOIN gold.dim_county c ON pm.county_key = c.county_key
WHERE bedroom_count = 2
ORDER BY avg_price_current DESC;
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/daily_etl.yml`) runs automatically:

- **Schedule:** Daily at 2 AM UTC
- **Steps:**
  1. Checkout repository
  2. Setup Python 3.11
  3. Install Python dependencies
  4. Install Playwright browsers (chromium)
  5. Run ETL pipeline (`python run_smart_etl.py`)
  6. Install and run dbt models and tests
  7. Upload logs as artifacts

### Manual Trigger
```bash
# Trigger workflow manually via GitHub UI or CLI
gh workflow run daily_etl.yml
```

## Development

### Adding a New Data Source

1. **Create scraper** in `etl/scrapers/new_scraper.py`
2. **Add raw table** in `sql/create_raw_tables.sql`
3. **Add loader method** in `etl/loaders/data_loader.py`
4. **Create dbt staging model** in `dbt/models/staging/`
5. **Update run_smart_etl.py** to include new scraper

### Running Tests
```bash
# Python tests
pytest -v

# dbt tests
cd dbt && dbt test --profiles-dir .

# Code formatting
make format
make lint
```

## Troubleshooting

### Common Issues

**Playwright browser not installed:**
```bash
playwright install chromium
```

**Database connection failed:**
```bash
# Ensure environment variables are set
export DB_HOST="your-neon-host"
export DB_NAME="your-database"
export DB_USER="your-user"
export DB_PASSWORD="your-password"
```

**Cloudflare blocking Daft scraper:**
- The scraper includes anti-detection measures
- Increase `SCRAPE_DELAY_SECONDS` in config if rate limited
- Run in non-headless mode for debugging: `SmartDaftScraper(headless=False)`

**dbt model failures:**
```bash
# Check dbt logs
cd dbt && dbt debug --profiles-dir .
dbt run --profiles-dir . --full-refresh
```

## Performance Benchmarks

| Operation           | Time      | Volume            |
|---------------------|-----------|-------------------|
| Daft Full Load      | 30-45 min | ~10,000 listings  |
| Daft Incremental    | 2-5 min.  | ~200 new listings |
| CSO Full Load       | ~90 sec   | ~320,000 records  |
| dbt Run (all models)| ~45 sec   | 11 models         |
| Warehouse Deploy    | ~30 sec   | 4 dims + 5 facts  |

## Contributing

This is a portfolio project demonstrating data engineering skills. Feel free to fork and adapt for your own use.

## License

MIT License - See LICENSE file for details.

---

**Project Status:** Production Ready
**Last Updated:** January 2026
**Database:** Neon PostgreSQL 17
**ETL:** Smart incremental loading
**Data Warehouse:** Medallion architecture with star schema
**Visualization:** Power BI dashboard
