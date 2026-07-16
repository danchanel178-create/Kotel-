"""Boiler thermal calculation engine (direct heat-balance method).

Реализует прямой (direct) метод теплового расчёта котла:
    - полезная теплота, переданная рабочему телу (пару);
    - теплота, внесённая топливом;
    - КПД котла (брутто) по прямому балансу.

All enthalpies are specific enthalpies in kJ/kg. Flow rates are given per hour
and converted internally to per-second values so the resulting powers are in kW.
"""

from __future__ import annotations

from dataclasses import dataclass

SECONDS_PER_HOUR = 3600.0


class BoilerInputError(ValueError):
    """Raised when boiler calculation inputs are physically invalid."""


@dataclass(frozen=True)
class BoilerInputs:
    """Input parameters for a boiler thermal calculation.

    Attributes:
        fuel_consumption_kg_per_h: Расход топлива B, кг/ч.
        lower_heating_value_kj_per_kg: Низшая теплота сгорания Q_r_i, кДж/кг.
        steam_flow_kg_per_h: Паропроизводительность D, кг/ч.
        steam_enthalpy_kj_per_kg: Энтальпия перегретого пара h", кДж/кг.
        feedwater_enthalpy_kj_per_kg: Энтальпия питательной воды h_пв, кДж/кг.
    """

    fuel_consumption_kg_per_h: float
    lower_heating_value_kj_per_kg: float
    steam_flow_kg_per_h: float
    steam_enthalpy_kj_per_kg: float
    feedwater_enthalpy_kj_per_kg: float

    def validate(self) -> None:
        if self.fuel_consumption_kg_per_h <= 0:
            raise BoilerInputError("Fuel consumption must be greater than zero.")
        if self.lower_heating_value_kj_per_kg <= 0:
            raise BoilerInputError("Lower heating value must be greater than zero.")
        if self.steam_flow_kg_per_h <= 0:
            raise BoilerInputError("Steam flow must be greater than zero.")
        if self.steam_enthalpy_kj_per_kg <= self.feedwater_enthalpy_kj_per_kg:
            raise BoilerInputError(
                "Steam enthalpy must exceed feedwater enthalpy "
                "(the boiler must add heat to the working fluid)."
            )


@dataclass(frozen=True)
class BoilerResult:
    """Result of a boiler thermal calculation."""

    heat_input_kw: float
    useful_heat_kw: float
    efficiency_percent: float
    steam_to_fuel_ratio: float


def calculate(inputs: BoilerInputs) -> BoilerResult:
    """Compute boiler thermal performance using the direct heat-balance method.

    Q_input  = B * Q_r_i                      (heat released by fuel)
    Q_useful = D * (h_steam - h_feedwater)    (heat absorbed by the steam)
    eta      = Q_useful / Q_input * 100       (gross boiler efficiency)
    """
    inputs.validate()

    fuel_per_s = inputs.fuel_consumption_kg_per_h / SECONDS_PER_HOUR
    steam_per_s = inputs.steam_flow_kg_per_h / SECONDS_PER_HOUR

    heat_input_kw = fuel_per_s * inputs.lower_heating_value_kj_per_kg
    enthalpy_rise = inputs.steam_enthalpy_kj_per_kg - inputs.feedwater_enthalpy_kj_per_kg
    useful_heat_kw = steam_per_s * enthalpy_rise

    efficiency_percent = useful_heat_kw / heat_input_kw * 100.0
    steam_to_fuel_ratio = inputs.steam_flow_kg_per_h / inputs.fuel_consumption_kg_per_h

    return BoilerResult(
        heat_input_kw=heat_input_kw,
        useful_heat_kw=useful_heat_kw,
        efficiency_percent=efficiency_percent,
        steam_to_fuel_ratio=steam_to_fuel_ratio,
    )
