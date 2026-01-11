{{
    config(
        materialized='incremental',
        unique_key='cso_rent_key',
        schema='marts',
        on_schema_change='sync_all_columns'
    )
}}

-- Incremental fact table for CSO official rent statistics
-- Provides authoritative government rent data for validation

with cso_rent as (
    select * from {{ ref('stg_cso_rent') }}

    {% if is_incremental() %}
    where year > (select max(year) from {{ this }})
    {% endif %}
),

counties as (
    select * from {{ ref('dim_county') }}
),

enriched as (
    select
        -- Surrogate key
        {{ dbt_utils.generate_surrogate_key(['r.county', 'r.year', 'r.bedroom_category', 'r.property_type_standardized']) }} as cso_rent_key,

        -- Dimensions
        c.county_key,
        r.year,
        r.bedroom_category,
        r.property_type_standardized as property_type,
        r.county,

        -- Metrics
        r.rent_value as official_avg_rent,

        -- Original fields for reference
        r.statistic_label,
        r.bedrooms_label,
        r.property_type_label,
        r.location_label,

        -- Metadata
        r.source,
        r.date_fetched,
        current_timestamp as dbt_updated_at

    from cso_rent r
    left join counties c on r.county = c.county_name
    where r.county is not null
)

select * from enriched
