{{
    config(
        materialized='table',
        unique_key='county_key',
        schema='marts'
    )
}}

-- Dimension table for Irish counties
-- Includes 'Unknown' for listings without county information

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
    union
    -- Always include 'Unknown' for listings without county
    select 'Unknown' as county
),

numbered as (
    select
        row_number() over (order by case when county = 'Unknown' then 1 else 0 end, county) as county_key,
        county as county_name,

        -- County metadata
        case
            when county in ('Dublin', 'Cork', 'Galway', 'Limerick', 'Waterford')
            then 'Urban'
            when county = 'Unknown' then 'Unknown'
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
            when county = 'Unknown' then 'Unknown'
            else 'Tier 3'
        end as market_tier,

        -- Is this a commuter belt county (within ~50km of Dublin)
        case
            when county in ('Kildare', 'Meath', 'Wicklow', 'Louth')
            then true
            else false
        end as is_commuter_belt,

        current_timestamp as dbt_updated_at

    from all_counties
)

select * from numbered
