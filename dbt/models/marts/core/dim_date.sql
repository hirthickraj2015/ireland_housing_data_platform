{{
    config(
        materialized='table',
        unique_key='date_key',
        schema='marts'
    )
}}

-- Date dimension table for time-based analysis
-- Covers range from 2000 to 2028 for historical and future planning

with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2000-01-01' as date)",
        end_date="cast(date_trunc('year', current_date) + interval '2 years' as date)"
    ) }}
),

date_dimension as (
    select
        date_day as date_key,

        -- Date components
        extract(year from date_day) as year,
        extract(quarter from date_day) as quarter,
        extract(month from date_day) as month,
        extract(day from date_day) as day,
        extract(dow from date_day) as day_of_week,
        extract(doy from date_day) as day_of_year,
        extract(week from date_day) as week_of_year,

        -- Formatted labels
        to_char(date_day, 'Month') as month_name,
        to_char(date_day, 'Mon') as month_name_short,
        to_char(date_day, 'Day') as day_name,
        to_char(date_day, 'Dy') as day_name_short,

        -- Fiscal periods (assume Jan start)
        extract(year from date_day) as fiscal_year,
        extract(quarter from date_day) as fiscal_quarter,

        -- Week/Month/Quarter start dates
        date_trunc('week', date_day)::date as week_start_date,
        date_trunc('month', date_day)::date as month_start_date,
        date_trunc('quarter', date_day)::date as quarter_start_date,
        date_trunc('year', date_day)::date as year_start_date,

        -- Formatted strings
        to_char(date_day, 'YYYY-MM-DD') as date_string,
        to_char(date_day, 'YYYY-MM') as year_month,
        to_char(date_day, 'YYYY-Q') as year_quarter,

        -- Flags
        case when extract(dow from date_day) in (0, 6) then true else false end as is_weekend,
        case when date_day = current_date then true else false end as is_current_day,
        case when extract(day from date_day) = 1 then true else false end as is_first_day_of_month,
        case
            when date_day = (date_trunc('month', date_day) + interval '1 month - 1 day')::date
            then true else false
        end as is_last_day_of_month,

        current_timestamp as dbt_updated_at

    from date_spine
)

select * from date_dimension
