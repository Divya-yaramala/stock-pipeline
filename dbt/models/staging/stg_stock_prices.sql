with source as (
    select * from {{ source('raw', 'raw_stock_prices') }}
),

cleaned as (
    select
        ticker::varchar(10)                          as ticker,
        to_date(date::varchar)                       as price_date,
        open::float                                  as open_price,
        high::float                                  as high_price,
        low::float                                   as low_price,
        close::float                                 as close_price,
        volume::bigint                               as volume,
        current_timestamp()                          as loaded_at
    from source
    qualify row_number() over (
        partition by ticker, to_date(date::varchar)
        order by loaded_at desc
    ) = 1
)

select * from cleaned
