#!/bin/bash

# Azure App Service startup script
pip install -r /home/site/wwwroot/requirements.txt
cd /home/site/wwwroot
gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
