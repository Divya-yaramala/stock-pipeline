{{
  config(
    materialized = 'table',
    schema       = 'intermediate'
  )
}}

with base as (
    select * from {{ ref('stg_stock_prices') }}
),

with_metrics as (
    select
        symbol,
        date,
        open,
        high,
        low,
        close,
        volume,

        -- Daily price movement
        round(
            close - lag(close) over (partition by symbol order by date),
            4
        ) as price_change,

        round(
            (close - lag(close) over (partition by symbol order by date))
            / nullif(lag(close) over (partition by symbol order by date), 0) * 100,
            4
        ) as pct_change,

        -- Intraday range
        round(high - low, 4) as daily_range,

        -- Moving averages (price)
        round(
            avg(close) over (
                partition by symbol
                order by date
                rows between 6 preceding and current row
            ), 4
        ) as ma_7d,

        round(
            avg(close) over (
                partition by symbol
                order by date
                rows between 19 preceding and current row
            ), 4
        ) as ma_20d,

        round(
            avg(close) over (
                partition by symbol
                order by date
                rows between 49 preceding and current row
            ), 4
        ) as ma_50d,

        -- Moving average (volume)
        round(
            avg(volume) over (
                partition by symbol
                order by date
                rows between 6 preceding and current row
            )
        ) as avg_volume_7d,

        -- Relative volume (current vs 7-day average)
        round(
            volume::numeric / nullif(
                avg(volume) over (
                    partition by symbol
                    order by date
                    rows between 7 preceding and 1 preceding
                ),
            0), 2
        ) as relative_volume,

        -- Cumulative return from first available date per symbol
        round(
            (close - first_value(close) over (partition by symbol order by date))
            / nullif(first_value(close) over (partition by symbol order by date), 0) * 100,
            4
        ) as cumulative_return_pct

    from base
)

select * from with_metrics
