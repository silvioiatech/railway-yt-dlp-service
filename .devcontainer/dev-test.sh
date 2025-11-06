#!/bin/bash

# Dev Container Test Runner Script
# Usage: ./dev-test.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Railway yt-dlp Service - Dev Container${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}>>> $1${NC}\n"
}

# Function to check if we're in a dev container
check_dev_container() {
    if [ -z "$REMOTE_CONTAINERS" ] && [ -z "$CODESPACES" ]; then
        echo -e "${YELLOW}Warning: Not running in a dev container${NC}"
        echo "This script is optimized for dev container environments"
        echo ""
    fi
}

# Parse command line arguments
RUN_TESTS=true
RUN_COVERAGE=false
RUN_LINT=false
RUN_FORMAT=false
RUN_APP=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-test)
            RUN_TESTS=false
            shift
            ;;
        --coverage)
            RUN_COVERAGE=true
            shift
            ;;
        --lint)
            RUN_LINT=true
            shift
            ;;
        --format)
            RUN_FORMAT=true
            shift
            ;;
        --run)
            RUN_APP=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "Usage: ./dev-test.sh [options]"
            echo ""
            echo "Options:"
            echo "  --no-test      Skip running tests"
            echo "  --coverage     Run tests with coverage report"
            echo "  --lint         Run linting checks"
            echo "  --format       Format code with Black and isort"
            echo "  --run          Start the application"
            echo "  -v, --verbose  Verbose output"
            echo "  --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./dev-test.sh                    # Run basic tests"
            echo "  ./dev-test.sh --coverage         # Run tests with coverage"
            echo "  ./dev-test.sh --format --lint    # Format and lint code"
            echo "  ./dev-test.sh --run              # Start the application"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

check_dev_container

# Verify environment
print_header "Checking Environment"
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "User: $(whoami)"
echo ""

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    print_header "Installing Dependencies"
    pip install -r requirements.txt -r requirements-test.txt
fi

# Format code
if [ "$RUN_FORMAT" = true ]; then
    print_header "Formatting Code"
    
    echo "Running Black formatter..."
    black app/ tests/ || echo -e "${RED}Black formatting failed${NC}"
    
    echo "Running isort..."
    isort app/ tests/ || echo -e "${RED}isort failed${NC}"
    
    echo -e "${GREEN}✓ Code formatted${NC}"
fi

# Lint code
if [ "$RUN_LINT" = true ]; then
    print_header "Linting Code"
    
    echo "Running Ruff..."
    ruff check app/ tests/ || echo -e "${YELLOW}Linting warnings detected${NC}"
    
    echo -e "${GREEN}✓ Linting complete${NC}"
fi

# Run tests
if [ "$RUN_TESTS" = true ]; then
    print_header "Running Tests"
    
    if [ "$RUN_COVERAGE" = true ]; then
        echo "Running tests with coverage..."
        pytest tests/ \
            --cov=app \
            --cov-report=html \
            --cov-report=term-missing \
            ${VERBOSE:+-v} \
            || echo -e "${RED}Some tests failed${NC}"
        
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
    else
        echo "Running tests..."
        pytest tests/ ${VERBOSE:+-v} || echo -e "${RED}Some tests failed${NC}"
    fi
    
    echo -e "${GREEN}✓ Tests complete${NC}"
fi

# Run the application
if [ "$RUN_APP" = true ]; then
    print_header "Starting Application"
    
    echo "Starting FastAPI server on http://localhost:8080"
    echo "API Documentation: http://localhost:8080/docs"
    echo "Health Check: http://localhost:8080/api/v1/health"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""
    
    uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
fi

# Summary
if [ "$RUN_APP" = false ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}All tasks completed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Next steps:"
    echo "  - Run './dev-test.sh --run' to start the application"
    echo "  - Visit http://localhost:8080/docs for API documentation"
    echo "  - Check logs in /workspace/logs/"
    echo ""
fi
