# Система плагинов

Плагины расширяют приложение без изменения ядра UI: отдельные окна-утилиты или расчётные модули с хуками в цепочку теплового баланса.

## Каталог

Внешние плагины лежат в `plugins/<id>/`. API — в `src/plugins/`.

При старте `create_default_registry(ROOT)` сканирует все подкаталоги `plugins/`, читает `manifest.json` и загружает модуль через `importlib`.

## Манифест

`plugins/my_plugin/manifest.json`:

```json
{
  "id": "my_plugin",
  "name": "Моя утилита",
  "version": "1.0.0",
  "entry": "plugin.py",
  "description": "Краткое описание"
}
```

| Поле | Обязательно | Описание |
|------|-------------|----------|
| `id` | да | Уникальный идентификатор |
| `name` | да | Подпись в меню |
| `entry` | да | Имя Python-файла относительно папки плагина |
| `version` | нет | Версия |
| `description` | нет | Описание |

## Типы плагинов

### `UtilityPlugin`

Окно со своим UI. Методы:

```python
def activate(self, host) -> None: ...
def open_window(self, parent) -> None: ...
```

`host` — главное окно (`HeatBalanceApp`), для доступа к полям формы.

### `CalculationPlugin`

Без собственного окна — расчётный модуль:

```python
def calculate(self, params: dict) -> dict: ...
```

### Общий хук — `PluginBase`

```python
def on_before_fuel_consumption(self, context: dict) -> None:
    # context: {"input": HeatBalanceInput, "result": HeatBalanceResult}
    ...
```

Вызывается после 5-16 и до расчёта расхода топлива (5-17…5-24). Можно скорректировать `result` или положить данные в `context["plugin_data"]` (попадут в `result.plugin_contributions`).

## Шаблон утилиты

```python
from src.plugins.base import UtilityPlugin


class MyPlugin(UtilityPlugin):
    id = "my_plugin"
    name = "Моя утилита"
    version = "1.0.0"
    description = "Пример"

    def activate(self, host):
        self._host = host

    def open_window(self, parent):
        # создать Toplevel / CTkToplevel
        ...


def create_plugin():
    return MyPlugin()
```

Фабрика `create_plugin()` обязательна — реестр вызывает её при загрузке.

## Встроенный плагин: Свойства пара

| | |
|--|--|
| Путь | `plugins/steam_quality/` |
| Id | `steam_quality` |
| Версия | 3.1.0 |
| Стандарт | IAPWS-IF97 (`iapws`) |

Вкладки утилиты:

1. **Состояние** — расчёт по парам свойств (P-T, P-x, …)
2. **Котёл** — энтальпии цикла для подстановки в баланс
3. **Насыщение** — линия насыщения
4. **Таблицы** — табличные значения

Интеграция с формой баланса через методы хоста (`apply_steam_values` и др.). Ядро расчётов свойств также доступно напрямую из `src/core/steam.py`.

Опционально: запуск внешнего WaterSteamPro Calculator, если он установлен на Windows.

## Ошибки загрузки

Ошибки при загрузке отдельного плагина обрабатываются реестром без остановки приложения. Если утилита не появилась в меню — проверьте `manifest.json`, `create_plugin()` и импорты в `plugin.py`.
