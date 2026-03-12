import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Streamlit removed for Lean Build
class MockSt:
    @staticmethod
    def warning(*args, **kwargs): pass
    @staticmethod
    def error(*args, **kwargs): pass
    @staticmethod
    def markdown(*args, **kwargs): pass
    @staticmethod
    def plotly_chart(*args, **kwargs): pass
class MockComponents:
    @staticmethod
    def iframe(*args, **kwargs): pass
st = MockSt()
components = MockComponents()

def renderLightweightCharts(*args, **kwargs): pass


def render_mt5_chart(data, ticker, timeframe, indicators=[], **kwargs):
    """
    MT5 Terminal Chart: Dual-Engine Visualization.
    """
    engine = kwargs.get("engine", "Ultra-Stable (Plotly)")
    display_name = kwargs.get("display_name", None)
    try:
        # 1. Validation
        if data is None or data.empty:
            st.warning(f"Connection established. Waiting for {ticker} ticks...")
            return

        # STABILITY: Force all column names to lowercase
        df = data.copy()
        df.columns = [c.lower() for c in df.columns]

        # Name to show on chart
        title_name = display_name if display_name else ticker

        # 2. Engine Routing
        if "Advanced" in engine:
            render_bridge_engine(df, title_name, timeframe, indicators)
            return
            
        if "Native Deriv" in engine:
            render_deriv_native_engine(ticker, timeframe)
            return

        # 3. Default Plotly Engine
        render_plotly_engine(df, title_name, timeframe, indicators)

    except Exception as e:
        st.error(f"Visualization Bridge Error: {str(e)}")

def render_bridge_engine(df, ticker, timeframe, indicators):
    """Specialized lightweight-charts bridge."""
    try:
        chart_options = {
            "layout": {"textColor": "#00FF00", "backgroundColor": "#000000", "fontSize": 11},
            "grid": {
                "vertLines": {"visible": True, "color": "rgba(42, 46, 45, 0.5)"},
                "horzLines": {"visible": True, "color": "rgba(42, 46, 45, 0.5)"}
            },
            "timeScale": {"borderColor": "#333333", "timeVisible": True},
        }

        chart_data = []
        for _, row in df.iterrows():
            try:
                t_val = row.get('time') if 'time' in df.columns else row.get('date')
                if t_val is None: continue
                
                t = int(t_val) if isinstance(t_val, (int, float, np.integer)) else int(pd.to_datetime(t_val).timestamp())
                chart_data.append({
                    "time": t, "open": float(row['open']), "high": float(row['high']), 
                    "low": float(row['low']), "close": float(row['close'])
                })
            except: continue

        series = [{
            "type": "Candlestick", "data": chart_data,
            "options": {"upColor": "#26a69a", "downColor": "#ef5350", "wickUpColor": "#26a69a", "wickDownColor": "#ef5350"}
        }]
        
        # Add indicators
        colors = ["#2962FF", "#9C27B0", "#FF6D00"]
        for i, ind in enumerate(indicators):
            col = ind.replace(" ", "_").lower()
            if col in df.columns:
                ind_list = [{"time": int(row['time']), "value": float(row[col])} for _, row in df.iterrows() if pd.notna(row[col])]
                if ind_list:
                    series.append({"type": "Line", "data": ind_list, "options": {"color": colors[i%3], "lineWidth": 1.5}})

        st.markdown('<style>iframe { height: 600px !important; }</style>', unsafe_allow_html=True)
        renderLightweightCharts(charts=[{"chart": chart_options, "series": series}], key=f"bridge_{ticker}_{len(df)}")
    except Exception as e:
        st.error(f"Bridge Render Error: {str(e)}")

def render_deriv_native_engine(symbol, timeframe):
    """
    Renders the Official Deriv SmartCharts via Iframe.
    """
    # Map timeframe to seconds/minutes as expected by Deriv if possible
    # Deriv URL format: https://charts.deriv.com/deriv-chart?symbol=R_100&timeframe=1t
    # We will use the standard web chart interface
    
    # Map internal symbols to Deriv URL symbols (usually the same)
    # Mapping TF: M1 -> 1m, H1 -> 1h, etc.
    tf_map = {
        "M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m",
        "H1": "1h", "H4": "4h", "D1": "1d"
    }
    tf = tf_map.get(timeframe, "1h")
    
    chart_url = f"https://charts.deriv.com/deriv-chart?symbol={symbol}&interval={tf}&theme=dark"
    
    components.iframe(chart_url, height=600, scrolling=True)

def render_plotly_engine(df, ticker, timeframe, indicators):
    """High-reliability Plotly-based MT5 styled chart."""
    # Ensure time is datetime for Plotly
    df['dt'] = pd.to_datetime(df['time'], unit='s') if isinstance(df['time'].iloc[0], (int, float, np.integer)) else pd.to_datetime(df['time'])
    
    fig = go.Figure()
    
    # 1. Candlestick (MT5 Classic: Green/White)
    fig.add_trace(go.Candlestick(
        x=df['dt'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#00FF00', decreasing_line_color='#FFFFFF',
        increasing_fillcolor='#00FF00', decreasing_fillcolor='#FFFFFF',
        name=ticker
    ))
    
    # 2. Indicators
    colors = ["#2962FF", "#9C27B0", "#FF6D00"]
    for i, ind in enumerate(indicators):
        col = ind.replace(" ", "_").lower()
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df['dt'], y=df[col], name=ind, line=dict(color=colors[i%3], width=1.5)))

    # 3. Industrial Optimization
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor='black',
        paper_bgcolor='black',
        height=600,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(gridcolor='#222', showgrid=True, title="", rangeslider=dict(visible=False)),
        yaxis=dict(gridcolor='#222', showgrid=True, title="", side="right"),
        font=dict(family="Courier New, monospace", size=10, color="#00FF00"),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
