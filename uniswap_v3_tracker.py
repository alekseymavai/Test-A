#!/usr/bin/env python3
"""
Uniswap V3 Position Tracker
Автоматический трекер позиций в Uniswap V3 пулах с расчетом метрик

Требования:
- Python 3.8+
- pip install pandas openpyxl requests python-dotenv

Использование:
1. Создайте файл .env с вашими настройками:
   WALLETS=0xYourWallet1,0xYourWallet2
   RPC_URL=https://eth-mainnet.alchemyapi.io/v2/YOUR_KEY

2. Запустите скрипт:
   python uniswap_v3_tracker.py
"""

import pandas as pd
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import math

class UniswapV3Tracker:
    """Класс для отслеживания позиций в Uniswap V3"""

    def __init__(self):
        self.subgraph_url = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
        self.coingecko_url = "https://api.coingecko.com/api/v3"

    def get_positions(self, wallet_address: str) -> List[Dict]:
        """Получить все позиции для кошелька"""
        query = """
        query getPositions($owner: String!) {
          positions(where: {owner: $owner}) {
            id
            liquidity
            depositedToken0
            depositedToken1
            withdrawnToken0
            withdrawnToken1
            collectedFeesToken0
            collectedFeesToken1
            pool {
              id
              token0 {
                symbol
                decimals
              }
              token1 {
                symbol
                decimals
              }
              feeTier
              sqrtPrice
              tick
            }
            tickLower {
              tickIdx
            }
            tickUpper {
              tickIdx
            }
          }
        }
        """

        variables = {"owner": wallet_address.lower()}

        try:
            response = requests.post(
                self.subgraph_url,
                json={"query": query, "variables": variables},
                timeout=30
            )
            data = response.json()

            if "errors" in data:
                print(f"GraphQL errors: {data['errors']}")
                return []

            return data.get("data", {}).get("positions", [])
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []

    def get_eth_price(self) -> float:
        """Получить текущую цену ETH"""
        try:
            response = requests.get(
                f"{self.coingecko_url}/simple/price",
                params={"ids": "ethereum", "vs_currencies": "usd"},
                timeout=10
            )
            return response.json()["ethereum"]["usd"]
        except Exception as e:
            print(f"Error fetching ETH price: {e}")
            return 0.0

    def calculate_price_from_tick(self, tick: int) -> float:
        """Рассчитать цену из tick"""
        return 1.0001 ** tick

    def calculate_impermanent_loss(self, price_entry: float, price_current: float) -> float:
        """
        Рассчитать Impermanent Loss

        IL = 2 * sqrt(price_ratio) / (1 + price_ratio) - 1
        где price_ratio = price_current / price_entry
        """
        if price_entry <= 0:
            return 0.0

        price_ratio = price_current / price_entry
        il = 2 * math.sqrt(price_ratio) / (1 + price_ratio) - 1
        return il * 100  # В процентах

    def calculate_apr(self, fees_earned: float, principal: float, days: int) -> float:
        """Рассчитать APR (Annual Percentage Rate)"""
        if principal <= 0 or days <= 0:
            return 0.0

        daily_rate = fees_earned / principal / days
        apr = daily_rate * 365 * 100
        return apr

    def format_position_data(self, position: Dict, eth_price: float) -> Dict:
        """Форматировать данные позиции для отображения"""
        pool = position["pool"]

        # Рассчитать границы диапазона
        tick_lower = int(position["tickLower"]["tickIdx"])
        tick_upper = int(position["tickUpper"]["tickIdx"])
        current_tick = int(pool["tick"])

        price_lower = self.calculate_price_from_tick(tick_lower)
        price_upper = self.calculate_price_from_tick(tick_upper)
        price_current = self.calculate_price_from_tick(current_tick)

        # Рассчитать комиссии
        fees_token0 = float(position["collectedFeesToken0"])
        fees_token1 = float(position["collectedFeesToken1"])

        # Для простоты, предполагаем что token1 это USDC/USDT
        # В реальности нужно проверить и конвертировать
        total_fees_usd = fees_token0 * eth_price + fees_token1

        # Депозиты
        deposited_token0 = float(position["depositedToken0"])
        deposited_token1 = float(position["depositedToken1"])
        total_deposited_usd = deposited_token0 * eth_price + deposited_token1

        # Проверка, в диапазоне ли позиция
        in_range = tick_lower <= current_tick <= tick_upper

        return {
            "position_id": position["id"],
            "pool": f"{pool['token0']['symbol']}/{pool['token1']['symbol']}",
            "fee_tier": int(pool["feeTier"]) / 10000,  # В процентах
            "price_lower": price_lower,
            "price_current": price_current,
            "price_upper": price_upper,
            "in_range": in_range,
            "liquidity": int(position["liquidity"]),
            "deposited_usd": total_deposited_usd,
            "fees_usd": total_fees_usd,
            "token0_symbol": pool['token0']['symbol'],
            "token1_symbol": pool['token1']['symbol'],
        }

    def create_summary_report(self, positions: List[Dict], output_file: str = "positions_summary.xlsx"):
        """Создать сводный отчет в Excel"""
        if not positions:
            print("No positions to report")
            return

        # Создать DataFrame
        df = pd.DataFrame(positions)

        # Добавить расчетные колонки
        df["roi_%"] = (df["fees_usd"] / df["deposited_usd"] * 100).round(2)

        # Предполагаем средний период 30 дней для примера
        # В реальности нужно получать дату создания позиции
        df["estimated_apr_%"] = (df["roi_%"] * 365 / 30).round(2)

        # Отсортировать по ROI
        df = df.sort_values("roi_%", ascending=False)

        # Сохранить в Excel
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Positions', index=False)

            # Создать сводку
            summary = {
                "Metric": [
                    "Total Positions",
                    "In Range",
                    "Out of Range",
                    "Total Deposited (USD)",
                    "Total Fees Earned (USD)",
                    "Average ROI (%)",
                    "Average APR (%)"
                ],
                "Value": [
                    len(df),
                    df["in_range"].sum(),
                    len(df) - df["in_range"].sum(),
                    df["deposited_usd"].sum(),
                    df["fees_usd"].sum(),
                    df["roi_%"].mean(),
                    df["estimated_apr_%"].mean()
                ]
            }

            summary_df = pd.DataFrame(summary)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

        print(f"Report saved to {output_file}")


def main():
    """Основная функция"""
    print("=" * 80)
    print("Uniswap V3 Position Tracker")
    print("=" * 80)

    # Инициализация
    tracker = UniswapV3Tracker()

    # Пример кошелька (замените на свой)
    wallet = "0x0000000000000000000000000000000000000000"

    print(f"\nFetching positions for wallet: {wallet}")

    # Получить позиции
    positions = tracker.get_positions(wallet)

    if not positions:
        print("No positions found or error occurred")
        return

    print(f"Found {len(positions)} positions")

    # Получить цену ETH
    eth_price = tracker.get_eth_price()
    print(f"Current ETH price: ${eth_price:,.2f}")

    # Форматировать данные
    formatted_positions = []
    for pos in positions:
        formatted = tracker.format_position_data(pos, eth_price)
        formatted_positions.append(formatted)

        print(f"\nPosition: {formatted['pool']}")
        print(f"  Fee Tier: {formatted['fee_tier']}%")
        print(f"  Range: ${formatted['price_lower']:,.2f} - ${formatted['price_upper']:,.2f}")
        print(f"  Current: ${formatted['price_current']:,.2f}")
        print(f"  In Range: {'✓' if formatted['in_range'] else '✗'}")
        print(f"  Deposited: ${formatted['deposited_usd']:,.2f}")
        print(f"  Fees Earned: ${formatted['fees_usd']:,.2f}")

    # Создать отчет
    tracker.create_summary_report(formatted_positions)


if __name__ == "__main__":
    # Для демонстрации, показываем структуру
    print("""
    Этот скрипт автоматически получает данные о позициях в Uniswap V3.

    Для использования:
    1. Замените wallet адрес на свой
    2. Установите зависимости: pip install pandas openpyxl requests
    3. Запустите: python uniswap_v3_tracker.py

    Скрипт создаст Excel файл с детальной информацией о всех позициях.
    """)

    # Раскомментируйте для запуска:
    # main()
