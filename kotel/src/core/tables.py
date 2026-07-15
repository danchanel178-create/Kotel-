"""Справочные таблицы и интерполяция (рис. 5.1 и др.)."""

from __future__ import annotations

import json
from pathlib import Path

# Рис. 5.1: зависимость q₅ном от номинальной паропроизводительности D_ном, т/ч
# Точки считаны по учебнику (гл. 5, рис. 5.1)
Q5_NOMINAL_CURVE: list[tuple[float, float]] = [
    (5, 2.45),
    (10, 1.85),
    (20, 1.35),
    (35, 1.05),
    (50, 0.85),
    (75, 0.70),
    (100, 0.58),
    (130, 0.50),
    (160, 0.45),
    (200, 0.38),
    (250, 0.32),
]

Q5_NOMINAL_CONSTANT_ABOVE = 250.0  # т/ч
Q5_NOMINAL_CONSTANT_VALUE = 0.20  # % при D > 250 т/ч


def linear_interp(x: float, points: list[tuple[float, float]]) -> float:
    """Линейная интерполяция по табличным точкам."""
    if not points:
        return 0.0
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        if x0 <= x <= x1:
            if x1 == x0:
                return y0
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return points[-1][1]


def q5_nominal_from_curve(D_nom: float, curve: list[tuple[float, float]] | None = None) -> float:
    """
    q₅ном по рис. 5.1, %.
    При D_ном > 250 т/ч — постоянное значение 0,2 %.
    """
    if D_nom > Q5_NOMINAL_CONSTANT_ABOVE:
        return Q5_NOMINAL_CONSTANT_VALUE
    pts = curve or Q5_NOMINAL_CURVE
    return linear_interp(D_nom, pts)


def load_q5_curve_from_file(path: Path) -> list[tuple[float, float]]:
    """Загрузка кривой q₅ном из JSON (для будущих БД)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [(float(p["D_nom"]), float(p["q5_nom"])) for p in data["points"]]


# Таблица XIV (фрагмент): энтальпия шлака (cθ)_шл при разных t_шл, кДж/кг
# Для расширения — полная таблица подгружается из провайдера данных
SLAG_ENTHALPY_TABLE: list[tuple[float, float]] = [
    (200, 180),
    (400, 420),
    (600, 720),
    (800, 1050),
    (1000, 1420),
    (1200, 1820),
    (1400, 2250),
]


def slag_enthalpy(t_shl: float, table: list[tuple[float, float]] | None = None) -> float:
    """(cθ)_шл по температуре шлака, кДж/кг."""
    return linear_interp(t_shl, table or SLAG_ENTHALPY_TABLE)
