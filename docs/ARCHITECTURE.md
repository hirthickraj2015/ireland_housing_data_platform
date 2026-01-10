# Architecture Overview

## System Components

The Irish Housing Data Platform is built on a modern data engineering stack that demonstrates enterprise-level practices while using free, open-source tools.

### 1. Data Sources Layer

**Live Data Sources** (All Free & Auto-Updating)
- **Daft.ie**: Web scraping for real-time rental listings
- **CSO (Central Statistics Office)**: REST API for official Irish statistics
- **Property Price Register**: CSV downloads of all property sales
- **ECB (European Central Bank)**: REST API for interest rates

### 2. Data Ingestion Layer

**Python ETL Pipeline**

```
etl/
├── scrapers/          # Data collection modules
│   ├── daft_scraper.py         # BeautifulSoup web scraping
│   ├── cso_scraper.py          # REST API client
│   ├── ecb_scraper.py          # ECB SDW API client
│   └── property_price_scraper.py  # CSV processing
├── loaders/           # Database loading
│   └── data_loader.py          # PostgreSQL bulk insert
├── utils/             # Shared utilities
│   ├── database.py             # Connection management
│   └── logger.py               # Structured logging
├── config.py          # Configuration management
└── main.py            # Pipeline orchestrator
```

**Key Features**:
- Modular design (each scraper is independent)
- Retry logic and error handling
- Rate limiting to respect website policies
- Structured logging with loguru
- Environment-based configuration

### 3. Data Storage Layer

**PostgreSQL Database** (Supabase/Neon)

**Raw Tables** (Operational Data Store):
```sql
raw_daft_listings       -- Scraped rental listings
raw_cso_rent           -- CSO rent index data
raw_cso_income         -- Disposable income by county
raw_property_sales     -- Property sales transactions
raw_ecb_rates          -- Interest rate history
```

**Design Decisions**:
- Raw tables preserve source data integrity
- Indexed by county and date for performance
- Append-only for historical tracking
- Minimal transformations at ingestion

### 4. Data Transformation Layer

**dbt Core** (Data Build Tool)

**Data Model Architecture**:

```
dbt/models/
├── staging/                    # Raw → Clean
│   ├── stg_daft_listings.sql
│   ├── stg_cso_rent.sql
│   └── schema.yml              # Source definitions
├── marts/
│   ├── core/                   # Star schema
│   │   ├── dim_date.sql        # Date dimension
│   │   ├── dim_county.sql      # County dimension
│   │   └── fact_rent_market.sql # Rental fact table
│   └── kpis/                   # Business metrics
│       └── rental_affordability_kpis.sql
```

**Star Schema Design**:

```
         ┌─────────────┐
         │  dim_date   │
         │             │
         │ - date_key  │
         │ - year      │
         │ - month     │
         │ - quarter   │
         └──────┬──────┘
                │
                │
    ┌───────────┴────────────┐
    │                        │
    │  fact_rent_market      │
    │                        │
    │ - rent_market_key (PK) │
    │ - county_key (FK) ─────┼─────► ┌──────────────┐
    │ - date_key (FK)        │        │  dim_county  │
    │ - avg_rent             │        │              │
    │ - median_rent          │        │ - county_key │
    │ - listing_count        │        │ - county_name│
    │ - supply_index         │        │ - province   │
    └────────────────────────┘        │ - county_type│
                                      └──────────────┘
```

**Transformation Layers**:
1. **Staging**: Data cleaning, type casting, basic validation
2. **Marts/Core**: Dimensional modeling (facts & dimensions)
3. **Marts/KPIs**: Business metrics and aggregations

### 5. Orchestration Layer

**GitHub Actions** (CI/CD Automation)

**Workflow**: `.github/workflows/daily_etl.yml`

```yaml
Schedule: Daily at 2 AM UTC
├── 1. Checkout code
├── 2. Setup Python 3.11
├── 3. Install dependencies (pip)
├── 4. Run ETL pipeline (etl.main)
├── 5. Install dbt
├── 6. Run dbt models (dbt run)
├── 7. Run dbt tests (dbt test)
└── 8. Upload logs (artifacts)
```

**Benefits**:
- Zero-cost automation (GitHub Actions free tier)
- Reliable scheduling
- Version control integration
- Audit trail via workflow logs

### 6. Visualization Layer

**Power BI Desktop → Power BI Service**

**Dashboard Structure**:

```
Dashboard Pages:
│
├── 1. National Overview
│   ├── Map: Rent by county
│   ├── KPIs: National averages
│   └── Trends: Time series
│
├── 2. County Drilldown
│   ├── County slicer
│   ├── Rent by bedroom type
│   └── Historical trends
│
├── 3. Housing Crisis Monitor
│   ├── Affordability heatmap
│   ├── Supply indicators
│   └── Stress scores
│
└── 4. Investor View
    ├── Price-to-rent ratio
    ├── Rental yield %
    └── Interest rate impact
```

**Data Refresh**:
- DirectQuery mode for real-time data
- Or scheduled refresh (8 times/day on Pro)

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                            │
│  Daft.ie  │  CSO API  │  Property Register  │  ECB API          │
└────┬─────────┬────────────────┬────────────────────┬────────────┘
     │         │                │                    │
     │         │                │                    │
     ▼         ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PYTHON ETL PIPELINE                        │
│                    (GitHub Actions - Daily)                     │
│  Scraping  │  API Calls  │  CSV Download  │  Data Validation    │
└────┬─────────┬────────────────┬────────────────────┬────────────┘
     │         │                │                    │
     │         │                │                    │
     ▼         ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                   POSTGRESQL DATABASE (Supabase)                │
│                         RAW TABLES                              │
│  raw_daft_listings  │  raw_cso_rent  │  raw_property_sales      │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        dbt TRANSFORMATIONS                      │
│  Staging Models  →  Dimension Tables  →  Fact Tables  →  KPIs   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ANALYTICAL DATA WAREHOUSE                     │
│   dim_date  │  dim_county  │  fact_rent_market  │  KPI views    │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        POWER BI DASHBOARD                       │
│  National Overview  │  County Drilldown  │  Investor View       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Data Sources** | Daft.ie, CSO, PPR, ECB | Live data feeds |
| **Scraping** | BeautifulSoup, Selenium, Requests | Web scraping & API calls |
| **ETL** | Python 3.11+ | Data pipeline orchestration |
| **Storage** | PostgreSQL (Supabase) | Relational database |
| **Transformation** | dbt Core | SQL-based transformations |
| **Orchestration** | GitHub Actions | Workflow automation |
| **Visualization** | Power BI | Interactive dashboards |
| **Logging** | Loguru | Structured logging |
| **Testing** | pytest, dbt tests | Data quality assurance |

---

## Design Principles

### 1. **Modularity**
- Each scraper is independent
- dbt models are granular and reusable
- Easy to add new data sources

### 2. **Idempotency**
- Pipeline can be re-run safely
- dbt models use `unique_key` for upserts
- Append-only raw tables for auditability

### 3. **Data Quality**
- Source validation in scrapers
- dbt tests on staging models
- Anomaly detection in KPIs

### 4. **Scalability**
- Horizontal scaling (add more scrapers)
- Database indexing for performance
- Incremental models in dbt (future)

### 5. **Observability**
- Structured logging at every layer
- GitHub Actions provides run history
- Power BI usage analytics

### 6. **Cost Efficiency**
- All free-tier services
- Serverless architecture
- Minimal compute requirements

---

## Security Considerations

1. **Credentials Management**
   - Never commit `.env` files
   - Use GitHub Secrets for CI/CD
   - Database SSL connections

2. **Rate Limiting**
   - Respect website terms of service
   - Configurable delay between requests
   - User-agent identification

3. **Data Privacy**
   - Public data only (no PII)
   - Aggregate metrics in reports
   - Compliance with GDPR principles

---

## Performance Optimizations

1. **Database**
   - Indexes on frequently queried columns (county, date)
   - Partitioning by date (future enhancement)
   - Connection pooling

2. **ETL**
   - Bulk inserts using `execute_values`
   - Parallel scraping (future)
   - Caching API responses

3. **dbt**
   - Materialized tables for large aggregations
   - Views for lightweight transformations
   - Incremental models for append-only data

4. **Power BI**
   - Star schema for optimal query performance
   - DirectQuery for real-time data
   - Pre-aggregated KPI tables

---

## Future Enhancements

### Short Term
- [ ] Incremental dbt models
- [ ] Email alerts on pipeline failures
- [ ] Data quality dashboards

### Medium Term
- [ ] Add more data sources (Housing.ie, MyHome.ie)
- [ ] Predictive modeling (rent forecasting)
- [ ] Tableau/Looker alternative dashboards

### Long Term
- [ ] Real-time streaming (Kafka/Pub/Sub)
- [ ] Machine learning for price predictions
- [ ] Mobile app with live alerts

---

## Questions?

Refer to:
- [Setup Guide](SETUP_GUIDE.md) for installation
- [README](../README.md) for usage instructions
- GitHub Issues for support
