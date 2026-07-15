# Kotel — Boiler Thermal Calculation / Тепловой расчёт котлов

A small web application for **boiler thermal calculation** using the direct
heat-balance method. It computes gross boiler efficiency, useful heat, heat
input from fuel, and the steam-to-fuel ratio.

## Stack

- **Backend / API:** [FastAPI](https://fastapi.tiangolo.com/) + [Pydantic](https://docs.pydantic.dev/)
- **Server (dev):** [Uvicorn](https://www.uvicorn.org/) with autoreload
- **Frontend:** single static HTML page (`app/static/index.html`), no build step
- **Tests:** `pytest` · **Lint/format:** `ruff`
- **Python:** 3.11+ (developed on 3.12)

## The calculation (direct method)

```
Q_input  = B * Q_r_i                    # heat released by fuel (kW)
Q_useful = D * (h_steam - h_feedwater)  # heat absorbed by steam (kW)
eta      = Q_useful / Q_input * 100     # gross boiler efficiency (%)
```

Flow rates `B` (fuel) and `D` (steam) are entered in kg/h and converted to kg/s
internally; enthalpies are specific enthalpies in kJ/kg.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # runtime + dev deps (pytest, ruff, httpx)
```

For runtime-only deps use `pip install -r requirements.txt`.

## Run (development)

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Then open http://localhost:8000 for the web UI. Interactive API docs are at
http://localhost:8000/docs.

### Endpoints

- `GET /` — web UI
- `GET /api/health` — health check
- `POST /api/calculate` — run a calculation (JSON body)

Example:

```bash
curl -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{"fuel_consumption_kg_per_h":720,"lower_heating_value_kj_per_kg":29300,"steam_flow_kg_per_h":6500,"steam_enthalpy_kj_per_kg":3200,"feedwater_enthalpy_kj_per_kg":420}'
```

## Lint & test

```bash
source .venv/bin/activate
ruff check .          # lint
ruff format --check . # formatting check
pytest -q             # tests
```
