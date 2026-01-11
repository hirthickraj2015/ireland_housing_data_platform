{{
    config(
        materialized='view',
        schema='staging'
    )
}}

-- Staging model for CSO Rent Index data (RIA02)
-- Standardizes rent index from Central Statistics Office

with source as (
    select * from {{ source('raw', 'raw_cso_rent') }}
),

cleaned as (
    select
        -- Identity
        id as raw_id,
        statistic_code,
        trim(statistic_label) as statistic_label,

        -- Time dimension
        time_period,
        year,

        -- Bedrooms dimension
        bedrooms_code,
        trim(bedrooms_label) as bedrooms_label,

        -- Standardize bedroom labels
        case
            when lower(bedrooms_label) like '%all bedroom%' then 'All Bedrooms'
            when lower(bedrooms_label) like '%studio%' then 'Studio'
            when lower(bedrooms_label) like '%1 bed%' then '1 Bed'
            when lower(bedrooms_label) like '%2 bed%' then '2 Bed'
            when lower(bedrooms_label) like '%3 bed%' then '3 Bed'
            when lower(bedrooms_label) like '%4%bed%' then '4+ Bed'
            else bedrooms_label
        end as bedroom_category,

        -- Property type dimension
        property_type_code,
        trim(property_type_label) as property_type_label,

        case
            when lower(property_type_label) like '%all%' then 'All Property Types'
            when lower(property_type_label) like '%apartment%' then 'Apartment'
            when lower(property_type_label) like '%house%' then 'House'
            else property_type_label
        end as property_type_standardized,

        -- Location dimension
        location_code,
        trim(location_label) as location_label,

        -- Standardize county names (remove codes like "110000")
        case
            when location_label ~ '^\d+$' then null  -- Numeric codes
            when lower(location_label) = 'state' then 'National'
            else trim(location_label)
        end as county,

        -- Measure
        unit,
        value as rent_value,

        -- Metadata
        date_fetched,
        source,
        created_at,

        -- Data quality flags
        case when value is null or value <= 0 then 1 else 0 end as missing_value_flag,
        case when year is null then 1 else 0 end as missing_year_flag,

        current_timestamp as dbt_updated_at

    from source

    where year is not null
        and value is not null
        and value > 0
)

select * from cleaned
