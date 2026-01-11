{{
    config(
        materialized='view',
        schema='staging'
    )
}}

-- Staging model for CSO Consumer Price Index data (CPA01)
-- Tracks inflation and price changes over time

with source as (
    select * from {{ source('raw', 'raw_cso_cpi') }}
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

        -- Commodity dimension
        commodity_code,
        trim(commodity_label) as commodity_label,

        -- Categorize commodities for filtering
        case
            when lower(commodity_label) like '%all items%' then 'All Items'
            when lower(commodity_label) like '%housing%' then 'Housing'
            when lower(commodity_label) like '%rent%' then 'Rent'
            when lower(commodity_label) like '%food%' then 'Food'
            when lower(commodity_label) like '%transport%' then 'Transport'
            else 'Other'
        end as commodity_category,

        -- Measure
        unit,
        value as cpi_value,

        -- Metadata
        date_fetched,
        source,
        created_at,

        -- Data quality flags
        case when value is null or value <= 0 then 1 else 0 end as missing_value_flag,

        current_timestamp as dbt_updated_at

    from source

    where year is not null
        and value is not null
        and value > 0
)

select * from cleaned
