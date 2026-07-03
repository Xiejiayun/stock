#!/bin/bash

# Azure App Service startup script
cd /home/site/wwwroot/backend
export PYTHONPATH=/home/site/wwwroot/.python_packages/lib/site-packages
python -m gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
