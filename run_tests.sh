#!/bin/bash
#
# Test runner script for Ultimate Media Downloader
# Runs comprehensive test suite with coverage reporting
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Ultimate Media Downloader - Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Install/upgrade test dependencies
echo -e "${BLUE}Installing test dependencies...${NC}"
pip install -q -r requirements-test.txt

echo ""
echo -e "${GREEN}Starting test execution...${NC}"
echo ""

# Parse command line arguments
TEST_TYPE="${1:-all}"
VERBOSE="${2:-}"

case "$TEST_TYPE" in
    unit)
        echo -e "${BLUE}Running unit tests...${NC}"
        pytest tests/unit/ $VERBOSE
        ;;
    integration)
        echo -e "${BLUE}Running integration tests...${NC}"
        pytest tests/integration/ $VERBOSE
        ;;
    e2e)
        echo -e "${BLUE}Running E2E tests...${NC}"
        pytest tests/e2e/ $VERBOSE
        ;;
    coverage)
        echo -e "${BLUE}Running all tests with coverage...${NC}"
        pytest tests/ --cov=app --cov-report=html --cov-report=term-missing $VERBOSE
        echo ""
        echo -e "${GREEN}Coverage report generated at: tests/coverage/html/index.html${NC}"
        ;;
    quick)
        echo -e "${BLUE}Running quick test (unit only, no coverage)...${NC}"
        pytest tests/unit/ -v --tb=short --no-cov
        ;;
    all|*)
        echo -e "${BLUE}Running all tests with coverage...${NC}"
        pytest tests/ --cov=app --cov-report=html --cov-report=term-missing -v
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}Test Summary${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""

        # Show test statistics
        echo -e "${BLUE}Unit Tests:${NC}"
        pytest tests/unit/ --collect-only -q | tail -1

        echo -e "${BLUE}Integration Tests:${NC}"
        pytest tests/integration/ --collect-only -q | tail -1

        echo -e "${BLUE}E2E Tests:${NC}"
        pytest tests/e2e/ --collect-only -q | tail -1

        echo ""
        echo -e "${GREEN}Coverage report: tests/coverage/html/index.html${NC}"
        ;;
esac

# Check test result
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}All tests passed! ✓${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Some tests failed! ✗${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
