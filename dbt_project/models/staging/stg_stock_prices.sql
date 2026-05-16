select
    ticker,
    trade_date,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    ingested_at,
    high_price - low_price                as daily_range,
    (open_price + close_price) / 2.0      as mid_price
from {{ source('staging', 'stock_prices_raw') }}
