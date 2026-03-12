"""
ChartDataManager: Local chart data caching with tick-by-tick updates.
Saves MT5 OHLC data to CSV files locally and keeps them updated in real-time.
"""

import os
import time
import threading
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta

# Default local storage directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "charts")

# MT5 Timeframe mapping
TF_MAP = {
    "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1
}

# UDF resolution string → internal TF key
UDF_TO_TF = {
    "1": "M1", "5": "M5", "15": "M15", "30": "M30",
    "60": "H1", "240": "H4", "D": "D1", "1D": "D1",
    "W": "W1", "1W": "W1"
}

# How many bars to bootstrap on first download
INITIAL_BAR_COUNT = 5000

# Tick update interval per timeframe (seconds)
# Smaller timeframes poll faster for responsiveness
TF_POLL_INTERVAL = {
    "M1": 1.0, "M5": 2.0, "M15": 3.0, "M30": 5.0,
    "H1": 10.0, "H4": 30.0, "D1": 60.0, "W1": 120.0
}


class ChartDataManager:
    """
    Manages local CSV chart data files.
    - Downloads initial history from MT5.
    - Runs a background thread that updates data tick-by-tick.
    - Serves chart data from local files for zero-latency reads.
    """

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)

        self._active_streams = {}   # key: (symbol, tf_key) → thread
        self._stream_flags = {}     # key: (symbol, tf_key) → threading.Event (stop flag)
        self._lock = threading.Lock()
        self._cache = {}            # key: (symbol, tf_key) → pd.DataFrame (in-memory)

    # ── File Path Helpers ──────────────────────────────────────────

    def _file_path(self, symbol, tf_key):
        """Returns the local CSV path for a symbol/timeframe pair."""
        safe_symbol = symbol.replace(" ", "_").replace("/", "_")
        return os.path.join(self.data_dir, f"{safe_symbol}_{tf_key}.csv")

    # ── Core Data Operations ───────────────────────────────────────

    def _download_initial(self, symbol, tf_key):
        """Downloads a full history chunk from MT5 and saves to CSV."""
        mt5_tf = TF_MAP.get(tf_key)
        if mt5_tf is None:
            print(f"[ChartData] Unknown timeframe: {tf_key}")
            return None

        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, INITIAL_BAR_COUNT)
        if rates is None or len(rates) == 0:
            print(f"[ChartData] No data from MT5 for {symbol} {tf_key}")
            return None

        df = pd.DataFrame(rates)
        # Keep time as unix timestamp (int) for consistency
        df = df[['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']]
        df.to_csv(self._file_path(symbol, tf_key), index=False)
        print(f"[ChartData] Saved {len(df)} bars for {symbol} {tf_key}")
        return df

    def _update_latest(self, symbol, tf_key):
        """
        Fetches the latest bars from MT5 and merges them into the local file.
        This handles both updating the current (forming) candle and appending new ones.
        """
        mt5_tf = TF_MAP.get(tf_key)
        if mt5_tf is None:
            return

        # Fetch last 5 bars to handle edge cases (new candle just formed)
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, 5)
        if rates is None or len(rates) == 0:
            return

        new_df = pd.DataFrame(rates)
        new_df = new_df[['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']]

        cache_key = (symbol, tf_key)
        file_path = self._file_path(symbol, tf_key)

        with self._lock:
            # Load from cache or file
            if cache_key in self._cache:
                existing = self._cache[cache_key]
            elif os.path.exists(file_path):
                existing = pd.read_csv(file_path)
            else:
                existing = self._download_initial(symbol, tf_key)
                if existing is not None:
                    self._cache[cache_key] = existing
                return

            if existing is None or existing.empty:
                return

            # Merge: update existing rows by time, append new ones
            existing.set_index('time', inplace=True)
            new_df.set_index('time', inplace=True)

            # Update existing timestamps (current candle's OHLC changes tick-by-tick)
            existing.update(new_df)

            # Append any truly new bars (timestamps not in existing)
            new_timestamps = new_df.index.difference(existing.index)
            if len(new_timestamps) > 0:
                existing = pd.concat([existing, new_df.loc[new_timestamps]])

            existing.sort_index(inplace=True)
            existing.reset_index(inplace=True)

            # Save to file and cache
            existing.to_csv(file_path, index=False)
            self._cache[cache_key] = existing

    # ── Streaming Control ──────────────────────────────────────────

    def start_stream(self, symbol, tf_key):
        """
        Start a background thread that keeps updating local data for a symbol/tf.
        Called when the user opens the chart section.
        """
        key = (symbol, tf_key)

        with self._lock:
            if key in self._active_streams and self._active_streams[key].is_alive():
                print(f"[ChartData] Stream already active for {symbol} {tf_key}")
                return

        # Ensure initial data exists
        file_path = self._file_path(symbol, tf_key)
        if not os.path.exists(file_path):
            self._download_initial(symbol, tf_key)
            # Warm the cache
            if os.path.exists(file_path):
                self._cache[key] = pd.read_csv(file_path)

        stop_event = threading.Event()
        self._stream_flags[key] = stop_event

        thread = threading.Thread(
            target=self._stream_loop,
            args=(symbol, tf_key, stop_event),
            daemon=True
        )
        thread.start()
        self._active_streams[key] = thread
        print(f"[ChartData] Started stream for {symbol} {tf_key}")

    def stop_stream(self, symbol, tf_key):
        """Stop the background update thread for a symbol/tf."""
        key = (symbol, tf_key)
        if key in self._stream_flags:
            self._stream_flags[key].set()
            print(f"[ChartData] Stopped stream for {symbol} {tf_key}")

    def stop_all_streams(self):
        """Stop all active chart data streams."""
        for key in list(self._stream_flags.keys()):
            self._stream_flags[key].set()
        self._active_streams.clear()
        self._stream_flags.clear()
        print("[ChartData] All streams stopped.")

    def _stream_loop(self, symbol, tf_key, stop_event):
        """Background loop: polls MT5 and updates local data at the appropriate interval."""
        interval = TF_POLL_INTERVAL.get(tf_key, 5.0)
        print(f"[ChartData] Stream loop running for {symbol} {tf_key} (interval: {interval}s)")

        while not stop_event.is_set():
            try:
                self._update_latest(symbol, tf_key)
            except Exception as e:
                print(f"[ChartData] Stream error for {symbol} {tf_key}: {e}")
            stop_event.wait(interval)

        print(f"[ChartData] Stream loop exited for {symbol} {tf_key}")

    # ── Data Retrieval (for API endpoints) ─────────────────────────

    def get_chart_data(self, symbol, tf_key, count=500, offset=0):
        """
        Returns OHLC data from the local file for the chart endpoint.
        Falls back to MT5 if local data doesn't exist yet.
        """
        key = (symbol, tf_key)
        file_path = self._file_path(symbol, tf_key)

        with self._lock:
            if key in self._cache:
                df = self._cache[key]
            elif os.path.exists(file_path):
                df = pd.read_csv(file_path)
                self._cache[key] = df
            else:
                # No local data yet — download it now
                df = self._download_initial(symbol, tf_key)
                if df is not None:
                    self._cache[key] = df
                else:
                    return [], False

        if df is None or df.empty:
            return [], False

        # Apply offset and count (offset from the end)
        total = len(df)
        if offset > 0:
            end = total - offset
            start = max(0, end - count)
            sliced = df.iloc[start:end]
        else:
            sliced = df.iloc[-count:]

        has_more = (len(df) > count + offset)

        chart_data = [{
            "time": int(row['time']),
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close'])
        } for _, row in sliced.iterrows()]

        return chart_data, has_more

    def get_udf_history(self, symbol, tf_key, from_ts=None, to_ts=None, countback=None):
        """
        Returns OHLCV data in UDF format from local files.
        Falls back to MT5 if local data doesn't exist yet.
        """
        key = (symbol, tf_key)
        file_path = self._file_path(symbol, tf_key)

        with self._lock:
            if key in self._cache:
                df = self._cache[key].copy()
            elif os.path.exists(file_path):
                df = pd.read_csv(file_path)
                self._cache[key] = df
                df = df.copy()
            else:
                df = self._download_initial(symbol, tf_key)
                if df is not None:
                    self._cache[key] = df
                    df = df.copy()
                else:
                    return {"s": "no_data"}

        if df is None or df.empty:
            return {"s": "no_data"}

        # Filter by time range or countback
        if countback:
            df = df.tail(min(countback, len(df)))
        elif from_ts is not None and to_ts is not None:
            df = df[(df['time'] >= from_ts) & (df['time'] <= to_ts)]

        if df.empty:
            return {"s": "no_data"}

        return {
            "s": "ok",
            "t": df['time'].astype(int).tolist(),
            "o": df['open'].astype(float).tolist(),
            "h": df['high'].astype(float).tolist(),
            "l": df['low'].astype(float).tolist(),
            "c": df['close'].astype(float).tolist(),
            "v": df['tick_volume'].astype(float).tolist()
        }

    def get_active_streams(self):
        """Returns a list of currently active streams for the status API."""
        return [
            {"symbol": sym, "timeframe": tf, "active": thread.is_alive()}
            for (sym, tf), thread in self._active_streams.items()
        ]
