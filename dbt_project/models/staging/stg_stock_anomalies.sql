select
    ticker,
    trade_date,
    is_anomaly,
    anomaly_score,
    case
        when is_anomaly then 'ANOMALY'
        else 'NORMAL'
    end as anomaly_label
from {{ source('staging', 'stock_anomalies') }}
