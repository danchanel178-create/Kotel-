# Программный API ядра

Ядро (`src/core`) не требует GUI. Подходит для скриптов, тестов и встраивания.

## Минимальный пример

```python
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent  # корень kotel/
sys.path.insert(0, str(ROOT))

from src.core.heat_balance import HeatBalanceCalculator
from src.core.models import (
    FuelType,
    FuelProperties,
    HeatBalanceInput,
    UsefulHeatParams,
)

inp = HeatBalanceInput(
    fuel=FuelProperties(
        fuel_type=FuelType.GASEOUS,
        Q_i_p=35588.0,
        A_p=0.0,
        W_r_c=0.0,
    ),
    useful=UsefulHeatParams(
        D_pe=20.0,      # кг/с
        i_pe=3400.0,    # кДж/кг
        i_pv=420.0,
    ),
)

calc = HeatBalanceCalculator()
result = calc.calculate(inp)

print(f"η_k = {result.eta_k:.2f} %")
print(f"Q_полн = {result.Q_poln:.1f} кВт")
print(f"B = {result.B:.4f} кг/с")
print(f"Формулы: {result.formulas_used}")
print(f"Рекомендации: {result.warnings}")
```

## С провайдером данных и плагинами

```python
from src.data.providers import JsonFileDataProvider
from src.plugins.registry import create_default_registry
from src.core.heat_balance import HeatBalanceCalculator

data = JsonFileDataProvider(ROOT / "data" / "reference")
plugins = create_default_registry(ROOT)
calc = HeatBalanceCalculator(data_provider=data, plugin_registry=plugins)

fuel = data.get_fuel_properties("natural_gas")
# ... заполнить HeatBalanceInput из fuel ...
```

Кривая q₅ном берётся из провайдера (если передан); иначе — встроенная в `tables.py`.

## Модели входа (`src/core/models.py`)

| Класс | Содержание |
|-------|------------|
| `FuelProperties` | Тип топлива, Qᵢᵖ, влажность, зольность, карбонаты, iₜл |
| `AshLosses` | Доли золы, горючее в шлаке/уносе, t_шл |
| `FlueGasParams` | Энтальпии газов, α_ух, β, q₃ |
| `BoilerParams` | D_ном, D, q₅ном override, H_неохл, Q_в.вн |
| `UsefulHeatParams` | Расходы/энтальпии пара и воды для Qполн |
| `FuelConsumptionParams` | Опции 5-17…5-23 |
| `HeatBalanceInput` | Агрегат всех групп |

Тип топлива: `FuelType.SOLID_LIQUID` / `FuelType.GASEOUS`.

## Модель результата — `HeatBalanceResult`

Основные поля:

| Поле | Единица | Смысл |
|------|---------|--------|
| `Q_p_p` | кДж/кг (или кДж/м³) | Располагаемое тепло |
| `q2`…`q6_shl`, `q5_oxl` | % | Статьи потерь |
| `sum_q` | % | Σq |
| `eta_k` | % | КПД |
| `phi` | — | Коэффициент сохранения тепла |
| `Q_poln` | кВт | Полезное тепло |
| `B` | кг/с (или м³/с) | Расход топлива |
| `B_p` | то же | Расчётный расход |
| `formulas_used` | list[str] | Номера формул |
| `warnings` | list[str] | Рекомендации |
| `plugin_contributions` | dict | Данные от плагинов |

Сериализация: `result.to_dict()`.

## Свойства пара — `src/core/steam.py`

Независимо от GUI:

```python
from src.core.steam import calculate_state, calculate_boiler_cycle

state = calculate_state(mode="P-T", p=10.0, t=500.0)  # см. docstring модуля
cycle = calculate_boiler_cycle(...)  # i_pe, i_pv, i_sat, i_phi
```

Режимы ввода состояния: P-T, P-x, P-h, P-s, T-x, h-s, T-s, насыщение по P/T. Поддерживаются разные единицы давления и температуры.

## Конструктор калькулятора

```python
HeatBalanceCalculator(
    data_provider: DataProvider | None = None,
    plugin_registry: PluginRegistry | None = None,
)
```

Оба аргумента опциональны: без них работают встроенные таблицы и нет хуков плагинов.
