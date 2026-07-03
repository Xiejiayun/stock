#!/bin/bash

# Azure App Service startup script
set -e

cd /home/site/wwwroot/backend
export PYTHONPATH=/home/site/wwwroot/.python_packages/lib/site-packages
PORT="${PORT:-8000}"

echo "Starting stock app from $(pwd)"
python3 --version
python3 -c "import sys; print(sys.executable); import gunicorn; import uvicorn; print('dependencies ok')"

exec python3 -m gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind "0.0.0.0:${PORT}" --timeout 120
