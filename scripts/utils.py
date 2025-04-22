import os
import json
import time
from pathlib import Path
from datetime import datetime
import requests
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API credentials
TRADEOGRE_KEY = os.getenv("TRADEOGRE_KEY")
TRADEOGRE_SECRET = os.getenv("TRADEOGRE_SECRET")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

# Base URLs
TRADEOGRE_BASE = "https://tradeogre.com/api/v1"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
FEARGREED_URL = "https://api.alternative.me/fng/"

# Ensure data directory exists
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def fetch_historical_prices(days=365, force_refresh=False):
    """Fetch historical BTC prices from CoinGecko or use cached data if recent."""
    cache_file = DATA_DIR / "prices.json"
    
    # Check if cache exists and is recent (less than 30 minutes old)
    if not force_refresh and cache_file.exists():
        file_age = time.time() - cache_file.stat().st_mtime
        if file_age < 1800:  # 30 minutes in seconds
            try:
                with open(cache_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass  # Fall through to fresh fetch if cache is corrupted
    
    # Fetch fresh data
    url = f"{COINGECKO_BASE}/coins/bitcoin/market_chart"
    params = {
        "vs_currency": "usd",
        "days": days,
        "interval": "daily"
    }
    headers = {}
    if COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = COINGECKO_API_KEY
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Cache the results
        with open(cache_file, "w") as f:
            json.dump(data, f)
        
        return data
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Error fetching historical prices: {e}")
        # Try to use cached data as fallback
        if cache_file.exists():
            with open(cache_file, "r") as f:
                return json.load(f)
        # If no cache exists, return empty structure
        return {"prices": []}


def fetch_fear_greed(limit=365, force_refresh=False):
    """Fetch Fear & Greed index data or use cached data if recent."""
    cache_file = DATA_DIR / "fear_greed.json"
    
    # Check if cache exists and is recent
    if not force_refresh and cache_file.exists():
        file_age = time.time() - cache_file.stat().st_mtime
        if file_age < 1800:  # 30 minutes in seconds
            try:
                with open(cache_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass  # Fall through to fresh fetch
    
    # Fetch fresh data
    params = {
        "limit": limit,
        "format": "json"
    }
    
    try:
        response = requests.get(FEARGREED_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Cache the results
        with open(cache_file, "w") as f:
            json.dump(data, f)
        
        return data
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Error fetching Fear & Greed data: {e}")
        # Try to use cached data as fallback
        if cache_file.exists():
            with open(cache_file, "r") as f:
                return json.load(f)
        # If no cache exists, return empty structure
        return {"data": []}


def fetch_tradeogre_ticker(market="BTC-USDC"):
    """Get current ticker information from TradeOgre."""
    url = f"{TRADEOGRE_BASE}/ticker/{market}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Error fetching TradeOgre ticker: {e}")
        return {"success": False, "error": str(e)}


def fetch_tradeogre_orderbook(market="BTC-USDC"):
    """Get current order book from TradeOgre."""
    url = f"{TRADEOGRE_BASE}/orders/{market}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Error fetching TradeOgre orderbook: {e}")
        return {"success": False, "error": str(e)}


def place_tradeogre_order(side, market, quantity, price):
    """Place a buy or sell order on TradeOgre."""
    if not TRADEOGRE_KEY or not TRADEOGRE_SECRET:
        return {"success": False, "error": "API credentials not configured"}
    
    endpoint = "/order/buy" if side.lower() == "buy" else "/order/sell"
    url = f"{TRADEOGRE_BASE}{endpoint}"
    
    data = {
        "market": market,
        "quantity": quantity,
        "price": price
    }
    
    try:
        response = requests.post(
            url,
            auth=(TRADEOGRE_KEY, TRADEOGRE_SECRET),
            data=data
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Error placing TradeOgre order: {e}")
        return {"success": False, "error": str(e)}


def prepare_price_data(price_data):
    """Convert price data to a pandas DataFrame with datetime index."""
    if not price_data or "prices" not in price_data:
        return pd.DataFrame(columns=["timestamp", "price", "date"])
    
    df = pd.DataFrame(price_data["prices"], columns=["timestamp", "price"])
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def prepare_fg_data(fg_data):
    """Convert Fear & Greed data to a pandas DataFrame with datetime index."""
    if not fg_data or "data" not in fg_data:
        return pd.DataFrame(columns=["timestamp", "value", "value_classification", "date"])
    
    df = pd.DataFrame(fg_data["data"])
    df["date"] = pd.to_datetime(df["timestamp"].astype(int), unit="s")
    df["value"] = df["value"].astype(int)
    return df