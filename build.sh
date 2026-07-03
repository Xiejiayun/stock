#!/bin/bash
# Build script: builds frontend and copies to static/ for production serving

set -e

echo "Building frontend..."
cd "$(dirname "$0")/frontend"
npm install
npm run build

echo "Copying to static/..."
rm -rf ../static
mv dist ../static

echo "Done! Run: pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000"
