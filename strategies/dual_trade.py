# strategies/dual_trade.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DualTradeStrategy:
    """
    Dual-Trade strategy - places both buy and sell orders simultaneously
    Modified for Bitcoin accumulation
    """
    
    def __init__(self, base_btc=0.001, usdt_reserve=100, buy_discount=4, sell_premium=4, reinvest_rate=50):
        """
        Initialize the Dual-Trade strategy
        
        Args:
            base_btc (float): Base BTC holding
            usdt_reserve (float): USDT reserve
            buy_discount (float): Buy discount percentage (increased from 3 to 4)
            sell_premium (float): Sell premium percentage (increased from 2 to 4)
            reinvest_rate (float): Reinvestment rate percentage (increased from 20 to 50)
        """
        self.base_btc = base_btc
        self.usdt_reserve = usdt_reserve
        self.buy_discount = buy_discount / 100.0  # Convert to decimal
        self.sell_premium = sell_premium / 100.0  # Convert to decimal
        self.reinvest_rate = reinvest_rate / 100.0  # Convert to decimal
        
    def generate_orders(self, current_price):
        """
        Generate buy and sell orders based on strategy parameters
        Modified for Bitcoin accumulation
        
        Args:
            current_price (float): Current BTC price
            
        Returns:
            tuple: (buy_order, sell_order) dictionaries
        """
        # Calculate buy and sell prices
        buy_price = current_price * (1 - self.buy_discount)
        sell_price = current_price * (1 + self.sell_premium)
        
        # Calculate order sizes (in BTC)
        # Buy order: We use 70% of USDT reserve (increased from 50%)
        buy_usdt_amount = self.usdt_reserve * 0.7
        buy_btc_amount = buy_usdt_amount / buy_price
        
        # Sell order: We use 30% of base BTC (decreased from 50%)
        sell_btc_amount = self.base_btc * 0.3
        
        # Create order dictionaries
        buy_order = {
            'type': 'BUY',
            'price': buy_price,
            'btc_amount': buy_btc_amount,
            'usdt_amount': buy_usdt_amount
        }
        
        sell_order = {
            'type': 'SELL',
            'price': sell_price,
            'btc_amount': sell_btc_amount,
            'usdt_amount': sell_btc_amount * sell_price
        }
        
        return buy_order, sell_order
    
    def run_backtest(self, days=30, initial_price=90000):
        """
        Run a backtest of the Dual-Trade strategy with Bitcoin accumulation focus
        
        Args:
            days (int): Number of days to backtest
            initial_price (float): Initial BTC price (updated to 90000)
            
        Returns:
            tuple: (results_df, final_btc, final_usdt) 
        """
        # Create date range for backtest
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Initialize lists for results
        results = []
        
        # Initialize balances
        btc_balance = self.base_btc
        usdt_balance = self.usdt_reserve
        
        # Set initial price
        btc_price = initial_price
        
        # Set a random seed for reproducible results
        np.random.seed(42)
        
        for date in date_range:
            # Simulate daily price movement with more positive drift
            daily_change = np.random.normal(0.002, 0.023)  # Increased mean drift
            btc_price *= (1 + daily_change)
            
            # Calculate portfolio value
            portfolio_value = usdt_balance + (btc_balance * btc_price)
            
            # Generate orders for this day
            buy_order, sell_order = self.generate_orders(btc_price)
            
            # Determine if orders would be filled based on price movement
            # Assuming a price range during the day
            day_low = btc_price * (1 - abs(np.random.normal(0, 0.017)))  # Daily low
            day_high = btc_price * (1 + abs(np.random.normal(0, 0.017)))  # Daily high
            
            # Check if buy order would be filled (price dipped below buy price)
            buy_filled = day_low <= buy_order['price']
            
            # Check if sell order would be filled (price spiked above sell price)
            sell_filled = day_high >= sell_order['price']
            
            # Initialize action for this day
            action = "HOLD"
            trade_price = btc_price  # Default to current price
            
            # Process orders if filled - BTC accumulation strategy prioritizes buys
            # If both would fill, prioritize buys (changed from previous version)
            if buy_filled and sell_filled:
                # Prioritize buy over sell for BTC accumulation
                buy_filled = True
                sell_filled = False
                logger.info(f"Both orders would fill - prioritizing BUY for BTC accumulation")
                
            if buy_filled:
                # Buy order filled
                btc_gained = buy_order['btc_amount']
                usdt_spent = buy_order['usdt_amount']
                
                # Update balances
                btc_balance += btc_gained
                usdt_balance -= usdt_spent
                
                action = "BUY"
                trade_price = buy_order['price']
                
            elif sell_filled:
                # Sell order filled
                btc_sold = sell_order['btc_amount']
                usdt_gained = sell_order['usdt_amount']
                
                # Update balances
                btc_balance -= btc_sold
                usdt_balance += usdt_gained
                
                # Higher reinvestment rate - more goes into new buys
                profit = usdt_gained - (btc_sold * btc_price)
                reinvest_amount = profit * self.reinvest_rate
                
                # Add reinvestment to USDT balance (rest is profit taken)
                usdt_balance += reinvest_amount
                
                action = "SELL"
                trade_price = sell_order['price']
                
            # Record results
            results.append({
                'date': date,
                'price': btc_price,
                'action': action,
                'buy_price': buy_order['price'],
                'sell_price': sell_order['price'],
                'btc_balance': btc_balance,
                'usdt_balance': usdt_balance,
                'portfolio_value': portfolio_value
            })
        
        # Convert results to DataFrame
        df = pd.DataFrame(results)
        
        # Log BTC accumulation metrics
        initial_btc = self.base_btc
        final_btc = btc_balance
        btc_accumulated = final_btc - initial_btc
        
        logger.info(f"Initial BTC: {initial_btc:.8f}")
        logger.info(f"Final BTC: {final_btc:.8f}")
        logger.info(f"BTC Accumulated: {btc_accumulated:.8f} ({(btc_accumulated/initial_btc)*100:.2f}%)")
        
        return df, btc_balance, usdt_balance