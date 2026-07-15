"""Tests for the FastAPI endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_index_served() -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert "Boiler Thermal Calculation" in res.text


def test_calculate_endpoint() -> None:
    payload = {
        "fuel_consumption_kg_per_h": 720.0,
        "lower_heating_value_kj_per_kg": 29300.0,
        "steam_flow_kg_per_h": 6500.0,
        "steam_enthalpy_kj_per_kg": 3200.0,
        "feedwater_enthalpy_kj_per_kg": 420.0,
    }
    res = client.post("/api/calculate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["heat_input_kw"] == 5860.0
    assert data["efficiency_percent"] == 85.66


def test_calculate_invalid_returns_422() -> None:
    payload = {
        "fuel_consumption_kg_per_h": 720.0,
        "lower_heating_value_kj_per_kg": 29300.0,
        "steam_flow_kg_per_h": 6500.0,
        "steam_enthalpy_kj_per_kg": 400.0,
        "feedwater_enthalpy_kj_per_kg": 420.0,
    }
    res = client.post("/api/calculate", json=payload)
    assert res.status_code == 422
