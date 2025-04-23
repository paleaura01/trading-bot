# strategies/virtual_vault.py
import pandas as pd
import numpy as np
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class VirtualVault:
    """
    Virtual vault for managing trading assets in test mode
    """
    
    def __init__(self, initial_btc=0.001, initial_usdt=100):
        """
        Initialize the virtual vault
        
        Args:
            initial_btc (float): Initial BTC balance
            initial_usdt (float): Initial USDT balance
        """
        self.btc_balance = initial_btc
        self.usdt_balance = initial_usdt
        self.trade_history = []
        self.portfolio_history = []
        self.initial_portfolio_value = None
        
        # Record initial state
        self.update_market_price(90000)  # Updated starting price
        
    def execute_trade(self, action, amount, price):
        """
        Execute a trade in the virtual vault
        
        Args:
            action (str): "BUY", "SELL", or "RESET"
            amount (float): Amount to trade
            price (float): Current price
            
        Returns:
            bool: True if trade was successful
        """
        timestamp = datetime.now()
        
        if action == "BUY":
            # Calculate how much BTC we can buy
            btc_amount = amount / price
            
            # Check if we have enough USDT
            if amount > self.usdt_balance:
                logger.warning(f"Not enough USDT for buy: {amount} > {self.usdt_balance}")
                return False
            
            # Execute buy
            self.usdt_balance -= amount
            self.btc_balance += btc_amount
            
            # Record trade
            self.trade_history.append({
                "timestamp": timestamp.isoformat(),
                "action": "BUY",
                "price": price,
                "usdt_amount": amount,
                "btc_amount": btc_amount,
                "usdt_balance": self.usdt_balance,
                "btc_balance": self.btc_balance
            })
            
        elif action == "SELL":
            # Calculate USDT we'll receive
            usdt_amount = amount * price
            
            # Check if we have enough BTC
            if amount > self.btc_balance:
                logger.warning(f"Not enough BTC for sell: {amount} > {self.btc_balance}")
                return False
            
            # Execute sell
            self.btc_balance -= amount
            self.usdt_balance += usdt_amount
            
            # Record trade
            self.trade_history.append({
                "timestamp": timestamp.isoformat(),
                "action": "SELL",
                "price": price,
                "usdt_amount": usdt_amount,
                "btc_amount": amount,
                "usdt_balance": self.usdt_balance,
                "btc_balance": self.btc_balance
            })
            
        elif action == "RESET":
            # Reset to Bitcoin-favorable values
            old_btc = self.btc_balance
            old_usdt = self.usdt_balance
            
            # Modified reset values for BTC accumulation
            self.btc_balance = 0.0032  # Higher BTC balance
            self.usdt_balance = 150  # Lower USDT balance
            
            # Record reset
            self.trade_history.append({
                "timestamp": timestamp.isoformat(),
                "action": "RESET",
                "price": price,
                "usdt_amount": abs(self.usdt_balance - old_usdt),
                "btc_amount": abs(self.btc_balance - old_btc),
                "usdt_balance": self.usdt_balance,
                "btc_balance": self.btc_balance
            })
        
        # Update portfolio history
        self.update_market_price(price)
        
        return True
        
    def reset(self, btc_balance, usdt_balance):
        """
        Reset vault to specific values
        
        Args:
            btc_balance (float): New BTC balance
            usdt_balance (float): New USDT balance
        """
        self.btc_balance = btc_balance
        self.usdt_balance = usdt_balance
        
    def update_market_price(self, price):
        """
        Update portfolio history with current market price
        
        Args:
            price (float): Current market price
        """
        timestamp = datetime.now()
        portfolio_value = self.get_total_value_usd(price)
        
        # Set initial portfolio value if not set
        if self.initial_portfolio_value is None:
            self.initial_portfolio_value = portfolio_value
        
        # Calculate returns
        total_return = 0
        daily_return = 0
        
        if self.initial_portfolio_value > 0:
            total_return = ((portfolio_value / self.initial_portfolio_value) - 1) * 100
            
        if len(self.portfolio_history) > 0:
            last_value = self.portfolio_history[-1]["portfolio_value"]
            if last_value > 0:
                daily_return = ((portfolio_value / last_value) - 1) * 100
        
        # Record portfolio state
        self.portfolio_history.append({
            "timestamp": timestamp.isoformat(),
            "btc_price": price,
            "btc_balance": self.btc_balance,
            "usdt_balance": self.usdt_balance,
            "portfolio_value": portfolio_value,
            "total_return": total_return,
            "daily_return": daily_return
        })
        
    def get_total_value_usd(self, current_price):
        """
        Calculate total portfolio value in USD
        
        Args:
            current_price (float): Current BTC price
            
        Returns:
            float: Total portfolio value in USD
        """
        btc_value = self.btc_balance * current_price
        return self.usdt_balance + btc_value
        
    def to_dict(self):
        """
        Convert vault to dictionary for storage
        
        Returns:
            dict: Vault data
        """
        return {
            "btc_balance": self.btc_balance,
            "usdt_balance": self.usdt_balance,
            "trade_history": self.trade_history,
            "portfolio_history": self.portfolio_history,
            "initial_portfolio_value": self.initial_portfolio_value
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Create vault from dictionary
        
        Args:
            data (dict): Vault data
            
        Returns:
            VirtualVault: New virtual vault
        """
        vault = cls(
            initial_btc=data.get("btc_balance", 0.001),
            initial_usdt=data.get("usdt_balance", 100)
        )
        
        vault.trade_history = data.get("trade_history", [])
        vault.portfolio_history = data.get("portfolio_history", [])
        vault.initial_portfolio_value = data.get("initial_portfolio_value", None)
        
        return vault
        
    def get_trade_history_df(self):
        """
        Get trade history as pandas DataFrame
        
        Returns:
            pd.DataFrame: Trade history
        """
        if not self.trade_history:
            return pd.DataFrame()
            
        df = pd.DataFrame(self.trade_history)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
        
    def get_portfolio_history_df(self, current_price=None):
        """
        Get portfolio history as pandas DataFrame with additional metrics
        
        Args:
            current_price (float, optional): Current price for updating latest value
            
        Returns:
            pd.DataFrame: Portfolio history
        """
        if not self.portfolio_history:
            return pd.DataFrame()
            
        # Update with current price if provided
        if current_price is not None:
            self.update_market_price(current_price)
            
        df = pd.DataFrame(self.portfolio_history)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date
        
        # Calculate BTC percentage of portfolio
        df["btc_percentage"] = (df["btc_balance"] * df["btc_price"]) / df["portfolio_value"] * 100
        
        # Add action column from trade history for charting
        if self.trade_history:
            trade_df = self.get_trade_history_df()
            df["action"] = "HOLD"
            
            # Match trades to portfolio updates
            for idx, row in df.iterrows():
                # Find trades that happened before this portfolio update
                trades = trade_df[trade_df["timestamp"] <= row["timestamp"]]
                
                if not trades.empty:
                    # Get the most recent trade
                    latest_trade = trades.iloc[-1]
                    
                    # Only use the action if it's from the same timestamp
                    if latest_trade["timestamp"] == row["timestamp"]:
                        df.at[idx, "action"] = latest_trade["action"]
        
        return df