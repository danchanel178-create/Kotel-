"""Модели данных для расчёта теплового баланса котла (гл. 5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FuelType(str, Enum):
    SOLID_LIQUID = "solid_liquid"
    GASEOUS = "gaseous"


@dataclass
class FuelProperties:
    """Свойства топлива."""

    fuel_type: FuelType = FuelType.SOLID_LIQUID
    Q_i_p: float = 25000.0  # Q_i^p — низшая теплота сгорания, кДж/кг или кДж/м³
    c_tl: float = 1.5  # c_тл — теплоёмкость топлива, кДж/(кг·К)
    t_tl: float = 20.0  # t_тл — температура топлива, °C
    include_physical_heat: bool = False  # учитывать i_тл (разд. 5-03)
    W1_p: float = 0.0  # влажность до размораживания, %
    W2_p: float = 0.0  # «безопасная» влажность, %
    CO2_carb: float = 0.0  # (CO₂)_карб, % — для формулы 5-05
    A_p: float = 15.0  # A^p — зольность рабочей массы, %
    W_r_c: float = 10.0  # W_r^c — влажность рабочего топлива, %
    W_r_c_dry: float = 0.0  # (W_r^c)' — влажность сухого топлива, %


@dataclass
class AshLosses:
    """Параметры для q₄ и q₆ (разд. 5-07–5-09)."""

    a_shl: float = 0.2  # a_шл — доля золы в шлаке
    a_pl: float = 0.0  # a_пл — доля золы в отложениях
    a_un: float = 0.8  # a_ун — доля золы в уносе
    C_shl: float = 2.0  # C_шл — содержание горючего в шлаке, %
    C_pl: float = 0.0  # C_пл
    C_un: float = 5.0  # C_ун
    ct_shl: float = 1200.0  # (cθ)_шл — энтальпия шлака, кДж/кг (табл. XIV)
    t_shl: float = 600.0  # t_шл — температура шлака, °C


@dataclass
class FlueGasParams:
    """Параметры для q₂ (формула 5-06)."""

    I_ukh: float = 1200.0  # I_ух — энтальпия уходящих газов, кДж/кг
    alpha_ukh: float = 1.4  # α_ух — коэффициент избытка воздуха
    I_hv_0: float = 35.0  # I_х.в^0 — энтальпия холодного воздуха, кДж/кг
    I_gv: float = 200.0  # I_г.в — энтальпия горячего воздуха, кДж/кг
    beta: float = 0.0  # β — доля рециркуляции воздуха
    q3: float = 0.1  # q₃ — потери от химической неполноты, %


@dataclass
class BoilerParams:
    """Параметры котла."""

    D_nom: float = 100.0  # D_ном — номинальная паропроизводительность, т/ч
    D: float = 80.0  # D — фактическая паропроизводительность, т/ч
    q5_nom_override: float | None = None  # ручное q₅ном (иначе — рис. 5.1)
    H_neohl: float = 0.0  # H_неохл — площадь неохлаждаемых поверхностей, м²
    Q_v_vn: float = 0.0  # Q_в.вн — тепло, вносимое с подогретым воздухом, кДж/кг


@dataclass
class UsefulHeatParams:
    """Параметры для Q_полн (формула 5-16)."""

    D_pe: float = 0.0  # D_пе — пар перегретый, кг/с
    i_pe: float = 3400.0  # i_пе
    i_pv: float = 420.0  # i_пв — питательная вода
    D_pr: float = 0.0  # D_пр — непрерывная продувка, кг/с
    i_sat: float = 1200.0  # i' — насыщенная вода в барабане
    spray_flows: list[tuple[float, float]] = field(default_factory=list)  # (D_впр, i_впр)
    D_pp: float = 0.0  # D_пп — пар через ПП, кг/с
    i_pp_out: float = 0.0  # i''_пп
    i_pp_in: float = 0.0  # i'_пп
    Q_otv: float = 0.0  # Q_отв, кВт
    Q_vod: float = 0.0  # Q_вод, кВт


@dataclass
class FuelConsumptionParams:
    """Параметры для расхода топлива (формулы 5-17–5-24)."""

    Q_k_override: float | None = None  # Q_к — если None, берётся из 5-16
    # 5-20
    beta_prime: float = 1.0
    beta_double_prime: float = 1.0
    I_v_vn: float = 200.0
    I_v_hv: float = 35.0
    use_external_air_heat: bool = False
    # 5-21
    G_phi: float = 0.0  # G_φ, кг/кг топлива
    i_phi: float = 2800.0
    use_steam_blast: bool = False
    # 5-17
    B_rasch: float = 0.0
    I_v_vyh: float = 0.0
    I_v_vkh: float = 0.0
    beta_v: float = 0.0
    use_excess_air_side: bool = False
    # 5-18
    r_g: float = 0.0
    I_g: float = 0.0
    use_gas_recirculation: bool = False
    # 5-22–5-23 сухое/рабочее топливо
    use_dry_fuel_correction: bool = False
    B_prime: float = 0.0
    Q_p_n_prime: float = 0.0
    eta_k_prime: float = 0.0


@dataclass
class HeatBalanceInput:
    """Полный набор входных данных."""

    fuel: FuelProperties = field(default_factory=FuelProperties)
    ash: AshLosses = field(default_factory=AshLosses)
    flue: FlueGasParams = field(default_factory=FlueGasParams)
    boiler: BoilerParams = field(default_factory=BoilerParams)
    useful: UsefulHeatParams = field(default_factory=UsefulHeatParams)
    consumption: FuelConsumptionParams = field(default_factory=FuelConsumptionParams)


@dataclass
class HeatBalanceResult:
    """Результаты расчёта."""

    # Располагаемое тепло
    Q_p_p: float = 0.0
    i_tl: float = 0.0
    delta_Q_razm: float = 0.0
    Q6_carb: float = 0.0

    # Потери, %
    q2: float = 0.0
    q3: float = 0.0
    q4: float = 0.0
    q5: float = 0.0
    q5_nom: float = 0.0
    q6_shl: float = 0.0
    q5_oxl: float = 0.0
    sum_q: float = 0.0

    # КПД и коэффициенты
    eta_k: float = 0.0
    phi: float = 0.0

    # Полезное тепло и расход
    Q_poln: float = 0.0  # кВт
    Q_k: float = 0.0
    Q_v_vn: float = 0.0
    Q_phi: float = 0.0
    Q_izb: float = 0.0
    Q_rec: float = 0.0
    B: float = 0.0  # кг/с
    B_p: float = 0.0
    B_corrected: float = 0.0
    eta_k_corrected: float = 0.0

    # Дополнительно
    C_sr: float = 0.0
    delta_I_zl: float = 0.0
    formulas_used: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    plugin_contributions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
