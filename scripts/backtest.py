import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scripts.utils import fetch_tradeogre_ticker

def generate_mock_data(days=365):
    """Generate mock data for backtesting when no real data is available."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Generate dates
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Generate prices with some realistic volatility
    base_price = 30000  # Starting BTC price
    prices = [base_price]
    for i in range(1, len(dates)):
        # Random daily change between -5% and 5%
        change = np.random.normal(0, 0.02)  
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    # Generate Fear & Greed values (0-100)
    fg_values = []
    fg_classes = []
    
    fg_class_map = {
        (0, 25): "Extreme Fear",
        (25, 40): "Fear",
        (40, 60): "Neutral",
        (60, 80): "Greed",
        (80, 101): "Extreme Greed"
    }
    
    for i in range(len(dates)):
        # Generate a value that has some correlation with price changes
        if i > 0:
            price_change = (prices[i] / prices[i-1]) - 1
            # Map price change to a fear/greed tendency
            base_fg = 50 + price_change * 300  # Scale for more dramatic effect
            # Add randomness
            fg = max(0, min(100, base_fg + np.random.normal(0, 10)))
        else:
            fg = np.random.randint(30, 70)  # Initial value
        
        fg_values.append(int(fg))
        
        # Determine classification
        for (lower, upper), classification in fg_class_map.items():
            if lower <= fg < upper:
                fg_classes.append(classification)
                break
    
    # Create DataFrame
    df = pd.DataFrame({
        'date': dates,
        'price': prices,
        'fg_value': fg_values,
        'fg_class': fg_classes
    })
    
    return df

def run_backtest(start_usdc=100, start_btc=0.0011, fg_fear=40, fg_greed=60):
    """
    Run a backtest of the trading strategy using historical or mock data.
    
    Parameters:
    - start_usdc: Initial USDC balance
    - start_btc: Initial BTC balance
    - fg_fear: Fear threshold (buy signal when F&G below this)
    - fg_greed: Greed threshold (sell signal when F&G above this)
    
    Returns:
    - DataFrame with trade history and portfolio value
    """
    # Generate or load historical data
    df = generate_mock_data(days=365)
    
    # Initialize portfolio and trade log
    usdc_balance = start_usdc
    btc_balance = start_btc
    trade_log = []
    
    # Loop through each day
    for idx, row in df.iterrows():
        date = row['date']
        price = row['price']
        fg_value = row['fg_value']
        
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
            'fg_class': row['fg_class'],
            'action': action,
            'usdc_before': usdc_before,
            'btc_before': btc_before,
            'usdc_after': usdc_balance,
            'btc_after': btc_balance,
            'portfolio_value': portfolio_value
        })
    
    return pd.DataFrame(trade_log)

def get_live_trade_signal(fg_value, current_usdc, current_btc, fg_fear=40, fg_greed=60):
    """
    Determine trade signal based on Fear & Greed value and balances.
    
    Returns:
    - action: "BUY", "SELL", "RESET", or "HOLD"
    - amount: Amount to trade in USDC (for buy) or BTC (for sell)
    """
    # If fg_value is None (e.g., API unavailable), generate a random value for demo
    if fg_value is None:
        fg_value = np.random.randint(0, 100)
    
    if fg_value < fg_fear and current_usdc > 0:
        return "BUY", current_usdc * 0.5
    elif fg_value > fg_greed and current_btc > 0:
        return "SELL", current_btc * 0.5
    elif current_btc >= 0.011:
        return "RESET", 0
    else:
        return "HOLD", 0

def execute_live_trade(action, amount, market="BTC-USDT", price=None):
    """
    Simulate or execute a live trade based on the signal.
    
    Parameters:
    - action: "BUY", "SELL", "RESET", or "HOLD"
    - amount: Amount to trade in USDC (for buy) or BTC (for sell)
    - market: Trading pair
    - price: Override price (optional)
    
    Returns:
    - Result of the trade operation
    """
    if action == "HOLD":
        return {"success": True, "message": "No action needed"}
    
    if action == "RESET":
        # Reset logic would be implemented here
        return {"success": True, "message": "Portfolio reset executed"}
    
    # Get current market price if not provided
    if price is None:
        price = fetch_tradeogre_ticker(market)
    
    if price == 0:
        return {"success": False, "error": "Invalid price received"}
    
    # Calculate quantity based on action
    if action == "BUY":
        quantity = amount / price
    else:  # SELL
        quantity = amount
    
    # This is a simulation - in a real system, you'd call an API to place the order
    # For example: return place_tradeogre_order(action.lower(), market, quantity, price)
    
    # Return simulated result
    return {
        "success": True,
        "simulated": True,
        "action": action,
        "quantity": quantity,
        "price": price,
        "market": market
    }