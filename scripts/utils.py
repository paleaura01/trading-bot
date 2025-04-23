# scripts/utils.py
import requests
import logging
import os
import json
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TRADEOGRE_KEY = os.getenv("TRADEOGRE_KEY")
TRADEOGRE_SECRET = os.getenv("TRADEOGRE_SECRET")

# TradeOgre API base URL
BASE_URL = "https://tradeogre.com/api/v1"

def fetch_tradeogre_ticker(market_pair):
    """
    Fetch the current ticker price for a given market pair
    
    Args:
        market_pair (str): Market pair in format 'BTC-USDT'
        
    Returns:
        float: Current price or 0 if error
    """
    try:
        url = f"{BASE_URL}/ticker/{market_pair}"
        response = requests.get(url)
        data = response.json()
        
        if data.get("success", False):
            return float(data.get("price", 0))
        else:
            logger.error(f"Error fetching ticker: {data.get('error', 'Unknown error')}")
            return 0
    except Exception as e:
        logger.error(f"Exception in fetch_tradeogre_ticker: {str(e)}")
        return 0

def fetch_tradeogre_orderbook(market_pair):
    """
    Fetch the current orderbook for a given market pair
    
    Args:
        market_pair (str): Market pair in format 'BTC-USDT'
        
    Returns:
        dict: Orderbook data with bids and asks or empty dict if error
    """
    try:
        url = f"{BASE_URL}/orders/{market_pair}"
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200:
            return {
                "buy": data.get("buy", {}),
                "sell": data.get("sell", {})
            }
        else:
            logger.error(f"Error fetching orderbook: {data.get('error', 'Unknown error')}")
            return {"buy": {}, "sell": {}}
    except Exception as e:
        logger.error(f"Exception in fetch_tradeogre_orderbook: {str(e)}")
        return {"buy": {}, "sell": {}}

def fetch_tradeogre_account():
    """
    Fetch account balances from TradeOgre
    
    Returns:
        dict: Account balances or empty dict if error
    """
    try:
        url = f"{BASE_URL}/account/balances"
        response = requests.get(
            url, 
            auth=(TRADEOGRE_KEY, TRADEOGRE_SECRET)
        )
        data = response.json()
        
        if data.get("success", False):
            # Return actual balances
            return data.get("balances", {})
        else:
            logger.error(f"Error fetching account: {data.get('error', 'Unknown error')}")
            return {}
    except Exception as e:
        logger.error(f"Exception in fetch_tradeogre_account: {str(e)}")
        return {}

def execute_live_trade(action, amount, price=None, market_pair="BTC-USDT"):
    """
    Execute a live trade on TradeOgre
    
    Args:
        action (str): "BUY" or "SELL"
        amount (float): Amount to buy or sell
        price (float, optional): Price to buy/sell at. If None, executes at market price.
        market_pair (str, optional): Market pair to trade on. Defaults to "BTC-USDT".
        
    Returns:
        dict: Result of the trade operation
    """
    try:
        # Validate action
        if action not in ["BUY", "SELL"]:
            logger.error(f"Invalid action: {action}")
            return {"success": False, "error": "Invalid action"}
            
        # Format amount to appropriate precision
        if action == "BUY":
            # For buying, amount is in base currency (BTC)
            formatted_amount = f"{amount:.8f}"
        else:
            # For selling, amount is in quote currency (USDT)
            formatted_amount = f"{amount:.8f}"
            
        # Format price if provided
        formatted_price = f"{price:.8f}" if price is not None else None
        
        # Prepare data for the request
        data = {
            "market": market_pair,
            "quantity": formatted_amount
        }
        
        if formatted_price is not None:
            data["price"] = formatted_price
            
        # Determine endpoint based on action
        endpoint = "buy" if action == "BUY" else "sell"
        url = f"{BASE_URL}/order/{endpoint}"
        
        # Make the request to the API
        response = requests.post(
            url,
            data=data,
            auth=(TRADEOGRE_KEY, TRADEOGRE_SECRET)
        )
        
        # Parse response
        result = response.json()
        
        if result.get("success", False):
            logger.info(f"Successfully executed {action} order: {amount} @ {price or 'market'}")
            return {
                "success": True,
                "action": action,
                "quantity": amount,
                "price": price,
                "market": market_pair,
                "order_id": result.get("uuid", "")
            }
        else:
            logger.error(f"Error executing {action} order: {result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "action": action
            }
    except Exception as e:
        logger.error(f"Exception in execute_live_trade: {str(e)}")
        return {"success": False, "error": str(e), "action": action}

def fetch_fear_and_greed(json_path="data/fear_greed.json"):
    """
    Fetch the latest Fear & Greed index value from a local JSON file.
    Returns an integer 0–100, or None on error.
    """
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        # The first element is the most recent
        latest = data.get("data", [])[0]
        return int(latest.get("value", 0))
    except Exception as e:
        logger.error(f"Error fetching Fear & Greed index: {e}")
        return None