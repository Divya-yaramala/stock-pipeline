select
    ticker,
    count(*)                                            as total_days_analyzed,
    sum(case when is_anomaly then 1 else 0 end)         as total_anomalies,
    round(
        sum(case when is_anomaly then 1 else 0 end)::numeric
        / nullif(count(*), 0) * 100,
        2
    )                                                   as anomaly_rate_pct,
    max(case when is_anomaly then trade_date end)       as last_anomaly_date,
    round(avg(anomaly_score)::numeric, 4)               as avg_anomaly_score
from {{ ref('stg_stock_anomalies') }}
group by ticker
