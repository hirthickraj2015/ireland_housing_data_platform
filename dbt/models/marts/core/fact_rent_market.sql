{{
    config(
        materialized='incremental',
        unique_key='rent_market_key',
        schema='marts',
        on_schema_change='sync_all_columns'
    )
}}

-- Incremental fact table for rental market aggregated metrics
-- Combines Daft listings aggregated by county, date, bedroom, property type

with listings as (
    select * from {{ ref('stg_daft_listings') }}

    {% if is_incremental() %}
    where scrape_date > (select max(date_key) from {{ this }})
    {% endif %}
),

counties as (
    select * from {{ ref('dim_county') }}
),

-- Aggregate Daft listings
daft_aggregated as (
    select
        {{ dbt_utils.generate_surrogate_key(['l.county', 'l.scrape_date', 'l.bedroom_category', 'l.property_type']) }} as rent_market_key,

        -- Dimensions
        c.county_key,
        l.scrape_date as date_key,
        l.bedroom_category,
        l.property_type,
        l.county,

        -- Metrics from Daft
        count(*) as listing_count,
        avg(l.price) as avg_rent,
        min(l.price) as min_rent,
        max(l.price) as max_rent,
        percentile_cont(0.5) within group (order by l.price) as median_rent,
        percentile_cont(0.25) within group (order by l.price) as p25_rent,
        percentile_cont(0.75) within group (order by l.price) as p75_rent,

        -- Price per bedroom
        avg(l.price_per_bedroom) as avg_price_per_bedroom,

        -- Supply indicator
        count(*) as supply_index,

        -- Premium listings
        sum(case when l.featured_level is not null then 1 else 0 end) as featured_listings_count,

        -- PRS share
        sum(case when l.prs_total_unit_types is not null then 1 else 0 end) as prs_listings_count,
        round(100.0 * sum(case when l.prs_total_unit_types is not null then 1 else 0 end) / nullif(count(*), 0), 2) as prs_percentage,

        -- Energy efficiency
        avg(case
            when l.ber_rating in ('A1', 'A2', 'A3') then 4
            when l.ber_rating in ('B1', 'B2', 'B3') then 3
            when l.ber_rating in ('C1', 'C2', 'C3') then 2
            else 1
        end) as avg_ber_score,

        -- Data source
        'daft.ie' as data_source,
        current_timestamp as dbt_updated_at

    from listings l
    left join counties c on l.county = c.county_name
    where l.price is not null
        and l.county is not null
    group by
        c.county_key,
        l.scrape_date,
        l.bedroom_category,
        l.property_type,
        l.county
)

select * from daft_aggregated
