#!/usr/bin/env python3
"""
Enhanced analysis of Uniswap v3 pools with real 30-day data:
- Uses GeckoTerminal API for current data (24h)
- Uses The Graph API to get real 30-day historical volume data
- Calculates accurate APY for both 24h and 30d periods
- Selects top-20 high-margin pools
"""

import requests
import json
import time
from datetime import datetime, timedelta

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
            return set(s.upper() for s in symbols)
    except FileNotFoundError:
        print("Warning: top_100_coins_symbols.json not found. Using empty set.")
        return set()

TOP_100_SYMBOLS = load_top_100_symbols()

def is_allowed_token(symbol):
    """Check if token is allowed based on criteria"""
    symbol = symbol.upper()
    return (symbol in STABLECOINS or
            symbol in MAJOR_COINS or
            symbol in TOP_100_SYMBOLS)

def parse_pool_name(pool_name):
    """Parse pool name to extract tokens and fee tier"""
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
    params = {"page": page}

    print(f"Fetching page {page}...")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page {page}: {e}")
        return None

def fetch_30d_volume_from_thegraph(pool_address):
    """
    Fetch 30-day volume data from The Graph Uniswap v3 subgraph
    Returns total volume over 30 days and average TVL
    """
    # The Graph endpoint (using public endpoint, for production use API key)
    url = "https://gateway.thegraph.com/api/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"

    # Calculate timestamp for 30 days ago
    timestamp_30d_ago = int((datetime.now() - timedelta(days=30)).timestamp())

    query = """
    query PoolDayData($poolAddress: String!, $timestamp: Int!) {
      poolDayDatas(
        first: 30
        orderBy: date
        orderDirection: desc
        where: {
          pool: $poolAddress
          date_gte: $timestamp
        }
      ) {
        date
        volumeUSD
        tvlUSD
        feesUSD
      }
    }
    """

    variables = {
        "poolAddress": pool_address.lower(),
        "timestamp": timestamp_30d_ago
    }

    try:
        response = requests.post(
            url,
            json={"query": query, "variables": variables},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if 'data' in data and 'poolDayDatas' in data['data']:
            pool_day_data = data['data']['poolDayDatas']

            if not pool_day_data:
                return None, None, None

            # Calculate total volume and average TVL over 30 days
            total_volume = sum(float(day['volumeUSD']) for day in pool_day_data)
            total_fees = sum(float(day['feesUSD']) for day in pool_day_data)
            avg_tvl = sum(float(day['tvlUSD']) for day in pool_day_data) / len(pool_day_data)

            return total_volume, avg_tvl, total_fees

        return None, None, None

    except Exception as e:
        print(f"  Error fetching 30d data for {pool_address}: {e}")
        return None, None, None

def calculate_apy_24h(pool, fee_tier):
    """Calculate APY based on 24h data"""
    try:
        volume_24h = float(pool['attributes']['volume_usd']['h24'])
        reserve_usd = float(pool['attributes']['reserve_in_usd'])

        if reserve_usd == 0 or fee_tier is None:
            return 0

        fees_24h = volume_24h * (fee_tier / 100)
        apy = (fees_24h / reserve_usd) * 365 * 100

        return apy
    except (KeyError, ValueError, TypeError):
        return 0

def calculate_apy_30d(volume_30d, avg_tvl_30d, fee_tier):
    """
    Calculate APY based on real 30-day data
    APY = (Total fees over 30 days / Average TVL) * (365 / 30) * 100
    """
    try:
        if avg_tvl_30d == 0 or fee_tier is None or volume_30d is None:
            return 0

        # Total fees over 30 days
        total_fees_30d = volume_30d * (fee_tier / 100)

        # APY calculation: annualize the 30-day return
        apy = (total_fees_30d / avg_tvl_30d) * (365 / 30) * 100

        return apy
    except (ValueError, TypeError):
        return 0

def analyze_pools_with_30d_data(num_pages=10, target_pools=30):
    """
    Analyze pools with real 30-day data from The Graph
    Fetch more pools initially to ensure we get enough with 30d data
    """
    all_pools = []

    print(f"Loaded {len(TOP_100_SYMBOLS)} top-100 coins")
    print(f"Stablecoins: {len(STABLECOINS)}")
    print(f"Major coins (BTC/ETH): {len(MAJOR_COINS)}")

    pools_checked = 0
    pools_passed_filter = 0
    pools_with_30d_data = 0

    # Fetch pools from GeckoTerminal
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

                # Parse fee tier
                _, _, fee_tier = parse_pool_name(pool_name)
                if fee_tier is None:
                    continue

                # Extract basic information
                reserve_usd = float(pool['attributes']['reserve_in_usd'])

                # Apply minimum TVL filter
                if reserve_usd < 100000:
                    continue

                pool_address = pool['attributes']['address']
                volume_24h = float(pool['attributes']['volume_usd']['h24'])
                txns_24h = int(pool['attributes']['transactions']['h24']['buys']) + \
                           int(pool['attributes']['transactions']['h24']['sells'])

                # Calculate APY for 24h
                apy_24h = calculate_apy_24h(pool, fee_tier)

                # Fetch 30-day data from The Graph
                print(f"  Fetching 30d data for {pool_name}...")
                volume_30d, avg_tvl_30d, fees_30d = fetch_30d_volume_from_thegraph(pool_address)

                # If we have 30d data, use it; otherwise use 24h as approximation
                if volume_30d is not None and avg_tvl_30d is not None:
                    apy_30d = calculate_apy_30d(volume_30d, avg_tvl_30d, fee_tier)
                    pools_with_30d_data += 1
                    has_real_30d_data = True
                else:
                    # Fallback: use 24h data as approximation
                    apy_30d = apy_24h
                    volume_30d = volume_24h * 30  # Rough estimate
                    avg_tvl_30d = reserve_usd
                    has_real_30d_data = False

                pool_info = {
                    'name': pool_name,
                    'address': pool_address,
                    'reserve_usd': reserve_usd,
                    'volume_24h': volume_24h,
                    'volume_30d': volume_30d,
                    'avg_tvl_30d': avg_tvl_30d,
                    'txns_24h': txns_24h,
                    'fee_tier': fee_tier,
                    'apy_24h': apy_24h,
                    'apy_30d': apy_30d,
                    'has_real_30d_data': has_real_30d_data,
                    'pool_created_at': pool['attributes']['pool_created_at']
                }

                all_pools.append(pool_info)

                # Stop if we have enough pools with 30d data
                if pools_with_30d_data >= target_pools:
                    print(f"\nReached target of {target_pools} pools with 30d data!")
                    break

            except (KeyError, ValueError, TypeError) as e:
                continue

            # Rate limiting to avoid hitting API limits
            time.sleep(0.5)

        if pools_with_30d_data >= target_pools:
            break

        # Rate limiting between pages
        time.sleep(1)

    print(f"\n{'='*60}")
    print(f"Pools checked: {pools_checked}")
    print(f"Pools passed filter: {pools_passed_filter}")
    print(f"Pools with TVL >= $100k: {len(all_pools)}")
    print(f"Pools with real 30d data: {pools_with_30d_data}")
    print(f"{'='*60}\n")

    return all_pools

def format_pool_report(pool, rank):
    """Format pool information for report"""
    real_data_indicator = "✅" if pool['has_real_30d_data'] else "⚠️"

    return f"""
### {rank}. {pool['name']} {real_data_indicator}

- **Адрес пула:** `{pool['address']}`
- **Объем торгов за 24ч:** ${pool['volume_24h']:,.0f}
- **Объем торгов за 30д:** ${pool['volume_30d']:,.0f}
- **TVL (текущий):** ${pool['reserve_usd']:,.0f}
- **TVL (среднее за 30д):** ${pool['avg_tvl_30d']:,.0f}
- **Ставка комиссии:** {pool['fee_tier']}%
- **📈 APY (24ч):** **{pool['apy_24h']:.2f}%**
- **📈 APY (30д):** **{pool['apy_30d']:.2f}%**
- **Транзакций за 24ч:** {pool['txns_24h']:,}
- **Создан:** {pool['pool_created_at'][:10]}
- **30д данные:** {'Реальные из The Graph' if pool['has_real_30d_data'] else 'Оценка на основе 24ч'}

**Ссылка на пул:** https://app.uniswap.org/explore/pools/ethereum/{pool['address']}

---
"""

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Uniswap v3 pools analysis with real 30-day data")
    print("=" * 60)

    # Analyze pools (fetch more pages to get enough pools with 30d data)
    pools = analyze_pools_with_30d_data(num_pages=15, target_pools=30)

    print(f"\nTotal pools analyzed: {len(pools)}")

    if not pools:
        print("No pools found matching criteria.")
        exit(1)

    # Sort by 30-day APY (using real historical data)
    pools_sorted = sorted(pools, key=lambda x: x['apy_30d'], reverse=True)

    # Get top 20
    top_20 = pools_sorted[:20]

    # Save results
    output_file = "experiments/top_20_pools_with_30d_data.json"
    with open(output_file, 'w') as f:
        json.dump(top_20, f, indent=2)
    print(f"\nResults saved to {output_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("TOP-20 POOLS BY 30-DAY APY (Real Historical Data)")
    print("=" * 60)

    for i, pool in enumerate(top_20, 1):
        data_source = "✅ Real" if pool['has_real_30d_data'] else "⚠️ Est"
        print(f"\n{i}. {pool['name']}")
        print(f"   APY 24h: {pool['apy_24h']:.2f}%")
        print(f"   APY 30d: {pool['apy_30d']:.2f}%  {data_source}")
        print(f"   Volume 30d: ${pool['volume_30d']:,.0f}")
        print(f"   TVL: ${pool['reserve_usd']:,.0f}")

    # Generate markdown report
    print("\n" + "=" * 60)
    print("Generating markdown report...")

    report = ""
    for i, pool in enumerate(top_20, 1):
        report += format_pool_report(pool, i)

    # Save report snippet
    with open("experiments/top_20_pools_report_snippet.md", 'w') as f:
        f.write(report)

    print("Report snippet saved to experiments/top_20_pools_report_snippet.md")

    # Print statistics
    real_data_count = sum(1 for p in top_20 if p['has_real_30d_data'])
    print(f"\n{'='*60}")
    print(f"Statistics:")
    print(f"  Pools with real 30d data: {real_data_count}/20")
    print(f"  Pools with estimated data: {20 - real_data_count}/20")
    print(f"{'='*60}")

    print("\n✅ Analysis complete!")
