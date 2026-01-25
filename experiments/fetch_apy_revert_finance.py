#!/usr/bin/env python3
"""
Скрипт для получения 30-дневного APY пулов Uniswap v3 через Revert Finance.

ПРИМЕЧАНИЕ: Revert Finance предоставляет веб-интерфейс для анализа пулов,
но не имеет публичного API для программного доступа. Этот скрипт демонстрирует
методологию сбора данных и структуру выходных данных.

Методы получения данных с Revert Finance:
1. Веб-интерфейс: https://revert.finance/#/pool-ranking
2. Анализ конкретного пула: https://revert.finance/#/pool/{chain_id}/{pool_address}
3. Экспорт данных вручную через веб-интерфейс

Для получения APY за 30 дней используется следующая методология:

1. Открыть страницу пула на Revert Finance
2. Выбрать период "30 дней"
3. Записать метрики:
   - Total Fees (общие комиссии за период)
   - TVL (средний Total Value Locked)
   - APR/APY (если показан напрямую)
4. Если APY не показан, рассчитать: APY = (Fees_30d / TVL_avg) × (365 / 30) × 100%

Документация:
- Revert Finance: https://docs.revert.finance/
- Pool Analytics: https://revert.finance/#/pool-ranking
"""

import json
from typing import List, Dict, Any
from datetime import datetime


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


def get_revert_finance_url(pool_address: str, chain_id: int = 1) -> str:
    """
    Формирует URL для анализа пула на Revert Finance.

    Args:
        pool_address: Адрес пула
        chain_id: ID сети (1 = Ethereum Mainnet)

    Returns:
        URL для анализа пула
    """
    return f"https://revert.finance/#/pool/{chain_id}/{pool_address}"


def create_manual_data_collection_guide() -> str:
    """
    Создает руководство по ручному сбору данных с Revert Finance.

    Returns:
        Текстовое руководство
    """
    guide = """
=================================================================================
📋 РУКОВОДСТВО ПО СБОРУ ДАННЫХ С REVERT FINANCE
=================================================================================

Revert Finance не предоставляет публичный API, поэтому данные собираются вручную
через веб-интерфейс.

ИНСТРУКЦИЯ:
-----------

1. Откройте страницу рейтинга пулов:
   https://revert.finance/#/pool-ranking

2. Для каждого пула из списка:

   а) Найдите пул в списке или используйте прямую ссылку:
      https://revert.finance/#/pool/1/{адрес_пула}

   б) В интерфейсе выберите период "30d" (30 дней)

   в) Запишите следующие метрики:
      - Total Fees (USD) - общие комиссии за 30 дней
      - Avg TVL (USD) - средний TVL за период
      - APR/APY - если отображается
      - Volume 30d - объем торгов за 30 дней
      - Fee APR - APR от комиссий

   г) Если APY не отображается, рассчитайте по формуле:
      APY = (Total_Fees_30d / Avg_TVL) × (365 / 30) × 100%

3. Внесите данные в файл apy_30d_revert_finance.json

АЛЬТЕРНАТИВНЫЙ МЕТОД:
--------------------

Использовать встроенную функцию экспорта данных Revert Finance:

1. На странице Pool Ranking нажмите кнопку Export (если доступна)
2. Выберите формат CSV или JSON
3. Сохраните файл и обработайте данные

ВАЖНО:
------

- Убедитесь, что выбрана сеть Ethereum (chain_id = 1)
- Период анализа должен быть 30 дней
- Проверяйте актуальность данных (дата последнего обновления)
- Некоторые новые пулы могут не иметь 30-дневной истории

=================================================================================
"""
    return guide


def create_pool_urls_list() -> str:
    """
    Создает список прямых ссылок на пулы в Revert Finance.

    Returns:
        Отформатированный список ссылок
    """
    output = "\n" + "="*80 + "\n"
    output += "🔗 ПРЯМЫЕ ССЫЛКИ НА ПУЛЫ В REVERT FINANCE\n"
    output += "="*80 + "\n\n"

    for i, pool in enumerate(POOLS, 1):
        url = get_revert_finance_url(pool['address'])
        output += f"{i:2d}. {pool['name']}\n"
        output += f"    {url}\n\n"

    output += "="*80 + "\n"

    return output


def create_demo_results() -> List[Dict[str, Any]]:
    """
    Создает демонстрационную структуру данных для Revert Finance.

    Returns:
        Список с демо-данными
    """
    results = []

    for pool in POOLS:
        results.append({
            'name': pool['name'],
            'address': pool['address'],
            'revert_url': get_revert_finance_url(pool['address']),
            'apy_30d': 0,
            'apr_30d': 0,
            'total_fees_usd': 0,
            'avg_tvl_usd': 0,
            'volume_30d_usd': 0,
            'fee_apr': 0,
            'source': 'Revert Finance',
            'collection_method': 'Manual',
            'note': 'Данные должны быть собраны вручную через веб-интерфейс',
            'data_collection_date': None
        })

    return results


def create_data_template() -> str:
    """
    Создает шаблон для заполнения данных.

    Returns:
        JSON шаблон
    """
    template = {
        'collection_date': datetime.now().isoformat(),
        'period_days': 30,
        'chain': 'Ethereum Mainnet',
        'chain_id': 1,
        'source': 'Revert Finance',
        'pools': []
    }

    for pool in POOLS:
        template['pools'].append({
            'name': pool['name'],
            'address': pool['address'],
            'revert_url': get_revert_finance_url(pool['address']),
            # Поля для ручного заполнения:
            'total_fees_30d_usd': '<ЗАПОЛНИТЕ>',
            'avg_tvl_30d_usd': '<ЗАПОЛНИТЕ>',
            'volume_30d_usd': '<ЗАПОЛНИТЕ>',
            'fee_apr_30d': '<ЗАПОЛНИТЕ>',
            'apy_30d': '<РАССЧИТАЙТЕ: (total_fees_30d / avg_tvl_30d) * (365/30) * 100>',
            'data_collection_timestamp': '<УКАЖИТЕ ДАТУ>',
            'notes': '<ДОПОЛНИТЕЛЬНЫЕ ЗАМЕТКИ>'
        })

    return json.dumps(template, indent=2, ensure_ascii=False)


def main():
    """Основная функция."""
    print("=" * 80)
    print("📊 Получение 30-дневного APY через Revert Finance")
    print("=" * 80)
    print()

    print("⚠️  ВНИМАНИЕ: Revert Finance не предоставляет публичный API")
    print()
    print("Данные должны быть собраны вручную через веб-интерфейс.")
    print()

    # Выводим руководство
    print(create_manual_data_collection_guide())

    # Выводим ссылки на пулы
    print(create_pool_urls_list())

    # Создаем демо-результаты
    demo_results = create_demo_results()

    # Сохраняем демо-результаты
    output_file = 'experiments/apy_30d_revert_finance.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(demo_results, f, indent=2, ensure_ascii=False)

    print(f"💾 Демо-структура данных сохранена в {output_file}")
    print()

    # Создаем и сохраняем шаблон для заполнения
    template_file = 'experiments/apy_30d_revert_finance_template.json'
    with open(template_file, 'w', encoding='utf-8') as f:
        f.write(create_data_template())

    print(f"📝 Шаблон для ручного заполнения сохранен в {template_file}")
    print()

    print("СЛЕДУЮЩИЕ ШАГИ:")
    print("-" * 80)
    print("1. Откройте каждую ссылку из списка выше")
    print("2. Соберите данные по метрикам (Total Fees, TVL, Volume)")
    print("3. Заполните файл apy_30d_revert_finance_template.json")
    print("4. Рассчитайте APY по формуле: (Fees_30d / TVL_avg) × (365 / 30) × 100%")
    print("5. Сохраните заполненные данные в apy_30d_revert_finance.json")
    print("-" * 80)
    print()

    print("✅ Подготовка завершена")


if __name__ == '__main__':
    main()
