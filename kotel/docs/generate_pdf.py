#!/usr/bin/env python3
"""Генерация подробной PDF-документации проекта «Тепловой баланс котла»."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "Teplovoy_balans_kotla_Dokumentatsiya.pdf"

# Windows fonts with Cyrillic
FONT_DIR = Path(r"C:\Windows\Fonts")
pdfmetrics.registerFont(TTFont("DocSans", str(FONT_DIR / "arial.ttf")))
pdfmetrics.registerFont(TTFont("DocSansBold", str(FONT_DIR / "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("DocMono", str(FONT_DIR / "consola.ttf")))

ACCENT = colors.HexColor("#C45C26")
DARK = colors.HexColor("#1A1A1A")
MUTED = colors.HexColor("#555555")
SOFT = colors.HexColor("#F5F2ED")
LINE = colors.HexColor("#D0CBC3")
CODE_BG = colors.HexColor("#F0ECE6")


def make_styles():
    base = getSampleStyleSheet()
    styles = {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName="DocSansBold",
            fontSize=26,
            leading=32,
            textColor=DARK,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            fontName="DocSans",
            fontSize=14,
            leading=20,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            fontName="DocSans",
            fontSize=11,
            leading=16,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "h1": ParagraphStyle(
            "h1",
            fontName="DocSansBold",
            fontSize=16,
            leading=22,
            textColor=ACCENT,
            spaceBefore=18,
            spaceAfter=10,
            borderPadding=3,
        ),
        "h2": ParagraphStyle(
            "h2",
            fontName="DocSansBold",
            fontSize=13,
            leading=18,
            textColor=DARK,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3",
            fontName="DocSansBold",
            fontSize=11,
            leading=15,
            textColor=DARK,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="DocSans",
            fontSize=10,
            leading=14,
            textColor=DARK,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontName="DocSans",
            fontSize=10,
            leading=14,
            textColor=DARK,
            leftIndent=8,
            spaceAfter=2,
        ),
        "code": ParagraphStyle(
            "code",
            fontName="DocMono",
            fontSize=8,
            leading=11,
            textColor=DARK,
            backColor=CODE_BG,
            leftIndent=4,
            rightIndent=4,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "caption": ParagraphStyle(
            "caption",
            fontName="DocSans",
            fontSize=8,
            leading=11,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceBefore=2,
            spaceAfter=10,
        ),
        "toc": ParagraphStyle(
            "toc",
            fontName="DocSans",
            fontSize=11,
            leading=18,
            textColor=DARK,
            leftIndent=10,
            spaceAfter=2,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="DocSans",
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "th": ParagraphStyle(
            "th",
            fontName="DocSansBold",
            fontSize=8,
            leading=11,
            textColor=DARK,
        ),
        "td": ParagraphStyle(
            "td",
            fontName="DocSans",
            fontSize=8,
            leading=11,
            textColor=DARK,
        ),
    }
    return styles


def p(styles, key, text):
    return Paragraph(text.replace("\n", "<br/>"), styles[key])


def bullets(styles, items: list[str]):
    flow = []
    for item in items:
        flow.append(Paragraph(f"• {item}", styles["bullet"]))
    flow.append(Spacer(1, 4))
    return flow


def code_block(styles, text: str):
    return Preformatted(text.strip("\n"), styles["code"])


def table(styles, headers: list[str], rows: list[list[str]], col_widths=None):
    data = [[Paragraph(h, styles["th"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), styles["td"]) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), SOFT),
                ("TEXTCOLOR", (0, 0), (-1, 0), DARK),
                ("FONTNAME", (0, 0), (-1, 0), "DocSansBold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
            ]
        )
    )
    return t


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, A4[1] - 1.4 * cm, A4[0] - 2 * cm, A4[1] - 1.4 * cm)
    canvas.setFont("DocSans", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(2 * cm, A4[1] - 1.1 * cm, "Тепловой баланс котла — документация")
    canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.1 * cm, "v1.0.0")
    canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.drawCentredString(A4[0] / 2, 1.0 * cm, f"стр. {doc.page}")
    canvas.restoreState()


def build():
    styles = make_styles()
    story = []
    w = A4[0] - 4 * cm  # content width

    # ===== COVER =====
    story.append(Spacer(1, 4 * cm))
    story.append(p(styles, "cover_title", "Тепловой баланс котла"))
    story.append(p(styles, "cover_sub", "Подробная техническая документация"))
    story.append(Spacer(1, 1 * cm))
    story.append(
        p(
            styles,
            "cover_meta",
            "Десктопное приложение для расчёта теплового баланса<br/>парового котла по формулам главы 5 (5-01 — 5-24)",
        )
    )
    story.append(Spacer(1, 2 * cm))
    story.append(p(styles, "cover_meta", "Версия приложения: <b>1.0.0</b>"))
    story.append(p(styles, "cover_meta", "Платформа: Windows 10 / 11 · Python 3"))
    story.append(p(styles, "cover_meta", "Стек: CustomTkinter · IAPWS-IF97 · matplotlib"))
    story.append(Spacer(1, 3 * cm))
    story.append(
        p(
            styles,
            "cover_meta",
            "Документ объединяет руководство пользователя,<br/>описание архитектуры, формул, API, плагинов и справочных данных.",
        )
    )
    story.append(PageBreak())

    # ===== TOC =====
    story.append(p(styles, "h1", "Содержание"))
    toc_items = [
        "1. Назначение и возможности",
        "2. Установка и запуск",
        "3. Руководство пользователя",
        "4. Архитектура системы",
        "5. Формулы теплового баланса",
        "6. Программный API ядра",
        "7. Система плагинов",
        "8. Справочные данные и форматы файлов",
        "9. Зависимости и структура проекта",
        "10. Развитие и ограничения",
    ]
    for item in toc_items:
        story.append(p(styles, "toc", item))
    story.append(PageBreak())

    # ===== 1 =====
    story.append(p(styles, "h1", "1. Назначение и возможности"))
    story.append(
        p(
            styles,
            "body",
            "Приложение <b>«Тепловой баланс котла»</b> предназначено для инженерного "
            "расчёта теплового баланса парового котла. Расчёты выполняются по формулам "
            "главы 5 учебника (номера 5-01 — 5-24): располагаемое тепло топлива, статьи "
            "потерь, КПД котла, полезная тепловая мощность и расход топлива.",
        )
    )
    story.append(p(styles, "h2", "Основные возможности"))
    story.extend(
        bullets(
            styles,
            [
                "Расчёт располагаемого тепла Qₚᵖ, потерь q₂…q₆ и q₅охл, суммы потерь Σq, КПД ηₖ",
                "Расчёт полезного тепла Qполн и расходов топлива B, Bₚ",
                "Интерполяция номинальных потерь в окружающую среду q₅ном по рис. 5.1",
                "Справочник топлив на JSON (15 пресетов, расширяемый)",
                "Система плагинов — сторонние утилиты из каталога plugins/",
                "Калькулятор свойств воды и пара по стандарту IAPWS-IF97 с подстановкой энтальпий в баланс",
                "Сохранение и загрузка сессий расчёта в JSON",
                "Практические рекомендации по результатам (анализ режима)",
                "Модульное ядро src/core — использование без графического интерфейса",
            ],
        )
    )
    story.append(p(styles, "h2", "Для кого предназначено"))
    story.append(
        p(
            styles,
            "body",
            "Для студентов теплоэнергетических специальностей, инженеров-энергетиков и "
            "расчётчиков котельных установок, которым нужен прозрачный расчёт по учебным "
            "формулам с сохранением исходных данных и возможностью встраивания ядра в "
            "другие программные системы.",
        )
    )

    # ===== 2 =====
    story.append(p(styles, "h1", "2. Установка и запуск"))
    story.append(p(styles, "h2", "Требования"))
    story.extend(
        bullets(
            styles,
            [
                "Python 3 (с поддержкой tkinter — обычно есть в установке на Windows)",
                "Windows 10/11 рекомендуется (есть оптимизации DPI и перетаскивания окна)",
                "pip для установки зависимостей",
            ],
        )
    )
    story.append(p(styles, "h2", "Установка зависимостей"))
    story.append(code_block(styles, "pip install -r requirements.txt"))
    story.append(
        table(
            styles,
            ["Пакет", "Версия", "Назначение"],
            [
                ["customtkinter", "≥ 5.2.0", "Современный GUI на базе tkinter"],
                ["Pillow", "≥ 10.0.0", "Отрисовка логотипа"],
                ["iapws", "≥ 1.5.0", "Свойства воды/пара IAPWS-IF97"],
                ["matplotlib", "≥ 3.8.0", "Диаграмма потерь в результатах"],
            ],
            col_widths=[w * 0.28, w * 0.18, w * 0.54],
        )
    )
    story.append(Spacer(1, 8))
    story.append(p(styles, "h2", "Запуск"))
    story.append(code_block(styles, "python main.py"))
    story.append(
        p(
            styles,
            "body",
            "Альтернатива на Windows: двойной клик по файлу <b>run.bat</b> "
            "(при ошибке окно консоли не закроется сразу).",
        )
    )
    story.append(p(styles, "h2", "Последовательность при старте"))
    story.extend(
        bullets(
            styles,
            [
                "Корень проекта добавляется в sys.path",
                "Применяются Windows-фиксы (src/ui/win32_fix.py)",
                "Создаётся JsonFileDataProvider для data/reference/",
                "Загружаются плагины из plugins/ через PluginRegistry",
                "Запускается главное окно HeatBalanceApp",
            ],
        )
    )

    # ===== 3 =====
    story.append(PageBreak())
    story.append(p(styles, "h1", "3. Руководство пользователя"))
    story.append(
        p(
            styles,
            "body",
            "Интерфейс построен на CustomTkinter в тёмной промышленной палитре. "
            "Слева — навигация по шести разделам, справа — поля ввода или результаты.",
        )
    )

    story.append(p(styles, "h2", "3.1. Топливо"))
    story.extend(
        bullets(
            styles,
            [
                "Выбор пресета из справочника (газ, мазут, угли и др.) либо ручной ввод",
                "Тип топлива: твёрдое/жидкое или газообразное — влияет на формулу Qₚᵖ (5-02 / 5-02а)",
                "Параметры: Qᵢᵖ, Aᵖ, влажность, теплоёмкость cₜл, (CO₂)карб",
                "Опция учёта физического тепла топлива iₜл = cₜл · tₜл",
                "Параметры шлака и уноса для q₄ и q₆: доли золы, содержание горючего, температура шлака",
            ],
        )
    )

    story.append(p(styles, "h2", "3.2. Уходящие газы"))
    story.extend(
        bullets(
            styles,
            [
                "Энтальпии I_ух, I_х.в⁰, I_г.в",
                "Коэффициент избытка воздуха α_ух",
                "Доля рециркуляции воздуха β",
                "Потери от химической неполноты q₃ (%) — задаются вручную",
            ],
        )
    )

    story.append(p(styles, "h2", "3.3. Котёл"))
    story.extend(
        bullets(
            styles,
            [
                "Номинальная и фактическая паропроизводительность D_ном, D (т/ч)",
                "Ручное переопределение q₅ном (иначе — интерполяция по рис. 5.1)",
                "Площадь неохлаждаемых поверхностей H_неохл",
                "Тепло с подогретым воздухом Q_в.вн (для твёрдого/жидкого топлива)",
            ],
        )
    )

    story.append(p(styles, "h2", "3.4. Полезное тепло"))
    story.append(
        p(
            styles,
            "body",
            "Параметры формулы 5-16: расходы и энтальпии перегретого пара, питательной воды, "
            "непрерывной продувки, пара через пароперегреватель, отборы тепла. "
            "Энтальпии i_пе, i_пв, i', i_φ можно рассчитать в плагине «Свойства пара» "
            "и подставить в форму одной кнопкой.",
        )
    )

    story.append(p(styles, "h2", "3.5. Расход топлива"))
    story.extend(
        bullets(
            styles,
            [
                "Переопределение Q_к (по умолчанию берётся Qполн)",
                "Тепло внешнего воздуха (формула 5-20)",
                "Паровое дутьё / впрыск (формула 5-21)",
            ],
        )
    )

    story.append(p(styles, "h2", "3.6. Результаты"))
    story.extend(
        bullets(
            styles,
            [
                "Метрики: ηₖ, Qполн, B, Bₚ, Σq",
                "Столбчатая диаграмма статей потерь",
                "Таблица полей результата и список использованных формул",
                "Практические рекомендации по режиму работы",
            ],
        )
    )

    story.append(p(styles, "h2", "3.7. Меню и настройки"))
    story.append(
        table(
            styles,
            ["Действие", "Описание"],
            [
                ["Сохранить", "Запись входных данных (и результата) в JSON v2"],
                ["Загрузить", "Восстановление полей из сохранённого JSON"],
                ["Утилиты", "Открытие плагинов (например, «Свойства пара»)"],
                ["Настройки", "Режим подписей полей; сведения о программе"],
            ],
            col_widths=[w * 0.25, w * 0.75],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        p(
            styles,
            "body",
            "Файл <b>settings.json</b>: параметр <b>label_mode</b> = full | compact — "
            "полные подписи (символ + описание + единица) или компактные (символ + единица).",
        )
    )

    story.append(p(styles, "h2", "3.8. Типовой сценарий работы"))
    story.extend(
        bullets(
            styles,
            [
                "Выберите топливо из справочника или введите характеристики вручную",
                "Заполните уходящие газы и параметры котла",
                "При необходимости откройте «Свойства пара», рассчитайте энтальпии и подставьте их",
                "Укажите полезные тепловые нагрузки",
                "Выполните расчёт и откройте раздел «Результаты»",
                "При необходимости сохраните сессию в JSON",
            ],
        )
    )

    story.append(p(styles, "h2", "3.9. Требования к данным"))
    story.extend(
        bullets(
            styles,
            [
                "Qᵢᵖ и располагаемое тепло должны быть положительными",
                "D &gt; 0 для корректного пересчёта q₅ по нагрузке",
                "Для B нужны Q_к &gt; 0 и знаменатель формулы 5-19 ≠ 0",
                "При некорректных данных показываются рекомендации, приложение не аварийно завершается",
            ],
        )
    )

    # ===== 4 =====
    story.append(PageBreak())
    story.append(p(styles, "h1", "4. Архитектура системы"))
    story.append(
        p(
            styles,
            "body",
            "Приложение разделено на слои: <b>UI → ядро расчёта → данные / плагины</b>. "
            "Ядро не зависит от CustomTkinter и может встраиваться в другие системы.",
        )
    )
    story.append(code_block(
        styles,
        """main.py
  ├── apply_windows_fixes()          # DPI / Win32
  ├── JsonFileDataProvider           # data/reference/
  ├── PluginRegistry                 # plugins/
  └── HeatBalanceApp.mainloop()      # CustomTkinter""",
    ))

    story.append(p(styles, "h2", "4.1. Слои и модули"))
    story.append(
        table(
            styles,
            ["Слой", "Путь", "Назначение"],
            [
                ["Точка входа", "main.py", "Инициализация, запуск GUI"],
                ["Ядро", "src/core/", "Формулы, модели, таблицы, steam"],
                ["Данные", "src/data/", "DataProvider и JSON/БД-провайдеры"],
                ["API плагинов", "src/plugins/", "Базовые классы и реестр"],
                ["Интерфейс", "src/ui/", "CustomTkinter UI"],
                ["Утилиты", "plugins/", "Внешние плагины (steam_quality и др.)"],
                ["Справочники", "data/reference/", "fuels.json, q5_nominal.json"],
            ],
            col_widths=[w * 0.2, w * 0.28, w * 0.52],
        )
    )
    story.append(Spacer(1, 8))

    story.append(p(styles, "h3", "Ядро (src/core/)"))
    story.append(
        table(
            styles,
            ["Модуль", "Назначение"],
            [
                ["heat_balance.py", "HeatBalanceCalculator — цепочка формул 5-01…5-24"],
                ["models.py", "Dataclass-модели входа и выхода"],
                ["tables.py", "Кривая q₅ном, энтальпия шлака, интерполяция"],
                ["notation.py", "Unicode-обозначения инженерных величин"],
                ["steam.py", "Обёртка IAPWS-IF97"],
            ],
            col_widths=[w * 0.28, w * 0.72],
        )
    )
    story.append(Spacer(1, 8))

    story.append(p(styles, "h2", "4.2. Поток расчёта"))
    story.append(code_block(
        styles,
        """Пользователь заполняет вкладки
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
HeatBalanceResult → метрики, график, рекомендации""",
    ))

    story.append(p(styles, "h2", "4.3. Провайдеры данных"))
    story.append(
        table(
            styles,
            ["Класс", "Источник"],
            [
                ["DataProvider", "Абстрактный интерфейс"],
                ["JsonFileDataProvider", "data/reference/*.json (по умолчанию)"],
                ["InMemoryDataProvider", "Встроенные значения без файлов"],
                ["DatabaseDataProvider", "Заглушка под будущую БД"],
            ],
            col_widths=[w * 0.35, w * 0.65],
        )
    )
    story.append(Spacer(1, 8))

    story.append(p(styles, "h2", "4.4. Связь плагина пара с формой"))
    story.append(
        table(
            styles,
            ["Метод хоста", "Назначение"],
            [
                ["get_steam_form_values()", "Чтение текущих энтальпий из формы"],
                ["apply_steam_values(values)", "Подстановка энтальпий в поля"],
                ["highlight_steam_source_fields(keys)", "Подсветка изменённых полей"],
                ["activate_plugin(plugin_id)", "Активация плагина по id"],
            ],
            col_widths=[w * 0.45, w * 0.55],
        )
    )

    # ===== 5 =====
    story.append(PageBreak())
    story.append(p(styles, "h1", "5. Формулы теплового баланса"))
    story.append(
        p(
            styles,
            "body",
            "Реализация: класс <b>HeatBalanceCalculator</b> в файле "
            "<b>src/core/heat_balance.py</b>. Нумерация соответствует главе 5 учебника.",
        )
    )
    story.append(
        table(
            styles,
            ["Формула", "Что считается", "Примечание"],
            [
                ["5-01", "Проверка баланса Qₚᵖ = Q₁+…+Q₆", "Информационно"],
                ["5-02", "Qₚᵖ твёрдое/жидкое топливо", "FuelType.SOLID_LIQUID"],
                ["5-02а", "Qₚᵖ газообразное", "FuelType.GASEOUS"],
                ["5-03", "Физическое тепло iₜл = cₜл·tₜл", "Опционально"],
                ["5-04", "Тепло на размораживание ΔQ_разм", "При W₁ᵖ &gt; W₂ᵖ"],
                ["5-05", "Разложение карбонатов", "40·(CO₂)карб"],
                ["5-06", "Потери с уходящими газами q₂", ""],
                ["5-07", "Химическая неполнота q₃", "Из ввода flue.q3"],
                ["5-08", "ΔI_зл", "Поправка золы/уноса"],
                ["5-09", "Механическая неполнота q₄", ""],
                ["5-10", "Потери в окружение q₅", "q₅ном·D_ном/D"],
                ["5-11", "Коэффициент сохранения тепла φ", ""],
                ["5-12", "Физическое тепло шлака q₆", ""],
                ["5-13", "Потери неохлаждаемых поверхностей", "При H_неохл &gt; 0"],
                ["5-14", "Сумма потерь Σq", ""],
                ["5-15", "КПД ηₖ = 100 − Σq", ""],
                ["5-16", "Полезное тепло Qполн, кВт", ""],
                ["5-17", "Тепло избыточного воздуха «в сторону»", "Опционально"],
                ["5-18", "Рециркуляция газов", "Опционально"],
                ["5-19", "Расход топлива B", ""],
                ["5-20", "Тепло внешнего воздуха Q_в.вн", "Опционально"],
                ["5-21", "Тепло парового дутья Q_φ", "Опционально"],
                ["5-22", "Пересчёт сухое → рабочее", "Опционально"],
                ["5-23", "Коррекция ηₖ (сухое топливо)", "Опционально"],
                ["5-24", "Расчётный расход Bₚ", "B·(1−q₄/100)"],
            ],
            col_widths=[w * 0.12, w * 0.48, w * 0.4],
        )
    )
    story.append(Spacer(1, 8))

    story.append(p(styles, "h2", "Ключевые соотношения"))
    story.append(p(styles, "h3", "Располагаемое тепло"))
    story.append(code_block(
        styles,
        """# Твёрдое / жидкое:
Q_p_p = Q_i_p + i_tl + Q_v_vn + ΔQ_razm

# Газообразное:
Q_p_p = Q_i_p + i_tl + ΔQ_razm""",
    ))
    story.append(p(styles, "h3", "КПД и расход"))
    story.append(code_block(
        styles,
        """η_k = 100 − (q2 + q3 + q4 + q5 + q6 + q5охл)

B   = Q_k / (Q_i_p · η_k/100 + Q_v_vn + Q_φ)
B_p = B_corrected · (1 − q4/100)""",
    ))
    story.append(
        p(
            styles,
            "body",
            "Значение q₅ном берётся из кривой рис. 5.1 (линейная интерполяция по D_ном) "
            "или из ручного override. Энтальпия шлака (cθ)_шл — по фрагменту табл. XIV "
            "либо из поля ввода. В HeatBalanceResult.formulas_used накапливаются номера "
            "формул, реально применённых при текущем наборе опций.",
        )
    )

    # ===== 6 =====
    story.append(PageBreak())
    story.append(p(styles, "h1", "6. Программный API ядра"))
    story.append(
        p(
            styles,
            "body",
            "Ядро в каталоге <b>src/core</b> не требует GUI. Подходит для скриптов, "
            "тестов и встраивания в SCADA / инженерные системы.",
        )
    )
    story.append(p(styles, "h2", "Минимальный пример"))
    story.append(code_block(
        styles,
        """from src.core.heat_balance import HeatBalanceCalculator
from src.core.models import (
    FuelType, FuelProperties, HeatBalanceInput, UsefulHeatParams,
)

inp = HeatBalanceInput(
    fuel=FuelProperties(
        fuel_type=FuelType.GASEOUS,
        Q_i_p=35588.0, A_p=0.0, W_r_c=0.0,
    ),
    useful=UsefulHeatParams(D_pe=20.0, i_pe=3400.0, i_pv=420.0),
)

result = HeatBalanceCalculator().calculate(inp)
print(result.eta_k, result.Q_poln, result.B)""",
    ))

    story.append(p(styles, "h2", "Модели входа"))
    story.append(
        table(
            styles,
            ["Класс", "Содержание"],
            [
                ["FuelProperties", "Тип топлива, Qᵢᵖ, влажность, зольность, карбонаты, iₜл"],
                ["AshLosses", "Доли золы, горючее в шлаке/уносе, t_шл"],
                ["FlueGasParams", "Энтальпии газов, α_ух, β, q₃"],
                ["BoilerParams", "D_ном, D, q₅ном override, H_неохл, Q_в.вн"],
                ["UsefulHeatParams", "Расходы/энтальпии для Qполн"],
                ["FuelConsumptionParams", "Опции формул 5-17…5-23"],
                ["HeatBalanceInput", "Агрегат всех групп входа"],
            ],
            col_widths=[w * 0.32, w * 0.68],
        )
    )
    story.append(Spacer(1, 8))

    story.append(p(styles, "h2", "Модель результата HeatBalanceResult"))
    story.append(
        table(
            styles,
            ["Поле", "Ед.", "Смысл"],
            [
                ["Q_p_p", "кДж/кг(м³)", "Располагаемое тепло"],
                ["q2…q6_shl, q5_oxl", "%", "Статьи потерь"],
                ["sum_q", "%", "Сумма потерь"],
                ["eta_k", "%", "КПД котла"],
                ["phi", "—", "Коэффициент сохранения тепла"],
                ["Q_poln", "кВт", "Полезное тепло"],
                ["B, B_p", "кг/с", "Расход и расчётный расход"],
                ["formulas_used", "list", "Номера применённых формул"],
                ["warnings", "list", "Практические рекомендации"],
                ["plugin_contributions", "dict", "Данные от плагинов"],
            ],
            col_widths=[w * 0.32, w * 0.18, w * 0.5],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        p(
            styles,
            "body",
            "Сериализация: <b>result.to_dict()</b>. Конструктор калькулятора: "
            "HeatBalanceCalculator(data_provider=None, plugin_registry=None).",
        )
    )

    story.append(p(styles, "h2", "Свойства пара (src/core/steam.py)"))
    story.append(
        p(
            styles,
            "body",
            "Независимо от GUI доступны calculate_state(), saturation_by_pressure/temperature(), "
            "generate_saturation_table(), calculate_boiler_cycle(). Режимы ввода: P-T, P-x, P-h, "
            "P-s, T-x, h-s, T-s, насыщение по P/T. Поддерживаются различные единицы давления и температуры.",
        )
    )

    # ===== 7 =====
    story.append(PageBreak())
    story.append(p(styles, "h1", "7. Система плагинов"))
    story.append(
        p(
            styles,
            "body",
            "Плагины расширяют приложение без изменения ядра UI. Внешние плагины лежат в "
            "<b>plugins/&lt;id&gt;/</b>, API — в <b>src/plugins/</b>. При старте реестр "
            "сканирует подкаталоги, читает manifest.json и загружает модуль через importlib.",
        )
    )

    story.append(p(styles, "h2", "Манифест"))
    story.append(code_block(
        styles,
        """{
  "id": "my_plugin",
  "name": "Моя утилита",
  "version": "1.0.0",
  "entry": "plugin.py",
  "description": "Краткое описание"
}""",
    ))

    story.append(p(styles, "h2", "Типы плагинов"))
    story.extend(
        bullets(
            styles,
            [
                "<b>UtilityPlugin</b> — утилита с собственным окном (activate, open_window)",
                "<b>CalculationPlugin</b> — расчётный модуль без UI (calculate)",
                "<b>Хук on_before_fuel_consumption</b> — вызывается после 5-16, до расчёта B; "
                "можно скорректировать result или записать plugin_data",
            ],
        )
    )

    story.append(p(styles, "h2", "Шаблон утилиты"))
    story.append(code_block(
        styles,
        """from src.plugins.base import UtilityPlugin

class MyPlugin(UtilityPlugin):
    id = "my_plugin"
    name = "Моя утилита"
    version = "1.0.0"

    def activate(self, host):
        self._host = host

    def open_window(self, parent):
        ...  # CTkToplevel

def create_plugin():
    return MyPlugin()""",
    ))
    story.append(
        p(
            styles,
            "body",
            "Фабрика <b>create_plugin()</b> обязательна. Ошибки загрузки одного плагина "
            "не останавливают приложение.",
        )
    )

    story.append(p(styles, "h2", "Встроенный плагин: Свойства пара"))
    story.append(
        table(
            styles,
            ["Параметр", "Значение"],
            [
                ["Путь", "plugins/steam_quality/"],
                ["Id / версия", "steam_quality / 3.1.0"],
                ["Стандарт", "IAPWS-IF97 (пакет iapws)"],
                ["Вкладки", "Состояние, Котёл, Насыщение, Таблицы"],
                ["Интеграция", "Подстановка энтальпий в форму баланса"],
            ],
            col_widths=[w * 0.25, w * 0.75],
        )
    )

    # ===== 8 =====
    story.append(PageBreak())
    story.append(p(styles, "h1", "8. Справочные данные и форматы файлов"))
    story.append(p(styles, "h2", "8.1. fuels.json"))
    story.append(
        p(
            styles,
            "body",
            "Справочник топлив в data/reference/fuels.json. Поля объекта: id, name, "
            "fuel_type (gaseous | solid_liquid), Q_i_p, A_p, W_r_c, c_tl, CO2_carb. "
            "Чтобы добавить топливо — допишите объект в массив fuels и перезапустите приложение.",
        )
    )
    story.append(
        table(
            styles,
            ["id", "Название", "Qᵢᵖ"],
            [
                ["natural_gas", "Природный газ (ГРС)", "35588"],
                ["associated_gas", "Попутный нефтяной газ", "41800"],
                ["lpg", "СУГ", "46000"],
                ["fuel_oil_m100", "Мазут М-100", "40200"],
                ["fuel_oil_m40", "Мазут М-40", "41800"],
                ["diesel", "Дизельное топливо", "42800"],
                ["kuzbass_g", "Кузнецкий уголь, марка Г", "24600"],
                ["kuzbass_d", "Кузнецкий уголь, марка Д", "26200"],
                ["ekibastuz", "Экибастузский уголь", "19200"],
                ["gas_coal", "Газовый уголь (Г)", "31000"],
                ["hard_coal", "Каменный уголь рядовой", "22800"],
                ["anthracite", "Антрацит", "34000"],
                ["brown_coal", "Бурый уголь", "14500"],
                ["wood_pellets", "Древесные пеллеты", "17500"],
                ["petcoke", "Нефтяной кокс", "32000"],
            ],
            col_widths=[w * 0.28, w * 0.5, w * 0.22],
        )
    )
    story.append(p(styles, "caption", "Таблица 1. Пресеты топлива (Qᵢᵖ в кДж/кг или кДж/м³)"))

    story.append(p(styles, "h2", "8.2. q5_nominal.json"))
    story.append(
        p(
            styles,
            "body",
            "Кривая рис. 5.1 — пары (D_ном, q₅ном) для линейной интерполяции. "
            "Если файл отсутствует, используется встроенная Q5_NOMINAL_CURVE из tables.py.",
        )
    )

    story.append(p(styles, "h2", "8.3. Формат сессии расчёта (версия 2)"))
    story.append(code_block(
        styles,
        """{
  "version": 2,
  "fuel_preset_id": "kuzbass_g",
  "input": {
    "fuel": { }, "ash": { }, "flue": { },
    "boiler": { }, "useful": { }, "consumption": { }
  },
  "result": { "eta_k": 89.5, "B": 2.1 }
}""",
    ))
    story.append(
        p(
            styles,
            "body",
            "При сохранении всегда пишется input; result — только если расчёт уже выполнялся. "
            "При загрузке восстанавливаются поля формы; пересчёт запускается вручную.",
        )
    )

    story.append(p(styles, "h2", "8.4. Прочие файлы"))
    story.extend(
        bullets(
            styles,
            [
                "<b>settings.json</b> — UI-настройки (label_mode)",
                "<b>assets/logo_header.png</b> — логотип в шапке (опционально; при отсутствии UI работает без него)",
            ],
        )
    )

    # ===== 9 =====
    story.append(p(styles, "h1", "9. Зависимости и структура проекта"))
    story.append(code_block(
        styles,
        """kotel/
├── main.py                 # Точка входа
├── run.bat                 # Запуск на Windows
├── requirements.txt
├── settings.json
├── docs/                   # Документация (MD + PDF)
├── src/
│   ├── core/               # Расчётный движок
│   ├── data/               # Провайдеры данных
│   ├── plugins/            # API плагинов
│   └── ui/                 # Интерфейс CustomTkinter
├── data/reference/         # Справочные JSON
└── plugins/
    └── steam_quality/      # IAPWS-IF97 калькулятор""",
    ))

    # ===== 10 =====
    story.append(p(styles, "h1", "10. Развитие и ограничения"))
    story.append(p(styles, "h2", "Планы развития"))
    story.extend(
        bullets(
            styles,
            [
                "Реализация DatabaseDataProvider для PostgreSQL/SQLite",
                "Расширение калькулятора пара (процессы расширения)",
                "Интеграция в составные SCADA / инженерные системы через API ядра",
            ],
        )
    )
    story.append(p(styles, "h2", "Текущие ограничения"))
    story.extend(
        bullets(
            styles,
            [
                "Нет автоматизированных тестов",
                "DatabaseDataProvider — заглушка",
                "Часть опций FuelConsumptionParams (избыточный воздух «в сторону», "
                "рециркуляция, коррекция сухого топлива) реализована в ядре, но не полностью "
                "вынесена в текущий GUI",
                "Ошибки загрузки отдельных плагинов подавляются в реестре",
            ],
        )
    )

    story.append(Spacer(1, 1.5 * cm))
    story.append(
        p(
            styles,
            "body",
            "<i>Конец документа. Актуальные исходные материалы также доступны в файлах "
            "README.md и docs/*.md репозитория проекта.</i>",
        )
    )

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Тепловой баланс котла — документация",
        author="kotel project",
        subject="Техническая документация приложения расчёта теплового баланса котла",
    )
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"OK: {OUT}")
    return OUT


if __name__ == "__main__":
    build()
