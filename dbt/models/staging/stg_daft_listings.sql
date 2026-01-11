{{
    config(
        materialized='view',
        schema='staging'
    )
}}

-- Staging model for Daft.ie rental listings
-- Cleans and standardizes all 38 fields from raw listing data

with source as (
    select * from {{ source('raw', 'raw_daft_listings') }}
),

cleaned as (
    select
        -- Identity
        id as raw_id,
        property_id,
        daft_shortcode,

        -- Basic Info
        trim(title) as title,
        trim(seo_title) as seo_title,
        trim(county) as county,
        trim(property_type) as property_type,

        -- Pricing (cleaned and validated)
        price,
        price_raw,
        abbreviated_price,

        -- Property Details
        bedrooms,
        num_bedrooms_raw,
        sections,
        sale_type,
        category,
        state,

        -- Dates (convert Unix timestamp to proper timestamp for publish_date)
        case
            when publish_date is not null
            then to_timestamp(publish_date / 1000.0)
            else null
        end as publish_date,
        date_of_construction,
        scraped_at,

        -- Featured Status
        featured_level,
        featured_level_full,
        coalesce(premier_partner, false) as premier_partner,

        -- Location
        latitude,
        longitude,
        seo_friendly_path,

        -- Seller Info
        seller_id,
        trim(seller_name) as seller_name,
        seller_phone,
        trim(seller_branch) as seller_branch,
        seller_type,
        licence_number,

        -- Media
        total_images,
        coalesce(has_video, false) as has_video,
        coalesce(has_virtual_tour, false) as has_virtual_tour,
        coalesce(has_brochure, false) as has_brochure,

        -- Energy
        upper(trim(ber_rating)) as ber_rating,

        -- PRS
        prs_total_unit_types,
        prs_tagline,

        -- URLs
        property_url,

        -- Metadata
        source,
        created_at,

        -- Calculated fields
        case
            when bedrooms = 0 then 'Studio'
            when bedrooms = 1 then '1 Bed'
            when bedrooms = 2 then '2 Bed'
            when bedrooms = 3 then '3 Bed'
            when bedrooms >= 4 then '4+ Bed'
            else 'Unknown'
        end as bedroom_category,

        -- Price per bedroom (for comparison)
        case
            when bedrooms > 0 then round(price / bedrooms, 2)
            else null
        end as price_per_bedroom,

        -- Data quality flags
        case when price is null or price <= 0 then 1 else 0 end as missing_price_flag,
        case when county is null or county = '' then 1 else 0 end as missing_county_flag,
        case when latitude is null or longitude is null then 1 else 0 end as missing_location_flag,

        -- Geo hash for clustering (if lat/lon available)
        case
            when latitude is not null and longitude is not null
            then concat(
                floor(latitude * 100)::text,
                '_',
                floor(longitude * 100)::text
            )
            else null
        end as location_cluster,

        -- Date extraction from scraped_at
        date(scraped_at) as scrape_date,
        date_trunc('week', scraped_at)::date as scrape_week,
        date_trunc('month', scraped_at)::date as scrape_month,

        -- Metadata
        current_timestamp as dbt_updated_at

    from source

    -- Data quality filters
    where price > 0  -- Filter out invalid prices
        and price < 50000  -- Filter out unrealistic prices (monthly rent)
        and scraped_at is not null
)

select * from cleaned
