#!/usr/bin/env python3
"""
Script to fetch top 100 cryptocurrencies by market cap from CoinGecko API
"""

import requests
import json
import time

def get_top_100_coins():
    """
    Fetch top 100 cryptocurrencies by market cap from CoinGecko API
    Returns a list of coin symbols and names
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False
    }

    print("Fetching top 100 cryptocurrencies from CoinGecko...")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Extract symbols and names
        coins = []
        for coin in data:
            coins.append({
                "id": coin["id"],
                "symbol": coin["symbol"].upper(),
                "name": coin["name"],
                "market_cap_rank": coin["market_cap_rank"],
                "market_cap": coin["market_cap"]
            })

        print(f"Successfully fetched {len(coins)} cryptocurrencies")
        return coins

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return []

def save_to_file(data, filename):
    """Save data to JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Data saved to {filename}")

if __name__ == "__main__":
    coins = get_top_100_coins()

    if coins:
        # Save full data
        save_to_file(coins, "experiments/top_100_coins_full.json")

        # Save just symbols for easy reference
        symbols = [coin["symbol"] for coin in coins]
        save_to_file(symbols, "experiments/top_100_coins_symbols.json")

        # Print summary
        print("\nTop 10 cryptocurrencies by market cap:")
        for i, coin in enumerate(coins[:10], 1):
            print(f"{i}. {coin['name']} ({coin['symbol']}) - Market Cap: ${coin['market_cap']:,.0f}")

        print(f"\nAll symbols: {', '.join(symbols[:20])}...")
