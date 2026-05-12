{{
  config(
    materialized = 'view',
    schema       = 'staging'
  )
}}

with source as (
    select * from {{ source('raw', 'stock_prices') }}
),

ranked as (
    select
        symbol,
        date,
        round(open::numeric,  4) as open,
        round(high::numeric,  4) as high,
        round(low::numeric,   4) as low,
        round(close::numeric, 4) as close,
        volume,
        s3_key,
        _loaded_at,
        -- Deduplicate: keep the most recently loaded record per symbol/date
        row_number() over (
            partition by symbol, date
            order by _loaded_at desc
        ) as row_num
    from source
    where
        close is not null
        and close > 0
        and date  is not null
),

cleaned as (
    select
        symbol,
        date,
        open,
        high,
        low,
        close,
        volume,
        s3_key,
        _loaded_at
    from ranked
    where row_num = 1
)

select * from cleaned
