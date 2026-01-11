{{
    config(
        materialized='view',
        schema='analytics'
    )
}}

-- Rental affordability KPIs combining market data, income, and CPI
-- Provides comprehensive affordability metrics for Power BI

with recent_rents as (
    select
        county_key,
        county,
        bedroom_category,
        date_key,
        avg_rent,
        median_rent,
        supply_index,
        listing_count
    from {{ ref('fact_rent_market') }}
    where date_key >= current_date - interval '90 days'
),

-- Get most recent month's average rent by county and bedroom
latest_month_rents as (
    select
        county_key,
        county,
        bedroom_category,
        max(date_key) as latest_date,
        avg(avg_rent) as current_avg_rent,
        avg(median_rent) as current_median_rent,
        sum(listing_count) as total_listings
    from recent_rents
    group by county_key, county, bedroom_category
),

-- Compare to same period last year
year_ago_rents as (
    select
        county,
        bedroom_category,
        avg(avg_rent) as yoy_avg_rent
    from {{ ref('fact_rent_market') }}
    where date_key between current_date - interval '15 months' and current_date - interval '12 months'
    group by county, bedroom_category
),

-- Get latest income data by county
latest_income as (
    select
        county,
        max(year) as latest_year,
        avg(income_amount) as avg_income
    from {{ ref('stg_cso_income') }}
    where income_type = 'Disposable Income'
        and county != 'National'
    group by county
),

-- Get CPI for housing
latest_cpi as (
    select
        max(year) as latest_year,
        avg(cpi_value) as housing_cpi
    from {{ ref('stg_cso_cpi') }}
    where commodity_category = 'Housing'
),

-- Get CSO official rent data for validation
cso_official_rent as (
    select
        county,
        max(year) as latest_year,
        avg(official_avg_rent) as cso_avg_rent
    from {{ ref('fact_cso_rent') }}
    where bedroom_category = 'All Bedrooms'
        and property_type = 'All Property Types'
    group by county
),

-- Combine all metrics
affordability_metrics as (
    select
        r.county_key,
        r.county,
        r.bedroom_category,
        r.latest_date,

        -- Current rent metrics
        round(r.current_avg_rent::numeric, 2) as current_avg_rent,
        round(r.current_median_rent::numeric, 2) as current_median_rent,
        r.total_listings,

        -- Year-over-year comparison
        round(y.yoy_avg_rent::numeric, 2) as yoy_avg_rent,
        round((((r.current_avg_rent - y.yoy_avg_rent) / nullif(y.yoy_avg_rent, 0)) * 100)::numeric, 2) as yoy_rent_growth_pct,

        -- CSO official comparison
        round(cso.cso_avg_rent::numeric, 2) as cso_official_rent,
        cso.latest_year as cso_rent_year,

        -- Annual rent (for affordability calculation)
        round(r.current_avg_rent * 12, 2) as annual_rent,

        -- Income metrics (if available)
        round((i.avg_income / 1000000)::numeric, 2) as avg_disposable_income_millions,
        i.latest_year as income_year,

        -- Affordability ratio (annual rent as % of annual income)
        -- Note: CSO income is aggregate, need per capita adjustment
        case
            when i.avg_income is not null then
                round((((r.current_avg_rent * 12) / (i.avg_income / 1000)) * 100)::numeric, 2)
            else null
        end as rent_to_income_ratio_pct,

        -- Affordability stress score (higher = less affordable)
        case
            when ((r.current_avg_rent * 12) / nullif(i.avg_income / 1000, 0)) > 0.35 then 'High Stress'
            when ((r.current_avg_rent * 12) / nullif(i.avg_income / 1000, 0)) > 0.25 then 'Moderate Stress'
            when ((r.current_avg_rent * 12) / nullif(i.avg_income / 1000, 0)) > 0.15 then 'Low Stress'
            else 'Affordable'
        end as affordability_category,

        -- CPI context
        round(c.housing_cpi::numeric, 2) as housing_cpi,
        c.latest_year as cpi_year,

        current_timestamp as dbt_updated_at

    from latest_month_rents r
    left join year_ago_rents y
        on r.county = y.county
        and r.bedroom_category = y.bedroom_category
    left join latest_income i
        on r.county = i.county
    left join cso_official_rent cso
        on r.county = cso.county
    cross join latest_cpi c
)

select * from affordability_metrics
order by rent_to_income_ratio_pct desc nulls last
