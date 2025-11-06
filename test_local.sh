#!/bin/bash
# Local Testing Script for Ultimate Media Downloader
# Run this inside the VSCode dev container

set -e  # Exit on error

echo "=========================================="
echo "Ultimate Media Downloader - Local Testing"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base URL
BASE_URL="http://localhost:8080"

# Function to print colored status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# Function to wait for service
wait_for_service() {
    echo "Waiting for service to start..."
    for i in {1..30}; do
        if curl -s -f "$BASE_URL/api/v1/health" > /dev/null 2>&1; then
            print_status 0 "Service is ready!"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    print_status 1 "Service failed to start"
    return 1
}

# Step 1: Check Python version
echo "1. Checking Python version..."
python3 --version
print_status $? "Python version check"
echo ""

# Step 2: Check dependencies
echo "2. Checking dependencies..."
pip list | grep -E "fastapi|uvicorn|pydantic|pydantic-settings|yt-dlp"
print_status $? "Dependencies installed"
echo ""

# Step 3: Copy environment file
echo "3. Setting up environment..."
if [ ! -f .env ]; then
    cp .env.local .env
    print_status 0 "Created .env from .env.local"
else
    print_status 0 ".env already exists"
fi
echo ""

# Step 4: Run verification script
echo "4. Running deployment verification..."
python3 verify_deployment.py
VERIFY_STATUS=$?
print_status $VERIFY_STATUS "Deployment verification"
echo ""

if [ $VERIFY_STATUS -ne 0 ]; then
    echo -e "${RED}Fix the issues above before continuing${NC}"
    exit 1
fi

# Step 5: Start the application in background
echo "5. Starting application..."
REQUIRE_API_KEY=false API_KEY=test python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload > /tmp/app.log 2>&1 &
APP_PID=$!
echo "Application started with PID: $APP_PID"

# Wait for service to be ready
wait_for_service || {
    echo ""
    echo "Application logs:"
    cat /tmp/app.log
    kill $APP_PID 2>/dev/null || true
    exit 1
}
echo ""

# Step 6: Run API tests
echo "6. Testing API endpoints..."
echo ""

# Test 6.1: Health check
echo "  6.1. Health check..."
HEALTH=$(curl -s "$BASE_URL/api/v1/health")
echo "       Response: $HEALTH"
echo "$HEALTH" | grep -q "healthy"
print_status $? "Health check endpoint"
echo ""

# Test 6.2: Version info
echo "  6.2. Version info..."
VERSION=$(curl -s "$BASE_URL/version")
echo "       Response: $VERSION"
echo "$VERSION" | grep -q "3.1.0"
print_status $? "Version endpoint"
echo ""

# Test 6.3: API docs
echo "  6.3. API documentation..."
curl -s -f "$BASE_URL/docs" > /dev/null
print_status $? "Swagger UI accessible"
echo ""

# Test 6.4: Frontend
echo "  6.4. Frontend web UI..."
curl -s -f "$BASE_URL/" > /dev/null
print_status $? "Frontend accessible"
echo ""

# Test 6.5: Static files
echo "  6.5. Static files..."
curl -s -f "$BASE_URL/js/app.js" > /dev/null
print_status $? "Static JavaScript files"
echo ""

# Test 6.6: Capabilities endpoint
echo "  6.6. Capabilities..."
CAPABILITIES=$(curl -s "$BASE_URL/api/v1/capabilities")
echo "       Response: $CAPABILITIES"
echo "$CAPABILITIES" | grep -q "channel_downloads"
print_status $? "Capabilities endpoint"
echo ""

# Test 6.7: Create test download
echo "  6.7. Test download (small test video)..."
TEST_URL="https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
DOWNLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/download" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"$TEST_URL\"}")
echo "       Response: $DOWNLOAD_RESPONSE"
echo "$DOWNLOAD_RESPONSE" | grep -q "request_id"
print_status $? "Download creation"

# Extract request_id
REQUEST_ID=$(echo "$DOWNLOAD_RESPONSE" | grep -o '"request_id":"[^"]*"' | cut -d'"' -f4)
if [ -n "$REQUEST_ID" ]; then
    echo "       Request ID: $REQUEST_ID"

    # Wait a bit and check status
    echo "       Waiting 3 seconds..."
    sleep 3

    STATUS_RESPONSE=$(curl -s "$BASE_URL/api/v1/downloads/$REQUEST_ID")
    echo "       Status: $STATUS_RESPONSE"
    echo "$STATUS_RESPONSE" | grep -q "status"
    print_status $? "Download status check"
fi
echo ""

# Test 6.8: Cookie endpoints
echo "  6.8. Cookie management endpoints..."
curl -s -f "$BASE_URL/api/v1/cookies" > /dev/null
print_status $? "Cookie list endpoint"
echo ""

# Test 6.9: Batch endpoints
echo "  6.9. Batch download endpoints..."
BATCH_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/batch/download" \
    -H "Content-Type: application/json" \
    -d '{"urls": ["https://example.com/test.mp4"], "concurrency": 1}')
echo "       Response: $BATCH_RESPONSE"
echo "$BATCH_RESPONSE" | grep -q "batch_id"
print_status $? "Batch download creation"
echo ""

# Test 6.10: Metrics endpoint
echo "  6.10. Prometheus metrics..."
curl -s -f "$BASE_URL/metrics" > /dev/null
print_status $? "Metrics endpoint"
echo ""

# Step 7: Run unit tests (if pytest is available)
echo "7. Running unit tests..."
if command -v pytest &> /dev/null; then
    pytest tests/ -v --tb=short -x || print_status 1 "Some tests failed (check output above)"
else
    echo -e "${YELLOW}⚠${NC} pytest not installed, skipping unit tests"
    echo "   Install with: pip install pytest pytest-cov pytest-asyncio"
fi
echo ""

# Cleanup
echo "=========================================="
echo "Cleaning up..."
echo "=========================================="
kill $APP_PID 2>/dev/null || true
print_status 0 "Application stopped"
echo ""

# Summary
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo ""
echo -e "${GREEN}✓${NC} Local testing complete!"
echo ""
echo "You can now:"
echo "  1. Start the app manually:"
echo "     ${YELLOW}uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload${NC}"
echo ""
echo "  2. Run tests:"
echo "     ${YELLOW}pytest tests/ -v --cov=app --cov-report=html${NC}"
echo ""
echo "  3. Access the application:"
echo "     ${YELLOW}http://localhost:8080${NC} (Frontend)"
echo "     ${YELLOW}http://localhost:8080/docs${NC} (API Docs)"
echo ""
echo "  4. View logs:"
echo "     ${YELLOW}tail -f /tmp/app.log${NC}"
echo ""
echo "=========================================="
