{{
    config(
        materialized='view'
    )
}}

-- KPI View: Rental Affordability Metrics by County

with rent_data as (
    select
        c.county_name,
        c.province,
        avg(f.avg_rent) as avg_monthly_rent,
        sum(f.listing_count) as total_listings
    from {{ ref('fact_rent_market') }} f
    join {{ ref('dim_county') }} c on f.county_key = c.county_key
    where f.date_key >= current_date - interval '30 days'
    group by c.county_name, c.province
),

-- Placeholder for income data (to be implemented when CSO data structure is known)
income_data as (
    select
        'Dublin' as county_name,
        35000.0 as avg_annual_income
    -- Add actual income data from CSO when available
),

affordability_calc as (
    select
        r.county_name,
        r.province,
        r.avg_monthly_rent,
        r.total_listings as supply_index,

        -- Income metrics (placeholder)
        i.avg_annual_income,
        i.avg_annual_income / 12.0 as avg_monthly_income,

        -- Affordability metrics
        (r.avg_monthly_rent / nullif(i.avg_annual_income / 12.0, 0)) * 100 as rent_to_income_ratio,

        -- Affordability stress score (30% is considered affordable)
        case
            when (r.avg_monthly_rent / nullif(i.avg_annual_income / 12.0, 0)) * 100 < 30 then 'Affordable'
            when (r.avg_monthly_rent / nullif(i.avg_annual_income / 12.0, 0)) * 100 between 30 and 40 then 'Moderate Stress'
            when (r.avg_monthly_rent / nullif(i.avg_annual_income / 12.0, 0)) * 100 > 40 then 'High Stress'
            else 'Unknown'
        end as affordability_category

    from rent_data r
    left join income_data i on r.county_name = i.county_name
)

select * from affordability_calc
order by rent_to_income_ratio desc
