select
    p.ticker,
    p.trade_date,
    p.open_price,
    p.high_price,
    p.low_price,
    p.close_price,
    p.volume,
    p.daily_range,
    p.mid_price,
    a.is_anomaly,
    a.anomaly_label,
    round(
        (
            p.close_price
            - lag(p.close_price) over (partition by p.ticker order by p.trade_date)
        )
        / nullif(
            lag(p.close_price) over (partition by p.ticker order by p.trade_date),
            0
        ) * 100,
        2
    ) as daily_return_pct
from {{ ref('stg_stock_prices') }} p
left join {{ ref('stg_stock_anomalies') }} a
    on  p.ticker     = a.ticker
    and p.trade_date = a.trade_date
