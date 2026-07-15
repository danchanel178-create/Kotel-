"""Tests for the boiler thermal calculation engine."""

from __future__ import annotations

import pytest

from app.calculations import BoilerInputError, BoilerInputs, calculate


def make_inputs(**overrides: float) -> BoilerInputs:
    base = {
        "fuel_consumption_kg_per_h": 720.0,
        "lower_heating_value_kj_per_kg": 29300.0,
        "steam_flow_kg_per_h": 6500.0,
        "steam_enthalpy_kj_per_kg": 3200.0,
        "feedwater_enthalpy_kj_per_kg": 420.0,
    }
    base.update(overrides)
    return BoilerInputs(**base)


def test_calculate_known_values() -> None:
    result = calculate(make_inputs())

    # Q_input = (720/3600) * 29300 = 5860 kW
    assert result.heat_input_kw == pytest.approx(5860.0, rel=1e-9)
    # Q_useful = (6500/3600) * (3200 - 420) = 5019.444... kW
    assert result.useful_heat_kw == pytest.approx(5019.4444, rel=1e-4)
    # eta = 5019.44 / 5860 * 100 = 85.66 %
    assert result.efficiency_percent == pytest.approx(85.6560, rel=1e-4)
    assert result.steam_to_fuel_ratio == pytest.approx(6500 / 720, rel=1e-9)


def test_efficiency_scales_with_fuel() -> None:
    less_fuel = calculate(make_inputs(fuel_consumption_kg_per_h=600.0))
    more_fuel = calculate(make_inputs(fuel_consumption_kg_per_h=900.0))
    # Burning more fuel for the same steam output lowers efficiency.
    assert less_fuel.efficiency_percent > more_fuel.efficiency_percent


@pytest.mark.parametrize(
    "overrides",
    [
        {"fuel_consumption_kg_per_h": 0.0},
        {"fuel_consumption_kg_per_h": -5.0},
        {"lower_heating_value_kj_per_kg": 0.0},
        {"steam_flow_kg_per_h": -1.0},
        {"steam_enthalpy_kj_per_kg": 400.0, "feedwater_enthalpy_kj_per_kg": 420.0},
    ],
)
def test_invalid_inputs_raise(overrides: dict[str, float]) -> None:
    with pytest.raises(BoilerInputError):
        calculate(make_inputs(**overrides))
