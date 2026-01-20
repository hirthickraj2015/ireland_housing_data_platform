-- ============================================================================
-- GOLD LAYER: Fact Tables (Star Schema)
-- Purpose: Create analytics-ready fact tables
-- ============================================================================

-- Create gold schema
CREATE SCHEMA IF NOT EXISTS gold;

-- Drop existing fact tables to recreate with correct schema
DROP TABLE IF EXISTS gold.fact_rental_listings CASCADE;
DROP TABLE IF EXISTS gold.fact_market_summary CASCADE;
DROP TABLE IF EXISTS gold.fact_affordability CASCADE;
DROP TABLE IF EXISTS gold.fact_economic_indicators CASCADE;
DROP TABLE IF EXISTS gold.fact_price_movements CASCADE;
DROP MATERIALIZED VIEW IF EXISTS gold.mv_kpi_dashboard CASCADE;

-- ============================================================================
-- FACT 1: fact_rental_listings (Grain: Individual Listing)
-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.fact_rental_listings (
    listing_key SERIAL PRIMARY KEY,
    date_key INT REFERENCES gold.dim_date(date_key),
    county_key INT REFERENCES gold.dim_county(county_key),
    property_type_key INT,

    -- Natural Keys
    property_id VARCHAR(50),
    daft_shortcode VARCHAR(50) UNIQUE,

    -- Measures
    price_monthly DECIMAL(10,2) NOT NULL,
    bedrooms INT,
    price_per_bedroom DECIMAL(10,2),

    -- Property Attributes
    ber_rating VARCHAR(10),
    energy_efficiency_category VARCHAR(50),

    -- Location Details
    title TEXT,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),

    -- Temporal Metrics
    publish_date DATE,
    scraped_date DATE,
    days_on_market INT,

    -- Quality Metrics
    listing_quality_score INT,
    has_images INT,
    is_price_outlier BOOLEAN,
    is_complete_record BOOLEAN,

    -- URLs
    property_url TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Populate fact_rental_listings from silver layer
INSERT INTO gold.fact_rental_listings (
    date_key, county_key, property_type_key,
    property_id, daft_shortcode,
    price_monthly, bedrooms, price_per_bedroom,
    ber_rating, energy_efficiency_category,
    title, latitude, longitude,
    publish_date, scraped_date, days_on_market,
    listing_quality_score, has_images, is_price_outlier, is_complete_record,
    property_url
)
SELECT DISTINCT ON (s.daft_shortcode)
    gold.get_date_key(s.publish_date) as date_key,
    gold.get_county_key(s.county_clean) as county_key,
    pt.property_type_key,

    s.property_id,
    s.daft_shortcode,

    s.price_monthly,
    s.bedrooms,
    s.price_per_bedroom,

    s.ber_rating,
    s.energy_efficiency_category,

    s.title,
    s.latitude,
    s.longitude,

    s.publish_date,
    s.scraped_date,
    s.days_on_market,

    s.listing_quality_score,
    s.has_images,
    s.is_price_outlier,
    s.is_complete_record,

    s.property_url
FROM silver.stg_daft_listings s
LEFT JOIN gold.dim_property_type pt ON s.property_category = pt.property_category
ORDER BY s.daft_shortcode, s.scraped_date DESC
ON CONFLICT (daft_shortcode) DO UPDATE SET
    price_monthly = EXCLUDED.price_monthly,
    days_on_market = EXCLUDED.days_on_market,
    updated_at = CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_fact_listings_date ON gold.fact_rental_listings(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_listings_county ON gold.fact_rental_listings(county_key);
CREATE INDEX IF NOT EXISTS idx_fact_listings_property_type ON gold.fact_rental_listings(property_type_key);
CREATE INDEX IF NOT EXISTS idx_fact_listings_publish_date ON gold.fact_rental_listings(publish_date);
CREATE INDEX IF NOT EXISTS idx_fact_listings_price ON gold.fact_rental_listings(price_monthly);

-- ============================================================================
-- FACT 2: fact_market_summary (Grain: Month × County × Property Type)
-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.fact_market_summary (
    summary_key SERIAL PRIMARY KEY,
    date_key INT REFERENCES gold.dim_date(date_key), -- First day of month
    county_key INT REFERENCES gold.dim_county(county_key),
    property_type_key INT,

    -- Volume Metrics
    listing_count INT NOT NULL,
    new_listings_count INT,

    -- Price Metrics
    avg_price DECIMAL(10,2),
    median_price DECIMAL(10,2),
    min_price DECIMAL(10,2),
    max_price DECIMAL(10,2),
    stddev_price DECIMAL(10,2),

    -- Property Mix
    avg_bedrooms DECIMAL(3,1),

    -- Bedroom Distribution
    studio_count INT,
    one_bed_count INT,
    two_bed_count INT,
    three_bed_count INT,
    four_plus_bed_count INT,

    -- Market Dynamics
    avg_days_on_market INT,
    market_velocity_score DECIMAL(5,2),

    -- Quality Metrics
    avg_listing_quality_score INT,
    pct_with_images DECIMAL(5,2),
    pct_with_ber DECIMAL(5,2),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    -- Note: No unique constraint because property_type_key can be NULL
    -- Use ON CONFLICT with specific condition instead
);

-- Populate fact_market_summary from silver layer
INSERT INTO gold.fact_market_summary (
    date_key, county_key, property_type_key,
    listing_count, new_listings_count,
    avg_price, median_price, min_price, max_price, stddev_price,
    avg_bedrooms,
    studio_count, one_bed_count, two_bed_count, three_bed_count, four_plus_bed_count,
    avg_days_on_market, market_velocity_score,
    avg_listing_quality_score, pct_with_images, pct_with_ber
)
SELECT
    gold.get_date_key(DATE_TRUNC('month', s.publish_date)::DATE) as date_key,
    gold.get_county_key(s.county_clean) as county_key,
    pt.property_type_key,

    COUNT(*) as listing_count,
    COUNT(*) as new_listings_count,

    AVG(s.price_monthly) as avg_price,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY s.price_monthly) as median_price,
    MIN(s.price_monthly) as min_price,
    MAX(s.price_monthly) as max_price,
    STDDEV(s.price_monthly) as stddev_price,

    AVG(s.bedrooms) as avg_bedrooms,

    COUNT(*) FILTER (WHERE s.bedrooms = 0) as studio_count,
    COUNT(*) FILTER (WHERE s.bedrooms = 1) as one_bed_count,
    COUNT(*) FILTER (WHERE s.bedrooms = 2) as two_bed_count,
    COUNT(*) FILTER (WHERE s.bedrooms = 3) as three_bed_count,
    COUNT(*) FILTER (WHERE s.bedrooms >= 4) as four_plus_bed_count,

    AVG(s.days_on_market) as avg_days_on_market,
    100 - (AVG(s.days_on_market) / 90.0 * 100) as market_velocity_score,

    AVG(s.listing_quality_score) as avg_listing_quality_score,
    AVG(CASE WHEN s.has_images = 1 THEN 100.0 ELSE 0.0 END) as pct_with_images,
    AVG(CASE WHEN s.ber_rating IS NOT NULL AND s.ber_rating != 'NA' THEN 100.0 ELSE 0.0 END) as pct_with_ber
FROM silver.stg_daft_listings s
LEFT JOIN gold.dim_property_type pt ON s.property_category = pt.property_category
WHERE s.publish_date IS NOT NULL
GROUP BY DATE_TRUNC('month', s.publish_date)::DATE, s.county_clean, pt.property_type_key;

-- Create unique index that handles NULLs properly
CREATE UNIQUE INDEX IF NOT EXISTS idx_fact_summary_unique
    ON gold.fact_market_summary(date_key, county_key, COALESCE(property_type_key, -1));

CREATE INDEX IF NOT EXISTS idx_fact_summary_date ON gold.fact_market_summary(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_summary_county ON gold.fact_market_summary(county_key);
CREATE INDEX IF NOT EXISTS idx_fact_summary_property_type ON gold.fact_market_summary(property_type_key);

-- ============================================================================
-- FACT 3: fact_affordability (Grain: Quarter × County)
-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.fact_affordability (
    affordability_key SERIAL PRIMARY KEY,
    date_key INT REFERENCES gold.dim_date(date_key), -- First day of quarter
    county_key INT REFERENCES gold.dim_county(county_key),

    -- Rent Metrics
    avg_monthly_rent DECIMAL(10,2),
    median_monthly_rent DECIMAL(10,2),
    avg_annual_rent DECIMAL(10,2),

    -- Income Metrics
    avg_household_income DECIMAL(10,2),

    -- Affordability Metrics
    rent_to_income_ratio DECIMAL(5,2), -- Percentage
    affordability_classification VARCHAR(50), -- Affordable, Moderate, Expensive, Crisis

    -- Economic Context
    cpi_index DECIMAL(10,2),
    inflation_rate_yoy DECIMAL(5,2),
    real_rent DECIMAL(10,2), -- Inflation-adjusted

    -- Population Context
    population_count BIGINT,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Populate fact_affordability (National level from silver economic indicators)
INSERT INTO gold.fact_affordability (
    date_key, county_key,
    avg_monthly_rent, avg_annual_rent,
    avg_household_income,
    rent_to_income_ratio, affordability_classification,
    cpi_index, inflation_rate_yoy, real_rent,
    population_count
)
WITH quarterly_rent AS (
    SELECT
        DATE_TRUNC('quarter', publish_date)::DATE as quarter_date,
        AVG(price_monthly) as avg_rent,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_monthly) as median_rent
    FROM silver.stg_daft_listings
    WHERE publish_date IS NOT NULL
    GROUP BY DATE_TRUNC('quarter', publish_date)::DATE
),
economic AS (
    SELECT
        year,
        avg_household_income,
        avg_cpi_value,
        cpi_yoy_change_pct,
        real_household_income,
        total_population
    FROM silver.stg_economic_indicators
    WHERE county = 'National'
)
SELECT
    gold.get_date_key(qr.quarter_date) as date_key,
    (SELECT county_key FROM gold.dim_county WHERE county_name = 'Dublin') as county_key, -- Default to Dublin

    qr.avg_rent as avg_monthly_rent,
    qr.avg_rent * 12 as avg_annual_rent,

    e.avg_household_income,

    ((qr.avg_rent * 12) / NULLIF(e.avg_household_income, 0) * 100) as rent_to_income_ratio,

    CASE
        WHEN ((qr.avg_rent * 12) / NULLIF(e.avg_household_income, 0) * 100) < 25 THEN 'Affordable'
        WHEN ((qr.avg_rent * 12) / NULLIF(e.avg_household_income, 0) * 100) < 30 THEN 'Moderate'
        WHEN ((qr.avg_rent * 12) / NULLIF(e.avg_household_income, 0) * 100) < 40 THEN 'Expensive'
        ELSE 'Crisis'
    END as affordability_classification,

    e.avg_cpi_value as cpi_index,
    e.cpi_yoy_change_pct as inflation_rate_yoy,
    e.real_household_income as real_rent,

    e.total_population::BIGINT as population_count
FROM quarterly_rent qr
LEFT JOIN economic e ON EXTRACT(YEAR FROM qr.quarter_date)::INT = e.year
WHERE qr.quarter_date IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_fact_affordability_unique
    ON gold.fact_affordability(date_key, county_key);

CREATE INDEX IF NOT EXISTS idx_fact_affordability_date ON gold.fact_affordability(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_affordability_county ON gold.fact_affordability(county_key);
CREATE INDEX IF NOT EXISTS idx_fact_affordability_classification ON gold.fact_affordability(affordability_classification);

-- ============================================================================
-- FACT 4: fact_economic_indicators (Grain: Year × County)
-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.fact_economic_indicators (
    indicator_key SERIAL PRIMARY KEY,
    date_key INT REFERENCES gold.dim_date(date_key), -- Jan 1st of year
    county_key INT REFERENCES gold.dim_county(county_key),

    -- CPI Metrics
    cpi_value DECIMAL(10,2),
    inflation_rate_yoy DECIMAL(5,2),

    -- Population Metrics
    population_count BIGINT,
    population_yoy_change_pct DECIMAL(5,2),

    -- Income Metrics
    avg_income_annual DECIMAL(10,2),
    avg_income_monthly DECIMAL(10,2),
    income_yoy_change_pct DECIMAL(5,2),

    -- Real Metrics (Inflation-Adjusted)
    real_income DECIMAL(10,2),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Populate fact_economic_indicators from silver layer
INSERT INTO gold.fact_economic_indicators (
    date_key, county_key,
    cpi_value, inflation_rate_yoy,
    population_count, population_yoy_change_pct,
    avg_income_annual, avg_income_monthly, income_yoy_change_pct,
    real_income
)
SELECT DISTINCT ON (date_key, county_key)
    gold.get_date_key((e.year || '-01-01')::DATE) as date_key,
    COALESCE(
        gold.get_county_key(e.county),
        (SELECT county_key FROM gold.dim_county WHERE county_name = 'Dublin')
    ) as county_key,

    e.avg_cpi_value as cpi_value,
    e.cpi_yoy_change_pct as inflation_rate_yoy,

    e.total_population::BIGINT as population_count,
    e.population_yoy_change_pct,

    e.avg_household_income as avg_income_annual,
    e.avg_household_income / 12.0 as avg_income_monthly,
    e.income_yoy_change_pct,

    e.real_household_income as real_income
FROM silver.stg_economic_indicators e
WHERE e.year IS NOT NULL
  AND e.year >= 2000  -- Only include years covered by dim_date
ORDER BY gold.get_date_key((e.year || '-01-01')::DATE),
         COALESCE(gold.get_county_key(e.county), (SELECT county_key FROM gold.dim_county WHERE county_name = 'Dublin')),
         e.year DESC;  -- Take the most recent data if duplicates exist

CREATE UNIQUE INDEX IF NOT EXISTS idx_fact_economic_unique
    ON gold.fact_economic_indicators(date_key, county_key);

CREATE INDEX IF NOT EXISTS idx_fact_economic_date ON gold.fact_economic_indicators(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_economic_county ON gold.fact_economic_indicators(county_key);

-- ============================================================================
-- FACT 5: fact_price_movements (Grain: Month × County × Bedroom Count)
-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.fact_price_movements (
    movement_key SERIAL PRIMARY KEY,
    date_key INT REFERENCES gold.dim_date(date_key), -- First day of month
    county_key INT REFERENCES gold.dim_county(county_key),
    bedroom_count INT NOT NULL,
    bedroom_category VARCHAR(50),

    -- Current Period Metrics
    avg_price_current DECIMAL(10,2),
    median_price_current DECIMAL(10,2),
    listing_count_current INT,

    -- Previous Period Metrics
    avg_price_previous_month DECIMAL(10,2),
    avg_price_previous_year DECIMAL(10,2),

    -- Change Metrics
    price_change_mom_amount DECIMAL(10,2), -- Month-over-Month
    price_change_mom_pct DECIMAL(5,2),
    price_change_yoy_amount DECIMAL(10,2), -- Year-over-Year
    price_change_yoy_pct DECIMAL(5,2),

    -- Market Trend Classification
    trend_classification VARCHAR(50), -- Strong Up, Up, Stable, Down, Strong Down

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Populate fact_price_movements with lag calculations
INSERT INTO gold.fact_price_movements (
    date_key, county_key, bedroom_count, bedroom_category,
    avg_price_current, median_price_current, listing_count_current,
    avg_price_previous_month, avg_price_previous_year,
    price_change_mom_amount, price_change_mom_pct,
    price_change_yoy_amount, price_change_yoy_pct,
    trend_classification
)
WITH monthly_prices AS (
    SELECT
        DATE_TRUNC('month', publish_date)::DATE as month_date,
        county_clean,
        bedrooms,
        bedroom_category,
        AVG(price_monthly) as avg_price,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_monthly) as median_price,
        COUNT(*) as listing_count
    FROM silver.stg_daft_listings
    WHERE publish_date IS NOT NULL AND bedrooms IS NOT NULL
    GROUP BY DATE_TRUNC('month', publish_date)::DATE, county_clean, bedrooms, bedroom_category
)
SELECT
    gold.get_date_key(mp.month_date) as date_key,
    gold.get_county_key(mp.county_clean) as county_key,
    mp.bedrooms as bedroom_count,
    mp.bedroom_category,

    mp.avg_price as avg_price_current,
    mp.median_price as median_price_current,
    mp.listing_count as listing_count_current,

    LAG(mp.avg_price, 1) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date) as avg_price_previous_month,
    LAG(mp.avg_price, 12) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date) as avg_price_previous_year,

    mp.avg_price - LAG(mp.avg_price, 1) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date) as price_change_mom_amount,

    (mp.avg_price - LAG(mp.avg_price, 1) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date)) /
        NULLIF(LAG(mp.avg_price, 1) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date), 0) * 100 as price_change_mom_pct,

    mp.avg_price - LAG(mp.avg_price, 12) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date) as price_change_yoy_amount,

    (mp.avg_price - LAG(mp.avg_price, 12) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date)) /
        NULLIF(LAG(mp.avg_price, 12) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date), 0) * 100 as price_change_yoy_pct,

    CASE
        WHEN (mp.avg_price - LAG(mp.avg_price, 1) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date)) /
             NULLIF(LAG(mp.avg_price, 1) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date), 0) * 100 > 5 THEN 'Strong Up'
        WHEN (mp.avg_price - LAG(mp.avg_price, 1) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date)) /
             NULLIF(LAG(mp.avg_price, 1) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date), 0) * 100 > 1 THEN 'Up'
        WHEN (mp.avg_price - LAG(mp.avg_price, 1) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date)) /
             NULLIF(LAG(mp.avg_price, 1) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date), 0) * 100 < -5 THEN 'Strong Down'
        WHEN (mp.avg_price - LAG(mp.avg_price, 1) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date)) /
             NULLIF(LAG(mp.avg_price, 1) OVER (PARTITION BY mp.county_clean, mp.bedrooms ORDER BY mp.month_date), 0) * 100 < -1 THEN 'Down'
        ELSE 'Stable'
    END as trend_classification
FROM monthly_prices mp
WHERE mp.month_date IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_fact_movements_unique
    ON gold.fact_price_movements(date_key, county_key, bedroom_count);

CREATE INDEX IF NOT EXISTS idx_fact_movements_date ON gold.fact_price_movements(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_movements_county ON gold.fact_price_movements(county_key);
CREATE INDEX IF NOT EXISTS idx_fact_movements_bedrooms ON gold.fact_price_movements(bedroom_count);
CREATE INDEX IF NOT EXISTS idx_fact_movements_trend ON gold.fact_price_movements(trend_classification);

-- ============================================================================
-- MATERIALIZED VIEW: KPI Summary Dashboard
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS gold.mv_kpi_dashboard AS
WITH latest_month AS (
    SELECT MAX(date_key) as max_date_key
    FROM gold.fact_market_summary
),
current_metrics AS (
    SELECT
        c.county_name,
        c.province,
        SUM(ms.listing_count) as total_listings,
        AVG(ms.avg_price) as avg_rent,
        AVG(ms.median_price) as median_rent,
        AVG(ms.avg_days_on_market) as avg_days_on_market,
        AVG(ms.market_velocity_score) as market_velocity
    FROM gold.fact_market_summary ms
    JOIN gold.dim_county c ON ms.county_key = c.county_key
    JOIN latest_month lm ON ms.date_key = lm.max_date_key
    GROUP BY c.county_name, c.province
)
SELECT
    cm.*,
    a.rent_to_income_ratio,
    a.affordability_classification,
    pm.price_change_yoy_pct,
    pm.trend_classification
FROM current_metrics cm
LEFT JOIN gold.fact_affordability a ON a.county_key = (SELECT county_key FROM gold.dim_county WHERE county_name = cm.county_name)
    AND a.date_key = (SELECT MAX(date_key) FROM gold.fact_affordability)
LEFT JOIN gold.fact_price_movements pm ON pm.county_key = (SELECT county_key FROM gold.dim_county WHERE county_name = cm.county_name)
    AND pm.date_key = (SELECT MAX(date_key) FROM gold.fact_price_movements)
    AND pm.bedroom_count = 2;  -- Use 2-bedroom as default for summary

CREATE INDEX IF NOT EXISTS idx_mv_kpi_county ON gold.mv_kpi_dashboard(county_name);
CREATE INDEX IF NOT EXISTS idx_mv_kpi_province ON gold.mv_kpi_dashboard(province);

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT SELECT ON ALL TABLES IN SCHEMA gold TO PUBLIC;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA gold TO PUBLIC;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE gold.fact_rental_listings IS 'Individual rental listing facts with full property details';
COMMENT ON TABLE gold.fact_market_summary IS 'Monthly market summary by county and property type';
COMMENT ON TABLE gold.fact_affordability IS 'Quarterly affordability metrics by county';
COMMENT ON TABLE gold.fact_economic_indicators IS 'Annual economic indicators by county';
COMMENT ON TABLE gold.fact_price_movements IS 'Monthly price movement trends by county and bedroom count';
COMMENT ON MATERIALIZED VIEW gold.mv_kpi_dashboard IS 'Pre-aggregated KPI dashboard for Power BI';

-- ============================================================================
-- VALIDATION QUERIES
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Gold Layer Fact Table Row Counts:';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'fact_rental_listings: % rows', (SELECT COUNT(*) FROM gold.fact_rental_listings);
    RAISE NOTICE 'fact_market_summary: % rows', (SELECT COUNT(*) FROM gold.fact_market_summary);
    RAISE NOTICE 'fact_affordability: % rows', (SELECT COUNT(*) FROM gold.fact_affordability);
    RAISE NOTICE 'fact_economic_indicators: % rows', (SELECT COUNT(*) FROM gold.fact_economic_indicators);
    RAISE NOTICE 'fact_price_movements: % rows', (SELECT COUNT(*) FROM gold.fact_price_movements);
    RAISE NOTICE '============================================================================';
END $$;
