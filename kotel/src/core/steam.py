"""
Расчёт термофизических свойств воды и пара по IAPWS-IF97.

Обёртка над библиотекой iapws — тот же стандарт, что использует WaterSteamPro.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from . import notation as sym

try:
    from iapws import IAPWS97

    IAPWS_AVAILABLE = True
except ImportError:
    IAPWS_AVAILABLE = False
    IAPWS97 = None  # type: ignore[misc, assignment]


class InputMode(str, Enum):
    """Наборы входных параметров (режимы WSP Calculator, поддерживаемые iapws)."""

    PT = "P, T"
    PX = "P, x"
    PH = "P, h"
    PS = "P, s"
    TX = "T, x"
    HS = "h, s"
    TS = "T, s"
    P_SAT = "Pнас"
    T_SAT = "Tнас"


class PressureUnit(str, Enum):
    """Единицы давления (как в WSP Calculator)."""

    PA = "Па"
    MM_H2O = "мм вод.ст."
    TORR = "торр"
    MM_HG = "мм рт.ст."
    KPA = "кПа"
    IN_HG = "дюйм рт.ст"
    PSI = "пси"
    M_H2O = "м вод.ст."
    AT = "ат (кгс/см2)"
    KGF_CM2 = "кгс/см2"
    BAR = "бар"
    ATM = "атм (физ.)"
    MPA = "МПа"


class TemperatureUnit(str, Enum):
    """Единицы температуры."""

    R = "R"
    F = "°F"
    C = "°C"
    K = "K"


class SaturationInput(str, Enum):
    BY_PRESSURE = "pressure"
    BY_TEMPERATURE = "temperature"


class TableAxis(str, Enum):
    BY_PRESSURE = "pressure"
    BY_TEMPERATURE = "temperature"


# Множители: значение_в_единице * factor = МПа
_PRESSURE_TO_MPA = {
    PressureUnit.PA: 1e-6,
    PressureUnit.MM_H2O: 9.80665e-6,
    PressureUnit.TORR: 0.000133322368,
    PressureUnit.MM_HG: 0.000133322368,
    PressureUnit.KPA: 0.001,
    PressureUnit.IN_HG: 0.003386389,
    PressureUnit.PSI: 0.006894757,
    PressureUnit.M_H2O: 0.00980665,
    PressureUnit.AT: 0.0980665,
    PressureUnit.KGF_CM2: 0.0980665,
    PressureUnit.BAR: 0.1,
    PressureUnit.ATM: 0.101325,
    PressureUnit.MPA: 1.0,
}

_PHASE_RU = {
    "liquid": "Жидкость",
    "gas": "Перегретый пар",
    "vapor": "Перегретый пар",
    "vapour": "Перегретый пар",
    "two phases": "Влажный пар (двухфазная область)",
    "critical": "Критическая точка",
    "undefined": "Не определено",
}

# Диапазон линии насыщения для таблиц (практический / стабильный IAPWS)
P_SAT_MIN_MPA = 0.1
P_SAT_MAX_MPA = 22.0  # чуть ниже критической точки 22.064 МПа
T_SAT_MIN_C = 0.01
T_SAT_MAX_C = 370.0

# Типичные пути установки WaterSteamPro (Windows)
_WSP_SEARCH_PATHS = [
    Path(r"C:\Program Files\WaterSteamPro\WSP Calculator.exe"),
    Path(r"C:\Program Files (x86)\WaterSteamPro\WSP Calculator.exe"),
    Path(r"C:\Program Files\WaterSteamPro\Calculator.exe"),
    Path(r"C:\Program Files (x86)\WaterSteamPro\Calculator.exe"),
    Path(r"C:\WaterSteamPro\WSP Calculator.exe"),
]


def pressure_to_mpa(value: float, unit: PressureUnit) -> float:
    return value * _PRESSURE_TO_MPA[unit]


def pressure_from_mpa(value_mpa: float, unit: PressureUnit) -> float:
    return value_mpa / _PRESSURE_TO_MPA[unit]


def temperature_to_c(value: float, unit: TemperatureUnit) -> float:
    if unit == TemperatureUnit.C:
        return value
    if unit == TemperatureUnit.K:
        return value - 273.15
    if unit == TemperatureUnit.F:
        return (value - 32.0) * 5.0 / 9.0
    if unit == TemperatureUnit.R:
        return (value - 491.67) * 5.0 / 9.0
    raise SteamCalculationError(f"Неизвестная единица температуры: {unit}")


def temperature_from_c(value_c: float, unit: TemperatureUnit) -> float:
    if unit == TemperatureUnit.C:
        return value_c
    if unit == TemperatureUnit.K:
        return value_c + 273.15
    if unit == TemperatureUnit.F:
        return value_c * 9.0 / 5.0 + 32.0
    if unit == TemperatureUnit.R:
        return (value_c + 273.15) * 9.0 / 5.0
    raise SteamCalculationError(f"Неизвестная единица температуры: {unit}")


def parse_float(text: str) -> float:
    return float(str(text).strip().replace(",", "."))


def format_iapws_error(raw: Exception | str, *, context: str = "") -> str:
    """Перевести типовые ошибки iapws в понятное русскоязычное сообщение."""
    msg = str(raw).strip()
    low = msg.lower()
    prefix = f"{context}: " if context else ""

    # Уже переведённые сообщения из ядра — не дублировать формулировку
    if "вне области применимости" in msg or msg.startswith("Невозможно выполнить"):
        return f"{prefix}{msg}" if context and not msg.startswith(context) else msg
    if any(
        key in msg
        for key in (
            "ниже допустим",
            "выше област",
            "должно быть",
            "Число точек",
            "Конечное значение",
            "Температура ниже",
            "Температура выше",
            "Давление должно",
        )
    ):
        return f"{prefix}{msg}" if context and not msg.startswith(context) else msg

    if "out of bound" in low or "incoming out of bound" in low:
        return (
            f"{prefix}Невозможно выполнить расчёт: исходные данные вне области "
            "применимости IAPWS-IF97 (давление примерно 0…100 МПа, температура "
            "примерно 0,01…800 °C, либо недопустимая комбинация параметров). "
            "Проверьте введённые значения."
        )
    if "not converge" in low or "convergen" in low:
        return (
            f"{prefix}Не удалось сойтись к решению IAPWS-IF97 при заданных "
            "параметрах. Попробуйте другие входные данные."
        )
    if "iapws" in low and "install" in low:
        return msg
    if msg:
        return f"{prefix}Невозможно выполнить расчёт: {msg}"
    return f"{prefix}Невозможно выполнить расчёт по заданным исходным данным."

@dataclass
class SteamProperties:
    """Полный набор свойств воды/пара в инженерных единицах."""

    p_mpa: float
    t_c: float
    h_kj: float
    s_kj: float
    u_kj: float
    v_m3: float
    rho: float
    x: float | None
    phase: str
    phase_ru: str
    region: int | None
    t_sat_c: float | None = None
    superheat_c: float | None = None
    subcooling_c: float | None = None
    cp: float | None = None
    cv: float | None = None
    w: float | None = None
    mu: float | None = None
    k: float | None = None
    pr: float | None = None
    kappa: float | None = None
    h_vap: float | None = None
    status: str = "OK"

    def as_result_rows(self) -> list[tuple[str, str, str]]:
        """Строки (группа, параметр, значение) для отображения в UI."""
        x_str = "—" if self.x is None else f"{self.x:.6f}"
        rows: list[tuple[str, str, str]] = [
            ("Основные", "Давление p", f"{self.p_mpa:.6f} МПа"),
            ("Основные", "Температура t", f"{self.t_c:.4f} °C"),
            ("Основные", "Доля пара x", x_str),
            ("Основные", "Фазовое состояние", self.phase_ru),
            ("Основные", "Область IF97", str(self.region) if self.region is not None else "—"),
        ]
        if self.t_sat_c is not None:
            rows.append(("Основные", f"{sym.T_nas} (при p)", f"{self.t_sat_c:.4f} °C"))
        if self.superheat_c is not None and self.superheat_c > 0.01:
            rows.append(("Основные", "Перегрев Δt", f"{self.superheat_c:.4f} °C"))
        if self.subcooling_c is not None and self.subcooling_c > 0.01:
            rows.append(("Основные", "Недогрев Δt", f"{self.subcooling_c:.4f} °C"))
        rows.extend([
            ("Термодинамика", "Энтальпия h", f"{self.h_kj:.4f} кДж/кг"),
            ("Термодинамика", "Энтропия s", f"{self.s_kj:.6f} кДж/(кг·K)"),
            ("Термодинамика", "Внутр. энергия u", f"{self.u_kj:.4f} кДж/кг"),
            ("Термодинамика", "Уд. объём v", f"{self.v_m3:.8f} м³/кг"),
            ("Термодинамика", "Плотность ρ", f"{self.rho:.4f} кг/м³"),
        ])
        if self.h_vap is not None:
            rows.append(("Термодинамика", "Теплота парообразования r", f"{self.h_vap:.4f} кДж/кг"))
        transport: list[tuple[str, str, str]] = []
        if self.cp is not None:
            transport.append(("Транспорт", "Теплоёмкость cp", f"{self.cp:.4f} кДж/(кг·K)"))
        if self.cv is not None:
            transport.append(("Транспорт", "Теплоёмкость cv", f"{self.cv:.4f} кДж/(кг·K)"))
        if self.w is not None:
            transport.append(("Транспорт", "Скорость звука w", f"{self.w:.2f} м/с"))
        if self.mu is not None:
            transport.append(("Транспорт", "Дин. вязкость μ", f"{self.mu:.2e} Па·с"))
        if self.k is not None:
            transport.append(("Транспорт", "Теплопроводность λ", f"{self.k:.4f} Вт/(м·K)"))
        if self.pr is not None:
            transport.append(("Транспорт", "Число Прандтля Pr", f"{self.pr:.4f}"))
        if self.kappa is not None:
            transport.append(("Транспорт", "Показатель κ", f"{self.kappa:.4f}"))
        return rows + transport

    def as_text_block(self) -> str:
        lines = [f"{param}: {value}" for _, param, value in self.as_result_rows()]
        return "\n".join(lines)


@dataclass
class SaturationProperties:
    """Свойства на линии насыщения."""

    p_mpa: float
    t_c: float
    h_l: float
    h_v: float
    s_l: float
    s_v: float
    u_l: float
    u_v: float
    v_l: float
    v_v: float
    rho_l: float
    rho_v: float
    r: float = field(default=0.0)

    def __post_init__(self) -> None:
        self.r = self.h_v - self.h_l

    def as_result_rows(self) -> list[tuple[str, str, str]]:
        return [
            ("Насыщение", "Давление p", f"{self.p_mpa:.6f} МПа"),
            ("Насыщение", "Температура t", f"{self.t_c:.4f} °C"),
            ("Жидкость (′)", f"Энтальпия {sym.h_l}", f"{self.h_l:.4f} кДж/кг"),
            ("Жидкость (′)", f"Энтропия {sym.s_l}", f"{self.s_l:.6f} кДж/(кг·K)"),
            ("Жидкость (′)", f"Уд. объём {sym.v_l}", f"{self.v_l:.8f} м³/кг"),
            ("Жидкость (′)", f"Плотность {sym.rho_l}", f"{self.rho_l:.4f} кг/м³"),
            ("Пар (″)", f"Энтальпия {sym.h_v}", f"{self.h_v:.4f} кДж/кг"),
            ("Пар (″)", f"Энтропия {sym.s_v}", f"{self.s_v:.6f} кДж/(кг·K)"),
            ("Пар (″)", f"Уд. объём {sym.v_v}", f"{self.v_v:.6f} м³/кг"),
            ("Пар (″)", f"Плотность {sym.rho_v}", f"{self.rho_v:.4f} кг/м³"),
            ("Насыщение", "Теплота парообразования r", f"{self.r:.4f} кДж/кг"),
        ]


@dataclass
class SaturationTableRow:
    """Строка таблицы насыщения."""

    index: int
    p_mpa: float
    t_c: float
    h_l: float
    h_v: float
    r: float
    rho_l: float
    rho_v: float


@dataclass
class BoilerCycleResult:
    """Типовые точки цикла котла для теплового баланса (глава 5)."""

    p_mpa: float
    t_sat_c: float
    t_superheat_c: float | None
    t_feedwater_c: float
    x_steam: float | None
    i_pe: float
    i_pv: float
    i_sat: float
    i_phi: float
    superheat_c: float | None
    delta_h_useful: float
    steam_state: SteamProperties
    feedwater_state: SteamProperties
    drum_liquid: SaturationProperties

    def as_result_rows(self) -> list[tuple[str, str, str]]:
        x_str = "—" if self.x_steam is None else f"{self.x_steam:.4f}"
        sh_str = "—" if self.superheat_c is None else f"{self.superheat_c:.2f} °C"
        return [
            ("Котёл", "Давление барабана p", f"{self.p_mpa:.4f} МПа"),
            ("Котёл", sym.T_nas, f"{self.t_sat_c:.2f} °C"),
            ("Котёл", "T питательной воды", f"{self.t_feedwater_c:.2f} °C"),
            ("Котёл", "T / x пара на выходе", f"{self.t_superheat_c or 0:.2f} °C / {x_str}"),
            ("Котёл", "Перегрев Δt", sh_str),
            ("Энтальпии", f"{sym.i_pe} (пар на выходе)", f"{self.i_pe:.2f} кДж/кг"),
            ("Энтальпии", f"{sym.i_pv} (питательная вода)", f"{self.i_pv:.2f} кДж/кг"),
            ("Энтальпии", f"{sym.i_sat} (насыщ. вода в барабане)", f"{self.i_sat:.2f} кДж/кг"),
            ("Энтальпии", f"{sym.i_phi} (пар обдувки)", f"{self.i_phi:.2f} кДж/кг"),
            ("Энтальпии", f"Δh полезного тепла ({sym.i_pe} − {sym.i_pv})", f"{self.delta_h_useful:.2f} кДж/кг"),
        ]

    def enthalpies_for_balance(self) -> dict[str, float]:
        return {
            "i_pe": self.i_pe,
            "i_pv": self.i_pv,
            "i_sat": self.i_sat,
            "i_phi": self.i_phi,
        }


class SteamCalculationError(Exception):
    """Ошибка расчёта свойств воды/пара."""


def _require_iapws() -> None:
    if not IAPWS_AVAILABLE:
        raise SteamCalculationError(
            "Библиотека iapws не установлена. Выполните: pip install iapws"
        )


def _phase_ru(phase: str, x: float | None) -> str:
    key = (phase or "").lower()
    if x is not None and 0.0 < x < 1.0:
        return _PHASE_RU["two phases"]
    return _PHASE_RU.get(key, phase or "—")


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:
        return None
    return f


def saturation_temperature(p_mpa: float) -> float:
    """Температура насыщения, °C, при заданном давлении."""
    return saturation_by_pressure(p_mpa).t_c


def _saturation_thermal(p_mpa: float) -> tuple[float, float, float]:
    """(T_нас °C, h', h'') при давлении p."""
    sat = saturation_by_pressure(p_mpa)
    return sat.t_c, sat.h_l, sat.h_v


def _from_iapws(state: Any, *, with_sat: bool = True) -> SteamProperties:
    phase = getattr(state, "phase", "") or ""
    x = _safe_float(getattr(state, "x", None))
    if x is not None and (x < 0 or x > 1):
        x = max(0.0, min(1.0, x))

    p_mpa = float(state.P)
    t_c = float(state.T) - 273.15

    t_sat_c: float | None = None
    superheat_c: float | None = None
    subcooling_c: float | None = None
    h_vap: float | None = None

    if with_sat:
        try:
            t_sat_c, h_l, h_v = _saturation_thermal(p_mpa)
            h_vap = h_v - h_l
            delta = t_c - t_sat_c
            if delta > 0.01:
                superheat_c = delta
            elif delta < -0.01:
                subcooling_c = -delta
        except Exception:
            pass

    return SteamProperties(
        p_mpa=p_mpa,
        t_c=t_c,
        h_kj=float(state.h),
        s_kj=float(state.s),
        u_kj=float(state.u),
        v_m3=float(state.v),
        rho=float(state.rho),
        x=x,
        phase=phase,
        phase_ru=_phase_ru(phase, x),
        region=int(state.region) if getattr(state, "region", None) is not None else None,
        t_sat_c=t_sat_c,
        superheat_c=superheat_c,
        subcooling_c=subcooling_c,
        cp=_safe_float(getattr(state, "cp", None)),
        cv=_safe_float(getattr(state, "cv", None)),
        w=_safe_float(getattr(state, "w", None)),
        mu=_safe_float(getattr(state, "mu", None)),
        k=_safe_float(getattr(state, "k", None)),
        pr=_safe_float(getattr(state, "Prandt", None)),
        kappa=_safe_float(getattr(state, "kappa", None)),
        h_vap=h_vap,
        status=getattr(state, "msg", "OK") or "OK",
    )


def _solve_iapws(**kwargs: float) -> Any:
    _require_iapws()
    try:
        state = IAPWS97(**kwargs)
    except Exception as exc:
        raise SteamCalculationError(format_iapws_error(exc)) from exc
    if getattr(state, "status", 1) != 1:
        msg = getattr(state, "msg", "Неизвестная ошибка")
        raise SteamCalculationError(format_iapws_error(msg))
    return state


def calculate_state(mode: InputMode, **values: float) -> SteamProperties:
    """
    Рассчитать свойства по заданному набору входных параметров.

    values:
        p_mpa — давление, МПа
        t_c — температура, °C
        x — доля пара, 0…1
        h_kj — энтальпия, кДж/кг
        s_kj — энтропия, кДж/(кг·K)
    """
    kwargs: dict[str, float] = {}
    if mode == InputMode.PT:
        kwargs = {"P": values["p_mpa"], "T": values["t_c"] + 273.15}
    elif mode == InputMode.PX:
        kwargs = {"P": values["p_mpa"], "x": values["x"]}
    elif mode == InputMode.PH:
        kwargs = {"P": values["p_mpa"], "h": values["h_kj"]}
    elif mode == InputMode.PS:
        kwargs = {"P": values["p_mpa"], "s": values["s_kj"]}
    elif mode == InputMode.TX:
        kwargs = {"T": values["t_c"] + 273.15, "x": values["x"]}
    elif mode == InputMode.HS:
        kwargs = {"h": values["h_kj"], "s": values["s_kj"]}
    elif mode == InputMode.TS:
        kwargs = {"T": values["t_c"] + 273.15, "s": values["s_kj"]}
    elif mode == InputMode.P_SAT:
        # Сухой насыщенный пар (x = 1) при заданном Pнас
        return calculate_state(InputMode.PX, p_mpa=values["p_mpa"], x=1.0)
    elif mode == InputMode.T_SAT:
        sat = saturation_by_temperature(values["t_c"])
        return calculate_state(InputMode.PX, p_mpa=sat.p_mpa, x=1.0)
    else:
        raise SteamCalculationError(f"Неизвестный режим: {mode}")

    return _from_iapws(_solve_iapws(**kwargs))


def calculate_from_enthalpy(p_mpa: float, h_kj: float) -> SteamProperties:
    """Обратный расчёт (P, h) — часто нужен для проверки замеров."""
    return calculate_state(InputMode.PH, p_mpa=p_mpa, h_kj=h_kj)


def saturation_by_pressure(p_mpa: float) -> SaturationProperties:
    if p_mpa <= 0:
        raise SteamCalculationError("Давление должно быть > 0")

    liq = _solve_iapws(P=p_mpa, x=0)
    vap = _solve_iapws(P=p_mpa, x=1)

    return SaturationProperties(
        p_mpa=p_mpa,
        t_c=float(liq.T) - 273.15,
        h_l=float(liq.h),
        h_v=float(vap.h),
        s_l=float(liq.s),
        s_v=float(vap.s),
        u_l=float(liq.u),
        u_v=float(vap.u),
        v_l=float(liq.v),
        v_v=float(vap.v),
        rho_l=float(liq.rho),
        rho_v=float(vap.rho),
    )


def saturation_by_temperature(t_c: float) -> SaturationProperties:
    t_k = t_c + 273.15
    if t_k < 273.16:
        raise SteamCalculationError("Температура ниже тройной точки (0.01 °C)")

    liq = _solve_iapws(T=t_k, x=0)
    vap = _solve_iapws(T=t_k, x=1)

    return SaturationProperties(
        p_mpa=float(liq.P),
        t_c=t_c,
        h_l=float(liq.h),
        h_v=float(vap.h),
        s_l=float(liq.s),
        s_v=float(vap.s),
        u_l=float(liq.u),
        u_v=float(vap.u),
        v_l=float(liq.v),
        v_v=float(vap.v),
        rho_l=float(liq.rho),
        rho_v=float(vap.rho),
    )


def generate_saturation_table(
    *,
    axis: TableAxis,
    start: float,
    end: float,
    n_points: int,
    pressure_unit: PressureUnit = PressureUnit.MPA,
) -> list[SaturationTableRow]:
    """Таблица свойств на линии насыщения (как в WSP Tables)."""
    if n_points < 2:
        raise SteamCalculationError("Число точек таблицы должно быть ≥ 2")
    if end <= start:
        raise SteamCalculationError("Конечное значение должно быть больше начального")

    rows: list[SaturationTableRow] = []
    step = (end - start) / (n_points - 1)

    for i in range(n_points):
        val = start + i * step
        if axis == TableAxis.BY_PRESSURE:
            p_mpa = pressure_to_mpa(val, pressure_unit)
            if p_mpa < P_SAT_MIN_MPA - 1e-9:
                p_disp = pressure_from_mpa(P_SAT_MIN_MPA, pressure_unit)
                raise SteamCalculationError(
                    f"Давление ниже допустимого для таблицы насыщения. "
                    f"Минимум: {P_SAT_MIN_MPA:.1f} МПа "
                    f"({p_disp:.4g} {pressure_unit.value}). "
                    f"Сейчас: {p_mpa:.4g} МПа."
                )
            if p_mpa > P_SAT_MAX_MPA + 1e-9:
                p_disp = pressure_from_mpa(P_SAT_MAX_MPA, pressure_unit)
                raise SteamCalculationError(
                    f"Давление выше области линии насыщения. "
                    f"Максимум: {P_SAT_MAX_MPA:.1f} МПа "
                    f"({p_disp:.4g} {pressure_unit.value}). "
                    f"Сейчас: {p_mpa:.4g} МПа."
                )
            sat = saturation_by_pressure(p_mpa)
        else:
            if val < T_SAT_MIN_C - 1e-9:
                raise SteamCalculationError(
                    f"Температура ниже допустимой ({T_SAT_MIN_C} °C). Сейчас: {val:.2f} °C."
                )
            if val > T_SAT_MAX_C + 1e-9:
                raise SteamCalculationError(
                    f"Температура выше области линии насыщения "
                    f"(максимум {T_SAT_MAX_C:.0f} °C). Сейчас: {val:.2f} °C."
                )
            sat = saturation_by_temperature(val)
        rows.append(
            SaturationTableRow(
                index=i + 1,
                p_mpa=sat.p_mpa,
                t_c=sat.t_c,
                h_l=sat.h_l,
                h_v=sat.h_v,
                r=sat.r,
                rho_l=sat.rho_l,
                rho_v=sat.rho_v,
            )
        )
    return rows


def saturation_table_as_text(
    rows: list[SaturationTableRow],
    *,
    pressure_unit: PressureUnit = PressureUnit.MPA,
) -> str:
    header = (
        f"{'№':>3}  {'p [' + pressure_unit.value + ']':>12}  {'T [C]':>10}  "
        f"{'h_l':>10}  {'h_v':>10}  {'r':>10}  {'rho_l':>10}  {'rho_v':>8}"
    )
    lines = [header, "-" * len(header)]
    for row in rows:
        p_disp = pressure_from_mpa(row.p_mpa, pressure_unit)
        lines.append(
            f"{row.index:3d}  {p_disp:12.4f}  {row.t_c:10.2f}  "
            f"{row.h_l:10.2f}  {row.h_v:10.2f}  {row.r:10.2f}  "
            f"{row.rho_l:10.2f}  {row.rho_v:8.4f}"
        )
    return "\n".join(lines)


def calculate_boiler_cycle(
    *,
    p_mpa: float,
    t_feedwater_c: float,
    t_superheat_c: float | None = None,
    x_steam: float | None = None,
) -> BoilerCycleResult:
    """
    Расчёт типовых энтальпий котла для подстановки в тепловой баланс.

    Перегретый пар: задайте t_superheat_c (t > T_нас).
    Влажный пар: задайте x_steam (0 < x < 1), t_superheat_c не используется.
    """
    if p_mpa <= 0:
        raise SteamCalculationError("Давление барабана должно быть > 0")

    drum = saturation_by_pressure(p_mpa)
    feedwater = calculate_state(InputMode.PT, p_mpa=p_mpa, t_c=t_feedwater_c)

    if x_steam is not None:
        if not 0 < x_steam <= 1:
            raise SteamCalculationError("Качество пара x должно быть в диапазоне (0, 1]")
        steam = calculate_state(InputMode.PX, p_mpa=p_mpa, x=x_steam)
        superheat: float | None = None
        t_out: float | None = None
    elif t_superheat_c is not None:
        if t_superheat_c <= drum.t_c:
            raise SteamCalculationError(
                f"T пара ({t_superheat_c:.1f} °C) должна быть выше T_нас ({drum.t_c:.1f} °C)"
            )
        steam = calculate_state(InputMode.PT, p_mpa=p_mpa, t_c=t_superheat_c)
        superheat = t_superheat_c - drum.t_c
        t_out = t_superheat_c
    else:
        raise SteamCalculationError("Укажите температуру перегрева или качество пара x")

    i_pe = steam.h_kj
    i_pv = feedwater.h_kj
    i_sat = drum.h_l
    i_phi = drum.h_v

    return BoilerCycleResult(
        p_mpa=p_mpa,
        t_sat_c=drum.t_c,
        t_superheat_c=t_out,
        t_feedwater_c=t_feedwater_c,
        x_steam=x_steam,
        i_pe=i_pe,
        i_pv=i_pv,
        i_sat=i_sat,
        i_phi=i_phi,
        superheat_c=superheat,
        delta_h_useful=i_pe - i_pv,
        steam_state=steam,
        feedwater_state=feedwater,
        drum_liquid=drum,
    )


def find_wsp_executable() -> Path | None:
    """Найти WaterSteamPro Calculator в стандартных путях Windows."""
    if sys.platform != "win32":
        return None
    for path in _WSP_SEARCH_PATHS:
        if path.is_file():
            return path
    return None


def launch_wsp() -> Path:
    """Запустить WSP Calculator, если установлен."""
    exe = find_wsp_executable()
    if exe is None:
        raise SteamCalculationError(
            "WaterSteamPro Calculator не найден. "
            "Установите WSP или используйте встроенный IAPWS-калькулятор."
        )
    subprocess.Popen([str(exe)], shell=False, cwd=str(exe.parent))
    return exe


def input_labels(mode: InputMode) -> tuple[str, str]:
    labels = {
        InputMode.PT: ("Давление", "Температура"),
        InputMode.PX: ("Давление", "Доля пара x"),
        InputMode.PH: ("Давление", "Энтальпия h"),
        InputMode.PS: ("Давление", "Энтропия s"),
        InputMode.TX: ("Температура", "Доля пара x"),
        InputMode.HS: ("Энтальпия h", "Энтропия s"),
        InputMode.TS: ("Температура", "Энтропия s"),
        InputMode.P_SAT: ("Давление насыщения", ""),
        InputMode.T_SAT: ("Температура насыщения", ""),
    }
    return labels[mode]


def input_kinds(mode: InputMode) -> tuple[str, str]:
    """Тип каждого аргумента: pressure | temperature | other | none."""
    kinds = {
        InputMode.PT: ("pressure", "temperature"),
        InputMode.PX: ("pressure", "other"),
        InputMode.PH: ("pressure", "other"),
        InputMode.PS: ("pressure", "other"),
        InputMode.TX: ("temperature", "other"),
        InputMode.HS: ("other", "other"),
        InputMode.TS: ("temperature", "other"),
        InputMode.P_SAT: ("pressure", "none"),
        InputMode.T_SAT: ("temperature", "none"),
    }
    return kinds[mode]


def input_units(
    mode: InputMode,
    pressure_unit: PressureUnit,
    temperature_unit: TemperatureUnit = TemperatureUnit.C,
) -> tuple[str, str]:
    p_unit = pressure_unit.value
    t_unit = temperature_unit.value
    u = {
        InputMode.PT: (p_unit, t_unit),
        InputMode.PX: (p_unit, "—"),
        InputMode.PH: (p_unit, "кДж/кг"),
        InputMode.PS: (p_unit, "кДж/(кг·K)"),
        InputMode.TX: (t_unit, "—"),
        InputMode.HS: ("кДж/кг", "кДж/(кг·K)"),
        InputMode.TS: (t_unit, "кДж/(кг·K)"),
        InputMode.P_SAT: (p_unit, ""),
        InputMode.T_SAT: (t_unit, ""),
    }
    return u[mode]


def default_inputs(mode: InputMode) -> tuple[str, str]:
    defaults = {
        InputMode.PT: ("4.0", "500"),
        InputMode.PX: ("4.0", "0.95"),
        InputMode.PH: ("4.0", "2800"),
        InputMode.PS: ("4.0", "6.5"),
        InputMode.TX: ("250", "0.9"),
        InputMode.HS: ("2800", "6.5"),
        InputMode.TS: ("250", "6.5"),
        InputMode.P_SAT: ("4.0", ""),
        InputMode.T_SAT: ("250", ""),
    }
    return defaults[mode]
