select
    p.ticker,
    p.trade_date,
    p.open_price,
    p.high_price,
    p.low_price,
    p.close_price,
    p.volume,
    p.daily_return_pct,
    p.is_anomaly,
    p.anomaly_label,
    pred.predicted_close,
    pred.lower_bound,
    pred.upper_bound,
    ins.insight_text
from {{ ref('fct_stock_prices') }} p
left join {{ source('staging', 'stock_predictions') }} pred
    on  p.ticker     = pred.ticker
    and p.trade_date = pred.trade_date
left join {{ source('staging', 'stock_insights') }} ins
    on  p.ticker     = ins.ticker
    and p.trade_date = ins.trade_date
