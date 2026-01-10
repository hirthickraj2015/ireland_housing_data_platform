{{
    config(
        materialized='table',
        unique_key='rent_market_key'
    )
}}

-- Fact table for rental market metrics

with listings as (
    select * from {{ ref('stg_daft_listings') }}
),

counties as (
    select * from {{ ref('dim_county') }}
),

aggregated as (
    select
        {{ dbt_utils.surrogate_key(['l.county', 'cast(l.date_scraped as date)', 'l.bedroom_category']) }} as rent_market_key,

        -- Dimensions
        c.county_key,
        cast(l.date_scraped as date) as date_key,
        l.bedroom_category,
        l.property_type,

        -- Metrics
        count(*) as listing_count,
        avg(l.price) as avg_rent,
        min(l.price) as min_rent,
        max(l.price) as max_rent,
        percentile_cont(0.5) within group (order by l.price) as median_rent,

        -- Price per bedroom (for properties with bedrooms)
        case
            when l.bedrooms > 0
            then avg(l.price / nullif(l.bedrooms, 0))
            else null
        end as avg_price_per_bedroom,

        -- Supply indicator
        count(*) as supply_index,

        -- Metadata
        current_timestamp as dbt_updated_at

    from listings l
    left join counties c on l.county = c.county_name
    where l.price is not null
        and l.county is not null
    group by
        c.county_key,
        cast(l.date_scraped as date),
        l.bedroom_category,
        l.property_type,
        l.county,
        l.bedrooms
)

select * from aggregated
