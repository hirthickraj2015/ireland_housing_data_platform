{{
    config(
        materialized='view'
    )
}}

-- Staging model for Daft.ie rental listings
-- Cleans and standardizes raw listing data

with source as (
    select * from {{ source('raw', 'raw_daft_listings') }}
),

cleaned as (
    select
        property_id,
        price,
        title,
        county,
        bedrooms,
        property_type,
        property_url,
        date_scraped,
        source,

        -- Calculated fields
        case
            when bedrooms = 0 then 'Studio'
            when bedrooms = 1 then '1 Bed'
            when bedrooms = 2 then '2 Bed'
            when bedrooms = 3 then '3 Bed'
            when bedrooms >= 4 then '4+ Bed'
            else 'Unknown'
        end as bedroom_category,

        -- Data quality flags
        case when price is null then 1 else 0 end as missing_price_flag,
        case when county is null then 1 else 0 end as missing_county_flag,

        -- Metadata
        current_timestamp as dbt_updated_at

    from source
    where price > 0  -- Filter out invalid prices
        and price < 50000  -- Filter out unrealistic prices
)

select * from cleaned
