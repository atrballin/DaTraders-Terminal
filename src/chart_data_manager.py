"""
ChartDataManager: Local chart data caching with tick-by-tick updates.
Saves MT5 OHLC data to JSON files locally and keeps them updated in real-time.
"""

import os
import json
import threading
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
    Manages local JSON chart data files.
    - Downloads initial history from MT5.
    - Runs a background thread that updates data tick-by-tick.
    - Serves chart data from local files for zero-latency reads.
    - Broadcasts live updates via callbacks.
    """

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)

        self._active_streams = {}   # key: (symbol, tf_key) → thread
        self._stream_flags = {}     # key: (symbol, tf_key) → threading.Event (stop flag)
        self._lock = threading.Lock()
        self._cache = {}            # key: (symbol, tf_key) → List[dict] (in-memory)
        
        # Callback for real-time updates: func(symbol, tf_key, candle_dict)
        self.on_candle_update = None

    # ── File Path Helpers ──────────────────────────────────────────

    def _file_path(self, symbol, tf_key):
        """Returns the local JSON path for a symbol/timeframe pair."""
        safe_symbol = symbol.replace(" ", "_").replace("/", "_")
        symbol_dir = os.path.join(self.data_dir, safe_symbol)
        os.makedirs(symbol_dir, exist_ok=True)
        return os.path.join(symbol_dir, f"{tf_key}.json")

    # ── Core Data Operations ───────────────────────────────────────

    def _download_initial(self, symbol, tf_key):
        """Downloads a full history chunk from MT5 and saves to JSON."""
        mt5_tf = TF_MAP.get(tf_key)
        if mt5_tf is None:
            print(f"[ChartData] Unknown timeframe: {tf_key}")
            return None

        # copy_rates_from_pos returns a structured numpy array
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, INITIAL_BAR_COUNT)
        if rates is None or len(rates) == 0:
            print(f"[ChartData] No data from MT5 for {symbol} {tf_key}")
            return None

        # Convert numpy array to list of dicts for JSON
        data = []
        for r in rates:
            data.append({
                "time": int(r['time']),
                "open": float(r['open']),
                "high": float(r['high']),
                "low": float(r['low']),
                "close": float(r['close']),
                "tick_volume": int(r['tick_volume'])
            })

        with open(self._file_path(symbol, tf_key), "w") as f:
            json.dump(data, f)
            
        print(f"[ChartData] Saved {len(data)} bars for {symbol} {tf_key}")
        return data

    def _update_latest(self, symbol, tf_key):
        """
        Fetches the latest bars from MT5 and merges them into the local cache.
        Broadcasting updates if new data is available.
        """
        mt5_tf = TF_MAP.get(tf_key)
        if mt5_tf is None:
            return

        # Fetch last 2 bars to handle both the current forming candle and potentially a new one
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, 2)
        if rates is None or len(rates) == 0:
            return

        cache_key = (symbol, tf_key)
        file_path = self._file_path(symbol, tf_key)

        with self._lock:
            # Load from cache or file
            if cache_key in self._cache:
                existing = self._cache[cache_key]
            elif os.path.exists(file_path):
                with open(file_path, "r") as f:
                    existing = json.load(f)
                self._cache[cache_key] = existing
            else:
                existing = self._download_initial(symbol, tf_key)
                if existing:
                    self._cache[cache_key] = existing
                return

            if not existing:
                return

            last_saved_time = existing[-1]['time']
            updates_made = False

            for r in rates:
                candle = {
                    "time": int(r['time']),
                    "open": float(r['open']),
                    "high": float(r['high']),
                    "low": float(r['low']),
                    "close": float(r['close']),
                    "tick_volume": int(r['tick_volume'])
                }

                if candle['time'] == last_saved_time:
                    # Update existing last candle
                    if existing[-1] != candle:
                        existing[-1] = candle
                        updates_made = True
                        # Trigger callback for updated candle
                        if self.on_candle_update:
                            self.on_candle_update(symbol, tf_key, candle)
                elif candle['time'] > last_saved_time:
                    # Append new candle
                    existing.append(candle)
                    last_saved_time = candle['time']
                    updates_made = True
                    # Trigger callback for NEW candle
                    if self.on_candle_update:
                        self.on_candle_update(symbol, tf_key, candle)

            # Persist if changed
            if updates_made:
                with open(file_path, "w") as f:
                    json.dump(existing, f)

    # ── Preloading ────────────────────────────────────────────────

    def preload_all(self, symbols, timeframes=None):
        """Preload 5000 candles for a list of symbols in background."""
        if timeframes is None:
            timeframes = ["M1", "M5", "M15", "H1"]
            
        def _worker():
            print(f"[ChartData] Starting Preload for {len(symbols)} symbols...")
            for sym in symbols:
                for tf in timeframes:
                    try:
                        self.get_chart_data(sym, tf, count=5000)
                    except Exception as e:
                        print(f"Preload error for {sym} {tf}: {e}")
            print("[ChartData] Preload Complete.")

        threading.Thread(target=_worker, daemon=True).start()

    # ── Streaming Control ──────────────────────────────────────────

    def start_stream(self, symbol, tf_key):
        """
        Start a background thread that keeps updating local data for a symbol/tf.
        """
        key = (symbol, tf_key)

        with self._lock:
            # Check if already running or if we should start it
            if key in self._active_streams:
                if self._active_streams[key].is_alive():
                    return
                else:
                    # Clean up dead thread
                    del self._active_streams[key]

            # Ensure initial data exists or load it into cache
            file_path = self._file_path(symbol, tf_key)
            if not os.path.exists(file_path):
                self._download_initial(symbol, tf_key)
            
            if key not in self._cache and os.path.exists(file_path):
                with open(file_path, "r") as f:
                    self._cache[key] = json.load(f)

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
        """Background loop: polls MT5 and updates local data."""
        interval = TF_POLL_INTERVAL.get(tf_key, 2.0)
        print(f"[ChartData] Stream loop running for {symbol} {tf_key} (interval: {interval}s)")

        while not stop_event.is_set():
            try:
                self._update_latest(symbol, tf_key)
            except Exception as e:
                print(f"[ChartData] Stream error for {symbol} {tf_key}: {e}")
            stop_event.wait(interval)

        print(f"[ChartData] Stream loop exited for {symbol} {tf_key}")

    # ── Data Retrieval (Zero-Latency) ─────────────────────────────

    def get_chart_data(self, symbol, tf_key, count=500, offset=0):
        """
        Returns OHLC data from the local cache.
        """
        key = (symbol, tf_key)
        file_path = self._file_path(symbol, tf_key)

        with self._lock:
            if key in self._cache:
                data = self._cache[key]
            elif os.path.exists(file_path):
                with open(file_path, "r") as f:
                    data = json.load(f)
                self._cache[key] = data
            else:
                data = self._download_initial(symbol, tf_key)
                if data:
                    self._cache[key] = data
                else:
                    return [], False

        if not data:
            return [], False

        total = len(data)
        if offset > 0:
            end = total - offset
            start = max(0, end - count)
            sliced = data[start:end]
        else:
            sliced = data[-count:]

        has_more = (total > count + offset)

        chart_data = [{
            "time": int(row['time']),
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close'])
        } for row in sliced]

        return chart_data, has_more

    def get_udf_history(self, symbol, tf_key, from_ts=None, to_ts=None, countback=None):
        """
        Returns OHLCV data in UDF format (array of arrays) from local files.
        """
        data, _ = self.get_chart_data(symbol, tf_key, count=5000) # Fetch enough data to cover typical UDF requests
        if not data:
            return {"s": "no_data"}

        # Filter by time range or countback
        result_data = data
        if countback:
            result_data = data[-min(countback, len(data)):]
        elif from_ts is not None and to_ts is not None:
            result_data = [d for d in data if from_ts <= d['time'] <= to_ts]

        if not result_data:
            return {"s": "no_data"}

        return {
            "s": "ok",
            "t": [d['time'] for d in result_data],
            "o": [d['open'] for d in result_data],
            "h": [d['high'] for d in result_data],
            "l": [d['low'] for d in result_data],
            "c": [d['close'] for d in result_data],
            "v": [d['tick_volume'] for d in result_data]
        }

    def get_active_streams(self):
        """Returns a list of currently active streams."""
        return [
            {"symbol": sym, "timeframe": tf, "active": thread.is_alive()}
            for (sym, tf), thread in self._active_streams.items()
        ]
