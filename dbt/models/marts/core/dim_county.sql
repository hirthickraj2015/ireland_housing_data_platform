{{
    config(
        materialized='table',
        unique_key='county_key',
        schema='marts'
    )
}}

-- Dimension table for Irish counties
-- Full refresh on each run to capture new counties from all sources

with daft_counties as (
    select distinct county
    from {{ ref('stg_daft_listings') }}
    where county is not null
        and county != ''
),

cso_rent_counties as (
    select distinct county
    from {{ ref('stg_cso_rent') }}
    where county is not null
        and county not in ('National', 'Unknown')
),

cso_income_counties as (
    select distinct county
    from {{ ref('stg_cso_income') }}
    where county is not null
        and county not in ('National', 'Unknown')
),

all_counties as (
    select county from daft_counties
    union
    select county from cso_rent_counties
    union
    select county from cso_income_counties
),

numbered as (
    select
        row_number() over (order by county) as county_key,
        county as county_name,

        -- County metadata
        case
            when county in ('Dublin', 'Cork', 'Galway', 'Limerick', 'Waterford')
            then 'Urban'
            else 'Rural'
        end as county_type,

        -- Province mapping
        case
            when county in ('Dublin', 'Kildare', 'Meath', 'Louth', 'Wicklow',
                           'Wexford', 'Carlow', 'Kilkenny', 'Laois', 'Offaly',
                           'Westmeath', 'Longford')
            then 'Leinster'
            when county in ('Cork', 'Clare', 'Kerry', 'Limerick', 'Tipperary', 'Waterford')
            then 'Munster'
            when county in ('Galway', 'Mayo', 'Roscommon', 'Sligo', 'Leitrim')
            then 'Connacht'
            when county in ('Donegal', 'Cavan', 'Monaghan')
            then 'Ulster'
            else 'Unknown'
        end as province,

        -- Housing market tier
        case
            when county = 'Dublin' then 'Tier 1'
            when county in ('Cork', 'Galway', 'Limerick', 'Waterford') then 'Tier 2'
            else 'Tier 3'
        end as market_tier,

        current_timestamp as dbt_updated_at

    from all_counties
)

select * from numbered
