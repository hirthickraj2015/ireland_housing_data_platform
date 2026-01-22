{{
    config(
        materialized='table',
        schema='marts'
    )
}}

-- Fact table for Daft rental listings

with listings as (
    select * from {{ ref('stg_daft_listings') }}
),

counties as (
    select * from {{ ref('dim_county') }}
),

enriched as (
    select
        -- Surrogate key
        {{ dbt_utils.generate_surrogate_key(['l.property_id', 'l.scrape_date']) }} as listing_key,

        -- Dimensions
        c.county_key,
        l.scrape_date as date_key,

        -- Property attributes
        l.property_id,
        l.daft_shortcode,
        l.title,
        l.county,
        l.property_type,
        l.bedrooms,
        l.bedroom_category,

        -- Pricing
        l.price,
        l.price_per_bedroom,
        l.abbreviated_price,

        -- Location
        l.latitude,
        l.longitude,
        l.location_cluster,

        -- Dates
        l.publish_date,
        l.date_of_construction,
        l.scraped_at,

        -- Seller
        l.seller_id,
        l.seller_name,
        l.seller_type,
        l.seller_branch,

        -- Media richness score (0-4)
        (case when l.has_video then 1 else 0 end +
         case when l.has_virtual_tour then 1 else 0 end +
         case when l.has_brochure then 1 else 0 end +
         case when l.total_images > 5 then 1 else 0 end) as media_richness_score,

        l.total_images,
        l.has_video,
        l.has_virtual_tour,
        l.has_brochure,

        -- Energy
        l.ber_rating,
        case
            when l.ber_rating in ('A1', 'A2', 'A3') then 'High Efficiency'
            when l.ber_rating in ('B1', 'B2', 'B3') then 'Good Efficiency'
            when l.ber_rating in ('C1', 'C2', 'C3') then 'Average Efficiency'
            else 'Low Efficiency'
        end as ber_category,

        -- Featured/PRS
        l.featured_level,
        l.premier_partner,
        l.prs_total_unit_types,
        case when l.prs_total_unit_types is not null then true else false end as is_prs,

        -- State
        l.state,
        case when l.state = 'PUBLISHED' then true else false end as is_active,

        -- URL
        l.property_url,

        -- Quality flags
        l.missing_price_flag,
        l.missing_county_flag,
        l.missing_location_flag,

        -- Metadata
        l."source" as data_source,
        current_timestamp as dbt_updated_at

    from listings l
    left join counties c on l.county = c.county_name
)

select * from enriched
