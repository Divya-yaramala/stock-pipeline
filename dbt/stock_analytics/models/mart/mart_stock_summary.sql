{{
  config(
    materialized = 'table',
    schema       = 'mart'
  )
}}

/*
  Final analytics-ready mart table.
  Consumers: dashboards, notebooks, analysts.
*/

with metrics as (
    select * from {{ ref('int_stock_daily_metrics') }}
),

enriched as (
    select
        -- Identity
        symbol,
        date,

        -- OHLCV
        open,
        high,
        low,
        close,
        volume,

        -- Daily metrics
        price_change,
        pct_change,
        daily_range,

        -- Trend indicators
        ma_7d,
        ma_20d,
        ma_50d,

        -- Golden/Death cross flags (price vs moving averages)
        case when close > ma_20d then true else false end as above_ma_20d,
        case when close > ma_50d then true else false end as above_ma_50d,
        case when ma_20d > ma_50d then true else false end as golden_cross,

        -- Volume metrics
        avg_volume_7d,
        relative_volume,

        -- Growth
        cumulative_return_pct,

        -- All-time stats (within the loaded dataset per symbol)
        min(close)   over (partition by symbol) as period_low,
        max(close)   over (partition by symbol) as period_high,
        sum(volume)  over (partition by symbol) as total_volume,
        count(*)     over (partition by symbol) as trading_days_loaded,

        -- Distance from period high/low
        round(
            (close - min(close) over (partition by symbol))
            / nullif(min(close) over (partition by symbol), 0) * 100,
            2
        ) as pct_above_period_low,

        round(
            (close - max(close) over (partition by symbol))
            / nullif(max(close) over (partition by symbol), 0) * 100,
            2
        ) as pct_below_period_high

    from metrics
)

select * from enriched
order by symbol, date
