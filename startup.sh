#!/bin/bash

# Build frontend and copy to backend/static
cd /home/site/wwwroot/frontend
npm install
npm run build

# Move build output to backend/static
rm -rf /home/site/wwwroot/backend/static
mv dist /home/site/wwwroot/backend/static

# Install Python dependencies and start server
cd /home/site/wwwroot/backend
pip install -r requirements.txt

# Start FastAPI with gunicorn
gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
