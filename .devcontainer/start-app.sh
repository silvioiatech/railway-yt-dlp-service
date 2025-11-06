#!/bin/bash

# Start the FastAPI application in the dev container
# This script should be run inside the dev container

set -e

echo "Starting FastAPI application..."
echo "API will be available at: http://localhost:8080"
echo "API Docs: http://localhost:8080/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Ensure logs directory exists
mkdir -p /workspace/logs

# Start uvicorn with hot-reload
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
