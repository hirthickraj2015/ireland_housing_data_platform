{{
    config(
        materialized='table',
        unique_key='county_key'
    )
}}

-- Dimension table for Irish counties

with counties as (
    select distinct county
    from {{ ref('stg_daft_listings') }}
    where county is not null

    union

    select distinct county
    from {{ source('raw', 'raw_property_sales') }}
    where county is not null
),

numbered as (
    select
        row_number() over (order by county) as county_key,
        county as county_name,

        -- Add county metadata
        case
            when county in ('Dublin', 'Cork', 'Galway', 'Limerick', 'Waterford')
            then 'Urban'
            else 'Rural'
        end as county_type,

        -- Add province
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
        end as province

    from counties
)

select * from numbered
