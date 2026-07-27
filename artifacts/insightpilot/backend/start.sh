#!/bin/bash
set -e
cd /home/runner/workspace/artifacts/insightpilot/backend
exec /home/runner/workspace/.pythonlibs/bin/uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
