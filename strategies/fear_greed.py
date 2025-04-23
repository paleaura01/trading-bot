# strategies/fear_greed.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def get_live_trade_signal(fg_index, usdt_balance, btc_balance, fg_fear=35, fg_greed=65):
    """
    Generate a trade signal based on Fear & Greed index
    Modified for Bitcoin accumulation strategy
    
    Args:
        fg_index (int): Current Fear & Greed index value
        usdt_balance (float): Current USDT balance
        btc_balance (float): Current BTC balance
        fg_fear (int): Fear threshold (lower = more fear) - buy signal
        fg_greed (int): Greed threshold (higher = more greed) - sell signal
        
    Returns:
        tuple: (action, amount) where action is 'BUY', 'SELL', 'RESET', or 'HOLD'
    """
    # If we don't have a real fg_index, we'll simulate one for demo
    if fg_index is None:
        # Simulate an index between 0-100
        fg_index = np.random.randint(0, 100)
        logger.info(f"Using simulated Fear & Greed index: {fg_index}")
    
    # Reset condition: If BTC balance is above threshold
    # Increased threshold to accumulate more BTC before reset
    if btc_balance >= 0.015:
        # Modified reset to keep more BTC after reset
        return "RESET", btc_balance
        
    # Buy signal: Index below fear threshold and we have USDT
    # More aggressive buying (75% instead of 50%)
    if fg_index < fg_fear and usdt_balance > 0:
        # Use 75% of available USDT to buy more BTC
        amount = usdt_balance * 0.75
        return "BUY", amount
        
    # Sell signal: Index above greed threshold and we have BTC
    # More conservative selling (25% instead of 50%)
    if fg_index > fg_greed and btc_balance > 0:
        # Sell only 25% of available BTC
        amount = btc_balance * 0.25
        return "SELL", amount
    
    # Default is to hold
    return "HOLD", 0

def run_backtest(start_usdc=100, start_btc=0.001, fg_fear=35, fg_greed=65, days=60):
    """
    Run a backtest of the Bitcoin Accumulation Fear & Greed strategy
    
    Args:
        start_usdc (float): Starting USDT balance
        start_btc (float): Starting BTC balance
        fg_fear (int): Fear threshold (default 35 instead of 40)
        fg_greed (int): Greed threshold (default 65 instead of 60)
        days (int): Number of days to backtest
        
    Returns:
        pd.DataFrame: Backtest results
    """
    # Create date range for backtest
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Initialize DataFrame for results
    results = []
    
    # Initial values
    usdc_balance = start_usdc
    btc_balance = start_btc
    
    # Set a random seed for reproducible results
    np.random.seed(42)
    
    # Initial price around current market price with some variation
    btc_price = 90000 + np.random.normal(0, 2000)
    
    for date in date_range:
        # Simulate price movement (random walk with drift)
        # Slightly more positive drift to reflect long-term BTC appreciation
        price_change = np.random.normal(0.002, 0.022)  # Positive mean drift
        btc_price *= (1 + price_change)
        
        # Simulate Fear & Greed index
        fg_index = np.random.randint(0, 100)
        
        # Calculate portfolio value
        portfolio_value = usdc_balance + (btc_balance * btc_price)
        
        # Get trade signal based on Bitcoin accumulation strategy
        action, amount = get_live_trade_signal(fg_index, usdc_balance, btc_balance, fg_fear, fg_greed)
        
        # Execute trade in simulation
        if action == "BUY":
            # Calculate how much BTC we can buy with the USDT amount
            btc_amount = amount / btc_price
            
            # Update balances
            usdc_balance -= amount
            btc_balance += btc_amount
            
        elif action == "SELL":
            # Calculate USDT we'll receive
            usdt_amount = amount * btc_price
            
            # Update balances
            btc_balance -= amount
            usdc_balance += usdt_amount
            
        elif action == "RESET":
            # Modified reset to keep more BTC
            usdc_balance = 150  # Less USDT
            btc_balance = 0.0032  # More BTC
        
        # Record results
        results.append({
            'date': date,
            'price': btc_price,
            'fg_index': fg_index,
            'action': action,
            'usdc_before': start_usdc if date == date_range[0] else results[-1]['usdc_after'],
            'btc_before': start_btc if date == date_range[0] else results[-1]['btc_after'],
            'usdc_after': usdc_balance,
            'btc_after': btc_balance,
            'portfolio_value': portfolio_value
        })
    
    # Convert results to DataFrame
    df = pd.DataFrame(results)
    
    # Calculate BTC and USD holdings over time
    initial_btc_value = start_btc * df['price'].iloc[0]
    final_btc_value = df['btc_after'].iloc[-1] * df['price'].iloc[-1]
    
    # Log performance metrics
    logger.info(f"Initial Portfolio: {start_usdc + initial_btc_value:.2f} USD")
    logger.info(f"Final Portfolio: {df['portfolio_value'].iloc[-1]:.2f} USD")
    logger.info(f"BTC Accumulated: {df['btc_after'].iloc[-1] - start_btc:.8f} BTC")
    
    return df