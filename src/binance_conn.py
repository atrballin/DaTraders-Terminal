import requests
import pandas as pd

def fetch_crypto_data(symbol="BTCUSDT", interval="5m", limit=100):
    """
    Robust fetch for Crypto Data. 
    Tries Binance Vision API first, then yfinance.
    """
    # 1. Try Binance Vision (Public, no auth)
    try:
        url = "https://data-api.binance.vision/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        r = requests.get(url, params=params, timeout=3)
        if r.status_code == 200:
            data = r.json()
            df = pd.DataFrame(data, columns=["open_time", "open", "high", "low", "close", "volume", "close_time", "v1", "c1", "b1", "b2", "i"])
            df["time"] = pd.to_datetime(df["open_time"], unit="ms")
            for c in ["open", "high", "low", "close", "volume"]: df[c] = df[c].astype(float)
            return df[["time", "open", "high", "low", "close", "volume"]]
    except:
        pass
        
    # 2. Fallback to yfinance
    try:
        import yfinance as yf
        y_sym = symbol.replace("USDT", "-USD") # BTCUSDT -> BTC-USD
        df = yf.download(y_sym, period="2d", interval=interval, progress=False)
        if not df.empty:
            df = df.reset_index()
            # Handle MultiIndex columns
            new_cols = []
            for c in df.columns:
                if isinstance(c, tuple):
                    new_cols.append(c[0].lower() if c[0] else "")
                else:
                    new_cols.append(str(c).lower())
            df.columns = new_cols
            
            if "datetime" in df.columns: df = df.rename(columns={"datetime": "time"})
            elif "date" in df.columns: df = df.rename(columns={"date": "time"})
            return df
    except Exception as e:
        print(f"Crypto Data Error: {e}")
        return None
    
    return None
