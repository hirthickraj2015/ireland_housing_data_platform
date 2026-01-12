-- ============================================================================
-- RAW TABLES FOR IRELAND HOUSING DATA PLATFORM
-- Database: Neon PostgreSQL 17
-- Schema: public (raw data layer)
-- ============================================================================

-- Drop existing tables (CAUTION: Only run on fresh setup or with backup!)
-- DROP TABLE IF EXISTS raw_daft_listings CASCADE;
-- DROP TABLE IF EXISTS raw_cso_rent CASCADE;
-- DROP TABLE IF EXISTS raw_cso_income CASCADE;
-- DROP TABLE IF EXISTS raw_cso_cpi CASCADE;
-- DROP TABLE IF EXISTS raw_cso_population CASCADE;
-- DROP TABLE IF EXISTS raw_property_sales CASCADE;
-- DROP TABLE IF EXISTS raw_ecb_rates CASCADE;

-- ============================================================================
-- SCRAPING CHECKPOINTS (For incremental loading)
-- ============================================================================
CREATE TABLE IF NOT EXISTS scraping_checkpoints (
    id SERIAL PRIMARY KEY,
    data_source VARCHAR(50) NOT NULL,  -- 'daft', 'cso', etc.
    last_scraped_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_property_id VARCHAR(100),  -- For daft listings
    last_publish_date BIGINT,  -- Unix timestamp for daft
    total_records_scraped INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'completed',  -- 'completed', 'failed', 'in_progress'
    error_message TEXT,
    UNIQUE(data_source)
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_checkpoints_data_source ON scraping_checkpoints(data_source);

-- ============================================================================
-- 1. DAFT.IE RENTAL LISTINGS (ALL 38 FIELDS)
-- ============================================================================
CREATE TABLE IF NOT EXISTS raw_daft_listings (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,

    -- Basic Property Info
    property_id VARCHAR(100) NOT NULL,
    daft_shortcode VARCHAR(50),
    title TEXT,
    seo_title TEXT,

    -- Pricing
    price DECIMAL(10, 2),
    price_raw VARCHAR(100),
    abbreviated_price VARCHAR(50),

    -- Property Characteristics
    property_type VARCHAR(100),
    bedrooms INTEGER,
    num_bedrooms_raw VARCHAR(50),
    county VARCHAR(100),

    -- Property Details
    sections TEXT,  -- Comma-separated list
    sale_type TEXT,  -- Comma-separated list
    category VARCHAR(50),
    state VARCHAR(50),

    -- Dates
    publish_date BIGINT,  -- Unix timestamp in milliseconds
    date_of_construction VARCHAR(50),
    scraped_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Featured Status
    featured_level VARCHAR(50),
    featured_level_full VARCHAR(100),
    premier_partner BOOLEAN,

    -- Location
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    seo_friendly_path TEXT,

    -- Seller Information
    seller_id INTEGER,
    seller_name VARCHAR(255),
    seller_phone VARCHAR(50),
    seller_branch VARCHAR(255),
    seller_type VARCHAR(50),
    licence_number VARCHAR(100),

    -- Media
    total_images INTEGER,
    has_video BOOLEAN,
    has_virtual_tour BOOLEAN,
    has_brochure BOOLEAN,

    -- Energy Rating
    ber_rating VARCHAR(10),

    -- PRS (Private Rental Sector) Info
    prs_total_unit_types INTEGER,
    prs_tagline TEXT,

    -- URLs
    property_url TEXT,

    -- Metadata
    source VARCHAR(50) DEFAULT 'daft.ie',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Daft Listings
CREATE INDEX IF NOT EXISTS idx_daft_property_id ON raw_daft_listings(property_id);
CREATE INDEX IF NOT EXISTS idx_daft_county ON raw_daft_listings(county);
CREATE INDEX IF NOT EXISTS idx_daft_scraped_at ON raw_daft_listings(scraped_at);
CREATE INDEX IF NOT EXISTS idx_daft_price ON raw_daft_listings(price) WHERE price IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_daft_bedrooms ON raw_daft_listings(bedrooms);
CREATE INDEX IF NOT EXISTS idx_daft_property_type ON raw_daft_listings(property_type);
CREATE INDEX IF NOT EXISTS idx_daft_location ON raw_daft_listings(latitude, longitude) WHERE latitude IS NOT NULL;

-- ============================================================================
-- 2. CSO RENT INDEX (RIA02 - 16 Fields)
-- ============================================================================
CREATE TABLE IF NOT EXISTS raw_cso_rent (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,

    -- Dataset Info
    statistic_code VARCHAR(50),        -- e.g., 'RIA02'
    statistic_label TEXT,              -- e.g., 'RTB Average Monthly Rent Report'

    -- Time Dimension
    time_period VARCHAR(50),           -- e.g., '2008'
    year INTEGER,

    -- Number of Bedrooms Dimension
    bedrooms_code VARCHAR(50),         -- e.g., 'C02970V03592'
    bedrooms_label VARCHAR(100),       -- e.g., 'All bedrooms', '1 Bed', '2 Bed', etc.

    -- Property Type Dimension
    property_type_code VARCHAR(50),    -- e.g., 'C02969V03591'
    property_type_label VARCHAR(100),  -- e.g., 'All property types', 'Apartment', 'House'

    -- Location Dimension
    location_code VARCHAR(50),         -- e.g., 'C03004V03625'
    location_label VARCHAR(100),       -- County name or area code

    -- Measure
    unit VARCHAR(50),                  -- e.g., 'Euro'
    value DECIMAL(10, 2),              -- Rent amount

    -- Metadata
    date_fetched TIMESTAMP,
    source VARCHAR(50) DEFAULT 'cso.ie',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for CSO Rent
CREATE INDEX IF NOT EXISTS idx_cso_rent_year ON raw_cso_rent(year);
CREATE INDEX IF NOT EXISTS idx_cso_rent_location ON raw_cso_rent(location_label);
CREATE INDEX IF NOT EXISTS idx_cso_rent_bedrooms ON raw_cso_rent(bedrooms_label);
CREATE INDEX IF NOT EXISTS idx_cso_rent_property_type ON raw_cso_rent(property_type_label);

-- ============================================================================
-- 3. CSO CONSUMER PRICE INDEX (CPA01 - 12 Fields)
-- ============================================================================
CREATE TABLE IF NOT EXISTS raw_cso_cpi (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,

    -- Dataset Info
    statistic_code VARCHAR(50),        -- e.g., 'CPA01C06'
    statistic_label TEXT,              -- e.g., 'Consumer Price Index (Base Dec 2023=100)'

    -- Time Dimension
    time_period VARCHAR(50),           -- e.g., '1975'
    year INTEGER,

    -- Commodity Dimension
    commodity_code VARCHAR(50),        -- e.g., 'C01779V03424'
    commodity_label TEXT,              -- e.g., 'All items', 'Housing', 'Rent', etc.

    -- Measure
    unit VARCHAR(100),                 -- e.g., 'Base Dec 2023=100'
    value DECIMAL(10, 3),              -- CPI value

    -- Metadata
    date_fetched TIMESTAMP,
    source VARCHAR(50) DEFAULT 'cso.ie',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for CSO CPI
CREATE INDEX IF NOT EXISTS idx_cso_cpi_year ON raw_cso_cpi(year);
CREATE INDEX IF NOT EXISTS idx_cso_cpi_commodity ON raw_cso_cpi(commodity_label);

-- ============================================================================
-- 4. CSO POPULATION (PEA01 - 14 Fields)
-- ============================================================================
CREATE TABLE IF NOT EXISTS raw_cso_population (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,

    -- Dataset Info
    statistic_code VARCHAR(50),        -- e.g., 'PEA01'
    statistic_label TEXT,              -- e.g., 'Population Estimates (Persons in April)'

    -- Time Dimension
    time_period VARCHAR(50),           -- e.g., '1950'
    year INTEGER,

    -- Age Group Dimension
    age_group_code VARCHAR(50),        -- e.g., 'C02076V02508'
    age_group_label VARCHAR(100),      -- e.g., 'Under 1 year', '1-4 years', etc.

    -- Sex Dimension
    sex_code VARCHAR(50),              -- e.g., 'C02199V02655'
    sex_label VARCHAR(50),             -- e.g., 'Both sexes', 'Male', 'Female'

    -- Measure
    unit VARCHAR(50),                  -- e.g., 'Thousand'
    value DECIMAL(12, 2),              -- Population value

    -- Metadata
    date_fetched TIMESTAMP,
    source VARCHAR(50) DEFAULT 'cso.ie',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for CSO Population
CREATE INDEX IF NOT EXISTS idx_cso_pop_year ON raw_cso_population(year);
CREATE INDEX IF NOT EXISTS idx_cso_pop_age_group ON raw_cso_population(age_group_label);
CREATE INDEX IF NOT EXISTS idx_cso_pop_sex ON raw_cso_population(sex_label);

-- ============================================================================
-- 5. CSO DISPOSABLE INCOME (CIA01 - 12 Fields)
-- ============================================================================
CREATE TABLE IF NOT EXISTS raw_cso_income (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,

    -- Location Dimension
    location_code VARCHAR(50),         -- e.g., 'C02196V02652'
    location_label VARCHAR(100),       -- County or 'State'

    -- Time Dimension
    time_period VARCHAR(50),           -- e.g., '2000'
    year INTEGER,

    -- Statistic Type
    statistic_code VARCHAR(50),        -- e.g., 'CIA01C01'
    statistic_label TEXT,              -- Income type description

    -- Measure
    unit VARCHAR(50),                  -- e.g., 'Euro Million'
    value DECIMAL(15, 2),              -- Income value

    -- Metadata
    date_fetched TIMESTAMP,
    source VARCHAR(50) DEFAULT 'cso.ie',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for CSO Income
CREATE INDEX IF NOT EXISTS idx_cso_income_location ON raw_cso_income(location_label);
CREATE INDEX IF NOT EXISTS idx_cso_income_year ON raw_cso_income(year);
CREATE INDEX IF NOT EXISTS idx_cso_income_statistic ON raw_cso_income(statistic_code);

-- ============================================================================
-- 6. PROPERTY PRICE REGISTER
-- ============================================================================
CREATE TABLE IF NOT EXISTS raw_property_sales (
    id BIGSERIAL PRIMARY KEY,
    date_of_sale DATE,
    price DECIMAL(12, 2),
    address TEXT,
    county VARCHAR(100),
    eircode VARCHAR(20),
    property_description VARCHAR(200),
    property_size VARCHAR(50),
    vat_exclusive BOOLEAN,
    date_fetched TIMESTAMP,
    source VARCHAR(50) DEFAULT 'propertypriceregister.ie',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_property_county ON raw_property_sales(county);
CREATE INDEX IF NOT EXISTS idx_property_date ON raw_property_sales(date_of_sale);

-- ============================================================================
-- 7. ECB INTEREST RATES
-- ============================================================================
CREATE TABLE IF NOT EXISTS raw_ecb_rates (
    id BIGSERIAL PRIMARY KEY,
    rate_type VARCHAR(100),
    time_period VARCHAR(50),
    rate_value DECIMAL(6, 3),
    series_key VARCHAR(200),
    date_fetched TIMESTAMP,
    source VARCHAR(50) DEFAULT 'ecb.europa.eu',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ecb_rate_type ON raw_ecb_rates(rate_type);
CREATE INDEX IF NOT EXISTS idx_ecb_period ON raw_ecb_rates(time_period);

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================
SELECT 'Raw tables created successfully with complete field sets!' as status;
