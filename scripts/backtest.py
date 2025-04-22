import pandas as pd
import numpy as np
from scripts.utils import (
    fetch_historical_prices, 
    fetch_fear_greed, 
    fetch_tradeogre_ticker,
    prepare_price_data,
    prepare_fg_data
)

def backtest(price_df, fg_df, start_usdc=100, start_btc=0.0011, fg_fear=40, fg_greed=60):
    """
    Run a backtest of the trading strategy using historical data.
    
    Parameters:
    - price_df: DataFrame with price data
    - fg_df: DataFrame with Fear & Greed index data
    - start_usdc: Initial USDC balance
    - start_btc: Initial BTC balance
    - fg_fear: Fear threshold (buy signal when F&G below this)
    - fg_greed: Greed threshold (sell signal when F&G above this)
    
    Returns:
    - DataFrame with trade history and portfolio value
    """
    # Merge price and Fear & Greed data by date
    merged_df = pd.merge_asof(
        price_df.sort_values('date'),
        fg_df.sort_values('date'),
        on='date',
        direction='nearest'
    )
    
    # Initialize portfolio and trade log
    usdc_balance = start_usdc
    btc_balance = start_btc
    trade_log = []
    
    # Loop through each day
    for idx, row in merged_df.iterrows():
        date = row['date']
        price = row['price']
        fg_value = row['value']
        
        # Calculate current portfolio value in USD
        portfolio_value = usdc_balance + (btc_balance * price)
        
        # Record for this day before any trades
        action = "HOLD"
        usdc_before = usdc_balance
        btc_before = btc_balance
        
        # Apply trading strategy based on Fear & Greed index
        if fg_value < fg_fear and usdc_balance > 0:  # Fear - Buy BTC
            buy_amount_usdc = usdc_balance * 0.5  # Use 50% of USDC
            btc_bought = buy_amount_usdc / price
            btc_balance += btc_bought
            usdc_balance -= buy_amount_usdc
            action = "BUY"
        elif fg_value > fg_greed and btc_balance > 0:  # Greed - Sell BTC
            sell_amount_btc = btc_balance * 0.5  # Sell 50% of BTC
            usdc_gained = sell_amount_btc * price
            btc_balance -= sell_amount_btc
            usdc_balance += usdc_gained
            action = "SELL"
        
        # Reset baseline when reaching BTC threshold
        if btc_balance >= 0.011:
            usdc_balance = 200
            btc_balance = 0.0022
            action = "RESET"
        
        # Add to trade log
        trade_log.append({
            'date': date,
            'price': price,
            'fg_value': fg_value,
            'fg_class': row.get('value_classification', ''),
            'action': action,
            'usdc_before': usdc_before,
            'btc_before': btc_before,
            'usdc_after': usdc_balance,
            'btc_after': btc_balance,
            'portfolio_value': portfolio_value
        })
    
    return pd.DataFrame(trade_log)


def run_backtest(force_refresh=False, **kwargs):
    """
    Fetch data and run a backtest with the specified parameters.
    """
    # Get historical data
    price_data = fetch_historical_prices(force_refresh=force_refresh)
    fg_data = fetch_fear_greed(force_refresh=force_refresh)
    
    # Prepare DataFrames
    price_df = prepare_price_data(price_data)
    fg_df = prepare_fg_data(fg_data)
    
    # Run backtest
    results = backtest(price_df, fg_df, **kwargs)
    return results


def get_live_trade_signal(fear_greed_value, current_usdc, current_btc, fg_fear=40, fg_greed=60):
    """
    Determine trade signal based on current Fear & Greed value and balances.
    
    Returns:
    - action: "BUY", "SELL", "RESET", or "HOLD"
    - amount: Amount to trade in USDC (for buy) or BTC (for sell)
    """
    if fear_greed_value < fg_fear and current_usdc > 0:
        return "BUY", current_usdc * 0.5
    elif fear_greed_value > fg_greed and current_btc > 0:
        return "SELL", current_btc * 0.5
    elif current_btc >= 0.011:
        return "RESET", 0
    else:
        return "HOLD", 0


def execute_live_trade(action, amount, market="BTC-USDC"):
    """
    Execute a live trade based on the signal.
    
    Parameters:
    - action: "BUY", "SELL", "RESET", or "HOLD"
    - amount: Amount to trade in USDC (for buy) or BTC (for sell)
    
    Returns:
    - Result of the trade operation
    """
    if action == "HOLD":
        return {"success": True, "message": "No action needed"}
    
    if action == "RESET":
        # Reset logic would be implemented here
        return {"success": True, "message": "Portfolio reset executed"}
    
    # Get current market price
    ticker = fetch_tradeogre_ticker(market)
    if not ticker.get("success", True):
        return {"success": False, "error": "Failed to fetch current price"}
    
    current_price = float(ticker.get("price", 0))
    if current_price == 0:
        return {"success": False, "error": "Invalid price received"}
    
    # Calculate quantity based on action
    if action == "BUY":
        quantity = amount / current_price
    else:  # SELL
        quantity = amount
    
    # Place order through TradeOgre API (commented out for safety)
    # return place_tradeogre_order(action.lower(), market, quantity, current_price)
    
    # Return simulated result for now
    return {
        "success": True,
        "simulated": True,
        "action": action,
        "quantity": quantity,
        "price": current_price,
        "market": market
    }