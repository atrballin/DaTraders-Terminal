import MetaTrader5 as mt5
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
        @staticmethod
        def success(*args, **kwargs): pass
    st = MockSt()

import pandas as pd
from datetime import datetime

def initialize_mt5():
    """Initialize MetaTrader 5 connection."""
    if not mt5.initialize():
        st.error("Failed to initialize MT5. Make sure MetaTrader 5 is installed and running.")
        return False
    return True

def shutdown_mt5():
    """Shutdown MT5 connection."""
    mt5.shutdown()

def get_account_info():
    """Get MT5 account information."""
    account_info = mt5.account_info()
    if account_info is None:
        return None
    
    return {
        "login": account_info.login,
        "server": account_info.server,
        "balance": account_info.balance,
        "equity": account_info.equity,
        "margin": account_info.margin,
        "free_margin": account_info.margin_free,
        "margin_level": account_info.margin_level,
        "profit": account_info.profit,
        "currency": account_info.currency,
        "leverage": account_info.leverage,
        "trade_allowed": account_info.trade_allowed
    }

def get_positions():
    """Get all open positions."""
    positions = mt5.positions_get()
    if positions is None or len(positions) == 0:
        return pd.DataFrame()
    
    positions_list = []
    for pos in positions:
        positions_list.append({
            "Ticket": pos.ticket,
            "Symbol": pos.symbol,
            "Type": "BUY" if pos.type == 0 else "SELL",
            "Volume": pos.volume,
            "Magic": pos.magic,
            "Open Price": pos.price_open,
            "Current Price": pos.price_current,
            "SL": pos.sl,
            "TP": pos.tp,
            "Profit": pos.profit,
            "Time": pd.to_datetime(pos.time, unit='s')
        })
    
    return pd.DataFrame(positions_list)



def resolve_symbol(base_symbol):
    """
    Attempts to find the broker-specific symbol name by trying common suffixes.
    e.g. BTCUSD -> BTCUSDm, BTCUSD.pro, etc.
    """
    if mt5.symbol_select(base_symbol, True):
        return base_symbol
        
    common_suffixes = ["m", ".pro", ".r", "_i", ".c", "c", "micro", "mini"]
    
    # Try appending suffixes
    for suffix in common_suffixes:
        trial = f"{base_symbol}{suffix}"
        if mt5.symbol_select(trial, True):
            return trial
            
    # Try inserting dot before suffix if not present
    for suffix in ["pro", "raw"]:
         trial = f"{base_symbol}.{suffix}"
         if mt5.symbol_select(trial, True):
            return trial
            
    return None

def get_valid_filling_mode(symbol):
    """
    Determines the correct filling mode for a symbol.
    Returns the integer value for type_filling.
    """
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return mt5.ORDER_FILLING_FOK # Default fallback
        
    # Bitmask checks for filling modes
    # 1 (0x1) = SYMBOL_FILLING_FOK
    # 2 (0x2) = SYMBOL_FILLING_IOC
    
    modes = symbol_info.filling_mode
    
    # Priority: FOK -> IOC -> RETURN
    if (modes & 1) != 0:
        return mt5.ORDER_FILLING_FOK
    elif (modes & 2) != 0:
        return mt5.ORDER_FILLING_IOC
        
    return mt5.ORDER_FILLING_RETURN

def place_order(symbol, order_type, volume, price=None, sl=None, tp=None, deviation=20):
    """
    Place a market order.
    order_type: "BUY" or "SELL"
    """
    if not mt5.symbol_select(symbol, True):
        return False, f"Failed to select {symbol}", None
    
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return False, f"Symbol {symbol} not found", None
    
    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            return False, f"Failed to make {symbol} visible", None
    
    # Prepare the request
    point = symbol_info.point
    
    if order_type == "BUY":
        order_type_mt5 = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).ask if price is None else price
    else:
        order_type_mt5 = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).bid if price is None else price
        
    filling_mode = get_valid_filling_mode(symbol)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type_mt5,
        "price": price,
        "deviation": deviation,
        "magic": 234000,
        "comment": "[Atlas Prime]",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    
    if sl is not None:
        # Validate minimum stop level distance
        min_stop_points = symbol_info.trade_stops_level
        min_stop_distance = min_stop_points * point
        
        if order_type == "BUY":
            # For BUY, SL must be below price by at least min_stop_distance
            if price - sl < min_stop_distance:
                # Adjust SL to meet minimum
                sl = price - min_stop_distance - (10 * point)  # Add buffer
        else:
            # For SELL, SL must be above price by at least min_stop_distance
            if sl - price < min_stop_distance:
                # Adjust SL to meet minimum
                sl = price + min_stop_distance + (10 * point)  # Add buffer
        
        import math
        digits = int(-1 * round(math.log10(point))) if point > 0 else 2
        request["sl"] = round(sl, digits)
        
    if tp is not None:
        # Validate minimum stop level distance
        min_stop_points = symbol_info.trade_stops_level
        min_stop_distance = min_stop_points * point
        
        if order_type == "BUY":
            # For BUY, TP must be above price by at least min_stop_distance
            if tp - price < min_stop_distance:
                # Adjust TP to meet minimum
                tp = price + min_stop_distance + (10 * point)  # Add buffer
        else:
            # For SELL, TP must be below price by at least min_stop_distance
            if price - tp < min_stop_distance:
                # Adjust TP to meet minimum
                tp = price - min_stop_distance - (10 * point)  # Add buffer
        
        import math
        digits = int(-1 * round(math.log10(point))) if point > 0 else 2
        request["tp"] = round(tp, digits)
    
    # ----------------------------------------------------
    # VOLUME NORMALIZATION SHIELD
    # ----------------------------------------------------
    # Ensure volume respects broker limits (min, max, step)
    vol_min = symbol_info.volume_min
    vol_max = symbol_info.volume_max
    vol_step = symbol_info.volume_step
    
    # 1. Enforce Min
    if volume < vol_min:
        volume = vol_min
        
    # 2. Enforce Max
    if volume > vol_max:
        volume = vol_max
        
    # 3. Enforce Step (Round to nearest step)
    # E.g. 0.01 step -> round(vol, 2)
    if vol_step > 0:
        steps = round(volume / vol_step)
        volume = steps * vol_step
        # Floating point fix
        import math
        volume = float(f"{volume:.{str(vol_step).split('.')[1].__len__()}f}")
        
    request["volume"] = volume
    # ----------------------------------------------------

    # Send the order
    result = mt5.order_send(request)
    
    # SAFETY SHIELD: Handle cases where the terminal doesn't respond
    if result is None:
        return False, "❌ MT5 Bridge Error: No response from terminal. Check if MT5 is connected and trading is enabled.", None
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        # Map common retcodes to helpful messages
        retcode_messages = {
            10004: "Requote - price has changed",
            10006: "Request rejected",
            10007: "Request canceled by trader",
            10010: "Only part of the request was completed",
            10011: "Request processing error",
            10012: "Request canceled by timeout",
            10013: "Invalid request",
            10014: "Invalid volume in the request",
            10015: "Invalid price in the request",
            10016: "Invalid stops in the request",
            10017: "Trade is disabled",
            10018: "Market is closed",
            10019: "There is not enough money to complete the request",
            10020: "Prices changed",
            10021: "There are no quotes to process the request",
            10022: "Invalid order expiration date in the request",
            10023: "Order state changed",
            10024: "Too frequent requests",
            10025: "No changes in request",
            10026: "Autotrading disabled by server",
            10027: "Autotrading disabled by client terminal",
            10028: "Request locked for processing",
            10029: "Order or position frozen",
            10030: "Invalid order filling type",
            10031: "No connection with the trade server",
            10032: "Operation is allowed only for live accounts",
            10033: "The number of pending orders has reached the limit",
            10034: "Volume limit reached",
            10035: "Invalid or prohibited order type",
            10036: "Position with specified ID already closed",
        }
        
        error_desc = retcode_messages.get(result.retcode, result.comment if result.comment else "Unknown error")
        
        if result.retcode == 10026 or "AutoTrading disabled" in str(result.comment):
            return False, "⚠️ AutoTrading is disabled in MT5! Click the 'Algo Trading' button in your MT5 terminal toolbar to enable it.", None
        
        return False, f"Order failed (code {result.retcode}): {error_desc}", None
    
    return True, f"Order placed successfully! Ticket: {result.order}", result.order

def close_position(ticket):
    """Close a specific position by ticket number."""
    positions = mt5.positions_get(ticket=ticket)
    if positions is None or len(positions) == 0:
        return False, "Position not found"
    
    position = positions[0]
    
    # Determine opposite order type
    if position.type == mt5.ORDER_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(position.symbol).bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(position.symbol).ask
    
    filling_mode = get_valid_filling_mode(position.symbol)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": order_type,
        "position": ticket,
        "price": price,
        "deviation": 20,
        "magic": 234000,
        "comment": "[Atlas Prime] (Close)",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        if "AutoTrading disabled" in result.comment:
             return False, "⚠️ AutoTrading is disabled! Click 'Algo Trading' in MT5 toolbar."
        return False, f"Failed to close: {result.comment}"
    
    return True, "Position closed successfully!"

def get_symbols():
    """Get available trading symbols."""
    symbols = mt5.symbols_get()
    if symbols is None:
        return []
    return [s.name for s in symbols if s.visible]

def capture_screenshot(symbol, timeframe=mt5.TIMEFRAME_M5, width=800, height=600):
    """
    Captures a screenshot of the specified symbol's chart.
    Returns the absolute path to the saved image.
    """
    os.makedirs("data/screenshots", exist_ok=True)
    filename = os.path.abspath(f"data/screenshots/{symbol.replace('.', '_')}_current.png")
    
    # mt5.ScreenShot requires the symbol to be selected and visible
    if not mt5.symbol_select(symbol, True):
        return None
        
    success = mt5.ScreenShot(symbol, timeframe, width, height, filename)
    if success:
        return filename
    return None

def close_all_positions():
    """Close all open positions."""
    positions = mt5.positions_get()
    if positions is None or len(positions) == 0:
        return True, "No open positions to close"
    
    success_count = 0
    fail_count = 0
    errors = []
    
    for pos in positions:
        success, msg = close_position(pos.ticket)
        if success:
            success_count += 1
        else:
            fail_count += 1
            errors.append(f"Ticket {pos.ticket}: {msg}")
            
    if fail_count == 0:
        return True, f"All {success_count} positions closed successfully!"
    else:
        return False, f"Closed {success_count} positions, failed to close {fail_count}. Errors: {'; '.join(errors[:3])}..."

def close_positions_by_symbol(symbol):
    """Close all open positions for a specific symbol."""
    positions = mt5.positions_get(symbol=symbol)
    if positions is None or len(positions) == 0:
        return True, f"No open positions to close for {symbol}"
    
    success_count = 0
    fail_count = 0
    errors = []
    
    for pos in positions:
        success, msg = close_position(pos.ticket)
        if success:
            success_count += 1
        else:
            fail_count += 1
            errors.append(f"Ticket {pos.ticket}: {msg}")
            
    if fail_count == 0:
        return True, f"All {success_count} positions for {symbol} closed successfully!"
    else:
        return False, f"Closed {success_count} positions for {symbol}, failed to close {fail_count}. Errors: {'; '.join(errors[:3])}..."

def calculate_max_lots(symbol, risk_percent, sl_price, order_type, account_balance):
    """
    Calculate max lot size based on risk percentage and stop loss.
    """
    if risk_percent <= 0 or risk_percent > 100:
        return 0, "Invalid risk percentage"
        
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return 0, f"Symbol {symbol} not found"
        
    # Get current price
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return 0, "Could not get current price"
        
    if order_type == "BUY":
        entry_price = tick.ask
        if sl_price >= entry_price:
            return 0, "Stop Loss must be below Entry Price for BUY"
        price_diff = entry_price - sl_price
    else: # SELL
        entry_price = tick.bid
        if sl_price <= entry_price:
            return 0, "Stop Loss must be above Entry Price for SELL"
        price_diff = sl_price - entry_price
        
    risk_amount = account_balance * (risk_percent / 100)
    
    if symbol_info.point == 0:
        return 0, "Invalid symbol point value"
        
    points = price_diff / symbol_info.point
    tick_value = symbol_info.trade_tick_value
    
    if tick_value == 0:
         return 0, "Could not determine tick value"
         
    loss_per_lot = points * tick_value
    
    if loss_per_lot == 0:
        return 0, "Zero loss calculated"
        
    lots = risk_amount / loss_per_lot
    
    # Normalize lots
    step = symbol_info.volume_step
    if step > 0:
        lots = round(lots / step) * step
        
    # Clamp to limits
    lots = max(symbol_info.volume_min, min(lots, symbol_info.volume_max))
    
    return float(f"{lots:.2f}"), f"Calculated based on ${risk_amount:.2f} risk"

def calculate_margin_based_lots(symbol, margin_percent, account_balance):
    """
    Calculate lots to use exactly X% of available Free Margin.
    margin_percent: e.g. 80.0
    """
    if margin_percent <= 0 or margin_percent > 100:
        return 0, "Invalid margin percentage"
        
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return 0, f"Symbol {symbol} not found"
        
    # Free Margin is typically what determines 'how much more' we can open.
    # But usually 'margin_percent' implies % of Balance or Equity dedicated to margin?
    # User said "Use 80Percent Margin". We'll interpret as 80% of Free Margin.
    
    acc_info = mt5.account_info()
    if not acc_info:
        return 0, "Could not get account info"
        
    free_margin = acc_info.margin_free
    
    # Target Margin = Free Margin * 0.80
    target_margin = free_margin * (margin_percent / 100.0)
    
    # We need to find the Lot Size X where OrderMargin(X) ~= Target Margin
    # MT5 has order_calc_margin(action, symbol, volume, price)
    
    # We can approximate linear relationship: Margin(1 Lot) * X = Target
    # Let's check margin for 1.0 lot
    
    tick = mt5.symbol_info_tick(symbol)
    price = tick.ask # Assumption for Long
    
    margin_1_lot = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, symbol, 1.0, price)
    
    if margin_1_lot is None or margin_1_lot == 0:
        # Fallback or error
        return 0, "Could not calculate margin requirements"
        
    lots = target_margin / margin_1_lot
    
    # Normalize
    step = symbol_info.volume_step
    if step > 0:
        lots = round(lots / step) * step
        
    # Clamp
    lots = max(symbol_info.volume_min, min(lots, symbol_info.volume_max))
    
    return float(f"{lots:.2f}"), f"Using {margin_percent}% Free Margin (Est. ${target_margin:.2f})"

def close_positions_by_type(position_type):
    """
    Close all positions of a specific type.
    position_type: "BUY" or "SELL"
    """
    positions = mt5.positions_get()
    if positions is None or len(positions) == 0:
        return True, "No open positions to close"
        
    target_type = mt5.ORDER_TYPE_BUY if position_type == "BUY" else mt5.ORDER_TYPE_SELL
    
    success_count = 0
    fail_count = 0
    errors = []
    
    # Filter positions by type
    target_positions = [p for p in positions if p.type == target_type]
    
    if not target_positions:
        return True, f"No open {position_type} positions found."
        
    for pos in target_positions:
        success, msg = close_position(pos.ticket)
        if success:
            success_count += 1
        else:
            fail_count += 1
            errors.append(f"Ticket {pos.ticket}: {msg}")
            
    if fail_count == 0:
        return True, f"All {success_count} {position_type} positions closed successfully!"
    else:
        return False, f"Closed {success_count} {position_type} positions, failed to close {fail_count}. Errors: {'; '.join(errors[:3])}..."

def close_positions_by_profit_status(status):
    """
    Close positions based on profit status.
    status: "PROFIT" (close > 0) or "LOSS" (close < 0)
    """
    positions = mt5.positions_get()
    if positions is None or len(positions) == 0:
        return True, "No open positions to close"
    
    success_count = 0
    fail_count = 0
    errors = []
    
    # Filter positions
    target_positions = []
    for p in positions:
        if status == "PROFIT" and p.profit > 0:
            target_positions.append(p)
        elif status == "LOSS" and p.profit < 0:
            target_positions.append(p)
            
    if not target_positions:
        return True, f"No positions in {status} found."
        
    for pos in target_positions:
        success, msg = close_position(pos.ticket)
        if success:
            success_count += 1
        else:
            fail_count += 1
            errors.append(f"Ticket {pos.ticket}: {msg}")
            
    if fail_count == 0:
        return True, f"All {success_count} {status} positions closed successfully!"
    else:
        return False, f"Closed {success_count} positions, failed to close {fail_count}. Errors: {'; '.join(errors[:3])}..."

def modify_position(ticket, sl, tp):
    """
    Modify SL and TP for a specific position.
    """
    # Get position details to ensure it exists
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        return False, "Position not found"
    
    pos = positions[0]
    symbol = pos.symbol
    
    # Get symbol info for proper rounding
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return False, f"Symbol {symbol} info not available"
    
    point = symbol_info.point
    digits = symbol_info.digits
    
    # Aggressive Retry Loop for SL/TP Application (Find the Minimum)
    max_retries = 15 # Increased retries
    # Dynamic increment based on point value
    # If point is 0.01, increment by 0.05
    # If point is 0.00001, increment by 0.0005
    points_increment = 100 
    search_buffer = 300 # Start a bit tighter to try for better fills
    
    for attempt in range(max_retries):
        # Fresh tick for actual distance validation
        tick = mt5.symbol_info_tick(symbol)
        if not tick: 
            import time
            time.sleep(0.1)
            continue
        
        # VALID PRICE MAPPING:
        # Buy Position SL is triggered by BID
        # Sell Position SL is triggered by ASK
        validation_price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        
        # Calculate broker's minimum required distance
        broker_min_points = symbol_info.trade_stops_level if symbol_info and symbol_info.trade_stops_level > 0 else 50
        
        # We must respect the broker_min_points at the very least.
        # But for VOC/VOB 550, they often require much more than trade_stops_level indicates.
        required_dist = (max(broker_min_points, search_buffer)) * point
        
        final_sl = pos.sl
        if sl is not None and sl != 0:
            final_sl = float(sl)
            # Ensure we respect the broker's minimum floor relative to CURRENT price
            if pos.type == mt5.ORDER_TYPE_BUY:
                if validation_price - final_sl < required_dist:
                    final_sl = validation_price - required_dist
            else:
                if final_sl - validation_price < required_dist:
                    final_sl = validation_price + required_dist
            final_sl = round(final_sl, digits)
        
        # Handle TP
        final_tp = pos.tp
        if tp is not None and tp != 0:
            # Similar validation for TP
            if pos.type == mt5.ORDER_TYPE_BUY:
                if float(tp) - validation_price < required_dist:
                    final_tp = validation_price + required_dist
                else:
                    final_tp = float(tp)
            else:
                if validation_price - float(tp) < required_dist:
                    final_tp = validation_price - required_dist
                else:
                    final_tp = float(tp)
            final_tp = round(final_tp, digits)
        
        # If no change needed, return success
        if abs(final_sl - pos.sl) < 0.0000001 and abs(final_tp - pos.tp) < 0.0000001:
            return True, "No modification needed (Already at target/min distance)"

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": ticket,
            "sl": final_sl,
            "tp": final_tp,
            "magic": 234000,
            "comment": f"[Atlas Prime] (Mod v2-{attempt+1})"
        }
        
        result = mt5.order_send(request)
        
        if result is None:
            import time
            time.sleep(0.1)
            continue
            
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            return True, f"Modified successfully (Attempt {attempt+1}, Final Buffer: {search_buffer})"
            
        # If still invalid, push the search buffer further
        if result.retcode in [10016, 10015, 10004, 10013]:
            search_buffer += points_increment
            import time
            time.sleep(0.05) # Faster cycling
        else:
            return False, f"Permanent failure: {result.comment} (code {result.retcode})"
            
    return False, f"Failed to find valid SL after {max_retries} hunting attempts (Last Buffer: {search_buffer})"

def modify_all_positions(sl, tp, filter_symbol=None):
    """
    Modify SL/TP for all positions, optionally filtered by symbol.
    """
    positions = mt5.positions_get()
    if positions is None or len(positions) == 0:
        return True, "No open positions to modify"
        
    success_count = 0
    fail_count = 0
    errors = []
    
    # Filter if needed
    target_positions = positions
    if filter_symbol:
        target_positions = [p for p in positions if p.symbol == filter_symbol]
        
    if not target_positions:
        return True, f"No positions found matching criteria."
        
    for pos in target_positions:
        target_sl = float(sl)
        target_tp = float(tp)
        
        success, msg = modify_position(pos.ticket, target_sl, target_tp)
        if success:
            success_count += 1
        else:
            fail_count += 1
            errors.append(f"Ticket {pos.ticket}: {msg}")
            
    if fail_count == 0:
        return True, f"Modified {success_count} positions successfully!"
    else:
        return False, f"Modified {success_count}, Failed {fail_count}. Errors: {'; '.join(errors[:3])}..."

def move_all_stops_to_breakeven(filter_symbol=None):
    """
    Move SL to the Open Price (Breakeven) for all positions.
    """
    positions = mt5.positions_get()
    if positions is None or len(positions) == 0:
        return True, "No open positions to modify"
        
    success_count = 0
    fail_count = 0
    errors = []
    
    # Filter if needed
    target_positions = positions
    if filter_symbol:
        target_positions = [p for p in positions if p.symbol == filter_symbol]
        
    if not target_positions:
        return True, f"No positions found matching criteria."
        
    for pos in target_positions:
        # Check if SL is already at open price (approximate check for floats)
        if abs(pos.sl - pos.price_open) < 0.00001:
            continue # Already at breakeven
            
        # Check actual profitability before attempting valid Move
        is_buy = pos.type == mt5.ORDER_TYPE_BUY
        current_price = pos.price_current
        open_price = pos.price_open
        
        # Valid logic: BE is only possible if price has moved in favor
        # For BUY: Current > Open
        # For SELL: Current < Open
        
        in_profit = False
        if is_buy and current_price > open_price:
            in_profit = True
        elif not is_buy and current_price < open_price:
            in_profit = True
            
        if not in_profit:
            fail_count += 1
            errors.append(f"Ticket {pos.ticket}: Trade in loss/entry, cannot set BE")
            continue
            
        # Move SL to Entry, Keep TP same
        success, msg = modify_position(pos.ticket, pos.price_open, pos.tp)
        if success:
            success_count += 1
        else:
            fail_count += 1
            errors.append(f"Ticket {pos.ticket}: {msg}")
            
    if fail_count == 0:
        if success_count == 0:
             return True, "No suitable trades (already at BE or not in profit)."
        return True, f"Moved {success_count} positions to Breakeven successfully!"
    else:
        return False, f"Moved {success_count}, Failed {fail_count}. Errors: {'; '.join(errors[:3])}..."

def get_initial_order_sl(symbol, ticket):
    """
    Retrieves the initial Stop Loss of an order from history.
    """
    # Fetch history for the last 24 hours to find the opening deal
    from datetime import datetime, timedelta
    from_date = datetime.now() - timedelta(hours=24)
    history = mt5.history_orders_get(from_date, datetime.now(), group=f"*{symbol}*")
    
    if history:
        for order in history:
            if order.ticket == ticket or order.position_id == ticket:
                return order.sl
    return 0

def manage_gold_trailing_stops(symbol_substring="XAU"):
    """
    Implements:
    - 1:1 Profit (Relative to Initial Risk) -> Move to BE
    - N:1 Profit -> Move SL to (N-1):1 Profit (e.g. 2:1 -> Trail to 1:1)
    """
    positions = mt5.positions_get()
    if not positions:
        return
        
    for pos in positions:
        if symbol_substring.upper() not in pos.symbol.upper() and "GOLD" not in pos.symbol.upper():
            continue
            
        entry = pos.price_open
        current = pos.price_current
        is_buy = pos.type == mt5.ORDER_TYPE_BUY
        
        # 1. Get Initial Risk (Distance to Initial SL)
        # We try to get initial SL from history if possible, fallback to current SL
        initial_sl = get_initial_order_sl(pos.symbol, pos.ticket)
        if initial_sl == 0:
            initial_sl = pos.sl
            
        if initial_sl == 0: # Still zero? Can't calculate R
            continue
            
        initial_risk = abs(entry - initial_sl)
        if initial_risk == 0:
            continue
            
        # 2. Calculate current profit in R units
        profit_dist = (current - entry) if is_buy else (entry - current)
        profit_r = profit_dist / initial_risk
        
        target_sl = None
        
        # 3. Rule: BE at 1:1
        if profit_r >= 1.0:
            target_sl = entry
            
            # Rule: Trail (N-1):1 at N:1
            # 2:1 -> 1:1 SL | 3:1 -> 2:1 SL | etc.
            if profit_r >= 2.0:
                 locked_r = float(int(profit_r)) - 1.0
                 locked_dist = locked_r * initial_risk
                 target_sl = entry + locked_dist if is_buy else entry - locked_dist
        
        # 4. Apply Update
        if target_sl is not None:
            should_update = False
            if is_buy:
                if target_sl > (pos.sl + 0.01):
                    should_update = True
            else:
                if pos.sl == 0 or target_sl < (pos.sl - 0.01):
                    should_update = True
                    
            if should_update:
                modify_position(pos.ticket, target_sl, pos.tp)

def place_pending_order(symbol, order_type, volume, price, sl=None, tp=None, deviation=20):
    """
    Place a pending order (BUY_STOP or SELL_STOP).
    """
    if not mt5.symbol_select(symbol, True):
        return False, f"Failed to select {symbol}", None
    
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return False, f"Symbol {symbol} not found", None
    
    order_type_mt5 = mt5.ORDER_TYPE_BUY_STOP if "BUY" in order_type.upper() else mt5.ORDER_TYPE_SELL_STOP
    
    filling_mode = get_valid_filling_mode(symbol)
    
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": order_type_mt5,
        "price": price,
        "deviation": deviation,
        "magic": 234001, # Separate magic for news
        "comment": "[Atlas Prime] (Pending)",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    
    if sl is not None:
        request["sl"] = sl
    if tp is not None:
        request["tp"] = tp
    
    result = mt5.order_send(request)
    if result is None:
        return False, "❌ No response from MT5", None
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"Pending Failed: {result.comment}", None
        
    return True, f"Pending placed! Ticket: {result.order}", result.order

def cancel_pending_orders(symbol=None, magic=234001):
    """
    Cancel all pending orders, optionally filtered by symbol and magic.
    """
    orders = mt5.orders_get()
    if not orders:
        return True, "No pending orders to cancel"
        
    success_count = 0
    fail_count = 0
    
    for order in orders:
        if (symbol is None or order.symbol == symbol) and (magic is None or order.magic == magic):
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": order.ticket
            }
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                success_count += 1
            else:
                fail_count += 1
                
    return True, f"Cancelled {success_count} orders, {fail_count} failed."

def get_history_24h():
    """
    Fetch trade deals from the last 24 hours and calculate total profit.
    Returns: { 'deals': [...], 'total_profit': float }
    """
    from datetime import datetime, timedelta
    
    # Initialize if needed
    if not mt5.initialize():
         return {"deals": [], "total_profit": 0.0, "error": "MT5 not initialized"}

    # Time range: Last 24 hours
    to_date = datetime.now()
    from_date = to_date - timedelta(hours=24)
    
    # Get deals (executed trades)
    deals = mt5.history_deals_get(from_date, to_date)
    
    if deals is None:
        return {"deals": [], "total_profit": 0.0}

    deal_list = []
    total_profit = 0.0
    
    for deal in deals:
        # entry types: 
        # DEAL_ENTRY_IN (0), DEAL_ENTRY_OUT (1), DEAL_ENTRY_INOUT (2)
        
        # We only want to list deals that have a profit impact (OUT or INOUT)
        # Entry (IN) deals have 0 profit and just clutter the log
        if deal.entry not in [1, 2]:
            continue

        net_profit = deal.profit + deal.commission + deal.swap
        total_profit += net_profit
             
        deal_list.append({
            "ticket": deal.ticket,
            "order": deal.order,
            "time": datetime.fromtimestamp(deal.time).strftime('%Y-%m-%d %H:%M:%S'),
            "symbol": deal.symbol,
            "type": "BUY" if deal.type == 0 else "SELL",
            "entry": "OUT" if deal.entry == 1 else "IN/OUT",
            "volume": deal.volume,
            "price": deal.price,
            "profit": round(net_profit, 2),
            "commission": round(deal.commission, 2),
            "swap": round(deal.swap, 2),
            "comment": deal.comment,
            "magic": deal.magic
        })
    
    # Sort by profit descending (Highest Profit to Biggest Loss)
    deal_list.sort(key=lambda x: x['profit'], reverse=True)
    
    return {
        "deals": deal_list,
        "total_profit": round(total_profit, 2)
    }
