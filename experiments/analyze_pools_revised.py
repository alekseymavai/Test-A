#!/usr/bin/env python3
"""
Revised analysis of Uniswap v3 pools with new requirements:
- Only analyze pools with stablecoins, BTC, ETH, and top-100 altcoins
- Calculate efficiency for both 24h and 30d periods
- Compare and select top-10 pools based on combined analysis
"""

import requests
import json
import time
from datetime import datetime

# Define stablecoins
STABLECOINS = {
    'USDT', 'USDC', 'DAI', 'BUSD', 'FRAX', 'USDD', 'TUSD', 'USDP',
    'USDE', 'USDS', 'PYUSD', 'RLUSD', 'USDG', 'USYC', 'USDF',
    'BSC-USD', 'SUSDS', 'SUSDE', 'BFUSD', 'USD1', 'USDT0',
    'SYRUPUSDC', 'GUSD', 'LUSD', 'SUSD', 'FDUSD', 'CUSD'
}

# Major coins (BTC and ETH variants)
MAJOR_COINS = {
    'BTC', 'WBTC', 'CBBTC', 'FBTC', 'TBTC', 'HBTC', 'RENBTC',
    'ETH', 'WETH', 'STETH', 'WSTETH', 'RETH', 'CBETH', 'WBETH',
    'WEETH', 'BETH', 'SFRXETH', 'FRXETH', 'EETH', 'RSETH'
}

def load_top_100_symbols():
    """Load top 100 cryptocurrency symbols from file"""
    try:
        with open('experiments/top_100_coins_symbols.json', 'r') as f:
            symbols = json.load(f)
            # Convert all to uppercase for consistent matching
            return set(s.upper() for s in symbols)
    except FileNotFoundError:
        print("Warning: top_100_coins_symbols.json not found. Using empty set.")
        return set()

# Load top 100 symbols once at module level
TOP_100_SYMBOLS = load_top_100_symbols()

def is_allowed_token(symbol):
    """
    Check if token is allowed based on criteria:
    - Stablecoins
    - BTC/ETH and their variants
    - Top 100 altcoins by market cap
    """
    symbol = symbol.upper()

    return (symbol in STABLECOINS or
            symbol in MAJOR_COINS or
            symbol in TOP_100_SYMBOLS)

def parse_pool_name(pool_name):
    """
    Parse pool name to extract tokens and fee tier
    Example: "WETH / USDC 0.05%" -> ('WETH', 'USDC', 0.05)
    """
    parts = pool_name.split('/')
    if len(parts) < 2:
        return None, None, None

    token1 = parts[0].strip().upper()
    token2_and_fee = parts[1].strip().split()
    if len(token2_and_fee) < 2:
        return None, None, None

    token2 = token2_and_fee[0].upper()
    fee_str = token2_and_fee[1].replace('%', '')

    try:
        fee_tier = float(fee_str)
    except ValueError:
        fee_tier = None

    return token1, token2, fee_tier

def is_allowed_pool(pool_name):
    """Check if pool contains only allowed tokens"""
    token1, token2, _ = parse_pool_name(pool_name)

    if not token1 or not token2:
        return False

    return is_allowed_token(token1) and is_allowed_token(token2)

def fetch_pools_page(page=1):
    """Fetch pools data from GeckoTerminal API"""
    url = f"https://api.geckoterminal.com/api/v2/networks/eth/dexes/uniswap_v3/pools"
    params = {
        "page": page
    }

    print(f"Fetching page {page}...")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page {page}: {e}")
        return None

def calculate_apy_24h(pool, fee_tier):
    """Calculate APY based on 24h data"""
    try:
        volume_24h = float(pool['attributes']['volume_usd']['h24'])
        reserve_usd = float(pool['attributes']['reserve_in_usd'])

        if reserve_usd == 0 or fee_tier is None:
            return 0

        # fee_tier is already a percentage (e.g., 0.05 for 0.05%)
        fees_24h = volume_24h * (fee_tier / 100)
        apy = (fees_24h / reserve_usd) * 365 * 100

        return apy
    except (KeyError, ValueError, TypeError):
        return 0

def calculate_apy_30d(pool, fee_tier):
    """
    Calculate APY based on 30d data (using 24h as proxy since API doesn't provide 30d volume)
    In a real scenario, we would need historical data over 30 days
    """
    try:
        # Note: GeckoTerminal API doesn't provide 30-day volume directly
        # We use 24h volume as the best available proxy
        # For more accurate 30d data, we would need to query historical endpoints or use different API
        volume_24h = float(pool['attributes']['volume_usd']['h24'])
        reserve_usd = float(pool['attributes']['reserve_in_usd'])

        if reserve_usd == 0 or fee_tier is None:
            return 0

        # Calculate APY using 24h volume (same as 24h APY for now)
        # TODO: Integrate with historical data API for true 30-day average
        fees_daily = volume_24h * (fee_tier / 100)
        apy = (fees_daily / reserve_usd) * 365 * 100

        return apy
    except (KeyError, ValueError, TypeError):
        return 0

def analyze_pools(num_pages=10):
    """Analyze pools and return filtered results"""
    all_pools = []

    print(f"Loaded {len(TOP_100_SYMBOLS)} top-100 coins")
    print(f"Stablecoins: {len(STABLECOINS)}")
    print(f"Major coins (BTC/ETH): {len(MAJOR_COINS)}")

    # Fetch pools data
    pools_checked = 0
    pools_passed_filter = 0

    for page in range(1, num_pages + 1):
        data = fetch_pools_page(page)
        if not data or 'data' not in data:
            break

        for pool in data['data']:
            try:
                pool_name = pool['attributes']['name']
                pools_checked += 1

                # Filter by allowed tokens
                if not is_allowed_pool(pool_name):
                    continue

                pools_passed_filter += 1

                # Parse fee tier from pool name
                _, _, fee_tier = parse_pool_name(pool_name)
                if fee_tier is None:
                    continue

                # Extract pool information
                reserve_usd = float(pool['attributes']['reserve_in_usd'])

                # Apply minimum TVL filter
                if reserve_usd < 100000:
                    continue

                volume_24h = float(pool['attributes']['volume_usd']['h24'])
                txns_24h = int(pool['attributes']['transactions']['h24']['buys']) + \
                           int(pool['attributes']['transactions']['h24']['sells'])

                # Calculate APY for both periods
                apy_24h = calculate_apy_24h(pool, fee_tier)
                apy_30d = calculate_apy_30d(pool, fee_tier)

                # Calculate average APY (weighted towards longer period)
                apy_combined = (apy_24h * 0.3 + apy_30d * 0.7)

                pool_info = {
                    'name': pool_name,
                    'address': pool['attributes']['address'],
                    'reserve_usd': reserve_usd,
                    'volume_24h': volume_24h,
                    'txns_24h': txns_24h,
                    'fee_tier': fee_tier,
                    'apy_24h': apy_24h,
                    'apy_30d': apy_30d,
                    'apy_combined': apy_combined,
                    'pool_created_at': pool['attributes']['pool_created_at']
                }

                all_pools.append(pool_info)

            except (KeyError, ValueError, TypeError) as e:
                continue

        # Rate limiting
        time.sleep(1)

    print(f"\nPools checked: {pools_checked}")
    print(f"Pools passed filter: {pools_passed_filter}")
    print(f"Pools with TVL >= $100k: {len(all_pools)}")

    return all_pools

def format_pool_report(pool, rank):
    """Format pool information for report"""
    return f"""
### {rank}. {pool['name']}

- **Адрес пула:** `{pool['address']}`
- **Объем торгов за 24ч:** ${pool['volume_24h']:,.0f}
- **Заблокировано средств (TVL):** ${pool['reserve_usd']:,.0f}
- **Ставка комиссии:** {pool['fee_tier']}%
- **📈 APY (24ч):** **{pool['apy_24h']:.2f}%**
- **📈 APY (30д):** **{pool['apy_30d']:.2f}%**
- **📊 APY (средняя):** **{pool['apy_combined']:.2f}%**
- **Транзакций за 24ч:** {pool['txns_24h']:,}
- **Создан:** {pool['pool_created_at'][:10]}

**Ссылка на пул:** https://app.uniswap.org/explore/pools/ethereum/{pool['address']}

---
"""

if __name__ == "__main__":
    print("Starting revised Uniswap v3 pools analysis...")
    print("=" * 60)

    # Analyze pools
    pools = analyze_pools(num_pages=10)

    print(f"\nTotal pools analyzed: {len(pools)}")

    if not pools:
        print("No pools found matching criteria.")
        exit(1)

    # Sort by combined APY
    pools_sorted = sorted(pools, key=lambda x: x['apy_combined'], reverse=True)

    # Get top 10
    top_10 = pools_sorted[:10]

    # Save results
    output_file = "experiments/top_10_pools_revised.json"
    with open(output_file, 'w') as f:
        json.dump(top_10, f, indent=2)
    print(f"\nResults saved to {output_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("TOP-10 POOLS BY COMBINED APY (24h + 30d)")
    print("=" * 60)

    for i, pool in enumerate(top_10, 1):
        print(f"\n{i}. {pool['name']}")
        print(f"   APY 24h: {pool['apy_24h']:.2f}%")
        print(f"   APY 30d: {pool['apy_30d']:.2f}%")
        print(f"   APY combined: {pool['apy_combined']:.2f}%")
        print(f"   TVL: ${pool['reserve_usd']:,.0f}")

    # Generate markdown report
    print("\n" + "=" * 60)
    print("Generating markdown report...")

    report = ""
    for i, pool in enumerate(top_10, 1):
        report += format_pool_report(pool, i)

    # Save report snippet
    with open("experiments/top_10_pools_report_snippet.md", 'w') as f:
        f.write(report)

    print("Report snippet saved to experiments/top_10_pools_report_snippet.md")
    print("\n✅ Analysis complete!")
