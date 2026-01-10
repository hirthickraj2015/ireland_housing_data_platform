{{
    config(
        materialized='table',
        unique_key='date_key'
    )
}}

-- Date dimension table for time-based analysis

with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2020-01-01' as date)",
        end_date="cast('2030-12-31' as date)"
    ) }}
),

date_details as (
    select
        cast(date_day as date) as date_key,
        date_day,

        -- Date components
        extract(year from date_day) as year,
        extract(quarter from date_day) as quarter,
        extract(month from date_day) as month,
        extract(day from date_day) as day,
        extract(dow from date_day) as day_of_week,
        extract(doy from date_day) as day_of_year,

        -- Month name
        to_char(date_day, 'Month') as month_name,
        to_char(date_day, 'Mon') as month_short_name,

        -- Day name
        to_char(date_day, 'Day') as day_name,
        to_char(date_day, 'Dy') as day_short_name,

        -- Formatted dates
        to_char(date_day, 'YYYY-MM-DD') as date_string,
        to_char(date_day, 'YYYY-MM') as year_month,
        to_char(date_day, 'YYYY-Q') as year_quarter,

        -- Flags
        case when extract(dow from date_day) in (0, 6) then true else false end as is_weekend,

        -- First and last day flags
        case when extract(day from date_day) = 1 then true else false end as is_first_day_of_month,
        case
            when date_day = (date_trunc('month', date_day) + interval '1 month - 1 day')::date
            then true else false
        end as is_last_day_of_month

    from date_spine
)

select * from date_details
