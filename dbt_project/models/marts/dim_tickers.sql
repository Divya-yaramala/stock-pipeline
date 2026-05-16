select *
from (
    values
        ('AAPL',  'Apple Inc.',            'Technology',        'NASDAQ'),
        ('MSFT',  'Microsoft Corporation', 'Technology',        'NASDAQ'),
        ('GOOGL', 'Alphabet Inc.',         'Technology',        'NASDAQ'),
        ('AMZN',  'Amazon.com Inc.',       'Consumer Cyclical', 'NASDAQ'),
        ('TSLA',  'Tesla Inc.',            'Automotive',        'NASDAQ')
) as t(ticker, company_name, sector, exchange)
