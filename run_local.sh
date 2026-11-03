#!/bin/bash
# Run the game on this machine: http://localhost:8010  (Ctrl+C to stop)
cd "$(dirname "$0")"
PY=${OSZ_VENV:-$HOME/venvs/osz}/bin
exec "$PY/uvicorn" app.main:app --host 0.0.0.0 --port "${PORT:-8010}"
