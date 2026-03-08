try:
    import streamlit as st
    import streamlit.components.v1 as components
except ImportError:
    class MockSt:
        @staticmethod
        def markdown(*args, **kwargs): pass
    class MockComponents:
        @staticmethod
        def html(*args, **kwargs): pass
    st = MockSt()
    components = MockComponents()


def render_tradingview_widget(ticker, height=800):
    """
    Renders the official TradingView Advanced Chart Widget.
    Completely re-implemented for robustness.
    """
    
    # 1. Symbol Normalization
    tv_symbol = ticker
    # Simple heuristics to ensure we get a valid chart even if user types "BTC"
    if ticker == "BTC": tv_symbol = "BINANCE:BTCUSDT"
    elif ticker == "ETH": tv_symbol = "BINANCE:ETHUSDT"
    elif '-' in ticker and 'USD' in ticker: # Crypto likely
        tv_symbol = "BINANCE:" + ticker.replace('-', '')
    elif '=' in ticker: # Forex likely
        tv_symbol = "FX:" + ticker.replace('=X', '')
    
    # 2. Construct HTML with aggressive CSS for sizing
    # internal container needs to be strictly 100% of the iframe
    html_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body, html {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background-color: #121212; /* Match app background to avoid flashes */
        }}
        .tradingview-widget-container {{
            width: 100%;
            height: 100%;
        }}
    </style>
    </head>
    <body>
    
    <!-- TradingView Widget BEGIN -->
    <div class="tradingview-widget-container">
      <div id="tradingview_123456" style="height:100%;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "autosize": true,
        "symbol": "{tv_symbol}",
        "interval": "D",
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "enable_publishing": false,
        "withdateranges": true,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "details": true,
        "hotlist": true,
        "calendar": true,
        "fullscreen": true,
        "container_id": "tradingview_123456"
      }}
      );
      </script>
    </div>
    <!-- TradingView Widget END -->
    
    </body>
    </html>
    """
    
    # 3. Render Component
    # We use a fixed height passed from app, defaulting to a large 1000px
    components.html(html_code, height=height, width=None, scrolling=False)
