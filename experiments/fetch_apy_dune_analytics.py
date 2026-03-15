#!/usr/bin/env python3
"""
Скрипт для получения 30-дневного APY пулов Uniswap v3 через Dune Analytics API.

Требования:
- pip install dune-client
- Установить переменную окружения DUNE_API_KEY

Dune Analytics предоставляет доступ к историческим данным блокчейна через SQL запросы.
Для получения APY за 30 дней используется следующая методология:

1. Запрос исторических данных о комиссиях и TVL для каждого пула
2. Расчет APY = (Комиссии_30д / TVL_средний) × (365 / 30) × 100%
3. Сортировка пулов по APY

Документация: https://docs.dune.com/api-reference/executions/endpoint/execute-query
"""

import os
import json
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta

try:
    from dune_client.client import DuneClient
    from dune_client.query import QueryBase
    from dune_client.types import QueryParameter
    DUNE_AVAILABLE = True
except ImportError:
    DUNE_AVAILABLE = False
    print("⚠️  Модуль dune-client не установлен. Установите: pip install dune-client")


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


def create_dune_query() -> str:
    """
    Создает SQL запрос для Dune Analytics для получения данных о пулах за 30 дней.

    Этот запрос возвращает:
    - pool_address: адрес пула
    - total_fees_usd: общие комиссии за 30 дней в USD
    - avg_tvl_usd: средний TVL за 30 дней в USD
    - daily_volume_usd: средний дневной объем торгов в USD

    Примечание: Этот запрос нужно создать в Dune Analytics UI и получить query_id
    """

    pool_addresses = [p["address"].lower() for p in POOLS]
    addresses_list = "', '".join(pool_addresses)

    query = f"""
    WITH pool_daily_stats AS (
        SELECT
            pool AS pool_address,
            DATE_TRUNC('day', block_time) AS day,
            SUM(amount0 * p0.price + amount1 * p1.price) AS volume_usd,
            AVG(reserve0 * p0.price + reserve1 * p1.price) AS tvl_usd
        FROM uniswap_v3_ethereum.Pool_evt_Swap s
        LEFT JOIN prices.usd p0 ON p0.contract_address = s.token0 AND DATE_TRUNC('day', p0.minute) = DATE_TRUNC('day', s.block_time)
        LEFT JOIN prices.usd p1 ON p1.contract_address = s.token1 AND DATE_TRUNC('day', p1.minute) = DATE_TRUNC('day', s.block_time)
        WHERE pool IN ('{addresses_list}')
            AND block_time >= NOW() - INTERVAL '30' DAY
        GROUP BY 1, 2
    ),
    pool_fees AS (
        SELECT
            pool_address,
            SUM(volume_usd * fee_tier / 1000000) AS total_fees_usd,
            AVG(tvl_usd) AS avg_tvl_usd,
            AVG(volume_usd) AS daily_volume_usd,
            COUNT(DISTINCT day) AS days_count
        FROM pool_daily_stats pds
        LEFT JOIN uniswap_v3_ethereum.Factory_evt_PoolCreated pc ON pc.pool = pds.pool_address
        GROUP BY 1
    )
    SELECT
        pool_address,
        total_fees_usd,
        avg_tvl_usd,
        daily_volume_usd,
        days_count,
        CASE
            WHEN avg_tvl_usd > 0 THEN (total_fees_usd / avg_tvl_usd) * (365.0 / 30.0) * 100
            ELSE 0
        END AS apy_30d
    FROM pool_fees
    ORDER BY apy_30d DESC
    """

    return query


def fetch_pool_data_from_dune(api_key: str, query_id: int = None) -> List[Dict[str, Any]]:
    """
    Получает данные о пулах через Dune Analytics API.

    Args:
        api_key: API ключ Dune Analytics
        query_id: ID запроса в Dune (нужно создать запрос в Dune UI)

    Returns:
        Список данных о пулах с APY за 30 дней
    """
    if not DUNE_AVAILABLE:
        raise ImportError("dune-client не установлен")

    # Инициализация клиента
    dune = DuneClient(api_key=api_key)

    # Для примера используем query_id, который нужно создать в Dune
    # Пользователь должен создать запрос с SQL выше и получить query_id
    if query_id is None:
        raise ValueError(
            "Необходимо создать запрос в Dune Analytics UI с SQL из функции create_dune_query() "
            "и передать полученный query_id в эту функцию"
        )

    query = QueryBase(
        name="Uniswap V3 Pool APY 30 Days",
        query_id=query_id,
    )

    print(f"🔄 Выполнение запроса Dune Analytics (query_id: {query_id})...")
    result = dune.run_query(query=query, performance='medium')

    print(f"✅ Получено {len(result.result.rows)} записей")

    return result.result.rows


def calculate_apy_30d(pools_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Обрабатывает данные от Dune и рассчитывает APY.

    Args:
        pools_data: Данные от Dune Analytics

    Returns:
        Список пулов с рассчитанным APY
    """
    results = []

    for pool in POOLS:
        # Находим данные для текущего пула
        pool_data = next(
            (p for p in pools_data if p['pool_address'].lower() == pool['address'].lower()),
            None
        )

        if pool_data:
            results.append({
                'name': pool['name'],
                'address': pool['address'],
                'apy_30d': pool_data.get('apy_30d', 0),
                'total_fees_usd': pool_data.get('total_fees_usd', 0),
                'avg_tvl_usd': pool_data.get('avg_tvl_usd', 0),
                'daily_volume_usd': pool_data.get('daily_volume_usd', 0),
                'days_count': pool_data.get('days_count', 0),
                'source': 'Dune Analytics'
            })
        else:
            # Если данных нет, добавляем с нулевыми значениями
            results.append({
                'name': pool['name'],
                'address': pool['address'],
                'apy_30d': 0,
                'total_fees_usd': 0,
                'avg_tvl_usd': 0,
                'daily_volume_usd': 0,
                'days_count': 0,
                'source': 'Dune Analytics',
                'error': 'No data available'
            })

    # Сортируем по APY
    results.sort(key=lambda x: x['apy_30d'], reverse=True)

    return results


def main():
    """Основная функция."""
    print("=" * 80)
    print("📊 Получение 30-дневного APY через Dune Analytics")
    print("=" * 80)
    print()

    # Проверяем наличие API ключа
    api_key = os.getenv('DUNE_API_KEY')

    if not api_key:
        print("❌ ОШИБКА: Не установлена переменная окружения DUNE_API_KEY")
        print()
        print("Для получения API ключа:")
        print("1. Зайдите на https://dune.com")
        print("2. Создайте аккаунт или войдите")
        print("3. Перейдите в Settings -> API Keys")
        print("4. Создайте новый API ключ")
        print("5. Экспортируйте: export DUNE_API_KEY='your-api-key'")
        print()
        print("Также необходимо:")
        print("1. Создать запрос в Dune Analytics UI с SQL из функции create_dune_query()")
        print("2. Получить query_id созданного запроса")
        print("3. Передать query_id в функцию fetch_pool_data_from_dune()")
        print()

        # Выводим SQL для создания запроса
        print("SQL запрос для Dune Analytics:")
        print("-" * 80)
        print(create_dune_query())
        print("-" * 80)
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
                'daily_volume_usd': 0,
                'days_count': 0,
                'source': 'Dune Analytics',
                'note': 'Требуется API ключ для получения реальных данных'
            })

        # Сохраняем результаты
        output_file = 'experiments/apy_30d_dune_analytics.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(demo_results, f, indent=2, ensure_ascii=False)

        print(f"💾 Демо-результаты сохранены в {output_file}")
        print()
        print("⚠️  ВНИМАНИЕ: Это демо-данные. Для получения реальных данных требуется API ключ.")

        return

    try:
        # Здесь нужно указать query_id созданного запроса в Dune
        # query_id = 1234567  # Замените на ваш query_id

        print("⚠️  Для работы скрипта необходимо создать запрос в Dune Analytics")
        print("и указать query_id в коде (строка 185)")
        print()
        print("SQL запрос для создания в Dune:")
        print("-" * 80)
        print(create_dune_query())
        print("-" * 80)

        # Раскомментируйте после создания запроса в Dune:
        # pools_data = fetch_pool_data_from_dune(api_key, query_id=query_id)
        # results = calculate_apy_30d(pools_data)

        # # Сохраняем результаты
        # output_file = 'experiments/apy_30d_dune_analytics.json'
        # with open(output_file, 'w', encoding='utf-8') as f:
        #     json.dump(results, f, indent=2, ensure_ascii=False)

        # print(f"💾 Результаты сохранены в {output_file}")
        # print()
        # print("📊 Топ-10 пулов по APY (30д) - Dune Analytics:")
        # print()
        # for i, pool in enumerate(results, 1):
        #     print(f"{i:2d}. {pool['name']:25s} - APY: {pool['apy_30d']:7.2f}%")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
