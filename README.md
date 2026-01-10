# Irish Housing & Rent Intelligence Platform

[![Daily ETL Pipeline](https://github.com/yourusername/ireland_housing_data_platform/actions/workflows/daily_etl.yml/badge.svg)](https://github.com/yourusername/ireland_housing_data_platform/actions/workflows/daily_etl.yml)

> Live Power BI dashboard powered by automated data pipelines tracking Irish rental markets, property prices, and housing affordability.

This system ingests live Irish rental, sales and economic data daily, transforms it using dbt, and powers a Power BI analytics platform tracking affordability, investment returns and housing pressure across Ireland.

## What This Project Demonstrates

This end-to-end data engineering project showcases professional-level skills valued by Irish employers:

- ✅ **Data Ingestion** - Automated scraping and API integration
- ✅ **ETL Pipelines** - Python-based extract, transform, load processes
- ✅ **Data Modeling** - Star schema with facts and dimensions
- ✅ **Cloud Databases** - PostgreSQL on Supabase/Neon
- ✅ **Data Transformation** - dbt Core for modular SQL transformations
- ✅ **Business Intelligence** - Power BI dashboards with KPIs
- ✅ **Automation** - GitHub Actions for daily pipeline execution
- ✅ **Data Quality** - Testing and validation throughout

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Data Sources (Live & Auto-Updating)                        │
├─────────────────────────────────────────────────────────────┤
│  • Daft.ie (Rental Listings)                                │
│  • CSO (Rent Index, Income, Population, CPI)                │
│  • Property Price Register (Sales Data)                     │
│  • ECB (Interest Rates)                                     │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Python ETL Pipeline (GitHub Actions - Daily at 2 AM)       │
├─────────────────────────────────────────────────────────────┤
│  • Web scraping (BeautifulSoup, Selenium)                   │
│  • API clients (CSO, ECB)                                   │
│  • Data validation & cleaning                               │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  PostgreSQL Database (Supabase / Neon)                      │
├─────────────────────────────────────────────────────────────┤
│  Raw Tables:                                                │
│  • raw_daft_listings                                        │
│  • raw_cso_rent                                             │
│  • raw_cso_income                                           │
│  • raw_property_sales                                       │
│  • raw_ecb_rates                                            │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  dbt Core (Data Transformation)                             │
├─────────────────────────────────────────────────────────────┤
│  Dimensions:                                                │
│  • dim_date                                                 │
│  • dim_county                                               │
│  • dim_property_type                                        │
│                                                             │
│  Facts:                                                     │
│  • fact_rent_market                                         │
│  • fact_property_sales                                      │
│  • fact_interest_rates                                      │
│                                                             │
│  KPIs:                                                      │
│  • rental_affordability_kpis                                │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Power BI Dashboard (Published to Power BI Service)         │
├─────────────────────────────────────────────────────────────┤
│  • National Overview                                        │
│  • County Drilldown                                         │
│  • Housing Crisis Monitor                                   │
│  • Investor View                                            │
└─────────────────────────────────────────────────────────────┘
```

## Live Data Sources

All data sources are **free**, **publicly available**, and **automatically updating**:

| Source | Type | Update Frequency | Purpose |
|--------|------|------------------|---------|
| [Daft.ie](https://www.daft.ie/property-for-rent/ireland) | Web Scraping | Daily | Live rental listings with price, location, bedrooms |
| [CSO Ireland](https://data.cso.ie/) | REST API | Monthly/Quarterly | Official rent index, income, population, CPI |
| [Property Price Register](https://www.propertypriceregister.ie/) | CSV Download | Daily | All property sales in Ireland |
| [ECB Data Portal](https://sdw.ecb.europa.eu/) | REST API | Monthly | Interest rates for mortgage pressure analysis |

## Key Performance Indicators

### Rental Market
- Average Rent by County
- Rent per Bedroom
- Month-over-Month Rent Growth
- Year-over-Year Rent Growth
- Rental Supply Index

### Affordability
- Rent vs Disposable Income
- Rent as % of Income
- Affordability Stress Score by County

### Investment View
- Price-to-Rent Ratio
- Rental Yield %
- Interest Rate Impact on Mortgage Costs

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database (Supabase or Neon recommended)
- Git

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/ireland_housing_data_platform.git
cd ireland_housing_data_platform
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your database credentials
nano .env
```

Required environment variables:
```env
DB_HOST=your-database-host
DB_PORT=5432
DB_NAME=postgres
DB_USER=your-username
DB_PASSWORD=your-password
```

### 4. Create Database Tables

```bash
# Connect to your PostgreSQL database and run:
psql -h your-host -U your-user -d your-database -f sql/create_raw_tables.sql
```

### 5. Run ETL Pipeline

```bash
# Run full pipeline (extract + load)
python -m etl.main

# Or run individual scrapers:
python -m etl.main daft      # Daft.ie only
python -m etl.main cso       # CSO only
python -m etl.main ecb       # ECB only
python -m etl.main property  # Property Register only
```

### 6. Run dbt Transformations

```bash
cd dbt

# Install dbt dependencies
dbt deps

# Run transformations
dbt run --profiles-dir .

# Run tests
dbt test --profiles-dir .
```

## Project Structure

```
ireland_housing_data_platform/
├── .github/
│   └── workflows/
│       └── daily_etl.yml          # GitHub Actions automation
├── etl/
│   ├── scrapers/
│   │   ├── daft_scraper.py        # Daft.ie rental listings
│   │   ├── cso_scraper.py         # CSO API client
│   │   ├── ecb_scraper.py         # ECB interest rates
│   │   └── property_price_scraper.py  # Property sales
│   ├── loaders/
│   │   └── data_loader.py         # Database loading
│   ├── utils/
│   │   ├── database.py            # Database utilities
│   │   └── logger.py              # Logging configuration
│   ├── config.py                  # Configuration management
│   └── main.py                    # ETL orchestrator
├── dbt/
│   ├── models/
│   │   ├── staging/               # Staging models (raw → clean)
│   │   └── marts/
│   │       ├── core/              # Dimensions & facts
│   │       └── kpis/              # KPI views
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── packages.yml
├── sql/
│   └── create_raw_tables.sql      # Database schema
├── powerbi/                        # Power BI files (.pbix)
├── docs/                           # Documentation & architecture
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
└── README.md                       # This file
```

## Automation with GitHub Actions

The ETL pipeline runs **automatically every day at 2 AM UTC** via GitHub Actions.

### Setting Up Automation

1. **Add GitHub Secrets**: Go to your repository → Settings → Secrets and add:
   - `DB_HOST`
   - `DB_PORT`
   - `DB_NAME`
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_SCHEMA`

2. **Enable Actions**: Ensure GitHub Actions is enabled in your repository

3. **Manual Trigger**: You can also trigger the workflow manually from the Actions tab

## Power BI Dashboard

### Dashboard Pages

#### 1. National Overview
- Map visualization of average rent by county
- KPI cards: National average rent, rent inflation %, supply index
- Trend charts for rent over time

#### 2. County Drilldown
- County slicer for filtering
- Detailed rent trends
- Rent vs income comparison
- Property type breakdown

#### 3. Housing Crisis Monitor
- Heatmap of rent growth by county
- Affordability stress scores
- Supply vs demand indicators

#### 4. Investor View
- Rent vs house price analysis
- Rental yield calculations
- Interest rate impact visualization

### Connecting Power BI

1. Open Power BI Desktop
2. Get Data → PostgreSQL
3. Enter your database credentials
4. Import the following tables:
   - `dim_date`
   - `dim_county`
   - `fact_rent_market`
   - `fact_property_sales`
   - `rental_affordability_kpis`

## Development

### Running Tests

```bash
# Python tests
pytest

# dbt tests
cd dbt
dbt test --profiles-dir .
```

### Code Quality

```bash
# Format code
black etl/

# Sort imports
isort etl/

# Lint
flake8 etl/
```

## Data Warehouse Design

### Star Schema

**Dimension Tables:**
- `dim_date` - Date dimension for time-based analysis
- `dim_county` - Irish counties with province and urban/rural classification
- `dim_property_type` - Property type categories

**Fact Tables:**
- `fact_rent_market` - Aggregated rental metrics by county, date, and property characteristics
- `fact_property_sales` - Property sales transactions
- `fact_interest_rates` - ECB interest rate history

**KPI Views:**
- `rental_affordability_kpis` - Pre-calculated affordability metrics

## Troubleshooting

### Database Connection Issues
```bash
# Test database connection
python -c "from etl.utils.database import db; print(db.get_engine())"
```

### Scraping Failures
- Check if website structure has changed
- Verify user agent and rate limiting settings
- Review logs in `logs/` directory

### dbt Errors
```bash
# Debug dbt
dbt debug --profiles-dir dbt/

# Compile without running
dbt compile --profiles-dir dbt/
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Central Statistics Office (CSO)** for providing free, open data
- **European Central Bank (ECB)** for financial data APIs
- **Property Price Register** for transparent property sale data
- **Daft.ie** for rental market listings

## Contact

Your Name - [your.email@example.com](mailto:your.email@example.com)

Project Link: [https://github.com/yourusername/ireland_housing_data_platform](https://github.com/yourusername/ireland_housing_data_platform)

---

**Built with** Python • PostgreSQL • dbt • Power BI • GitHub Actions
