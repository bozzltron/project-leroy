#!/bin/bash
# Quick test runner script
# Runs tests in Docker container with all dependencies

set -e

echo "=========================================="
echo "Project Leroy - Test Runner"
echo "=========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running"
    exit 1
fi

# Build Docker image if needed
echo "Building Docker image (if needed)..."
docker-compose -f docker-compose.pi5.yml build --quiet

# Run tests
echo ""
echo "Running tests..."
echo ""

if [ -z "$1" ]; then
    # Run all tests
    docker-compose -f docker-compose.pi5.yml run --rm leroy-pi5 bash -c \
        "cd /app && source venv/bin/activate && python3 -m unittest discover tests -v"
else
    # Run specific test
    docker-compose -f docker-compose.pi5.yml run --rm leroy-pi5 bash -c \
        "cd /app && source venv/bin/activate && python3 -m unittest $1 -v"
fi

echo ""
echo "=========================================="
echo "Tests complete!"
echo "=========================================="

