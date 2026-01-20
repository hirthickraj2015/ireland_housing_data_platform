-- ============================================================================
-- GOLD LAYER: Dimension Tables (Star Schema)
-- Purpose: Create analytics-ready dimension tables
-- ============================================================================

-- Create gold schema
CREATE SCHEMA IF NOT EXISTS gold;

-- ============================================================================
-- DIMENSION 1: dim_date (Date Dimension)
-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.dim_date (
    date_key INT PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    week INT NOT NULL,
    day INT NOT NULL,
    day_of_week INT NOT NULL,
    day_of_year INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    month_abbr VARCHAR(3) NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    day_abbr VARCHAR(3) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_month_start BOOLEAN NOT NULL,
    is_month_end BOOLEAN NOT NULL,
    is_quarter_start BOOLEAN NOT NULL,
    is_quarter_end BOOLEAN NOT NULL,
    is_year_start BOOLEAN NOT NULL,
    is_year_end BOOLEAN NOT NULL,
    fiscal_year INT,
    fiscal_quarter INT,
    week_of_month INT,
    day_of_quarter INT,
    quarter_name VARCHAR(10),
    year_month VARCHAR(7),
    year_quarter VARCHAR(7)
);

-- Populate dim_date with data from 2000-2030 (covers economic data + future)
INSERT INTO gold.dim_date (
    date_key, date, year, quarter, month, week, day,
    day_of_week, day_of_year, month_name, month_abbr,
    day_name, day_abbr, is_weekend, is_month_start, is_month_end,
    is_quarter_start, is_quarter_end, is_year_start, is_year_end,
    fiscal_year, fiscal_quarter, week_of_month, day_of_quarter,
    quarter_name, year_month, year_quarter
)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INT as date_key,
    d as date,
    EXTRACT(YEAR FROM d)::INT as year,
    EXTRACT(QUARTER FROM d)::INT as quarter,
    EXTRACT(MONTH FROM d)::INT as month,
    EXTRACT(WEEK FROM d)::INT as week,
    EXTRACT(DAY FROM d)::INT as day,
    EXTRACT(DOW FROM d)::INT as day_of_week,
    EXTRACT(DOY FROM d)::INT as day_of_year,
    TO_CHAR(d, 'Month') as month_name,
    TO_CHAR(d, 'Mon') as month_abbr,
    TO_CHAR(d, 'Day') as day_name,
    TO_CHAR(d, 'Dy') as day_abbr,
    CASE WHEN EXTRACT(DOW FROM d) IN (0, 6) THEN TRUE ELSE FALSE END as is_weekend,
    CASE WHEN EXTRACT(DAY FROM d) = 1 THEN TRUE ELSE FALSE END as is_month_start,
    CASE WHEN d = (DATE_TRUNC('MONTH', d) + INTERVAL '1 MONTH - 1 day') THEN TRUE ELSE FALSE END as is_month_end,
    CASE WHEN DATE_TRUNC('QUARTER', d) = d THEN TRUE ELSE FALSE END as is_quarter_start,
    CASE WHEN d = (DATE_TRUNC('QUARTER', d) + INTERVAL '3 MONTH - 1 day') THEN TRUE ELSE FALSE END as is_quarter_end,
    CASE WHEN TO_CHAR(d, 'MMDD') = '0101' THEN TRUE ELSE FALSE END as is_year_start,
    CASE WHEN TO_CHAR(d, 'MMDD') = '1231' THEN TRUE ELSE FALSE END as is_year_end,
    EXTRACT(YEAR FROM d)::INT as fiscal_year,
    EXTRACT(QUARTER FROM d)::INT as fiscal_quarter,
    CEIL(EXTRACT(DAY FROM d) / 7.0)::INT as week_of_month,
    EXTRACT(DAY FROM (d - DATE_TRUNC('QUARTER', d)::DATE))::INT + 1 as day_of_quarter,
    'Q' || EXTRACT(QUARTER FROM d) as quarter_name,
    TO_CHAR(d, 'YYYY-MM') as year_month,
    TO_CHAR(d, 'YYYY') || '-Q' || EXTRACT(QUARTER FROM d) as year_quarter
FROM GENERATE_SERIES('2000-01-01'::DATE, '2030-12-31'::DATE, '1 day') AS d
ON CONFLICT (date_key) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_dim_date_date ON gold.dim_date(date);
CREATE INDEX IF NOT EXISTS idx_dim_date_year_month ON gold.dim_date(year, month);
CREATE INDEX IF NOT EXISTS idx_dim_date_year_quarter ON gold.dim_date(year, quarter);

-- ============================================================================
-- DIMENSION 2: dim_county (Geography Dimension)
-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.dim_county (
    county_key SERIAL PRIMARY KEY,
    county_name VARCHAR(50) NOT NULL UNIQUE,
    province VARCHAR(20),
    region VARCHAR(50),
    population_2023 INT,
    area_km2 DECIMAL(10,2),
    distance_to_dublin_km INT,
    is_commuter_belt BOOLEAN DEFAULT FALSE,
    is_urban BOOLEAN DEFAULT FALSE,
    economic_classification VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert county data with provinces
INSERT INTO gold.dim_county (county_name, province, region, distance_to_dublin_km, is_commuter_belt, is_urban) VALUES
-- Leinster
('Dublin', 'Leinster', 'Eastern & Midland', 0, TRUE, TRUE),
('Kildare', 'Leinster', 'Eastern & Midland', 40, TRUE, FALSE),
('Meath', 'Leinster', 'Eastern & Midland', 45, TRUE, FALSE),
('Wicklow', 'Leinster', 'Eastern & Midland', 50, TRUE, FALSE),
('Louth', 'Leinster', 'Eastern & Midland', 80, FALSE, FALSE),
('Westmeath', 'Leinster', 'Eastern & Midland', 80, FALSE, FALSE),
('Offaly', 'Leinster', 'Eastern & Midland', 90, FALSE, FALSE),
('Laois', 'Leinster', 'Eastern & Midland', 85, FALSE, FALSE),
('Longford', 'Leinster', 'Eastern & Midland', 120, FALSE, FALSE),
('Carlow', 'Leinster', 'Southern', 85, FALSE, FALSE),
('Kilkenny', 'Leinster', 'Southern', 120, FALSE, FALSE),
('Wexford', 'Leinster', 'Southern', 140, FALSE, FALSE),

-- Munster
('Cork', 'Munster', 'Southern', 260, FALSE, TRUE),
('Limerick', 'Munster', 'Southern', 200, FALSE, TRUE),
('Kerry', 'Munster', 'Southern', 330, FALSE, FALSE),
('Waterford', 'Munster', 'Southern', 180, FALSE, TRUE),
('Tipperary', 'Munster', 'Southern', 150, FALSE, FALSE),
('Clare', 'Munster', 'Southern', 230, FALSE, FALSE),

-- Connacht
('Galway', 'Connacht', 'Western', 220, FALSE, TRUE),
('Mayo', 'Connacht', 'Western', 260, FALSE, FALSE),
('Roscommon', 'Connacht', 'Western', 150, FALSE, FALSE),
('Sligo', 'Connacht', 'Western', 220, FALSE, FALSE),
('Leitrim', 'Connacht', 'Western', 180, FALSE, FALSE),

-- Ulster (Republic of Ireland counties only)
('Donegal', 'Ulster', 'Northern & Western', 240, FALSE, FALSE),
('Cavan', 'Ulster', 'Northern & Western', 110, FALSE, FALSE),
('Monaghan', 'Ulster', 'Northern & Western', 120, FALSE, FALSE)
ON CONFLICT (county_name) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_dim_county_name ON gold.dim_county(county_name);
CREATE INDEX IF NOT EXISTS idx_dim_county_province ON gold.dim_county(province);

-- ============================================================================
-- DIMENSION 3: dim_property_type (Property Classification)
-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.dim_property_type (
    property_type_key SERIAL PRIMARY KEY,
    property_category VARCHAR(50) NOT NULL,
    property_subcategory VARCHAR(100),
    typical_min_bedrooms INT,
    typical_max_bedrooms INT,
    typical_occupancy INT,
    target_demographic VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert property types
INSERT INTO gold.dim_property_type (
    property_category, property_subcategory,
    typical_min_bedrooms, typical_max_bedrooms,
    typical_occupancy, target_demographic, description
) VALUES
('Studio', 'Studio Apartment', 0, 0, 1, 'Students, Young Professionals', 'Single-room living space with kitchen and bathroom'),
('Apartment', '1-Bedroom Apartment', 1, 1, 1-2, 'Singles, Couples', 'Separate bedroom, living area, kitchen, bathroom'),
('Apartment', '2-Bedroom Apartment', 2, 2, 2-3, 'Small Families, Roommates', 'Two bedrooms, living area, kitchen, bathroom'),
('Apartment', '3+ Bedroom Apartment', 3, 5, 3-5, 'Families, Multiple Roommates', 'Three or more bedrooms, larger living spaces'),
('House', 'Terraced House', 2, 4, 2-6, 'Families', 'Row house with shared walls'),
('House', 'Semi-Detached House', 3, 5, 3-6, 'Families', 'House sharing one wall with neighbor'),
('House', 'Detached House', 3, 6, 4-8, 'Large Families', 'Standalone house with no shared walls'),
('Duplex', 'Duplex', 2, 4, 2-6, 'Families', 'Multi-level apartment or house'),
('Room', 'Single Room in Shared House', 1, 1, 1, 'Students, Young Professionals', 'Private bedroom in shared accommodation'),
('Other', 'Other Property Type', 0, 10, 1-10, 'Varies', 'Other or unclassified property types')
ON CONFLICT DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_dim_property_category ON gold.dim_property_type(property_category);

-- ============================================================================
-- DIMENSION 4: dim_market_segment (Customer Segmentation)
-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.dim_market_segment (
    segment_key SERIAL PRIMARY KEY,
    price_band VARCHAR(50) NOT NULL,
    price_min DECIMAL(10,2),
    price_max DECIMAL(10,2),
    bedroom_category VARCHAR(50),
    target_demographic VARCHAR(100),
    market_positioning VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert market segments
INSERT INTO gold.dim_market_segment (
    price_band, price_min, price_max,
    bedroom_category, target_demographic, market_positioning
) VALUES
-- Budget Segment
('Budget', 0, 1000, 'Studio/1BR', 'Students, Entry-level workers', 'Affordable entry point'),
('Budget', 0, 1000, '2BR', 'Roommates, Budget-conscious families', 'Shared living arrangements'),

-- Mid-Market Segment
('Mid-Market', 1000, 1500, '1BR', 'Young professionals', 'Standard urban rentals'),
('Mid-Market', 1000, 1500, '2BR', 'Small families, Working couples', 'Mainstream market'),
('Mid-Market', 1000, 1500, '3BR', 'Growing families', 'Suburban family homes'),

-- Premium Segment
('Premium', 1500, 2500, '1BR', 'Well-paid professionals', 'High-quality urban living'),
('Premium', 1500, 2500, '2BR', 'Dual-income couples', 'Upscale apartments'),
('Premium', 1500, 2500, '3BR', 'Affluent families', 'Premium family homes'),

-- Luxury Segment
('Luxury', 2500, 999999, '2BR+', 'High earners, Executives', 'Premium properties, prime locations'),
('Luxury', 2500, 999999, '3BR+', 'Wealthy families, Executives', 'Luxury homes, exclusive areas')
ON CONFLICT DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_dim_market_segment_price_band ON gold.dim_market_segment(price_band);

-- ============================================================================
-- HELPER FUNCTION: Get date_key from date
-- ============================================================================

CREATE OR REPLACE FUNCTION gold.get_date_key(input_date DATE)
RETURNS INT AS $$
BEGIN
    RETURN TO_CHAR(input_date, 'YYYYMMDD')::INT;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- HELPER FUNCTION: Get county_key from county name
-- ============================================================================

CREATE OR REPLACE FUNCTION gold.get_county_key(county_name_input VARCHAR)
RETURNS INT AS $$
DECLARE
    key INT;
BEGIN
    SELECT county_key INTO key
    FROM gold.dim_county
    WHERE LOWER(county_name) = LOWER(county_name_input);

    RETURN key;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT USAGE ON SCHEMA gold TO PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO PUBLIC;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA gold TO PUBLIC;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON SCHEMA gold IS 'Gold layer: Analytics-ready star schema with dimensions and facts';
COMMENT ON TABLE gold.dim_date IS 'Date dimension with comprehensive time attributes for trend analysis';
COMMENT ON TABLE gold.dim_county IS 'County dimension with geographic hierarchies and classifications';
COMMENT ON TABLE gold.dim_property_type IS 'Property type dimension for segmentation analysis';
COMMENT ON TABLE gold.dim_market_segment IS 'Market segment dimension for customer targeting';

-- ============================================================================
-- VALIDATION QUERIES
-- ============================================================================

-- Check dimension row counts
DO $$
BEGIN
    RAISE NOTICE 'Dimension Table Row Counts:';
    RAISE NOTICE 'dim_date: % rows', (SELECT COUNT(*) FROM gold.dim_date);
    RAISE NOTICE 'dim_county: % rows', (SELECT COUNT(*) FROM gold.dim_county);
    RAISE NOTICE 'dim_property_type: % rows', (SELECT COUNT(*) FROM gold.dim_property_type);
    RAISE NOTICE 'dim_market_segment: % rows', (SELECT COUNT(*) FROM gold.dim_market_segment);
END $$;
