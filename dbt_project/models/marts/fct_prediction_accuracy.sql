with prices_with_prev as (
    select
        ticker,
        trade_date,
        close_price,
        lag(close_price) over (
            partition by ticker order by trade_date
        ) as prev_close
    from {{ ref('stg_stock_prices') }}
)

select
    pred.ticker,
    pred.trade_date,
    pred.predicted_close,
    p.close_price                                           as actual_close,
    round((pred.predicted_close - p.close_price)::numeric, 4)
                                                            as prediction_error,
    round(
        (pred.predicted_close - p.close_price)
        / nullif(p.close_price, 0) * 100,
        2
    )                                                       as prediction_error_pct,
    case
        when sign(pred.predicted_close - p.prev_close)
           = sign(p.close_price - p.prev_close)
        then true
        else false
    end                                                     as direction_correct
from {{ source('staging', 'stock_predictions') }} pred
inner join prices_with_prev p
    on  pred.ticker     = p.ticker
    and pred.trade_date = p.trade_date
