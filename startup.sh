#!/bin/bash

# Azure App Service startup script
cd /home/site/wwwroot/backend
pip install -r requirements.txt
gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
