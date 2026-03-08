# Common tickers for the dashboard

TICKERS = {
    "Indices & ETFs": [
        "SPY", "QQQ", "DIA", "IWM", "VTI", "VOO", "GLD", "SLV", "TLT", "UVXY"
    ],
    "Top US Stocks": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "INTC", 
        "NFLX", "DIS", "JPM", "BAC", "WMT", "KO", "PEP", "XOM", "CVX", "PFE"
    ],
    "Crypto": [
        "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "SOL-USD", "ADA-USD", 
        "DOGE-USD", "SHIB-USD", "DOT-USD", "MATIC-USD", "LTC-USD"
    ],
    "Forex": [
        "EURUSD=X", "JPY=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X", 
        "EURJPY=X", "GBPJPY=X"
    ]
}

# Flattened list for easy searching if needed
ALL_TICKERS = [t for category in TICKERS.values() for t in category]
