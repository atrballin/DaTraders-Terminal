import pandas as pd
from datetime import datetime, timedelta
from src.data_loader import get_mt5_calendar_data
from src.mt5_trading import close_all_positions
try:
    import streamlit as st
except ImportError:
    class MockSt:
        @staticmethod
        def error(*args, **kwargs): pass
        @staticmethod
        def warning(*args, **kwargs): pass
        @staticmethod
        def info(*args, **kwargs): pass
    st = MockSt()


class NewsGuard:
    """
    Monitors high-impact economic news and triggers trade closures.
    Target Events: CPI, NFP, FOMC.
    Threshold: 1 minute (60 seconds) before release.
    """
    def __init__(self):
        self.high_impact_keywords = ["CPI", "NFP", "FOMC", "NON-FARM PAYROLLS", "INTEREST RATE", "FED"]
        self.last_check_time = datetime.now()
        self.triggered_events = set() # Avoid multiple closures for the same event

    def check_and_clear(self):
        """
        Fetches calendar data and clears positions if a major news event is within 1 minute.
        Returns: (bool triggered, str message)
        """
        try:
            df = get_mt5_calendar_data()
            if df.empty or "Error" in df.columns:
                return False, "No active news feed"

            now = datetime.now()
            
            for _, row in df.iterrows():
                event_name = str(row.get("Event", "")).upper()
                event_time_str = row.get("Date", "")
                
                # 1. Filter for High-Impact Keywords
                is_high_impact = any(k in event_name for k in self.high_impact_keywords)
                if not is_high_impact:
                    continue

                # 2. Parse Event Time
                try:
                    # Expecting format YYYY-MM-DD HH:MM:SS or similar from MT5 Bridge
                    event_time = pd.to_datetime(event_time_str)
                except:
                    continue

                # 3. Calculate Time to Event
                # Ensure objects are timezone-naive or both aware
                if event_time.tzinfo is not None:
                     event_time = event_time.replace(tzinfo=None)
                
                time_to_event = (event_time - now).total_seconds()
                
                # 4. Trigger logic (60 seconds window)
                # We trigger if we are between 0 and 65 seconds before the event
                if 0 <= time_to_event <= 65:
                    event_id = f"{event_name}_{event_time_str}"
                    if event_id not in self.triggered_events:
                        success, msg = close_all_positions()
                        if success:
                            self.triggered_events.add(event_id)
                            return True, f"🚨 NEWS GUARD: Closed all trades 1m before {event_name} ({event_time_str})"
                        else:
                            return True, f"⚠️ NEWS GUARD FAILED to close trades for {event_name}: {msg}"

            return False, "Market Stable: No imminent high-impact news."

        except Exception as e:
            return False, f"News Guard Error: {str(e)}"
