# Setup Guide - Irish Housing Data Platform

This guide will walk you through setting up the entire data platform from scratch.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Database Setup](#database-setup)
3. [Local Development Setup](#local-development-setup)
4. [GitHub Actions Setup](#github-actions-setup)
5. [Power BI Setup](#power-bi-setup)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required
- **Python 3.11+** - [Download here](https://www.python.org/downloads/)
- **Git** - [Download here](https://git-scm.com/downloads)
- **PostgreSQL Database** - Free options:
  - [Supabase](https://supabase.com/) - Recommended, generous free tier
  - [Neon](https://neon.tech/) - Serverless PostgreSQL
  - [ElephantSQL](https://www.elephantsql.com/) - Free tier available

### Optional
- **Power BI Desktop** - [Download here](https://powerbi.microsoft.com/desktop/)
- **Make** - For using Makefile commands (pre-installed on macOS/Linux)

---

## Database Setup

### Option 1: Supabase (Recommended)

1. **Create Account**
   - Go to [supabase.com](https://supabase.com/)
   - Sign up with GitHub or email
   - Create a new project

2. **Get Database Credentials**
   - Go to Project Settings → Database
   - Copy these values:
     - Host
     - Port (usually 5432)
     - Database name
     - User
     - Password
   - Connection string format:
     ```
     postgresql://[user]:[password]@[host]:[port]/[database]
     ```

3. **Create Tables**
   - Go to SQL Editor in Supabase dashboard
   - Copy contents of `sql/create_raw_tables.sql`
   - Click "Run"
   - Verify tables were created in Table Editor

### Option 2: Neon

1. **Create Account**
   - Go to [neon.tech](https://neon.tech/)
   - Sign up and create a project

2. **Get Connection String**
   - Copy the connection string from dashboard
   - Format: `postgresql://user:password@host/database`

3. **Create Tables**
   - Use Neon's SQL Editor or connect via psql:
     ```bash
     psql [your-connection-string] -f sql/create_raw_tables.sql
     ```

### Option 3: Local PostgreSQL

1. **Install PostgreSQL**
   - macOS: `brew install postgresql`
   - Ubuntu: `sudo apt-get install postgresql`
   - Windows: Download from [postgresql.org](https://www.postgresql.org/download/)

2. **Create Database**
   ```bash
   createdb irish_housing
   ```

3. **Create Tables**
   ```bash
   psql -d irish_housing -f sql/create_raw_tables.sql
   ```

---

## Local Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/ireland_housing_data_platform.git
cd ireland_housing_data_platform
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install dbt packages
cd dbt
dbt deps
cd ..
```

Or use the Makefile:
```bash
make install
```

### 4. Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

Required `.env` configuration:
```env
DB_HOST=your-supabase-host.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_SCHEMA=public

DATABASE_URL=postgresql://user:password@host:port/database
```

### 5. Test Database Connection

```bash
python -c "from etl.utils.database import db; print('✅ Database connected!' if db.get_engine() else '❌ Connection failed')"
```

### 6. Run Your First ETL

```bash
# Run full pipeline
python -m etl.main

# Or run individual scrapers:
python -m etl.main daft
```

Or use the Makefile:
```bash
make run-etl
```

### 7. Run dbt Transformations

```bash
cd dbt

# Test connection
dbt debug --profiles-dir .

# Run models
dbt run --profiles-dir .

# Run tests
dbt test --profiles-dir .
```

Or use the Makefile:
```bash
make run-dbt
```

---

## GitHub Actions Setup

### 1. Fork/Clone Repository

Ensure the repository is in your GitHub account.

### 2. Add GitHub Secrets

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `DB_HOST` | Your database host | `xxx.supabase.co` |
| `DB_PORT` | Database port | `5432` |
| `DB_NAME` | Database name | `postgres` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `your-password` |
| `DB_SCHEMA` | Database schema | `public` |

### 3. Enable GitHub Actions

1. Go to **Actions** tab
2. Click **I understand my workflows, go ahead and enable them**
3. The workflow will run daily at 2 AM UTC

### 4. Manual Trigger

1. Go to **Actions** → **Daily ETL Pipeline**
2. Click **Run workflow**
3. Select branch and click **Run workflow**

---

## Power BI Setup

### 1. Install Power BI Desktop

Download from [Microsoft Power BI](https://powerbi.microsoft.com/desktop/)

### 2. Connect to Database

1. Open Power BI Desktop
2. Click **Get Data** → **PostgreSQL database**
3. Enter your database credentials:
   - Server: `your-host:5432`
   - Database: `postgres`
4. Click **OK** and enter username/password

### 3. Import Tables

Select these tables:
- `dim_date`
- `dim_county`
- `fact_rent_market`
- `fact_property_sales` (if available)
- `rental_affordability_kpis`

### 4. Create Relationships

Power BI should auto-detect relationships, but verify:
- `fact_rent_market.county_key` → `dim_county.county_key`
- `fact_rent_market.date_key` → `dim_date.date_key`

### 5. Build Dashboards

Create visualizations using the imported data:

**Page 1: National Overview**
- Map: County boundaries with avg_rent as color
- Cards: National averages, YoY growth
- Line chart: Rent over time

**Page 2: County Drilldown**
- Slicer: County selector
- Bar chart: Rent by bedroom count
- Trend lines: Monthly rent changes

**Page 3: Affordability**
- Use `rental_affordability_kpis` table
- Heatmap: Rent-to-income ratio by county
- Gauge: Affordability stress score

### 6. Publish to Power BI Service

1. Click **File** → **Publish** → **Publish to Power BI**
2. Sign in to Power BI account (free tier available)
3. Select workspace
4. Share the link!

---

## Troubleshooting

### Database Connection Errors

**Problem**: Can't connect to database

**Solutions**:
1. Check `.env` file has correct credentials
2. Verify database is accessible (check firewall rules)
3. For Supabase: Ensure your IP is allowed (or enable "Allow all" in database settings)
4. Test connection:
   ```bash
   psql "postgresql://user:password@host:port/database"
   ```

### ETL Pipeline Errors

**Problem**: Scraper fails

**Solutions**:
1. Check website is accessible
2. Review rate limiting settings in `config.py`
3. Check logs in `logs/` directory
4. Website structure may have changed - update selectors in scraper

**Problem**: No data loaded

**Solutions**:
1. Check scrapers are returning data
2. Verify database tables exist
3. Check database user has INSERT permissions

### dbt Errors

**Problem**: `dbt run` fails

**Solutions**:
1. Run `dbt debug --profiles-dir .` to check setup
2. Ensure `profiles.yml` has correct database credentials
3. Check `dbt_project.yml` configuration
4. Verify raw tables exist and have data

**Problem**: Source not found

**Solutions**:
1. Ensure `schema.yml` lists all sources
2. Check table names match exactly (case-sensitive)
3. Verify schema name in `profiles.yml`

### GitHub Actions Errors

**Problem**: Workflow fails

**Solutions**:
1. Check all secrets are set correctly
2. Review workflow logs in Actions tab
3. Test pipeline locally first
4. Ensure database is accessible from GitHub's IP ranges

---

## Next Steps

Once setup is complete:

1. **Run Daily**: Let the pipeline run for a week to accumulate data
2. **Explore Data**: Query the database to see trends
3. **Build Dashboards**: Create visualizations in Power BI
4. **Share**: Publish your dashboard and add it to your CV/portfolio
5. **Iterate**: Add more KPIs, improve visualizations, optimize queries

---

## Support

For issues:
1. Check this guide
2. Review logs in `logs/` directory
3. Open an issue on GitHub
4. Check dbt documentation: [docs.getdbt.com](https://docs.getdbt.com/)

---

**You're ready to go! Run `make all` to execute the full pipeline.**
