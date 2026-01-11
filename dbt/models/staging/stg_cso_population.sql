{{
    config(
        materialized='view',
        schema='staging'
    )
}}

-- Staging model for CSO Population data (PEA01)
-- Annual population estimates by age group and sex

with source as (
    select * from {{ source('raw', 'raw_cso_population') }}
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

        -- Age group dimension
        age_group_code,
        trim(age_group_label) as age_group_label,

        -- Classify into broad age bands
        case
            when age_group_label ~ 'Under|0 -|1-4' then '0-14'
            when age_group_label ~ '15-|20-|25-|30-35' then '15-34'
            when age_group_label ~ '35-|40-|45-|50-54' then '35-54'
            when age_group_label ~ '55-|60-64' then '55-64'
            when age_group_label ~ '65|70|75|80|85' then '65+'
            else 'All Ages'
        end as age_band,

        -- Sex dimension
        sex_code,
        trim(sex_label) as sex_label,

        -- Measure
        unit,
        value as population_value,

        -- Convert thousands to actual count
        case
            when lower(unit) like '%thousand%' then value * 1000
            else value
        end as population_count,

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
