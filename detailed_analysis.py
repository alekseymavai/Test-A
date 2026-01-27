#!/usr/bin/env python3
"""
Detailed analysis of the Uniswap V3 Pool Analysis Excel file
"""
import pandas as pd
import json

def detailed_analysis(filename):
    """Perform detailed analysis of the Excel file"""

    # Read the Excel file
    df = pd.read_excel(filename, sheet_name='Лист1')

    # Print all data for better understanding
    print("=" * 80)
    print("FULL DATA ANALYSIS")
    print("=" * 80)

    # Display all rows
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    print("\n\nALL DATA:")
    print(df.to_string())

    # Identify the structure
    print("\n\n" + "=" * 80)
    print("STRUCTURE ANALYSIS")
    print("=" * 80)

    # Find rows with "Итого" (Total)
    total_rows = df[df['Дата'].astype(str).str.contains('Итого', na=False)]
    print("\n\nTotal rows found:")
    print(total_rows)

    # Find wallet groups
    wallet_names = df['Кошель'].dropna().unique()
    print("\n\nUnique wallets:")
    for wallet in wallet_names:
        print(f"  - {wallet}")

    # Analyze numeric columns
    print("\n\n" + "=" * 80)
    print("NUMERIC ANALYSIS")
    print("=" * 80)

    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        non_null = df[col].dropna()
        if len(non_null) > 0:
            print(f"\n{col}:")
            print(f"  Min: {non_null.min()}")
            print(f"  Max: {non_null.max()}")
            print(f"  Mean: {non_null.mean()}")
            print(f"  Non-null count: {len(non_null)}")

    # Key metrics
    print("\n\n" + "=" * 80)
    print("KEY METRICS SUMMARY")
    print("=" * 80)

    # Extract commission totals
    commission_col = 'Unnamed: 13'
    total_commission = pd.to_numeric(df[commission_col], errors='coerce').sum()
    print(f"\nTotal commissions earned: {total_commission}")

    # Extract loan and pool body
    loans = df['Займ на 01.01.2026'].dropna()
    pool_bodies = df['Тело пула на 01.01.2026'].dropna()

    print(f"\nLoans on 01.01.2026: {loans}")
    print(f"Pool bodies on 01.01.2026: {pool_bodies}")

if __name__ == '__main__':
    detailed_analysis('STAIKINGII.xlsx')
