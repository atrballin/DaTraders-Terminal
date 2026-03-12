import threading
import time
import MetaTrader5 as mt5
from collections import deque
import numpy as np

class TickMonitor:
    """
    Low-latency tick monitor for MetaTrader 5.
    Calculates Volatility (Stability) and Jump Detection for Crash/Boom spikes.
    """
    def __init__(self, symbols, window_seconds=5):
        self.symbols = symbols
        self.window_seconds = window_seconds
        self.tick_history = {symbol: deque() for symbol in symbols}
        self.tick_metrics = {symbol: {
            'velocity': 0.0,
            'range': 0.0,
            'is_breakout': False,
            'is_stable': True,
            'last_jump': 0.0
        } for symbol in symbols}
        self.running = False
        self.thread = None
        self._lock = threading.Lock()

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print(f"TickMonitor: Started for {self.symbols}")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def _monitor_loop(self):
        while self.running:
            try:
                for symbol in self.symbols:
                    tick = mt5.symbol_info_tick(symbol)
                    if tick:
                        with self._lock:
                            self._process_tick(symbol, tick)
                time.sleep(0.1) # 100ms poll rate for balanced performance
            except Exception as e:
                print(f"TickMonitor Error: {e}")
                time.sleep(1)

    def _process_tick(self, symbol, tick):
        history = self.tick_history[symbol]
        now = time.time()
        
        # 1. Add current tick
        current_price = tick.bid # Use bid for Crash/Boom downspikes/upspikes context
        history.append((now, current_price))
        
        # 2. Cleanup old ticks outside window
        while history and now - history[0][0] > self.window_seconds:
            history.popleft()
            
        if len(history) < 2:
            return

        # 3. Calculate Stability (Range over window)
        prices = [p for t, p in history]
        price_range = max(prices) - min(prices)
        
        # 4. Jump Detection (Delta from previous tick)
        prev_price = history[-2][1]
        delta = abs(current_price - prev_price)
        
        # 5. Average Tick Size (Dynamic thresholding)
        # In Crash/Boom, average "normal" ticks are tiny. Spikes are massive.
        # We calculate avg delta over window to distinguish normal move from jump.
        deltas = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        avg_delta = np.mean(deltas) if deltas else 0.0
        
        # 6. Update Metrics
        self.tick_metrics[symbol] = {
            'velocity': delta * 10, # Points per update (scaled)
            'range': price_range,
            'is_stable': price_range < 0.2, # Hard threshold for stability (0.2 points)
            'last_jump': delta,
            'is_breakout': delta > (avg_delta * 3.0) and delta > 0.5 # Jump must be 3x normal AND > 0.5 points
        }

    def get_metrics(self, symbol):
        with self._lock:
            return self.tick_metrics.get(symbol, {})
