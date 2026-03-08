from typing import Protocol, List, Dict, Any, Optional
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime
from src.data_loader import get_mt5_ticker_data

class IDatafeedChartApi(Protocol):
    """
    Pythonic interface mimic of TradingView Datafeed API.
    """
    def get_bars(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        """
        Fetch historical bars.
        Returns DataFrame with columns: ['time', 'open', 'high', 'low', 'close', 'volume']
        Index should be datetime or numeric timestamp.
        """
        ...
        
    def resolve_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Return symbol information.
        """
        ...

class MT5Datafeed:
    """
    Implementation of IDatafeedChartApi for MetaTrader 5.
    """
    def __init__(self):
        pass
        
    def get_bars(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        """
        Fetches bars from MT5 using the existing data loader helper 
        and standardizes columns for TradingView/Lightweight Charts.
        """
        # Clean ticker if needed (e.g. remove prefixes)
        clean_symbol = symbol.split(":")[-1] if ":" in symbol else symbol
        
        # Use existing loader which returns: ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
        df = get_mt5_ticker_data(clean_symbol, timeframe, count=limit)
        
        if df is None or df.empty:
            return pd.DataFrame()
            
        
        # Standardize for Chart
        # Convert 'time' (seconds) to datetime
        df['Date'] = pd.to_datetime(df['time'], unit='s')
        
        # Extremely Robust Column Selection (Handle any source)
        df.columns = [c.capitalize() if c.lower() in ['open','high','low','close','volume'] else c for c in df.columns]
        if 'Volume' not in df.columns and 'Tick_volume' in df.columns:
            df = df.rename(columns={'Tick_volume': 'Volume'})
        
        # Select and reorder
        available_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        # Filter only what exists
        final_cols = [c for c in available_cols if c in df.columns]
        
        output_df = df[final_cols].copy()
        output_df.set_index('Date', inplace=True)
        
        # CRITICAL: Ensure Unique and Sorted Index
        output_df = output_df[~output_df.index.duplicated(keep='last')]
        output_df.sort_index(inplace=True)
        
        return output_df

    def resolve_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Get symbol properties from MT5.
        """
        clean_symbol = symbol.split(":")[-1] if ":" in symbol else symbol
        info = mt5.symbol_info(clean_symbol)
        
        if not info:
            return {"symbol": clean_symbol, "error": "Symbol not found"}
            
        return {
            "symbol": info.name,
            "description": info.description,
            "digits": info.digits,
            "min_move": info.point,
            "currency": info.currency_profit
        }
