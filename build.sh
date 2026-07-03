#!/bin/bash
# Build script: builds frontend and copies to backend/static for production serving

set -e

echo "Building frontend..."
cd "$(dirname "$0")/frontend"
npm install
npm run build

echo "Copying to backend/static..."
rm -rf ../backend/static
mv dist ../backend/static

echo "Done! Run: cd backend && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000"
