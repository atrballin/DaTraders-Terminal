import numpy as np
import pandas as pd

# Streamlit removed for Lean Build
class MockSt:
    @staticmethod
    def warning(*args, **kwargs): pass
    @staticmethod
    def error(*args, **kwargs): pass
    @staticmethod
    def markdown(*args, **kwargs): pass
    class components:
        class v1:
            @staticmethod
            def html(*args, **kwargs): pass
st = MockSt()

def renderLightweightCharts(*args, **kwargs): pass


def render_advanced_tv_chart(ticker, timeframe="1h", theme="Light"):
    """
    Renders the full-featured Advanced Real-Time Chart Widget.
    """
    # Map symbols for TradingView (Standard Tickers)
    tv_map = {
        "US30": "DJI",
        "Nikkei 225": "NI225",
        "Gold": "GOLD",
        "BTCUSD": "BINANCE:BTCUSDT",
        "^DJI": "DJI",
        "^N225": "NI225",
        "GC=F": "GOLD"
    }
    
    tv_symbol = tv_map.get(ticker, ticker)
    tv_theme = "dark" if theme == "Dark" else "light"
    
    # Map Streamlit MT5 Timeframes to TV Timeframes
    tf_map = {
        "M1": "1", "M5": "5", "M15": "15", "M30": "30",
        "H1": "60", "H4": "240", "D1": "D", "W1": "W"
    }
    tv_interval = tf_map.get(timeframe, "60")

    widget_html = f"""
    <div class="tradingview-widget-container" style="height: 85vh; width: 100%; border-radius: 8px; overflow: hidden; border: 1px solid {'#333' if theme == 'Dark' else '#ccc'};">
        <div id="tradingview_advanced" style="height: 100%; width: 100%;"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({{
            "autosize": true,
            "symbol": "{tv_symbol}",
            "interval": "{tv_interval}",
            "timezone": "Etc/UTC",
            "theme": "{tv_theme}",
            "style": "1",
            "locale": "en",
            "toolbar_bg": "{'#121212' if theme == 'Dark' else '#f1f3f6'}",
            "enable_publishing": false,
            "withdateranges": true,
            "hide_side_toolbar": false,
            "allow_symbol_change": true,
            "save_image": true,
            "container_id": "tradingview_advanced",
            "show_popup_button": true,
            "popup_width": "1000",
            "popup_height": "650",
            "details": true,
            "hotlist": true,
            "calendar": true,
            "studies": [
                "MASimple@tv-basicstudies",
                "RSI@tv-basicstudies",
                "MACD@tv-basicstudies"
            ],
            "drawings_access": {{
                "type": 'black',
                "tools": [
                    {{ "name": "Regression Trend" }}
                ]
            }},
            "enabled_features": ["study_templates", "use_localstorage_for_settings_save"],
            "disabled_features": ["header_saveload"]
        }});
        </script>
    </div>
    """
    # Increased height for "Full Screen" feel (85% of viewport height)
    st.components.v1.html(widget_html, height=720)

def render_native_chart(data, ticker, indicators=[], theme="Light", chart_style="Modern"):
    """
    Renders a premium Lightweight Chart with technical indicators.
    Supports Light/Dark themes and Classic(MT5) styles.
    """
    try:
        if data is None or data.empty:
            st.warning(f"Waiting for {ticker} data sequence...")
            return
            
        # 1. Theme Configuration
        is_dark = theme == "Dark" or chart_style == "MetaTrader 5"
        
        if chart_style == "MetaTrader 5":
            # AUTHENTIC MT5 COLORS
            bg_color = "#000000"
            text_color = "#00FF00" # Classic Lime Green text
            grid_color = "rgba(40, 40, 40, 0.5)"
            border_color = "#222222"
            up_color = "#00FF00"         # Green
            down_color = "#FFFFFF"       # White (MT5 Default for Bear)
            wick_up = "#00FF00"
            wick_down = "#FFFFFF"
        else:
            bg_color = "#121212" if is_dark else "#FFFFFF"
            text_color = "#FFFFFF" if is_dark else "#131722"
            grid_color = "rgba(197, 203, 206, 0.1)" if is_dark else "rgba(197, 203, 206, 0.5)"
            border_color = "rgba(197, 203, 206, 0.8)" if is_dark else "rgba(197, 203, 206, 1)"
            up_color = "#26a69a"
            down_color = "#ef5350"
            wick_up = "#26a69a"
            wick_down = "#ef5350"

        # 2. Prepare Data (Hardened Formatting)
        df = data.reset_index().copy()
        
        # Identify the time column
        time_col = None
        for col in ['Date', 'time', 'datetime', 'index']:
            if col in df.columns:
                time_col = col
                break
        
        if not time_col:
            st.error("Chart Error: No time-series index found.")
            return

        # FORCE DISCOVERY: Map everything to a standard internal lowercase set
        # This makes the rest of the logic case-insensitive
        df.columns = [c.lower() for c in df.columns]

        chart_data = []
        for _, row in df.iterrows():
            try:
                # Handle Unix or Datetime
                raw_time = row['date'] if 'date' in df.columns else row.get(time_col.lower())
                if isinstance(raw_time, (int, float, np.integer, np.floating)):
                    t = int(raw_time)
                else:
                    t = int(pd.to_datetime(raw_time).timestamp())
                
                # Use strictly lowercase keys as mapped above
                o, h, l, c = row.get('open'), row.get('high'), row.get('low'), row.get('close')
                
                if pd.isna(o) or pd.isna(h) or pd.isna(l) or pd.isna(c):
                    continue
                    
                chart_data.append({
                    "time": t,
                    "open": float(o),
                    "high": float(h),
                    "low": float(l),
                    "close": float(c)
                })
            except:
                continue

        if not chart_data:
            st.error(f"Data Processing Error: No valid price bars found for {ticker}")
            return

        # 3. Chart Options
        chart_options = {
            "layout": {
                "textColor": text_color,
                "background": {"type": 'solid', "color": bg_color},
                "fontSize": 11,
                "fontFamily": "Courier New, monospace" if chart_style == "MetaTrader 5" else "Inter, sans-serif"
            },
            "grid": {
                "vertLines": {"color": grid_color, "style": 2},
                "horzLines": {"color": grid_color, "style": 2}
            },
            "crosshair": {"mode": 1},
            "timeScale": {"borderColor": border_color, "timeVisible": True, "secondsVisible": False},
            "rightPriceScale": {"borderColor": border_color, "visible": True},
            "handleScroll": True,
            "handleScale": True
        }

        # 4. Candlestick Series
        series = [{
            "type": "Candlestick",
            "data": chart_data,
            "options": {
                "upColor": up_color, "downColor": down_color,
                "borderVisible": True if chart_style != "MetaTrader 5" else False,
                "wickUpColor": wick_up, "wickDownColor": wick_down,
                "borderColor": "#00FF00" if chart_style == "MetaTrader 5" else up_color,
            }
        }]

        # 5. Technical Indicators
        indicator_colors = ["#2962FF", "#9C27B0", "#FF6D00", "#4CAF50"]
        for i, ind in enumerate(indicators):
            col_name = ind.replace(" ", "_")
            if col_name in df.columns:
                ind_list = []
                for _, row in df.iterrows():
                    if pd.notna(row[col_name]):
                        try:
                            raw_t = row[time_col]
                            if isinstance(raw_t, (int, float, np.integer, np.floating)):
                                tt = int(raw_t)
                            else:
                                tt = int(pd.to_datetime(raw_t).timestamp())
                            ind_list.append({"time": tt, "value": float(row[col_name])})
                        except: continue
                if ind_list:
                    series.append({
                        "type": "Line",
                        "data": ind_list,
                        "options": {
                            "color": indicator_colors[i % 4], 
                            "lineWidth": 1 if chart_style == "MetaTrader 5" else 2,
                            "priceLineVisible": False
                        }
                    })

        # Render with a very specific Streamlit IFrame height
        # We use a key that combines style to force a refresh if style changes
        chart_key = f"native_chart_{ticker}_{mt5_tf if 'mt5_tf' in locals() else 'H1'}_{chart_style}".replace(" ", "_")
        
        # Final Iframe wrapper to ensure visibility
        st.markdown(f"""
            <style>
                iframe[title="streamlit_lightweight_charts.renderLightweightCharts"] {{
                    height: 600px !important;
                    width: 100% !important;
                }}
            </style>
        """, unsafe_allow_html=True)

        renderLightweightCharts(charts=[{"chart": chart_options, "series": series}], key=chart_key)
        
    except Exception as e:
        st.error(f"Terminal Visualization Error: {str(e)}")


