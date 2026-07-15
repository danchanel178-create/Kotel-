# Архитектура

## Обзор

Приложение разделено на слои: **UI → ядро расчёта → данные / плагины**. Ядро не зависит от CustomTkinter и может встраиваться в другие системы.

```
main.py
  ├── apply_windows_fixes()          # DPI / Win32
  ├── JsonFileDataProvider           # data/reference/
  ├── PluginRegistry                 # plugins/
  └── HeatBalanceApp.mainloop()      # CustomTkinter
```

## Слои

### Точка входа — `main.py`

1. Добавляет корень проекта в `sys.path`
2. Применяет Windows-фиксы для CustomTkinter
3. Создаёт провайдер справочных данных
4. Загружает плагины
5. Запускает главное окно

### Ядро — `src/core/`

| Модуль | Назначение |
|--------|------------|
| `heat_balance.py` | `HeatBalanceCalculator` — цепочка формул 5-01…5-24 |
| `models.py` | Dataclass-модели входа/выхода |
| `tables.py` | Кривая q₅ном, таблица энтальпии шлака, интерполяция |
| `notation.py` | Unicode-обозначения инженерных величин |
| `steam.py` | Обёртка IAPWS-IF97 (состояния, насыщение, цикл котла) |

### Данные — `src/data/providers.py`

Абстракция `DataProvider`:

| Реализация | Источник |
|------------|----------|
| `JsonFileDataProvider` | `data/reference/*.json` (по умолчанию) |
| `InMemoryDataProvider` | Встроенные значения без файлов |
| `DatabaseDataProvider` | Заглушка под будущую БД |

### Плагины — `src/plugins/`

- `base.py` — `PluginBase`, `UtilityPlugin`, `CalculationPlugin`
- `registry.py` — сканирование `plugins/*/manifest.json`, динамический `importlib`

Хук жизненного цикла расчёта: `on_before_fuel_consumption` — перед формулами 5-17…5-24.

### UI — `src/ui/`

| Модуль | Назначение |
|--------|------------|
| `app.py` | Главное окно, вкладки, сбор входа, отображение результата |
| `widgets.py` | Переиспользуемые виджеты (поля, карточки, таблица, график) |
| `theme.py` | Тёмная «промышленная» палитра |
| `settings_store.py` / `settings_window.py` | Настройки и «О программе» |
| `logo.py` | Логотип из `assets/logo_header.png` (опционально) |
| `win32_fix.py` | Фиксы DPI и перетаскивания окна |

Внешние плагины с UI лежат в `plugins/` (не в `src/plugins/` — там только API).

## Поток расчёта

```
Пользователь заполняет вкладки
        │
        ▼
HeatBalanceApp._collect_input()  →  HeatBalanceInput
        │
        ▼
HeatBalanceCalculator.calculate()
  ├── 5-02…5-05  располагаемое тепло
  ├── 5-06…5-13  потери
  ├── 5-14…5-16  Σq, ηₖ, φ, Qполн
  ├── хуки плагинов (before_fuel_consumption)
  └── 5-17…5-24  расход топлива B, Bₚ
        │
        ▼
HeatBalanceResult
        │
        ▼
_display_results()  →  метрики, график, таблица, рекомендации
```

## Связь плагина пара с формой

Главное окно предоставляет методы хоста для утилит:

| Метод | Назначение |
|-------|------------|
| `get_steam_form_values()` | Текущие энтальпии из формы |
| `apply_steam_values(values)` | Подстановка энтальпий в поля полезного тепла / расхода |
| `highlight_steam_source_fields(keys)` | Подсветка изменённых полей |
| `activate_plugin(plugin_id)` | Активация плагина по id |

## Границы ответственности

- **Формулы и физика** — только `src/core`
- **Справочники** — JSON через `DataProvider`, без хардкода в UI
- **Окна-утилиты** — плагины; ядро UI их не знает по имени
- **Персистентность UI** — `settings.json`; сессии расчёта — пользовательские JSON-файлы
