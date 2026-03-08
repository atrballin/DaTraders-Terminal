try:
    import streamlit as st
except ImportError:
    class MockSt:
        @staticmethod
        def markdown(*args, **kwargs): pass
        @staticmethod
        def error(*args, **kwargs): pass
        @staticmethod
        def warning(*args, **kwargs): pass
        @staticmethod
        def info(*args, **kwargs): pass
        @staticmethod
        def divider(): pass
        @staticmethod
        def caption(*args, **kwargs): pass
        @staticmethod
        def columns(*args, **kwargs): return [MockSt() for _ in range(10)]
        @staticmethod
        def spinner(*args, **kwargs):
            class MockSpinner:
                def __enter__(self): return self
                def __exit__(self, *args): pass
            return MockSpinner()
        class components:
            @staticmethod
            def v1(*args, **kwargs):
                class MockV1:
                    @staticmethod
                    def html(*args, **kwargs): pass
                return MockV1()
        def __enter__(self): return self
        def __exit__(self, *args): pass
    st = MockSt()
    st.components.v1 = st.components.v1() # Hack to make st.components.v1.html work

import pandas as pd
from src.data_loader import get_fred_economic_data, get_mt5_calendar_data

def render_fred_calendar(api_key, theme="Light"):
    """
    Renders a custom FRED economic calendar in an Industrial Pro style.
    """
    is_dark = theme == "Dark"
    bg_table = "#222" if is_dark else "white"
    text_table = "#EEE" if is_dark else "#222"
    border_table = "#444" if is_dark else "#333"
    header_bg = "#333" if is_dark else "#333" # Keep table head dark
    row_hover = "#333" if is_dark else "#F2F2F2"
    
    title_color = "#E0E0E0" if is_dark else "#333"
    
    st.markdown('<h2 class="industrial-header">Economic Release Portal (FRED)</h2>', unsafe_allow_html=True)

    
    with st.spinner("Accessing Federal Reserve Data..."):
        df = get_fred_economic_data(api_key)
        
    if not df.empty:
        # Custom Industrial Table Styling for FRED
        st.markdown(f"""
<style>
.fred-table {{
    width: 100%;
    border-collapse: collapse;
    background: {bg_table};
    border: 2px solid {border_table};
    font-family: 'Inter', sans-serif;
}}
.fred-table th {{
    background: {header_bg};
    color: white;
    padding: 12px;
    text-align: left;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 1px;
}}
.fred-table td {{
    padding: 12px;
    border-bottom: 1px solid {'#444' if is_dark else '#DDD'};
    font-size: 13px;
    color: {text_table};
}}
.fred-table tr:hover {{
    background-color: {row_hover};
}}
.impact-high {{
    color: #CC0000;
    font-weight: 800;
}}
.impact-medium {{
    color: #CC7700;
    font-weight: 700;
}}
</style>
""", unsafe_allow_html=True)


        
        table_html = '<table class="fred-table"><thead><tr><th>Event</th><th>Release Date</th><th>Period Change (%)</th><th>Impact</th></tr></thead><tbody>'
        
        for _, row in df.iterrows():
            impact_class = f"impact-{row['Impact'].lower()}"
            change_val = row['Change']
            # Color-code based on sign
            change_color = "#008800" if "+" in change_val else "#CC0000" if "-" in change_val else "#222"
            
            table_html += f'<tr><td style="font-weight: 700;">{row["Event"]}</td>'
            table_html += f'<td style="color: #666;">{row["Date"]}</td>'
            table_html += f'<td style="font-family: monospace; font-size: 14px; font-weight: 800; color: {change_color};">{change_val}</td>'
            table_html += f'<td class="{impact_class}">{row["Impact"]}</td></tr>'
        table_html += "</tbody></table>"


        
        st.markdown(table_html, unsafe_allow_html=True)
        st.caption("Data source: Federal Reserve Economic Data (FRED). Scheduled updates via API.")
    else:
        st.error("Unable to retrieve FRED data. Check your API key or connection.")

def render_mt5_calendar(theme="Light"):
    """
    Renders MT5 economic calendar with premium color-coded UI.
    Red = Negative/Below Forecast, Green = Positive/Above Forecast
    """
    is_dark = theme == "Dark"
    
    # Premium Color Palette
    bg_card = "#1A1C23" if is_dark else "#FFFFFF"
    bg_page = "#0E1117" if is_dark else "#F5F5F5"
    text_primary = "#FAFAFA" if is_dark else "#1A1A2E"
    text_secondary = "#888" if is_dark else "#666"
    border_color = "#2D323E" if is_dark else "#E5E7EB"
    positive_color = "#10B981"
    negative_color = "#EF4444"
    neutral_color = "#6B7280"
    
    df = get_mt5_calendar_data()

    if "Error" in df.columns:
        error_msg = df["Error"].iloc[0]
        st.error(f"⚠️ {error_msg}")
        if "MQL5 Bridge Required" in error_msg:
            st.info("Run the CalendarExporter_EA.mq5 Expert Advisor in MT5 to enable live data sync.")
        return

    if df.empty:
        st.info("📭 No high-impact events scheduled")
        return
    
    # Build event rows for a clean table
    st.markdown("### 📅 Economic Calendar")
    st.caption("Live MT5 Terminal Feed • High Impact Events • 🔄 Auto-syncing every minute")
    
    for _, row in df.iterrows():
        event_name = row.get("Event", "Unknown Event")
        event_time = row.get("Date", "-")
        actual = row.get("Value", "-")
        forecast = row.get("Forecast", "-")
        previous = row.get("Previous", "-")
        impact = row.get("Impact", "Medium")
        
        # Determine sentiment: Actual vs Previous
        sentiment = "neutral"
        icon = "📊"
        color = neutral_color
        
        try:
            actual_clean = actual.replace("%", "").replace("pts", "").replace("+", "").replace(" ", "").strip()
            previous_clean = previous.replace("%", "").replace("pts", "").replace("+", "").replace(" ", "").strip()
            forecast_clean = forecast.replace("%", "").replace("pts", "").replace("+", "").replace(" ", "").strip()
            
            # Primary sentiment: Actual vs Previous
            if actual_clean != "-" and previous_clean != "-" and actual_clean and previous_clean:
                actual_num = float(actual_clean)
                previous_num = float(previous_clean)
                
                if actual_num > previous_num:
                    sentiment = "positive"
                    icon = "📈"
                    color = positive_color
                elif actual_num < previous_num:
                    sentiment = "negative"
                    icon = "📉"
                    color = negative_color
            elif actual_clean != "-" and actual_clean:
                # Fallback: Actual vs Forecast if Previous is missing
                if forecast_clean != "-" and forecast_clean:
                    actual_num = float(actual_clean)
                    forecast_num = float(forecast_clean)
                    if actual_num > forecast_num:
                        sentiment = "positive"
                        icon = "📈"
                        color = positive_color
                    elif actual_num < forecast_num:
                        sentiment = "negative"
                        icon = "📉"
                        color = negative_color
                else:
                    # Simple polarity check
                    val = float(actual_clean)
                    if val > 0:
                        sentiment = "positive"
                        icon = "📈"
                        color = positive_color
                    elif val < 0:
                        sentiment = "negative"
                        icon = "📉"
                        color = negative_color
        except:
            pass
        
        # Use Streamlit columns for layout
        col1, col2, col3, col4, col5 = st.columns([0.5, 2.5, 1, 1, 1])
        
        with col1:
            st.markdown(f"<span style='font-size: 24px;'>{icon}</span>", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"**{event_name}**")
            st.caption(f"🕐 {event_time}")
        
        with col3:
            st.markdown(f"<span style='color: {color}; font-weight: bold; font-family: monospace;'>{actual}</span>", unsafe_allow_html=True)
            st.caption("Actual")
        
        with col4:
            st.markdown(f"<span style='color: {neutral_color}; font-family: monospace;'>{forecast}</span>", unsafe_allow_html=True)
            st.caption("Forecast")

        with col5:
            st.markdown(f"<span style='color: {neutral_color}; font-family: monospace;'>{previous}</span>", unsafe_allow_html=True)
            st.caption("Previous")
        
        st.divider()


def render_tv_calendar(theme="Light"):
    """
    Renders the TradingView Economic Calendar widget.
    """
    is_dark = theme == "Dark"
    tv_theme = "dark" if is_dark else "light"
    
    st.markdown('<h2 class="industrial-header">Global Economic Events</h2>', unsafe_allow_html=True)
    
    # TradingView Economic Calendar Widget
    widget_html = f"""
    <div class="tradingview-widget-container" style="height: 700px;">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
      {{
      "colorTheme": "{tv_theme}",
      "isMaximized": true,
      "width": "100%",
      "height": "700",
      "locale": "en",
      "importanceFilter": "-1,0,1",
      "currencyFilter": "USD,EUR,GBP,JPY,AUD,CAD,CHF"
    }}
      </script>
    </div>
    """
    
    st.components.v1.html(widget_html, height=720)
    st.caption("Live global events provided by TradingView. Real-time synchronization.")
