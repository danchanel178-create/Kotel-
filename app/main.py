"""FastAPI application exposing the boiler thermal calculation."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import __version__
from app.calculations import BoilerInputError, BoilerInputs, calculate

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Kotel — Boiler Thermal Calculation",
    description="Тепловой расчёт котлов: КПД, полезная теплота и тепловой баланс.",
    version=__version__,
)


class CalculationRequest(BaseModel):
    """Request body for a boiler thermal calculation."""

    fuel_consumption_kg_per_h: float = Field(..., gt=0, examples=[720.0])
    lower_heating_value_kj_per_kg: float = Field(..., gt=0, examples=[29300.0])
    steam_flow_kg_per_h: float = Field(..., gt=0, examples=[6500.0])
    steam_enthalpy_kj_per_kg: float = Field(..., gt=0, examples=[3200.0])
    feedwater_enthalpy_kj_per_kg: float = Field(..., ge=0, examples=[420.0])


class CalculationResponse(BaseModel):
    """Response body with computed boiler thermal performance."""

    heat_input_kw: float
    useful_heat_kw: float
    efficiency_percent: float
    steam_to_fuel_ratio: float


@app.get("/api/health")
def health() -> dict[str, str]:
    """Simple health check."""
    return {"status": "ok", "version": __version__}


@app.post("/api/calculate", response_model=CalculationResponse)
def calculate_endpoint(request: CalculationRequest) -> CalculationResponse:
    """Run the boiler thermal calculation and return the results."""
    inputs = BoilerInputs(
        fuel_consumption_kg_per_h=request.fuel_consumption_kg_per_h,
        lower_heating_value_kj_per_kg=request.lower_heating_value_kj_per_kg,
        steam_flow_kg_per_h=request.steam_flow_kg_per_h,
        steam_enthalpy_kj_per_kg=request.steam_enthalpy_kj_per_kg,
        feedwater_enthalpy_kj_per_kg=request.feedwater_enthalpy_kj_per_kg,
    )
    try:
        result = calculate(inputs)
    except BoilerInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return CalculationResponse(
        heat_input_kw=round(result.heat_input_kw, 2),
        useful_heat_kw=round(result.useful_heat_kw, 2),
        efficiency_percent=round(result.efficiency_percent, 2),
        steam_to_fuel_ratio=round(result.steam_to_fuel_ratio, 3),
    )


@app.get("/")
def index() -> FileResponse:
    """Serve the single-page web UI."""
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
