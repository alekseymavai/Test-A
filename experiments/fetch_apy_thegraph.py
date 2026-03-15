#!/usr/bin/env python3
"""
Скрипт для получения 30-дневного APY пулов Uniswap v3 через The Graph API.

Требования:
- pip install requests
- API ключ The Graph (получить на https://thegraph.com/studio/)

The Graph предоставляет децентрализованный доступ к данным блокчейна через GraphQL.
Для получения APY за 30 дней используется следующая методология:

1. Запрос исторических данных PoolDayData для каждого пула за последние 30 дней
2. Суммирование комиссий и расчет среднего TVL
3. Расчет APY = (Комиссии_30д / TVL_средний) × (365 / 30) × 100%

Документация:
- Uniswap v3 Subgraph: https://docs.uniswap.org/api/subgraph/guides/v3-examples
- The Graph API: https://thegraph.com/docs/
"""

import os
import json
import requests
from typing import List, Dict, Any
from datetime import datetime, timedelta


# Список пулов для анализа
POOLS = [
    {"name": "XAUt / WETH 0.3%", "address": "0xc5c7c21f4e60770ca5991a8832127a40f5236f73"},
    {"name": "XAUt / USDT 0.05%", "address": "0x6546055f46e866a4b9a4a13e81273e3152bae5da"},
    {"name": "WETH / USDT 0.3%", "address": "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36"},
    {"name": "XAUt / USDT 0.3%", "address": "0xa91f80380d9cc9c86eb98d2965a0ded9e2000791"},
    {"name": "UNI / WBTC 0.3%", "address": "0x8f0cb37cdff37e004e0088f563e5fe39e05ccc5b"},
    {"name": "WLFI / USDT 0.3%", "address": "0x813b1bce815c15774f85f8ff6b0dcbbb75a1d995"},
    {"name": "BNB / WETH 1%", "address": "0x9e7809c21ba130c1a51c112928ea6474d9a9ae3c"},
    {"name": "ONDO / WETH 0.3%", "address": "0x7b1e5d984a43ee732de195628d20d05cfabc3cc7"},
    {"name": "PAXG / XAUt 0.05%", "address": "0xed7ef9a9a05a48858a507c080def0405ad1eaa3e"},
    {"name": "ENA / WETH 0.3%", "address": "0xc3db44adc1fcdfd5671f555236eae49f4a8eea18"},
]

# Uniswap v3 Subgraph ID на Ethereum Mainnet
UNISWAP_V3_SUBGRAPH_ID = "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"


def create_graphql_query(pool_address: str, days: int = 30) -> str:
    """
    Создает GraphQL запрос для получения исторических данных пула.

    Args:
        pool_address: Адрес пула
        days: Количество дней для анализа

    Returns:
        GraphQL запрос
    """
    # Вычисляем timestamp 30 дней назад
    timestamp_30d_ago = int((datetime.now() - timedelta(days=days)).timestamp())

    query = """
    {{
      pool(id: "{pool_id}") {{
        id
        token0 {{
          symbol
        }}
        token1 {{
          symbol
        }}
        feeTier
        totalValueLockedUSD
        volumeUSD
        feesUSD
        poolDayData(
          first: {days}
          orderBy: date
          orderDirection: desc
          where: {{ date_gte: {timestamp} }}
        ) {{
          date
          volumeUSD
          tvlUSD
          feesUSD
          txCount
        }}
      }}
    }}
    """.format(
        pool_id=pool_address.lower(),
        days=days,
        timestamp=timestamp_30d_ago
    )

    return query


def fetch_pool_data_from_thegraph(
    api_key: str,
    pool_address: str,
    days: int = 30
) -> Dict[str, Any]:
    """
    Получает данные пула через The Graph API.

    Args:
        api_key: API ключ The Graph
        pool_address: Адрес пула
        days: Количество дней для анализа

    Returns:
        Данные пула
    """
    # Формируем endpoint
    endpoint = f"https://gateway.thegraph.com/api/{api_key}/subgraphs/id/{UNISWAP_V3_SUBGRAPH_ID}"

    # Создаем запрос
    query = create_graphql_query(pool_address, days)

    # Выполняем запрос
    response = requests.post(
        endpoint,
        json={'query': query},
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code != 200:
        raise Exception(f"GraphQL query failed: {response.status_code} - {response.text}")

    data = response.json()

    if 'errors' in data:
        raise Exception(f"GraphQL errors: {data['errors']}")

    return data['data']['pool']


def calculate_apy_from_thegraph_data(pool_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Рассчитывает APY на основе данных от The Graph.

    Args:
        pool_data: Данные пула от The Graph

    Returns:
        Словарь с метриками APY
    """
    if not pool_data or not pool_data.get('poolDayData'):
        return {
            'apy_30d': 0,
            'total_fees_usd': 0,
            'avg_tvl_usd': 0,
            'total_volume_usd': 0,
            'days_count': 0,
            'error': 'No pool day data available'
        }

    pool_day_data = pool_data['poolDayData']

    # Суммируем комиссии и объемы
    total_fees = sum(float(day['feesUSD']) for day in pool_day_data)
    total_volume = sum(float(day['volumeUSD']) for day in pool_day_data)

    # Рассчитываем средний TVL
    tvl_values = [float(day['tvlUSD']) for day in pool_day_data if float(day['tvlUSD']) > 0]
    avg_tvl = sum(tvl_values) / len(tvl_values) if tvl_values else 0

    days_count = len(pool_day_data)

    # Рассчитываем APY
    if avg_tvl > 0 and days_count > 0:
        apy_30d = (total_fees / avg_tvl) * (365.0 / days_count) * 100
    else:
        apy_30d = 0

    return {
        'apy_30d': apy_30d,
        'total_fees_usd': total_fees,
        'avg_tvl_usd': avg_tvl,
        'total_volume_usd': total_volume,
        'days_count': days_count,
        'daily_avg_volume_usd': total_volume / days_count if days_count > 0 else 0
    }


def fetch_all_pools_data(api_key: str) -> List[Dict[str, Any]]:
    """
    Получает данные для всех пулов.

    Args:
        api_key: API ключ The Graph

    Returns:
        Список данных по всем пулам
    """
    results = []

    for i, pool in enumerate(POOLS, 1):
        print(f"🔄 [{i}/{len(POOLS)}] Получение данных для {pool['name']}...")

        try:
            # Получаем данные пула
            pool_data = fetch_pool_data_from_thegraph(api_key, pool['address'])

            # Рассчитываем метрики
            metrics = calculate_apy_from_thegraph_data(pool_data)

            # Добавляем результат
            results.append({
                'name': pool['name'],
                'address': pool['address'],
                'token0': pool_data.get('token0', {}).get('symbol', 'N/A'),
                'token1': pool_data.get('token1', {}).get('symbol', 'N/A'),
                'fee_tier': pool_data.get('feeTier', 0),
                **metrics,
                'source': 'The Graph'
            })

            print(f"✅ {pool['name']}: APY = {metrics['apy_30d']:.2f}%")

        except Exception as e:
            print(f"❌ Ошибка при получении данных для {pool['name']}: {e}")
            results.append({
                'name': pool['name'],
                'address': pool['address'],
                'apy_30d': 0,
                'total_fees_usd': 0,
                'avg_tvl_usd': 0,
                'total_volume_usd': 0,
                'days_count': 0,
                'source': 'The Graph',
                'error': str(e)
            })

    # Сортируем по APY
    results.sort(key=lambda x: x['apy_30d'], reverse=True)

    return results


def main():
    """Основная функция."""
    print("=" * 80)
    print("📊 Получение 30-дневного APY через The Graph")
    print("=" * 80)
    print()

    # Проверяем наличие API ключа
    api_key = os.getenv('THEGRAPH_API_KEY')

    if not api_key:
        print("❌ ОШИБКА: Не установлена переменная окружения THEGRAPH_API_KEY")
        print()
        print("Для получения API ключа:")
        print("1. Зайдите на https://thegraph.com/studio/")
        print("2. Создайте аккаунт или войдите")
        print("3. Создайте новый API ключ")
        print("4. Экспортируйте: export THEGRAPH_API_KEY='your-api-key'")
        print()

        # Создаем демо-данные для примера
        print("📝 Создание демо-данных для примера...")
        demo_results = []
        for pool in POOLS:
            demo_results.append({
                'name': pool['name'],
                'address': pool['address'],
                'apy_30d': 0,
                'total_fees_usd': 0,
                'avg_tvl_usd': 0,
                'total_volume_usd': 0,
                'days_count': 0,
                'source': 'The Graph',
                'note': 'Требуется API ключ для получения реальных данных'
            })

        # Сохраняем результаты
        output_file = 'experiments/apy_30d_thegraph.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(demo_results, f, indent=2, ensure_ascii=False)

        print(f"💾 Демо-результаты сохранены в {output_file}")
        print()
        print("⚠️  ВНИМАНИЕ: Это демо-данные. Для получения реальных данных требуется API ключ.")
        print()
        print("Пример GraphQL запроса для The Graph:")
        print("-" * 80)
        print(create_graphql_query(POOLS[0]['address']))
        print("-" * 80)

        return

    try:
        # Получаем данные для всех пулов
        results = fetch_all_pools_data(api_key)

        # Сохраняем результаты
        output_file = 'experiments/apy_30d_thegraph.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print()
        print(f"💾 Результаты сохранены в {output_file}")
        print()
        print("📊 Топ-10 пулов по APY (30д) - The Graph:")
        print()
        for i, pool in enumerate(results, 1):
            print(f"{i:2d}. {pool['name']:25s} - APY: {pool['apy_30d']:7.2f}%")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
