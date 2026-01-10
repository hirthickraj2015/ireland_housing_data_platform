{{
    config(
        materialized='view'
    )
}}

-- Staging model for CSO Rent Index data
-- Standardizes rent index from Central Statistics Office

with source as (
    select * from {{ source('raw', 'raw_cso_rent') }}
),

cleaned as (
    select
        -- Add appropriate columns based on CSO API response structure
        -- This is a template - adjust based on actual data structure

        date_fetched,
        source,
        current_timestamp as dbt_updated_at

    from source
)

select * from cleaned
