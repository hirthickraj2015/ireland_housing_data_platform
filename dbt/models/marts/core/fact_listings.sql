{{
    config(
        materialized='table',
        schema='marts'
    )
}}

-- Fact table for Daft rental listings
-- Ensures no NULL values for county/province by:
-- 1. Using original county if available
-- 2. Deriving county from lat/long coordinates
-- 3. Defaulting to 'Unknown' if no location info

with listings as (
    select * from {{ ref('stg_daft_listings') }}
),

counties as (
    select * from {{ ref('dim_county') }}
),

-- Derive county from lat/long using approximate bounding boxes for Ireland
listings_with_derived_county as (
    select
        l.*,
        case
            -- If county already exists, use it
            when l.county is not null and l.county != '' then l.county
            -- Derive from lat/long (approximate bounding boxes)
            when l.latitude is not null and l.longitude is not null then
                case
                    -- Dublin: Central and greater Dublin area
                    when l.latitude between 53.2 and 53.5 and l.longitude between -6.5 and -6.0 then 'Dublin'
                    -- Cork: Cork city and county
                    when l.latitude between 51.5 and 52.2 and l.longitude between -10.0 and -8.0 then 'Cork'
                    -- Galway: Galway city and county
                    when l.latitude between 53.0 and 53.6 and l.longitude between -10.0 and -8.0 then 'Galway'
                    -- Limerick
                    when l.latitude between 52.4 and 52.8 and l.longitude between -9.5 and -8.3 then 'Limerick'
                    -- Waterford
                    when l.latitude between 52.0 and 52.4 and l.longitude between -7.5 and -6.8 then 'Waterford'
                    -- Kerry
                    when l.latitude between 51.7 and 52.5 and l.longitude between -10.5 and -9.2 then 'Kerry'
                    -- Clare
                    when l.latitude between 52.5 and 53.2 and l.longitude between -10.0 and -8.3 then 'Clare'
                    -- Wicklow
                    when l.latitude between 52.8 and 53.2 and l.longitude between -6.5 and -6.0 then 'Wicklow'
                    -- Kildare
                    when l.latitude between 53.0 and 53.4 and l.longitude between -7.2 and -6.5 then 'Kildare'
                    -- Meath
                    when l.latitude between 53.4 and 53.9 and l.longitude between -7.2 and -6.2 then 'Meath'
                    -- Louth
                    when l.latitude between 53.7 and 54.1 and l.longitude between -6.8 and -6.0 then 'Louth'
                    -- Wexford
                    when l.latitude between 52.2 and 52.7 and l.longitude between -6.8 and -6.0 then 'Wexford'
                    -- Kilkenny
                    when l.latitude between 52.3 and 52.8 and l.longitude between -7.8 and -7.0 then 'Kilkenny'
                    -- Tipperary
                    when l.latitude between 52.2 and 53.0 and l.longitude between -8.5 and -7.3 then 'Tipperary'
                    -- Mayo
                    when l.latitude between 53.5 and 54.3 and l.longitude between -10.5 and -9.0 then 'Mayo'
                    -- Donegal
                    when l.latitude between 54.3 and 55.5 and l.longitude between -8.5 and -7.0 then 'Donegal'
                    -- Sligo
                    when l.latitude between 53.9 and 54.5 and l.longitude between -9.0 and -8.0 then 'Sligo'
                    -- Default to Unknown if coords don't match known areas
                    else 'Unknown'
                end
            -- No county and no coordinates
            else 'Unknown'
        end as derived_county
    from listings l
),

enriched as (
    select
        -- Surrogate key
        {{ dbt_utils.generate_surrogate_key(['l.property_id', 'l.scrape_date']) }} as listing_key,

        -- Dimensions - always ensure county_key is populated
        coalesce(c.county_key, unk.county_key) as county_key,
        l.scrape_date as date_key,

        -- Property attributes - use derived county (never NULL)
        l.property_id,
        l.daft_shortcode,
        l.title,
        l.derived_county as county,
        coalesce(c.province, 'Unknown') as province,
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
        case when l.county is null or l.county = '' then 1 else 0 end as county_was_derived,
        l.missing_location_flag,

        -- Metadata
        l."source" as data_source,
        current_timestamp as dbt_updated_at

    from listings_with_derived_county l
    left join counties c on l.derived_county = c.county_name
    -- Join to get 'Unknown' county key as fallback
    left join counties unk on unk.county_name = 'Unknown'
)

select * from enriched
