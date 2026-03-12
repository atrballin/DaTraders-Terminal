# Streamlit removed for Lean Build
class MockSt:
    @staticmethod
    def info(*args, **kwargs): print(f"INFO: {args}")
    @staticmethod
    def plotly_chart(*args, **kwargs): print(f"PLOT: {args}")
st = MockSt()

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def render_plotly_chart(data, ticker, indicators=[], theme="Light"):
    """
    Renders a professional candlestick chart with indicators using Plotly.
    """
    
    is_dark = theme == "Dark"
    bg_color = "#121212" if is_dark else "#FFFFFF"
    text_color = "#FFFFFF" if is_dark else "#131722"
    grid_color = "rgba(197, 203, 206, 0.1)" if is_dark else "rgba(197, 203, 206, 0.5)"
    
    # Prepare data
    df = data.reset_index()
    date_col = df.columns[0] if df.columns[0] == 'Date' else 'Date'
    
    # Create figure
    fig = go.Figure()
    
    # Add candlestick
    fig.add_trace(go.Candlestick(
        x=df[date_col],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name=ticker,
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350'
    ))
    
    # Add indicators
    if "SMA 20" in indicators and "SMA_20" in df.columns:
        fig.add_trace(go.Scatter(
            x=df[date_col],
            y=df['SMA_20'],
            name='SMA 20',
            line=dict(color='#2962FF', width=2)
        ))
    
    if "RSI" in indicators and "RSI" in df.columns:
        fig.add_trace(go.Scatter(
            x=df[date_col],
            y=df['RSI'],
            name='RSI',
            line=dict(color='#9C27B0', width=2),
            yaxis='y2'
        ))
    
    # Update layout
    fig.update_layout(
        title=f"{ticker}",
        title_font=dict(size=20, color=text_color, family='Inter'),
        xaxis_title="Date",
        yaxis_title="Price",
        template='plotly_dark' if is_dark else 'plotly_white',
        height=700,
        font=dict(family='Inter', size=12, color=text_color),
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        xaxis=dict(
            showgrid=True,
            gridcolor=grid_color,
            type='date'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=grid_color
        ),
        hovermode='x unified',
        margin=dict(l=50, r=50, t=50, b=50),
        dragmode='pan'  # Enable pan by default, scroll for zoom
    )
    
    # Remove range slider
    fig.update_xaxes(rangeslider_visible=False)
    
    # Streamlit note for zoom
    st.info("📊 **Chart Controls**: Use the toolbar buttons above the chart - Click 'Zoom' button then drag to select area, or use 'Pan' to move around. Double-click to reset view.")
    
    # Enable comprehensive interactions (scrollZoom doesn't work reliably in Streamlit)
    config = {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': [],  # Keep all buttons
        'toImageButtonOptions': {
            'format': 'png',
            'filename': f'{ticker}_chart',
            'height': 700,
            'width': 1400,
            'scale': 2
        }
    }
    
    st.plotly_chart(fig, use_container_width=True, config=config)
