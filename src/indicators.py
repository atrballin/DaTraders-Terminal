import pandas as pd
import numpy as np

def calculate_sma(df, period=20):
    return df['close'].rolling(window=period).mean()

def calculate_ema(df, period=20):
    return df['close'].ewm(span=period, adjust=False).mean()

def calculate_rma(df, period=20):
    """Wilder's Smoothed Moving Average (RMA). Alpha = 1/period."""
    return df['close'].ewm(alpha=1.0/period, adjust=False).mean()

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    # Use Wilder's Smoothing (RMA) for MT5/TradingView accuracy
    alpha = 1 / period
    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()

    # Avoid division by zero
    avg_loss = avg_loss.replace(0, 1e-10)
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(df, period=11):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calculate_atr_wilder(df, period=11):
    """
    Calculates Average True Range using Wilder's Smoothing (RMA) rather than simple SMA.
    """
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0/period, adjust=False).mean()

def calculate_adx(df, period=14):
    """
    Calculates the Average Directional Index (ADX) using Wilder's smoothing.
    """
    df = df.copy()
    high = df['high']
    low = df['low']
    close = df['close']
    
    p_dm = high.diff()
    m_dm = -low.diff() # prev_low - low
    
    plus_dm = np.where((p_dm > m_dm) & (p_dm > 0), p_dm, 0.0)
    minus_dm = np.where((m_dm > p_dm) & (m_dm > 0), m_dm, 0.0)
    
    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)
    
    # True Range (ATR(1))
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).fillna(0.0001)
    
    # Wilder's Smoothing = EMA with alpha = 1 / period
    def wilders_ema(s, period):
        res = np.full(len(s), np.nan)
        s_clean = s.dropna()
        if len(s_clean) < period:
            return pd.Series(res, index=s.index)
            
        start_idx = s.index.get_loc(s_clean.index[period-1])
        res[start_idx] = s_clean.iloc[:period].mean()
        
        alpha = 1.0 / period
        for i in range(start_idx + 1, len(s)):
            val = s.iloc[i]
            if not np.isnan(val):
                res[i] = alpha * val + (1 - alpha) * res[i-1]
            else:
                res[i] = res[i-1]
        return pd.Series(res, index=s.index)

    atr = wilders_ema(tr, period).replace(0, 0.0001)
    plus_dm_avg = wilders_ema(plus_dm, period)
    minus_dm_avg = wilders_ema(minus_dm, period)
    
    # DI Calculation (will have NaNs for first 'period' bars)
    plus_di = 100 * (plus_dm_avg / atr)
    minus_di = 100 * (minus_dm_avg / atr)
    
    sum_di = (plus_di + minus_di).replace(0, 1e-10)
    dx = (np.abs(plus_di - minus_di) / sum_di) * 100
    
    # ADX Calculation (will have NaNs for first '2*period' bars)
    adx = wilders_ema(dx, period)
    
    # Final bfill so UI always sees a value (even if less accurate at start of history)
    return adx.bfill().ffill()

def calculate_quarterly_levels(df):
    """
    Identifies quarterly and yearly opening prices.
    """
    df = df.copy()
    df['quarter'] = df.index.quarter
    df['year'] = df.index.year
    
    # Quarterly Open
    df['q_start'] = (df['quarter'] != df['quarter'].shift(1))
    df['quarter_open'] = df['open'].where(df['q_start']).ffill()
    
    # Yearly Open
    df['y_start'] = (df['year'] != df['year'].shift(1))
    df['year_open'] = df['open'].where(df['y_start']).ffill()
    
    return df

def calculate_macd(df, fast=12, slow=26, signal=9):
    exp1 = df['close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    
    return pd.DataFrame({
        'MACD': macd,
        'MACD_Signal': signal_line,
        'MACD_Hist': histogram
    })

def calculate_fvg(df):
    df = df.copy()
    df['Bullish_FVG'] = (df['low'] > df['high'].shift(2)) & (df['close'].shift(1) > df['high'].shift(2))
    df['Bearish_FVG'] = (df['high'] < df['low'].shift(2)) & (df['close'].shift(1) < df['low'].shift(2))
    df['FVG_Top'] = df['high'].shift(2)
    df['FVG_Bottom'] = df['low']
    return df

def calculate_zones(df, period=20):
    df = df.copy()
    df['Support'] = df['low'].rolling(window=period, center=True).min().ffill()
    df['Resistance'] = df['high'].rolling(window=period, center=True).max().ffill()
    return df

def calculate_mtf_zones(df):
    """
    Calculates Daily and Weekly zones from 4H data.
    """
    df = df.copy()
    
    # Daily Zones
    d_df = df.resample('D').agg({'high': 'max', 'low': 'min', 'close': 'last'})
    d_df['D_Support'] = d_df['low'].rolling(window=10).min()
    d_df['D_Resistance'] = d_df['high'].rolling(window=10).max()
    
    # Weekly Zones
    w_df = df.resample('W').agg({'high': 'max', 'low': 'min', 'close': 'last'})
    w_df['W_Support'] = w_df['low'].rolling(window=5).min()
    w_df['W_Resistance'] = w_df['high'].rolling(window=5).max()
    
    # Map back to 4H
    df['temp_date'] = df.index.normalize()
    df = df.merge(d_df[['D_Support', 'D_Resistance']], left_on='temp_date', right_index=True, how='left')
    
    df['temp_week'] = df.index.to_period('W').to_timestamp()
    df = df.merge(w_df[['W_Support', 'W_Resistance']], left_on='temp_week', right_index=True, how='left')
    
    # Clean up temp columns
    df = df.drop(columns=['temp_date', 'temp_week'])
    
    # Ffill for continuous coverage
    df['D_Support'] = df['D_Support'].ffill()
    df['D_Resistance'] = df['D_Resistance'].ffill()
    df['W_Support'] = df['W_Support'].ffill()
    df['W_Resistance'] = df['W_Resistance'].ffill()
    
    return df

def detect_order_blocks(df):
    df = df.copy()
    df['Bullish_OB'] = (df['close'].shift(3) < df['open'].shift(3)) & df['Bullish_FVG']
    df['Bearish_OB'] = (df['close'].shift(3) > df['open'].shift(3)) & df['Bearish_FVG']
    return df

def is_in_session(dt, session="London"):
    """
    ULTRA-ROBUST SESSION CHECKER.
    Handles raw ints, floats, strings, and Timestamps without crashing.
    
    Session Windows (UTC) - Extended for 24/5 coverage with overlaps:
    - Asian:  00:00 - 08:00 (8 hours) - Tokyo/Sydney
    - London: 07:00 - 16:00 (9 hours) - London open through NY overlap
    - NY:     12:00 - 21:00 (9 hours) - Full NY session including close
    """
    try:
        # 1. Forensic Type Conversion
        if not hasattr(dt, 'hour'):
            # Check for any numeric type (including numpy ones)
            if isinstance(dt, (int, float, np.integer, np.floating)):
                dt = pd.to_datetime(dt, unit='s')
            else:
                dt = pd.to_datetime(str(dt))
        
        # 2. Safety Attribute Access
        hour = getattr(dt, 'hour', None)
        if hour is None:
            return False
            
        # 3. Session Logic (Extended windows with overlaps)
        if session == "London":
            return 7 <= hour < 16  # Extended: 7am - 4pm UTC
        elif session == "NY":
            return 12 <= hour < 21  # Extended: 12pm - 9pm UTC
        elif session == "Asian":
            return 0 <= hour < 8  # Extended: 12am - 8am UTC
            
    except Exception:
        # NUCLEAR FAIL-SAFE
        return False
        
    return False

def calculate_liquidity_sweep(df):
    """
    Identifies liquidity sweeps of previous high/low.
    A bullish sweep: current low < previous low AND current close > previous low.
    A bearish sweep: current high > previous high AND current close < previous high.
    """
    df = df.copy()
    prev_low = df['low'].shift(1)
    prev_high = df['high'].shift(1)
    
    df['Bullish_Sweep'] = (df['low'] < prev_low) & (df['close'] > prev_low)
    df['Bearish_Sweep'] = (df['high'] > prev_high) & (df['close'] < prev_high)
    return df

def calculate_structure_shift(df):
    """
    Identifies Market Structure Shifts (MSS) after a sweep.
    Standardized: Check if MSS occurred within the last 5 candles after a sweep.
    """
    df = df.copy()
    if 'Bullish_Sweep' not in df.columns:
        df = calculate_liquidity_sweep(df)
        
    # Swing points (avoiding lookahead with center=False)
    df['Swing_High'] = df['high'].rolling(window=5).max()
    df['Swing_Low'] = df['low'].rolling(window=5).min()
    
    # Raw shift signal
    # Bullish MSS: Price breaks above previous local high after a sweep
    df['Bull_Shift_Raw'] = (df['high'] > df['Swing_High'].shift(1)).astype(int)
    df['Bear_Shift_Raw'] = (df['low'] < df['Swing_Low'].shift(1)).astype(int)
    
    # Final MSS: A sweep happened recently (last 5 bars) AND price just broke structure
    df['Bullish_MSS'] = (df['Bullish_Sweep'].rolling(5).max() > 0) & (df['Bull_Shift_Raw'] > 0)
    df['Bearish_MSS'] = (df['Bearish_Sweep'].rolling(5).max() > 0) & (df['Bear_Shift_Raw'] > 0)
    
    return df

def add_indicators(df, indicators):
    df = df.copy()
    # Robustness: ensure lowercase for internal calculations via forensic mapping
    for req in ['open', 'high', 'low', 'close', 'time']:
        actual = next((c for c in df.columns if c.lower() == req), None)
        if actual:
            df = df.rename(columns={actual: req})
    # --- Dynamic Moving Average Handling ---
    # Supports MA_X, EMA_X, and SMA_X for any integer X.
    # USER REQUEST: "Ma's Not SMA" -> MA_X will now return EMA.
    for indicator in indicators:
        if indicator.startswith("MA_") or indicator.startswith("EMA_") or indicator.startswith("SMA_") or indicator.startswith("RMA_"):
            try:
                parts = indicator.split("_")
                prefix = parts[0]
                period = int(parts[1])
                
                if prefix == "SMA":
                    df[indicator] = calculate_sma(df, period)
                elif prefix == "RMA":
                    df[indicator] = calculate_rma(df, period)
                else: # Default MA or explicit EMA to calculate_ema
                    df[indicator] = calculate_ema(df, period)
            except (ValueError, IndexError):
                continue

    if "RSI" in indicators:
        df['RSI'] = calculate_rsi(df)
    if "RSI_7" in indicators:
        df['RSI_7'] = calculate_rsi(df, 7)
    if "RSI_4" in indicators:
        df['RSI_4'] = calculate_rsi(df, 4)
    # Dynamic RSI_X processing
    for ind in indicators:
        if ind.startswith("RSI_") and ind not in df.columns:
            try:
                period = int(ind.split("_")[1])
                df[ind] = calculate_rsi(df, period)
            except (ValueError, IndexError):
                pass
    if "MACD" in indicators:
        macd_df = calculate_macd(df)
        df['MACD'] = macd_df['MACD']
        df['MACD_Signal'] = macd_df['MACD_Signal']
        df['MACD_Hist'] = macd_df['MACD_Hist']
    if "FVG" in indicators:
        df = calculate_fvg(df)
    if "DZ" in indicators:
        df = calculate_zones(df)
    if "MTF_Zones" in indicators:
        df = calculate_mtf_zones(df)
    if "Quarterly" in indicators:
        df = calculate_quarterly_levels(df)
    if "OB" in indicators:
        if 'Bullish_FVG' not in df.columns:
            df = calculate_fvg(df)
        df = detect_order_blocks(df)
    if "Sweep" in indicators:
        df = calculate_liquidity_sweep(df)
    if "MSS" in indicators:
        df = calculate_structure_shift(df)
    if "Vol_SMA" in indicators:
        df['Vol_SMA'] = df['tick_volume'].rolling(window=19).mean()
    if "ATR" in indicators:
        df['ATR'] = calculate_atr(df, 11)
    if "ATR_21" in indicators:
        df['ATR_21'] = calculate_atr(df, 21)
    
    # Dynamic ATR Wilder processing
    for ind in indicators:
        if ind.startswith("ATR_W_"):
            try:
                period = int(ind.split("_")[-1])
                df[ind] = calculate_atr_wilder(df, period)
            except ValueError:
                pass
                
    if "ADX" in indicators:
        # Default period 14, can be overridden in strategy
        df['ADX'] = calculate_adx(df, 14)
    if "ADX_6" in indicators:
        df['ADX_6'] = calculate_adx(df, 6)
    if "ADX_7" in indicators:
        df['ADX_7'] = calculate_adx(df, 7)
    if "ADX_14" in indicators:
        df['ADX_14'] = calculate_adx(df, 14)
    if "ADX_80" in indicators:
        df['ADX_80'] = calculate_adx(df, 80)
    # Dynamic ADX_X processing
    for ind in indicators:
        if ind.startswith("ADX_") and ind not in df.columns:
            try:
                period = int(ind.split("_")[1])
                df[ind] = calculate_adx(df, period)
            except (ValueError, IndexError):
                pass
    if "Fractals" in indicators:
        df = calculate_fractals(df)
    return df

def calculate_fractals(df):
    """
    Calculates Bill Williams Fractals.
    - Up Fractal: High[i] > High[i-1], High[i] > High[i-2], High[i] > High[i+1], High[i] > High[i+2]
    - Down Fractal: Low[i] < Low[i-1], Low[i] < Low[i-2], Low[i] < Low[i+1], Low[i] < Low[i+2]
    Note: A fractal is confirmed only after 2 bars to the right are closed.
    """
    df = df.copy()
    highs = df['high'].values
    lows = df['low'].values
    
    up_fractals = np.zeros(len(df), dtype=bool)
    down_fractals = np.zeros(len(df), dtype=bool)
    
    # Needs at least 5 bars for calculation
    for i in range(2, len(df) - 2):
        # Up Fractal
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
           highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            up_fractals[i] = True
            
        # Down Fractal
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
           lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            down_fractals[i] = True
            
    df['Up_Fractal'] = up_fractals
    df['Down_Fractal'] = down_fractals
    
    return df

def calculate_volume_profile(df, row_size=178, va_vol_pct=0.68):
    """
    Calculates Fixed Range Volume Profile (FRVP) metrics: POC, VAH, VAL.
    POC: Point of Control (Price with highest volume)
    VAH: Value Area High
    VAL: Value Area Low
    """
    import numpy as np
    if df is None or df.empty:
        return None
    
    # 1. Determine price range
    low = df['low'].min()
    high = df['high'].max()
    if low == high: return None
    
    # 2. Setup Bins
    bin_size = (high - low) / row_size
    
    # 3. Aggregate Volume per bin
    volume_per_bin = np.zeros(row_size)
    total_vol = 0
    
    for _, row in df.iterrows():
        bar_vol = row.get('tick_volume', row.get('volume', 0))
        if bar_vol <= 0: continue
            
        # Distribute volume across all bins the bar touches
        bar_low = row['low']
        bar_high = row['high']
        
        idx_start = max(0, int((bar_low - low) / bin_size))
        idx_end = min(row_size - 1, int((bar_high - low) / bin_size))
        
        num_bins = (idx_end - idx_start) + 1
        vol_share = bar_vol / num_bins
        
        for i in range(idx_start, idx_end + 1):
            volume_per_bin[i] += vol_share
        
        total_vol += bar_vol
        
    if total_vol == 0: return None
    
    # 4. Find POC
    poc_idx = np.argmax(volume_per_bin)
    poc = low + (poc_idx + 0.5) * bin_size
    
    # 5. Find Value Area (VAH/VAL)
    target_vol = total_vol * va_vol_pct
    current_vol = volume_per_bin[poc_idx]
    
    upper_idx = poc_idx
    lower_idx = poc_idx
    
    while current_vol < target_vol:
        can_expand_upper = (upper_idx < row_size - 1)
        can_expand_lower = (lower_idx > 0)
        
        if not can_expand_upper and not can_expand_lower:
            break
            
        v_upper = volume_per_bin[upper_idx + 1] if can_expand_upper else -1
        v_lower = volume_per_bin[lower_idx - 1] if can_expand_lower else -1
        
        if v_upper >= v_lower:
            upper_idx += 1
            current_vol += v_upper
        else:
            lower_idx -= 1
            current_vol += v_lower
            
    val = low + lower_idx * bin_size
    vah = low + (upper_idx + 1) * bin_size
    
    return {
        'poc': round(poc, 2),
        'vah': round(vah, 2),
        'val': round(val, 2),
        'total_vol': total_vol
    }
