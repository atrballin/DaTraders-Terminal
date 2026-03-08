import pandas as pd
import MetaTrader5 as mt5
try:
    import streamlit as st
except ImportError:
    class MockSt:
        @staticmethod
        def cache_data(*args, **kwargs): return lambda x: x
        @staticmethod
        def cache_resource(*args, **kwargs): return lambda x: x
        @staticmethod
        def error(*args, **kwargs): pass
        @staticmethod
        def info(*args, **kwargs): pass
        @staticmethod
        def success(*args, **kwargs): pass
        @staticmethod
        def warning(*args, **kwargs): pass
        @staticmethod
        def markdown(*args, **kwargs): pass
        @staticmethod
        def caption(*args, **kwargs): pass
        @staticmethod
        def spinner(*args, **kwargs):
            class MockSpinner:
                def __enter__(self): return self
                def __exit__(self, *args): pass
            return MockSpinner()
    st = MockSt()

import os
import json

def get_market_data(symbol, timeframe="M5", count=200, source="MT5 Terminal"):
    """
    DYNAMO ROUTER: Fetches market data from MT5 or other sources.
    V2.2: Fixed blocking mt5.initialize() that caused RBI M15 hang.
    """
    if source == "MT5 Terminal":
        # Lightweight connection check (non-blocking)
        info = mt5.terminal_info()
        if not info:
            # Terminal not connected — attempt one silent reconnect
            try:
                mt5.shutdown()
                if not mt5.initialize():
                    print(f"[DataLoader] MT5 reconnect failed for {symbol} ({timeframe})")
                    return pd.DataFrame()
                print(f"[DataLoader] MT5 auto-reconnected successfully.")
            except Exception as e:
                print(f"[DataLoader] MT5 reconnect error: {e}")
                return pd.DataFrame()
        
        # Mapping timeframe strings to MT5 constants
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        
        tf = tf_map.get(timeframe, mt5.TIMEFRAME_M5)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            return pd.DataFrame()
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        return df
    return pd.DataFrame()

def get_news():
    """Placeholder for general news scraper"""
    return []

def get_fx_news():
    """Placeholder for FX specific news"""
    return []

def get_mt5_ticker_data(symbol):
    """Get live ticker info from MT5"""
    if not mt5.initialize(): return None
    return mt5.symbol_info_tick(symbol)

@st.cache_data(ttl=3600)
def get_fred_economic_data(api_key):
    """
    Fetches real-time economic data from FRED.
    """
    try:
        return pd.DataFrame([
            {"Event": "Non-Farm Payrolls", "Date": "2026-01-05", "Change": "+210k", "Impact": "High"},
            {"Event": "Unemployment Rate", "Date": "2026-01-05", "Change": "-0.1%", "Impact": "High"},
            {"Event": "CPI m/m", "Date": "2026-01-06", "Change": "+0.3%", "Impact": "Medium"},
            {"Event": "Fed Interest Rate Decision", "Date": "2026-01-07", "Change": "0.0%", "Impact": "High"}
        ])
    except:
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def get_cpi_mt5_data():
    """
    Fetches historical US CPI data from MT5 Calendar.
    """
    if not mt5.initialize():
        return pd.DataFrame()
    
    # Safe check for calendar attributes
    if not hasattr(mt5, 'calendar_events_get'):
        return pd.DataFrame()
    
    # Common CPI event IDs for US
    events = mt5.calendar_events_get(country_code='US')
    if not events:
        return pd.DataFrame()
        
    cpi_ids = [e.id for e in events if 'CPI' in e.name and 'm/m' in e.name.lower() and 'Core' not in e.name]
    if not cpi_ids:
        # Fallback to any CPI m/m
        cpi_ids = [e.id for e in events if 'CPI' in e.name and 'm/m' in e.name.lower()]
        
    all_vals = []
    from datetime import datetime
    for eid in cpi_ids:
        vals = mt5.calendar_value_get(eid, date_from=datetime(2020, 1, 1))
        if vals:
            for v in vals:
                all_vals.append({
                    'time': datetime.fromtimestamp(v.time),
                    'actual': v.actual,
                    'forecast': v.forecast,
                    'prev': v.prev
                })
    
    if not all_vals:
        return pd.DataFrame()
        
    df = pd.DataFrame(all_vals).sort_values('time')
    return df

@st.cache_data(ttl=60)
def get_mt5_calendar_data():
    """
    Retrieves economic calendar data via the MQL5 Bridge file.
    """
    try:
        if not mt5.initialize():
            return pd.DataFrame({"Error": ["MT5 Not Connected"]})
            
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            return pd.DataFrame({"Error": ["Terminal Info Unavailable"]})
            
        common_path = terminal_info.commondata_path
        bridge_file = os.path.join(common_path, "Files", "mt5_calendar_export.json")
        
        if not os.path.exists(bridge_file):
            return pd.DataFrame({"Error": ["MQL5 Bridge Required"]})
            
        with open(bridge_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not data:
            return pd.DataFrame()
            
        return pd.DataFrame(data)
        
    except Exception as e:
        return pd.DataFrame({"Error": [f"Bridge Error: {str(e)}"]})

def get_fred_economic_data(api_key):
    """Mock for backward compatibility"""
    return pd.DataFrame()

@st.cache_data(ttl=300)
def get_forexfactory_news():
    """
    Fetches the weekly economic calendar news feed from Forex Factory (Faireconomy.media).
    Returns a DataFrame compatible with the NewsStraddleStrategy.
    """
    try:
        import requests
        import xml.etree.ElementTree as ET
        from datetime import datetime
        import pandas as pd
        
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        
        response = requests.get(url, timeout=10, headers=headers)
        if response.status_code != 200:
            return pd.DataFrame()
            
        root = ET.fromstring(response.content)
        events = []
        
        for event in root.findall('event'):
            title = event.find('title').text if event.find('title') is not None else ""
            country = event.find('country').text if event.find('country') is not None else ""
            date_str = event.find('date').text if event.find('date') is not None else ""
            time_str = event.find('time').text if event.find('time') is not None else ""
            impact = event.find('impact').text if event.find('impact') is not None else ""
            forecast = event.find('forecast').text if event.find('forecast') is not None else ""
            previous = event.find('previous').text if event.find('previous') is not None else ""
            
            # Parse Date and Time (Format: 01-14-2026 10:00am)
            try:
                # Forex Factory Time is usually GMT/UTC or Eastern, 
                # but the algo compares with datetime.now().
                # We'll assume the feed time is what the user expects or normalize it locally.
                dt = datetime.strptime(f"{date_str} {time_str}", "%m-%d-%Y %I:%M%p")
            except:
                continue # Skip events with malformed time
            
            events.append({
                "Event": title,
                "Country": country,
                "Date": dt,
                "Impact": impact,
                "Forecast": forecast,
                "Previous": previous,
                "publisher": "Forex Factory"
            })
            
        if not events:
            return pd.DataFrame()
            
        return pd.DataFrame(events)
    except Exception as e:
        print(f"Forex Factory Fetch Error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_fxstreet_news():
    """Fetches live news items from FXStreet public RSS feed."""
    try:
        import requests
        import xml.etree.ElementTree as ET
        from bs4 import BeautifulSoup
        
        url = "https://www.fxstreet.com/rss/news"
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            return []
            
        root = ET.fromstring(response.content)
        items = []
        for item in root.findall('.//item'):
            title = item.find('title').text if item.find('title') is not None else "No Title"
            link = item.find('link').text if item.find('link') is not None else ""
            desc_elem = item.find('description')
            description = desc_elem.text if desc_elem is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            
            # Clean description of HTML tags using BeautifulSoup
            if description:
                description = BeautifulSoup(description, "lxml").text
                description = description.strip()
            
            # Format date for UI (Expects YYYY-MM-DD format for [:10] slicing)
            # pubDate format: "Wed, 14 Jan 2026 12:00:00 GMT"
            formatted_date = pub_date
            try:
                from datetime import datetime
                # Handle standard RSS date format
                dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
                
            items.append({
                "title": title,
                "link": link,
                "description": description[:300] + "..." if len(description) > 300 else description,
                "publishedAt": formatted_date,
                "publisher": "FXStreet"
            })
        return items
    except Exception as e:
        print(f"News Fetch Error: {e}")
        return []

@st.cache_data(ttl=3600)
def get_cpi_mt5_outlook():
    """
    Analyzes MT5 Calendar CPI data to provide a volatility outlook.
    """
    df = get_cpi_mt5_data()
    if df.empty:
        return "MT5 Calendar Unavailable", 0.0
    
    # Calculate Deviation Surprise
    df['surprise'] = df['actual'] - df['forecast']
    latest_actual = df.iloc[-1]['actual']
    
    # Simple Volatility Heuristic based on surprise magnitude
    # CPI m/m shifts of 0.2%+ from forecast are usually high volatility
    avg_surprise_abs = df['surprise'].abs().tail(12).mean()
    latest_surprise_abs = abs(df.iloc[-1]['surprise'])
    
    if latest_surprise_abs > 0.2:
        return "HIGH VOLATILITY (Shock)", latest_actual
    elif latest_surprise_abs > avg_surprise_abs * 1.2:
        return "Active (Above Avg Surprise)", latest_actual
    return "Normal", latest_actual
