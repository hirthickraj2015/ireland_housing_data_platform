{{
    config(
        materialized='view',
        schema='staging'
    )
}}

-- Staging model for CSO Disposable Income data (CIA01)
-- County-level income statistics for affordability analysis

with source as (
    select * from {{ source('raw', 'raw_cso_income') }}
),

cleaned as (
    select
        -- Identity
        id as raw_id,

        -- Location dimension
        location_code,
        trim(location_label) as location_label,

        -- Standardize location names
        case
            when lower(location_label) = 'state' then 'National'
            when location_label is null or location_label = '-' then 'Unknown'
            else trim(location_label)
        end as county,

        -- Time dimension
        time_period,
        year,

        -- Statistic type
        statistic_code,
        trim(statistic_label) as statistic_label,

        -- Categorize income types
        case
            when lower(statistic_label) like '%compensation of employees%' then 'Wages & Salaries'
            when lower(statistic_label) like '%disposable income%' then 'Disposable Income'
            when lower(statistic_label) like '%gross%' then 'Gross Income'
            else 'Other Income'
        end as income_type,

        -- Measure
        unit,
        value as income_value,

        -- Convert millions to actual value for consistency
        case
            when lower(unit) like '%million%' then value * 1000000
            else value
        end as income_amount,

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
)

select * from cleaned
