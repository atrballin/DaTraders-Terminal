# MT5 Trading View for ProTrade Dashboard
# This will be inserted into app.py

elif option == "Trading":
    st.markdown('<h2 class="industrial-header">⚡ MT5 Live Trading Terminal</h2>', unsafe_allow_html=True)
    
    try:
        from src.mt5_trading import (
            initialize_mt5, shutdown_mt5, get_account_info,
            get_positions, place_order, close_position, get_symbols
        )
        
        # Initialize MT5
        if 'mt5_initialized' not in st.session_state:
            st.session_state['mt5_initialized'] = False
        
        if not st.session_state['mt5_initialized']:
            with st.spinner("Connecting to MetaTrader 5..."):
                if initialize_mt5():
                    st.session_state['mt5_initialized'] = True
                    st.success("✅ Connected to MT5 successfully!")
                else:
                    st.error("❌ Failed to connect to MT5. Please ensure:")
                    st.info("""
                    1. MetaTrader 5 is installed and running
                    2. You're logged into your MT5 account  
                    3. Python 3.11 or lower is being used (Python 3.14 has compatibility issues)
                    
                    **To fix**: Install Python 3.11 and reinstall MT5: `pip install MetaTrader5`
                    """)
                    st.stop()
        
        # Account Information Section
        st.markdown("### 💼 Account Overview")
        account_info = get_account_info()
        
        if account_info:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Balance", f"${account_info['balance']:,.2f}")
            with col2:
                profit_color = "normal" if account_info['profit'] >= 0 else "inverse"
                st.metric("Equity", f"${account_info['equity']:,.2f}", 
                         delta=f"${account_info['profit']:,.2f}")
            with col3:
                st.metric("Free Margin", f"${account_info['free_margin']:,.2f}")
            with col4:
                st.metric("Margin Level", f"{account_info['margin_level']:.2f}%")
            
            with st.expander("📊 Full Account Details"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Login:** {account_info['login']}")
                    st.write(f"**Server:** {account_info['server']}")
                    st.write(f"**Currency:** {account_info['currency']}")
                with col_b:
                    st.write(f"**Leverage:** 1:{account_info['leverage']}")
                    st.write(f"**Trade Allowed:** {'✅ Yes' if account_info['trade_allowed'] else '❌ No'}")
                    st.write(f"**Margin Used:** ${account_info['margin']:,.2f}")
        
        st.markdown("---")
        
        # Trading Interface
        st.markdown("### 🎯 Place New Order")
        
        col_trade1, col_trade2, col_trade3 = st.columns([2, 1, 1])
        
        with col_trade1:
            symbols = get_symbols()
            if symbols:
                symbol = st.selectbox("Symbol", symbols[:50], index=0 if symbols else None)
            else:
                st.warning("No symbols available")
                symbol = st.text_input("Enter Symbol", "EURUSD")
        
        with col_trade2:
            order_type = st.selectbox("Type", ["BUY", "SELL"])
        
        with col_trade3:
            volume = st.number_input("Volume (Lots)", min_value=0.01, max_value=100.0, value=0.1, step=0.01)
        
        col_sl, col_tp = st.columns(2)
        with col_sl:
            sl = st.number_input("Stop Loss (0 = None)", min_value=0.0, value=0.0, step=0.0001, format="%.5f")
        with col_tp:
            tp = st.number_input("Take Profit (0 = None)", min_value=0.0, value=0.0, step=0.0001, format="%.5f")
        
        if st.button(f"🚀 Execute {order_type} Order", type="primary"):
            sl_value = sl if sl > 0 else None
            tp_value = tp if tp > 0 else None
            
            result = place_order(symbol, order_type, volume, sl=sl_value, tp=tp_value)
            success, message, ticket_id = result if (result and len(result) == 3) else (False, "Order Error", None)
            
            if success:
                # trading_view.py is injected into app.py, so it has access to send_trade_notification
                try: send_trade_notification(symbol, order_type, ticket_id)
                except: pass
                st.success(message)
                st.balloons()
            else:
                st.error(message)
        
        st.markdown("---")
        
        # Open Positions
        st.markdown("### 📈 Open Positions")
        positions_df = get_positions()
        
        if not positions_df.empty:
            # Color code profit
            def highlight_profit(val):
                color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
                return f'color: {color}; font-weight: bold'
            
            styled_df = positions_df.style.applymap(highlight_profit, subset=['Profit'])
            st.dataframe(styled_df, use_container_width=True)
            
            st.markdown("#### Close Position")
            ticket_to_close = st.number_input("Enter Ticket Number to Close", min_value=1, step=1)
            
            if st.button("❌ Close Position", type="secondary"):
                success, message = close_position(ticket_to_close)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        else:
            st.info("📭 No open positions")
        
        # Disconnect button
        if st.button("🔌 Disconnect MT5"):
            shutdown_mt5()
            st.session_state['mt5_initialized'] = False
            st.success("Disconnected from MT5")
            st.rerun()
    
    except ImportError:
        st.error("❌ MetaTrader5 library not installed!")
        st.info("""
        **Installation Steps:**
        
        1. **Check Python Version** (must be 3.11 or lower):
           ```
           python --version
           ```
        
        2. **Install MT5 library**:
           ```
           pip install MetaTrader5
           ```
        
        3. **Install MetaTrader 5 platform** from: https://www.metatrader5.com/
        
        4. **Restart the application**
        
        **Note:** Your current Python version is 3.14.2, which is NOT compatible with MT5.
        You'll need to install Python 3.11 or use a virtual environment.
        """)
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.exception(e)
