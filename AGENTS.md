# AGENTS.md

## Cursor Cloud specific instructions

This repo is a **FastAPI boiler thermal calculation** web app (Python 3.12).
Standard commands live in `README.md`; only the non-obvious notes are here.

- **Virtualenv:** a `.venv/` is used. The startup update script recreates/refreshes
  it and installs `requirements-dev.txt`. Always `source .venv/bin/activate`
  before running lint/tests/server.
- **System dependency:** creating the venv requires the `python3.12-venv` apt
  package. It is installed at environment build time (not in the update script).
  If `python3 -m venv` fails with an `ensurepip` error, run
  `sudo apt-get install -y python3.12-venv`.
- **Run the dev server** (do NOT put this in the update script):
  `uvicorn app.main:app --reload --port 8000`. UI at `/`, docs at `/docs`.
- **Lint/format/test:** `ruff check .`, `ruff format --check .`, `pytest -q`.
- The frontend (`app/static/index.html`) is plain HTML/JS with no build step; the
  page fetches `POST /api/calculate`, so both are served by the same Uvicorn
  process. Editing the HTML only requires a browser refresh (no server restart).
