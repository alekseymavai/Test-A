#!/usr/bin/env python3
"""Analyze Uniswap v3 pools data from GeckoTerminal API"""

import json
import sys
from datetime import datetime, timedelta

# Read the raw data
with open('experiments/uniswap_pools_raw.json', 'r') as f:
    data = json.load(f)

pools = data['data']
print(f'Total pools fetched: {len(pools)}')

# Analyze first pool
if pools:
    print(f'\nFirst pool structure:')
    pool = pools[0]['attributes']
    print(f'Name: {pool["name"]}')
    print(f'24h Volume: ${float(pool["volume_usd"]["h24"]):,.2f}')
    print(f'Reserve (TVL): ${float(pool["reserve_in_usd"]):,.2f}')

    # Calculate fee revenue (volume * fee tier)
    # Extract fee tier from name (e.g., "WETH / USDT 0.01%" -> 0.01%)
    name = pool["name"]
    if "%" in name:
        fee_str = name.split()[-1].rstrip('%')
        fee_rate = float(fee_str) / 100
        volume_24h = float(pool["volume_usd"]["h24"])
        fees_24h = volume_24h * fee_rate
        print(f'Fee tier: {fee_str}%')
        print(f'24h Fees earned: ${fees_24h:,.2f}')

        # Calculate APY approximation
        # APY = (daily_fees / TVL) * 365 * 100
        tvl = float(pool["reserve_in_usd"])
        if tvl > 0:
            daily_apy = (fees_24h / tvl) * 365 * 100
            print(f'Estimated APY from fees: {daily_apy:.2f}%')

print('\n--- Calculating margins for all pools ---\n')

# Calculate margin (fees earned) for each pool
pool_analysis = []

for pool_data in pools:
    pool = pool_data['attributes']
    name = pool["name"]
    address = pool["address"]

    try:
        # Extract fee tier
        if "%" in name:
            fee_str = name.split()[-1].rstrip('%')
            fee_rate = float(fee_str) / 100
        else:
            fee_rate = 0.003  # Default 0.3% if not specified

        volume_24h = float(pool["volume_usd"]["h24"])
        tvl = float(pool["reserve_in_usd"])
        fees_24h = volume_24h * fee_rate

        # Calculate annualized return (APY)
        if tvl > 0:
            apy = (fees_24h / tvl) * 365 * 100
        else:
            apy = 0

        pool_analysis.append({
            'name': name,
            'address': address,
            'volume_24h': volume_24h,
            'tvl': tvl,
            'fee_tier': fee_rate * 100,
            'fees_24h': fees_24h,
            'apy': apy,
            'created_at': pool.get('pool_created_at', '')
        })
    except Exception as e:
        print(f'Error processing pool {name}: {e}')
        continue

# Sort by APY (margin/return)
pool_analysis.sort(key=lambda x: x['apy'], reverse=True)

print(f'\nTop 10 pools by APY (fee-based returns):')
print('=' * 100)

for i, pool in enumerate(pool_analysis[:10], 1):
    print(f'\n{i}. {pool["name"]}')
    print(f'   Address: {pool["address"]}')
    print(f'   24h Volume: ${pool["volume_24h"]:,.2f}')
    print(f'   TVL: ${pool["tvl"]:,.2f}')
    print(f'   Fee Tier: {pool["fee_tier"]}%')
    print(f'   24h Fees Earned: ${pool["fees_24h"]:,.2f}')
    print(f'   Estimated APY: {pool["apy"]:.2f}%')

# Save results to JSON
with open('experiments/top_pools_analysis.json', 'w') as f:
    json.dump(pool_analysis[:10], f, indent=2)

print('\n\nResults saved to experiments/top_pools_analysis.json')
