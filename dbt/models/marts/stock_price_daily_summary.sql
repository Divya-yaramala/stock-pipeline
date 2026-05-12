with stg as (
    select * from {{ ref('stg_stock_prices') }}
),

summary as (
    select
        ticker,
        price_date,
        open_price,
        close_price,
        high_price,
        low_price,
        volume,
        round(
            (close_price - open_price) / nullif(open_price, 0) * 100,
            4
        )                                            as daily_return_pct,
        close_price - open_price                     as price_change,
        lag(close_price) over (
            partition by ticker order by price_date
        )                                            as prev_close_price
    from stg
)

select * from summary
