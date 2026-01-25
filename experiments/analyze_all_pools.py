#!/usr/bin/env python3
"""Comprehensive analysis of Uniswap v3 pools from multiple pages"""

import json
import glob
from datetime import datetime

# Combine all pages
all_pools = []
for file in sorted(glob.glob('experiments/pools_page_*.json')):
    print(f'Reading {file}...')
    with open(file, 'r') as f:
        data = json.load(f)
        all_pools.extend(data['data'])

print(f'\nTotal pools collected: {len(all_pools)}')

# Analyze each pool
pool_analysis = []

for pool_data in all_pools:
    pool = pool_data['attributes']
    name = pool["name"]
    address = pool["address"]

    try:
        # Extract fee tier from pool name
        if "%" in name:
            fee_str = name.split()[-1].rstrip('%')
            fee_rate = float(fee_str) / 100
        else:
            fee_rate = 0.003  # Default 0.3%

        volume_24h = float(pool["volume_usd"]["h24"])
        tvl = float(pool["reserve_in_usd"])
        fees_24h = volume_24h * fee_rate

        # Calculate APY (annualized return from fees)
        # This represents the margin/return for liquidity providers
        if tvl > 0:
            apy = (fees_24h / tvl) * 365 * 100
        else:
            apy = 0

        # Get creation date
        created_at = pool.get('pool_created_at', '')

        # Check if pool was created in last 6 months
        # (for our purposes, we'll include all active pools as they show recent performance)

        pool_analysis.append({
            'name': name,
            'address': address,
            'volume_24h': volume_24h,
            'tvl': tvl,
            'fee_tier': fee_rate * 100,
            'fees_24h': fees_24h,
            'apy': apy,
            'created_at': created_at,
            'transactions_24h': (pool.get('transactions', {}).get('h24', {}).get('buys', 0) +
                                pool.get('transactions', {}).get('h24', {}).get('sells', 0))
        })
    except Exception as e:
        print(f'Error processing pool {name}: {e}')
        continue

# Sort by APY (margin/return on invested capital)
pool_analysis.sort(key=lambda x: x['apy'], reverse=True)

# Filter out pools with very low TVL (less than $100k) to avoid unreliable data
significant_pools = [p for p in pool_analysis if p['tvl'] >= 100000]

print(f'\nPools with TVL >= $100k: {len(significant_pools)}')
print('\n' + '='*120)
print('TOP 10 UNISWAP V3 POOLS BY MARGIN (APY FROM FEES)')
print('='*120)

top_10 = significant_pools[:10]

for i, pool in enumerate(top_10, 1):
    print(f'\n{i}. {pool["name"]}')
    print(f'   Pool Address: {pool["address"]}')
    print(f'   24h Volume: ${pool["volume_24h"]:,.2f}')
    print(f'   Total Value Locked (TVL): ${pool["tvl"]:,.2f}')
    print(f'   Fee Tier: {pool["fee_tier"]}%')
    print(f'   24h Fees Earned: ${pool["fees_24h"]:,.2f}')
    print(f'   Estimated APY (Margin): {pool["apy"]:.2f}%')
    print(f'   24h Transactions: {pool["transactions_24h"]:,}')
    if pool['created_at']:
        print(f'   Pool Created: {pool["created_at"][:10]}')

# Save results
with open('experiments/top_10_pools_by_margin.json', 'w') as f:
    json.dump(top_10, f, indent=2)

print('\n' + '='*120)
print(f'\nResults saved to experiments/top_10_pools_by_margin.json')
print('\nNote: APY is calculated based on 24h fee earnings annualized.')
print('This represents the return (margin) that liquidity providers earn from trading fees.')
