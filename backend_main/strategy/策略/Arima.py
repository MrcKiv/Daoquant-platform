
import pandas as pd
import numpy as np
import strategy.mysql_connect as sc
import warnings

try:
    import statsmodels.api as sm
    from statsmodels.tsa.arima.model import ARIMA
except Exception as exc:
    sm = None
    ARIMA = None
    _STATSMODELS_IMPORT_ERROR = exc
else:
    _STATSMODELS_IMPORT_ERROR = None

# Suppress statsmodels warnings
warnings.filterwarnings("ignore")

def arima_main(fund_data, InvestmentRatio, max_hold, start_date, end_date, Optionfactors, sell_policy_list, sid, uid):
    """
    ARIMA + AIC Strategy Main Entry Point
    Target: 000001.SZ (Hardcoded)
    Model: ARIMA(p,0,q), p,q in 0..3, Min AIC
    """
    if _STATSMODELS_IMPORT_ERROR is not None:
        raise RuntimeError(
            f"Strategy 'ARIMA_AIC' is not available in this deployment: {_STATSMODELS_IMPORT_ERROR}"
        )
    
    # 1. Mandatory Data Initialization
    # Must be the first executable line
    sc.database(start_date, end_date, sid, uid, None)
    
    print(f"✅ ARIMA Main Started. SID: {sid}, UID: {uid}, Date: {start_date}-{end_date}")

    # 2. Strategy Constants
    TARGET_CODE = "000001.SH"
    WINDOW_SIZE = 50
    TRANSACTION_COST = 0.0015
    CAPITAL = float(fund_data)
    
    # 3. Data Preparation
    daily_df = sc.df_table_index
    if daily_df is None or daily_df.empty:
        print("⚠️ Daily data is empty.")
        return CAPITAL
        
    # Filter for target stock and sort
    stock_df = daily_df[daily_df['st_code'] == TARGET_CODE].sort_values('trade_date')
    if stock_df.empty:
        print(f"⚠️ No data found for {TARGET_CODE}")
        return CAPITAL

    # Calculate Log Returns
    # r_t = log(P_t) - log(P_{t-1})
    stock_df['log_price'] = np.log(stock_df['close'])
    stock_df['log_ret'] = stock_df['log_price'].diff()
    
    # Drop NaNs created by diff
    data_clean = stock_df.dropna(subset=['log_ret']).reset_index(drop=True)
    
    if len(data_clean) < WINDOW_SIZE:
        print("⚠️ Not enough data for initial window.")
        return CAPITAL
        
    # 4. Simulation Loop
    # We need to simulate trading day by day.
    # To use sc.df_table_transaction etc, we must mimic the recording logic.
    
    cash = CAPITAL
    shares = 0
    total_asset = CAPITAL
    
    # Records for output
    transactions = []
    daily_stats = []
    shareholdings = []
    
    # Trading Loop
    # We walk forward.
    # Prediction for T+1 is made using data up to T.
    # Trade execution happens at T+1 Open (or Close of T+1? Requirement says "Forecast next-day return").
    # Standard backtest: Signal at Close T, Execute at Open T+1, or Close T+1.
    # "Predict next-day return": r_{t+1}.
    # If r_{t+1} > 0, we want to hold the stock during T+1.
    # So we buy at T+1 Open (or T Close if possible).
    # Let's assume execution at T+1 Open to be realistic, or T Close if using closing prices for signal.
    # Given data is daily close, we assume we get signal after close of T.
    # We trade at Open of T+1.
    
    # Iterate through days where we can make a prediction
    # We need at least WINDOW_SIZE data points to train.
    # data_clean index i is valid data point.
    
    # Align dates with Calendar? 
    # We iterate through the data_clean directly which represents trading days.
    
    # Starting index: Window Size.
    # e.g. Window 50. We use 0..49 to predict 50.
    # So loop starts at WINDOW_SIZE.
    
    print("⏳ Starting Walk-forward Loop...")
    
    for i in range(WINDOW_SIZE, len(data_clean)):
        current_date = data_clean.loc[i, 'trade_date']
        prev_date = data_clean.loc[i-1, 'trade_date']
        
        # 1. Training Data (Rolling Window or Expanding?)
        # Requirement: "Initial training window >= 50... Walk-forward... Rolling prediction"
        # Usually Rolling means fixed size window, or at least expanding anchor.
        # "Rolling prediction" often implies fixed or expanding.
        # Given "Walk-forward" and computationally intensive, let's use Fixed Window of 50 or Expanding?
        # Requirement says "Initial >= 50". Let's use Expanding window for better stability, or Fixed 50-100?
        # "Rolling" usually implies moving window. Let's stick to Fixed Window = 50 to match "Rolling" perfectly and save time?
        # Or better, expanding from start.
        # Let's use Fixed Window 100 for balance of speed/info, or just the requirement min 50.
        # Let's use data_clean[:i] (Expanding) for maximum information, but strict Rolling Window 50 is faster.
        # I'll use Expanding Window (all history available) as it's generally more robust for ARIMA,
        # UNLESS performance is critical. Requirement: "Performance warning...".
        # Let's use a fixed large window (e.g. 100) to keep it manageable, or just last 60.
        # Let's use last 60 points.
        
        train_start_idx = max(0, i - 60)
        train_data = data_clean.iloc[train_start_idx:i]['log_ret']
        
        # 2. Model Selection (Grid Search AIC)
        best_aic = float('inf')
        best_order = None
        best_model_res = None
        
        # Grid Search
        # p, q in 0..3
        for p in range(4):
            for q in range(4):
                if p == 0 and q == 0:
                    continue
                try:
                    # ARIMA(p,0,q)
                    model = ARIMA(train_data, order=(p, 0, q))
                    res = model.fit()
                    if res.aic < best_aic:
                        best_aic = res.aic
                        best_order = (p, 0, q)
                        best_model_res = res
                except:
                    continue
        
        # 3. Forecast
        # Predict next step (which corresponds to index i's return)
        pred_ret = 0
        if best_model_res:
            # Statsmodels forecast
            # forecast next 1 step
            pred = best_model_res.forecast(steps=1)
            pred_ret = pred.iloc[0]
        
        # 4. Signal & Execution
        # Interpretation: pred_ret is prediction for period 'i'.
        # We are currently at decision point 'i-1' (conceptually, looking at tomorrow's prediction).
        # Wait, if we use data up to i-1 to predict i.
        # Execution:
        # If pred > 0 -> Hold Long.
        # If pred <= 0 -> Hold Cash.
        
        # We need to adjust position for Day i.
        # Execution price: Open of Day i.
        current_open = data_clean.loc[i, 'open']
        current_close = data_clean.loc[i, 'close']
        
        # Current Holdings check
        # shares > 0 means Long.
        
        target_shares = 0
        if pred_ret > 0:
            # Signal: Full Long
            # Calculate max shares we can buy with current cash (if not already long)
            # If already long, hold.
            
            # Value check
            total_value_est = cash + shares * current_open # Mark to Open
            
            if shares == 0:
                # Buy
                # Cost = current_open * (1 + cost)
                max_buy_val = cash / (1 + TRANSACTION_COST)
                buy_shares = int(max_buy_val / current_open / 100) * 100
                
                if buy_shares > 0:
                    cost = buy_shares * current_open * (1 + TRANSACTION_COST)
                    cash -= cost
                    shares += buy_shares
                    
                    # Record Transaction
                    transactions.append({
                        'st_code': TARGET_CODE,
                        'trade_date': current_date,
                        'trade_type': '买入',
                        'trade_price': current_open,
                        'number_of_transactions': buy_shares,
                        'turnover': cost,
                        'strategy_id': sid,
                        'user_id': uid
                    })
        else:
            # Signal: Empty
            if shares > 0:
                # Sell All
                revenue = shares * current_open * (1 - TRANSACTION_COST)
                cash += revenue
                
                # Record Transaction
                transactions.append({
                    'st_code': TARGET_CODE,
                    'trade_date': current_date,
                    'trade_type': '卖出',
                    'trade_price': current_open,
                    'number_of_transactions': shares,
                    'turnover': revenue,
                    'strategy_id': sid,
                    'user_id': uid
                })
                
                shares = 0
        
        # 5. Daily Settlement (Mark to Market at Close)
        stock_val = shares * current_close
        total_asset = cash + stock_val
        
        # Record Daily Stats
        # 'trade_date', 'balance', 'available', 'reference_market_capitalization', 'assets', 'profit_and_loss', 'profit_and_loss_ratio', 'strategy_id', 'user_id'
        daily_stats.append({
            'trade_date': current_date,
            'balance': cash,
            'available': cash,
            'reference_market_capitalization': stock_val,
            'assets': total_asset,
            'profit_and_loss': total_asset - CAPITAL,
            'profit_and_loss_ratio': (total_asset - CAPITAL) / CAPITAL,
            'strategy_id': sid,
            'user_id': uid,
            'net_value': total_asset / CAPITAL
        })
        
        # Record Shareholding
        if shares > 0:
            shareholdings.append({
                'trade_date': current_date,
                'st_code': TARGET_CODE,
                'number_of_securities': shares,
                'saleable_quantity': shares,
                'cost_price': 0, # Simplified
                'profit_and_loss': 0,
                'profit_and_loss_ratio': 0,
                'latest_value': stock_val,
                'current_price': current_close,
                'strategy_id': sid,
                'user_id': uid
            })

    # 6. Finalize & Save to Global SC Tables
    print("💾 Saving Results...")
    
    if transactions:
        new_tx_df = pd.DataFrame(transactions)
        sc.df_table_transaction = pd.concat([sc.df_table_transaction, new_tx_df], ignore_index=True)
        
    if daily_stats:
        new_stats_df = pd.DataFrame(daily_stats)
        sc.df_table_statistic = pd.concat([sc.df_table_statistic, new_stats_df], ignore_index=True)
        
    if shareholdings:
        new_holds_df = pd.DataFrame(shareholdings)
        sc.df_table_shareholding = pd.concat([sc.df_table_shareholding, new_holds_df], ignore_index=True)

    print(f"🏁 ARIMA Main Finished. Final Asset: {total_asset:.2f}")
    
    # Calculate required metrics for printing (Optional, but good for log check)
    if daily_stats:
        final_ret = (total_asset - CAPITAL) / CAPITAL
        print(f"📈 Cumulative Return: {final_ret*100:.2f}%")
        
    return total_asset

# If executed directly for testing
if __name__ == "__main__":
    import sys
    import os
    import random
    
    # Mock 'strategy.mysql_connect' since we are running standalone
    class MockSC:
        df_table_index = None
        df_table_transaction = pd.DataFrame(columns=['st_code', 'trade_date', 'trade_type', 'trade_price', 'number_of_transactions', 'turnover', 'strategy_id', 'user_id'])
        df_table_statistic = pd.DataFrame(columns=['trade_date', 'balance', 'available', 'reference_market_capitalization', 'assets', 'profit_and_loss', 'profit_and_loss_ratio', 'strategy_id', 'user_id', 'net_value'])
        df_table_shareholding = pd.DataFrame(columns=['trade_date', 'st_code', 'number_of_securities', 'saleable_quantity', 'cost_price', 'profit_and_loss', 'profit_and_loss_ratio', 'latest_value', 'current_price', 'strategy_id', 'user_id'])
        
        def database(self, start_date, end_date, sid, uid, params):
            print(f"MOCK SC: Loading data for {start_date}-{end_date}")
            # Generate Mock Daily Data for 000001.SH
            dates = pd.date_range(start_date, end_date, freq='B')
            data = []
            price = 10.0
            for d in dates:
                # Random walk
                change = (random.random() - 0.5) * 0.1
                price *= (1 + change)
                data.append({
                    'st_code': '000001.SH',
                    'trade_date': d.strftime('%Y%m%d'),
                    'open': price,
                    'close': price * (1 + (random.random()-0.5)*0.01),
                    'high': price * 1.02,
                    'low': price * 0.98,
                    'vol': 10000,
                    'amount': 100000
                })
            self.df_table_index = pd.DataFrame(data)

    # Patch modules
    # We need to ensure 'strategy' module can be imported or patched
    # Since we are inside the file, we can patch global 'sc'
    sc = MockSC()
    
    print("🚀 Running Standalone Test for ARIMA Strategy...")
    
    # Test Parameters
    sid = 888
    uid = 1
    start_date = '20250101'
    end_date = '20250401'
    fund = 1000000
    
    # Execute
    # Note: We need to pass our mocked 'sc' into the function scope? 
    # The function uses 'sc' from global import. 
    # We can rely on the fact that we reassigned 'sc' in this script's global scope 
    # BUT 'arima_main' uses the 'sc' imported at top level.
    # To make it work, we need to monkeypatch the module level 'sc'.
    import sys
    this_module = sys.modules[__name__]
    this_module.sc = sc
    
    final_val = arima_main(fund, 100, 5, start_date, end_date, [], None, sid, uid)
    
    print(f"✅ Test Complete. Final Value: {final_val}")
    print("Transactions:", len(sc.df_table_transaction))
