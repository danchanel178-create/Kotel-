# Тепловой баланс котла

Десктопное приложение (Windows 10/11) для расчёта теплового баланса парового котла по **главе 5** учебника — формулы **5-01 … 5-24**.

**Версия:** 1.0.0

## Возможности

- Расчёт располагаемого тепла, потерь (q₂…q₆, q₅охл), КПД ηₖ, полезного тепла Qполн и расхода топлива B, Bₚ
- Интерполяция q₅ном по рис. 5.1
- Справочник топлив (JSON, расширяемый)
- Система плагинов — утилиты из каталога `plugins/`
- Калькулятор свойств пара IAPWS-IF97 с подстановкой энтальпий в баланс
- Сохранение и загрузка сессий расчёта (JSON)
- Практические рекомендации по результатам
- Модульное ядро `src/core` — можно использовать без GUI

## Быстрый старт

```bash
pip install -r requirements.txt
python main.py
```

или двойной клик по `run.bat`.

**Зависимости:** CustomTkinter ≥ 5.2, Pillow ≥ 10, iapws ≥ 1.5, matplotlib ≥ 3.8. Нужен Python с tkinter (обычно есть в стандартной установке на Windows).

## Документация

| Документ | Содержание |
|----------|------------|
| **[Документация PDF](docs/Teplovoy_balans_kotla_Dokumentatsiya.pdf)** | Полная документация одним файлом |
| [Руководство пользователя](docs/user-guide.md) | Интерфейс, разделы ввода, сохранение сессий |
| [Архитектура](docs/architecture.md) | Модули, потоки данных, слои |
| [Формулы](docs/formulas.md) | Соответствие формул 5-01…5-24 коду |
| [Программный API](docs/api.md) | Использование ядра без GUI, модели данных |
| [Плагины](docs/plugins.md) | API плагинов, калькулятор пара |
| [Справочные данные](docs/data.md) | fuels.json, q₅ном, формат сохранения |

Пересобрать PDF: `python docs/generate_pdf.py` (нужен пакет `reportlab`).

## Структура проекта

```
kotel/
├── main.py                 # Точка входа
├── run.bat                 # Запуск на Windows
├── requirements.txt
├── settings.json           # Настройки UI (режим подписей)
├── docs/                   # Документация
├── src/
│   ├── core/               # Расчётный движок
│   ├── data/               # Провайдеры данных
│   ├── plugins/            # API плагинов
│   └── ui/                 # Интерфейс CustomTkinter
├── data/reference/         # Справочные JSON
└── plugins/                # Сторонние утилиты
    └── steam_quality/      # Свойства воды/пара (IAPWS-IF97)
```

## Использование ядра без GUI

```python
from src.core.heat_balance import HeatBalanceCalculator
from src.core.models import HeatBalanceInput

calc = HeatBalanceCalculator()
result = calc.calculate(HeatBalanceInput())
print(result.eta_k, result.B)
```

Подробнее — в [docs/api.md](docs/api.md).

## Добавление плагина

1. Создайте `plugins/my_plugin/`
2. Добавьте `manifest.json` и `plugin.py` с `create_plugin()`
3. Перезапустите приложение

Подробнее — в [docs/plugins.md](docs/plugins.md).

## Развитие

- Подключение БД через `DatabaseDataProvider`
- Расширение калькулятора пара (процессы расширения)
- Интеграция в SCADA / инженерные системы через API ядра
