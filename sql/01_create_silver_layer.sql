-- ============================================================================
-- SILVER LAYER: Cleaned and Standardized Data
-- Purpose: Apply business rules, clean data, standardize formats
-- ============================================================================

-- Create silver schema
CREATE SCHEMA IF NOT EXISTS silver;

-- ============================================================================
-- 1. SILVER: Daft Listings (Cleaned)
-- ============================================================================

CREATE OR REPLACE VIEW silver.stg_daft_listings AS
SELECT
    -- Identifiers
    property_id,
    daft_shortcode,
    id as raw_id,

    -- Temporal (convert Unix timestamp in milliseconds to date, use scraped_at if NULL)
    COALESCE(TO_TIMESTAMP(publish_date / 1000.0)::DATE, scraped_at::DATE) as publish_date,
    scraped_at::DATE as scraped_date,
    CURRENT_DATE - COALESCE(TO_TIMESTAMP(publish_date / 1000.0)::DATE, scraped_at::DATE) as days_on_market,

    -- Location (Standardized)
    CASE
        WHEN county ILIKE '%dublin%' THEN 'Dublin'
        WHEN county ILIKE '%cork%' THEN 'Cork'
        WHEN county ILIKE '%galway%' THEN 'Galway'
        WHEN county ILIKE '%kerry%' THEN 'Kerry'
        WHEN county ILIKE '%limerick%' THEN 'Limerick'
        WHEN county ILIKE '%waterford%' THEN 'Waterford'
        WHEN county ILIKE '%clare%' THEN 'Clare'
        WHEN county ILIKE '%mayo%' THEN 'Mayo'
        WHEN county ILIKE '%sligo%' THEN 'Sligo'
        WHEN county ILIKE '%donegal%' THEN 'Donegal'
        WHEN county ILIKE '%wicklow%' THEN 'Wicklow'
        WHEN county ILIKE '%meath%' THEN 'Meath'
        WHEN county ILIKE '%kildare%' THEN 'Kildare'
        WHEN county ILIKE '%louth%' THEN 'Louth'
        WHEN county ILIKE '%westmeath%' THEN 'Westmeath'
        WHEN county ILIKE '%offaly%' THEN 'Offaly'
        WHEN county ILIKE '%laois%' THEN 'Laois'
        WHEN county ILIKE '%carlow%' THEN 'Carlow'
        WHEN county ILIKE '%kilkenny%' THEN 'Kilkenny'
        WHEN county ILIKE '%wexford%' THEN 'Wexford'
        WHEN county ILIKE '%tipperary%' THEN 'Tipperary'
        WHEN county ILIKE '%roscommon%' THEN 'Roscommon'
        WHEN county ILIKE '%longford%' THEN 'Longford'
        WHEN county ILIKE '%cavan%' THEN 'Cavan'
        WHEN county ILIKE '%monaghan%' THEN 'Monaghan'
        WHEN county ILIKE '%leitrim%' THEN 'Leitrim'
        ELSE INITCAP(TRIM(county))
    END as county_clean,
    county as county_original,
    title,
    seo_friendly_path,
    latitude,
    longitude,

    -- Property Details
    CASE
        WHEN property_type ILIKE '%apartment%' THEN 'Apartment'
        WHEN property_type ILIKE '%flat%' THEN 'Apartment'
        WHEN property_type ILIKE '%house%' THEN 'House'
        WHEN property_type ILIKE '%studio%' THEN 'Studio'
        WHEN property_type ILIKE '%room%' THEN 'Room'
        WHEN property_type ILIKE '%duplex%' THEN 'Duplex'
        ELSE 'Other'
    END as property_category,
    property_type as property_type_original,

    -- Price (Cleaned and Validated)
    price as price_monthly,
    CASE
        WHEN price < 500 THEN TRUE  -- Suspiciously low
        WHEN price > 10000 THEN TRUE  -- Suspiciously high
        ELSE FALSE
    END as is_price_outlier,

    CASE
        WHEN price < 1000 THEN 'Budget (<€1000)'
        WHEN price < 1500 THEN 'Mid-Market (€1000-1500)'
        WHEN price < 2500 THEN 'Premium (€1500-2500)'
        ELSE 'Luxury (€2500+)'
    END as price_band,

    -- Bedrooms
    COALESCE(bedrooms, 0) as bedrooms,
    CASE
        WHEN bedrooms = 0 OR bedrooms IS NULL THEN 'Studio'
        WHEN bedrooms = 1 THEN '1 Bedroom'
        WHEN bedrooms = 2 THEN '2 Bedrooms'
        WHEN bedrooms = 3 THEN '3 Bedrooms'
        WHEN bedrooms >= 4 THEN '4+ Bedrooms'
    END as bedroom_category,

    -- Derived Metrics
    CASE
        WHEN bedrooms > 0 THEN price / bedrooms
        ELSE price
    END as price_per_bedroom,

    -- Property Features
    ber_rating,
    CASE
        WHEN ber_rating IN ('A1', 'A2', 'A3', 'B1', 'B2', 'B3') THEN 'High Efficiency'
        WHEN ber_rating IN ('C1', 'C2', 'C3') THEN 'Medium Efficiency'
        WHEN ber_rating IN ('D1', 'D2', 'E1', 'E2', 'F', 'G') THEN 'Low Efficiency'
        ELSE 'Unknown'
    END as energy_efficiency_category,

    -- Seller Information
    seller_name,
    seller_type,
    seller_branch,
    premier_partner,

    -- Media
    total_images,
    has_video,
    has_virtual_tour,
    has_brochure,

    -- URLs
    property_url,

    -- State
    state,
    featured_level,

    -- Data Quality Flags
    CASE
        WHEN county IS NULL THEN FALSE
        WHEN price IS NULL OR price <= 0 THEN FALSE
        WHEN bedrooms IS NULL THEN FALSE
        WHEN latitude IS NULL OR longitude IS NULL THEN FALSE
        ELSE TRUE
    END as is_complete_record,

    CASE
        WHEN total_images > 0 THEN 1
        ELSE 0
    END as has_images,

    -- Listing Quality Score (0-100)
    (
        CASE WHEN total_images > 0 THEN 30 ELSE 0 END +
        CASE WHEN LENGTH(COALESCE(title, '')) > 10 THEN 20 ELSE 0 END +
        CASE WHEN ber_rating IS NOT NULL AND ber_rating != 'NA' THEN 20 ELSE 0 END +
        CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 20 ELSE 0 END +
        CASE WHEN price BETWEEN 500 AND 5000 THEN 10 ELSE 0 END
    ) as listing_quality_score

FROM raw_daft_listings
WHERE price IS NOT NULL AND price > 0;

-- ============================================================================
-- 2. SILVER: CSO Rent Index (Cleaned and Pivoted)
-- ============================================================================

CREATE OR REPLACE VIEW silver.stg_cso_rent_index AS
WITH cleaned AS (
    SELECT
        year,
        CASE
            WHEN location_label ILIKE '%dublin%' THEN 'Dublin'
            WHEN location_label ILIKE '%cork%' THEN 'Cork'
            WHEN location_label ILIKE '%galway%' THEN 'Galway'
            ELSE location_label
        END as county_clean,
        bedrooms_label,
        property_type_label,
        value as rent_index_value,
        date_fetched
    FROM raw_cso_rent
    WHERE year IS NOT NULL
      AND value IS NOT NULL
),
aggregated AS (
    SELECT
        year,
        county_clean,
        property_type_label,
        MAX(CASE WHEN bedrooms_label ILIKE '%1 bedroom%' THEN rent_index_value END) as rent_index_1br,
        MAX(CASE WHEN bedrooms_label ILIKE '%2 bedroom%' THEN rent_index_value END) as rent_index_2br,
        MAX(CASE WHEN bedrooms_label ILIKE '%3 bedroom%' THEN rent_index_value END) as rent_index_3br,
        MAX(CASE WHEN bedrooms_label ILIKE '%4 bedroom%' THEN rent_index_value END) as rent_index_4br,
        MAX(CASE WHEN bedrooms_label ILIKE '%all%' OR bedrooms_label ILIKE '%total%' THEN rent_index_value END) as rent_index_avg,
        MAX(date_fetched) as date_fetched
    FROM cleaned
    GROUP BY year, county_clean, property_type_label
)
SELECT
    year,
    county_clean,
    property_type_label,
    rent_index_1br,
    rent_index_2br,
    rent_index_3br,
    rent_index_4br,
    rent_index_avg,
    date_fetched,

    -- Calculate YoY change using window function
    LAG(rent_index_avg) OVER (PARTITION BY county_clean, property_type_label ORDER BY year) as rent_index_prev_year,

    (rent_index_avg - LAG(rent_index_avg) OVER (PARTITION BY county_clean, property_type_label ORDER BY year)) /
        NULLIF(LAG(rent_index_avg) OVER (PARTITION BY county_clean, property_type_label ORDER BY year), 0) * 100 as yoy_change_pct
FROM aggregated;

-- ============================================================================
-- 3. SILVER: Economic Indicators (Combined View)
-- ============================================================================

CREATE OR REPLACE VIEW silver.stg_economic_indicators AS
SELECT
    COALESCE(cpi.year, pop.year, inc.year) as year,
    COALESCE(cpi.county, pop.county, inc.county) as county,

    -- CPI Data
    cpi.avg_cpi_value,
    cpi.cpi_yoy_change_pct,

    -- Population Data
    pop.total_population,
    pop.population_yoy_change_pct,

    -- Income Data
    inc.avg_household_income,
    inc.income_yoy_change_pct,

    -- Calculated: Real Income (adjusted for inflation)
    CASE
        WHEN cpi.avg_cpi_value IS NOT NULL AND inc.avg_household_income IS NOT NULL
        THEN inc.avg_household_income / (cpi.avg_cpi_value / 100.0)
        ELSE inc.avg_household_income
    END as real_household_income

FROM (
    -- CPI aggregated
    SELECT
        year,
        'National' as county,
        AVG(value) as avg_cpi_value,
        (AVG(value) - LAG(AVG(value)) OVER (ORDER BY year)) /
            NULLIF(LAG(AVG(value)) OVER (ORDER BY year), 0) * 100 as cpi_yoy_change_pct
    FROM raw_cso_cpi
    WHERE value IS NOT NULL
    GROUP BY year
) cpi
FULL OUTER JOIN (
    -- Population aggregated
    SELECT
        year,
        'National' as county,
        SUM(value) as total_population,
        (SUM(value) - LAG(SUM(value)) OVER (ORDER BY year)) /
            NULLIF(LAG(SUM(value)) OVER (ORDER BY year), 0) * 100 as population_yoy_change_pct
    FROM raw_cso_population
    WHERE value IS NOT NULL
    GROUP BY year
) pop ON cpi.year = pop.year AND cpi.county = pop.county
FULL OUTER JOIN (
    -- Income aggregated
    SELECT
        year,
        location_label as county,
        AVG(value) as avg_household_income,
        (AVG(value) - LAG(AVG(value)) OVER (PARTITION BY location_label ORDER BY year)) /
            NULLIF(LAG(AVG(value)) OVER (PARTITION BY location_label ORDER BY year), 0) * 100 as income_yoy_change_pct
    FROM raw_cso_income
    WHERE value IS NOT NULL
    GROUP BY year, location_label
) inc ON COALESCE(cpi.year, pop.year) = inc.year;

-- ============================================================================
-- 4. SILVER: Market Activity Summary
-- ============================================================================

CREATE OR REPLACE VIEW silver.stg_market_activity AS
SELECT
    COALESCE(TO_TIMESTAMP(publish_date / 1000.0)::DATE, scraped_at::DATE) as activity_date,
    county,
    COUNT(*) as new_listings_count,
    AVG(price) as avg_price_new_listings,
    MIN(price) as min_price,
    MAX(price) as max_price,
    STDDEV(price) as price_stddev,

    -- Property type distribution
    COUNT(*) FILTER (WHERE property_type ILIKE '%house%') as house_count,
    COUNT(*) FILTER (WHERE property_type ILIKE '%apartment%') as apartment_count,
    COUNT(*) FILTER (WHERE property_type ILIKE '%studio%') as studio_count,

    -- Bedroom distribution
    AVG(bedrooms) as avg_bedrooms,
    COUNT(*) FILTER (WHERE bedrooms = 1) as one_bed_count,
    COUNT(*) FILTER (WHERE bedrooms = 2) as two_bed_count,
    COUNT(*) FILTER (WHERE bedrooms = 3) as three_bed_count,
    COUNT(*) FILTER (WHERE bedrooms >= 4) as four_plus_bed_count

FROM raw_daft_listings
WHERE price > 0
GROUP BY COALESCE(TO_TIMESTAMP(publish_date / 1000.0)::DATE, scraped_at::DATE), county;

-- ============================================================================
-- 5. SILVER: Data Quality Monitoring
-- ============================================================================

CREATE OR REPLACE VIEW silver.vw_data_quality_metrics AS
SELECT
    'raw_daft_listings' as table_name,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE price IS NULL) as null_price_count,
    COUNT(*) FILTER (WHERE county IS NULL) as null_county_count,
    COUNT(*) FILTER (WHERE publish_date IS NULL) as null_date_count,
    ROUND(COUNT(*) FILTER (WHERE price IS NULL)::NUMERIC / COUNT(*) * 100, 2) as pct_null_price,
    COUNT(*) FILTER (WHERE price < 500 OR price > 10000) as outlier_count,
    MAX(scraped_at) as last_updated,
    CURRENT_TIMESTAMP - MAX(scraped_at) as data_age
FROM raw_daft_listings

UNION ALL

SELECT
    'raw_cso_rent' as table_name,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE value IS NULL) as null_value_count,
    COUNT(*) FILTER (WHERE year IS NULL) as null_year_count,
    COUNT(*) FILTER (WHERE location_label IS NULL) as null_location_count,
    ROUND(COUNT(*) FILTER (WHERE value IS NULL)::NUMERIC / COUNT(*) * 100, 2) as pct_null_value,
    0 as outlier_count,
    MAX(date_fetched) as last_updated,
    CURRENT_TIMESTAMP - MAX(date_fetched) as data_age
FROM raw_cso_rent;

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT USAGE ON SCHEMA silver TO PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA silver TO PUBLIC;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON SCHEMA silver IS 'Silver layer: Cleaned and standardized data ready for analytics';
COMMENT ON VIEW silver.stg_daft_listings IS 'Cleaned Daft listings with standardized columns and quality flags';
COMMENT ON VIEW silver.stg_cso_rent_index IS 'CSO rent index pivoted by bedrooms with YoY calculations';
COMMENT ON VIEW silver.stg_economic_indicators IS 'Combined economic indicators (CPI, Population, Income)';
COMMENT ON VIEW silver.stg_market_activity IS 'Daily market activity summary by county';
COMMENT ON VIEW silver.vw_data_quality_metrics IS 'Data quality metrics for monitoring ETL health';
