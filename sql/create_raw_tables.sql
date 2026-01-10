-- SQL Script to create raw data tables
-- Run this before the ETL pipeline

-- Drop existing tables if needed (careful in production!)
-- DROP TABLE IF EXISTS raw_daft_listings CASCADE;
-- DROP TABLE IF EXISTS raw_cso_rent CASCADE;
-- DROP TABLE IF EXISTS raw_cso_income CASCADE;
-- DROP TABLE IF EXISTS raw_property_sales CASCADE;
-- DROP TABLE IF EXISTS raw_ecb_rates CASCADE;

-- 1. Daft.ie Rental Listings
CREATE TABLE IF NOT EXISTS raw_daft_listings (
    id SERIAL PRIMARY KEY,
    property_id VARCHAR(100),
    price DECIMAL(10, 2),
    title TEXT,
    county VARCHAR(100),
    bedrooms INTEGER,
    property_type VARCHAR(100),
    property_url TEXT,
    date_scraped TIMESTAMP,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_daft_county ON raw_daft_listings(county);
CREATE INDEX idx_daft_date ON raw_daft_listings(date_scraped);
CREATE INDEX idx_daft_property_id ON raw_daft_listings(property_id);

-- 2. CSO Rent Index
CREATE TABLE IF NOT EXISTS raw_cso_rent (
    id SERIAL PRIMARY KEY,
    -- Add columns based on CSO API structure
    -- These are placeholders - update based on actual API response
    county VARCHAR(100),
    time_period VARCHAR(50),
    rent_index DECIMAL(10, 2),
    date_fetched TIMESTAMP,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cso_rent_county ON raw_cso_rent(county);
CREATE INDEX idx_cso_rent_period ON raw_cso_rent(time_period);

-- 3. CSO Disposable Income
CREATE TABLE IF NOT EXISTS raw_cso_income (
    id SERIAL PRIMARY KEY,
    county VARCHAR(100),
    year INTEGER,
    disposable_income DECIMAL(12, 2),
    date_fetched TIMESTAMP,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cso_income_county ON raw_cso_income(county);
CREATE INDEX idx_cso_income_year ON raw_cso_income(year);

-- 4. Property Price Register
CREATE TABLE IF NOT EXISTS raw_property_sales (
    id SERIAL PRIMARY KEY,
    date_of_sale DATE,
    price DECIMAL(12, 2),
    address TEXT,
    county VARCHAR(100),
    eircode VARCHAR(20),
    property_description VARCHAR(200),
    property_size VARCHAR(50),
    vat_exclusive BOOLEAN,
    date_fetched TIMESTAMP,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_property_county ON raw_property_sales(county);
CREATE INDEX idx_property_date ON raw_property_sales(date_of_sale);

-- 5. ECB Interest Rates
CREATE TABLE IF NOT EXISTS raw_ecb_rates (
    id SERIAL PRIMARY KEY,
    rate_type VARCHAR(100),
    time_period VARCHAR(50),
    rate_value DECIMAL(6, 3),
    series_key VARCHAR(200),
    date_fetched TIMESTAMP,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ecb_rate_type ON raw_ecb_rates(rate_type);
CREATE INDEX idx_ecb_period ON raw_ecb_rates(time_period);

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_user;

-- Success message
SELECT 'Raw tables created successfully!' as status;
