#!/bin/bash
# Automated setup script for the Customer Service AI project

set -e  # Exit on error

echo "======================================================================"
echo "Customer Service AI - Automated Setup"
echo "======================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo "ℹ $1"
}

# Check if Docker is running
echo "Checking Docker..."
if ! docker ps > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi
print_success "Docker is running"
echo ""

# Check if docker-compose is available
echo "Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install it first."
    exit 1
fi
print_success "Docker Compose is installed"
echo ""

# Stop and remove any existing containers
echo "Cleaning up existing containers..."
docker-compose down 2>/dev/null || true
docker rm -f ollama ollama-init customer-service-app 2>/dev/null || true
print_success "Cleanup complete"
echo ""

# Start Ollama service
echo "Starting Ollama service..."
docker-compose up -d ollama
print_success "Ollama service started"
echo ""

# Wait for Ollama to be healthy
echo "Waiting for Ollama to be healthy..."
TIMEOUT=60
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if docker inspect --format='{{.State.Health.Status}}' ollama 2>/dev/null | grep -q "healthy"; then
        print_success "Ollama is healthy"
        break
    fi
    echo "  Waiting... ($ELAPSED/$TIMEOUT seconds)"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    print_error "Ollama failed to become healthy within $TIMEOUT seconds"
    echo "  Check logs with: docker logs ollama"
    exit 1
fi
echo ""

# Pull models using ollama-init
echo "Pulling Ollama models (this may take 3-7 minutes)..."
echo "  - smollm2:135m (~271 MB)"
echo "  - nomic-embed-text (~274 MB)"
echo ""

if docker-compose up ollama-init; then
    print_success "Models pulled successfully"
else
    print_error "Failed to pull models"
    echo "  Try manually with: docker exec ollama ollama pull smollm2:135m"
    exit 1
fi
echo ""

# Verify models are available
echo "Verifying models..."
if docker exec ollama ollama list | grep -q "smollm2" && docker exec ollama ollama list | grep -q "nomic-embed-text"; then
    print_success "All required models are available"
    docker exec ollama ollama list
else
    print_warning "Models may not be properly installed"
    docker exec ollama ollama list
fi
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
if command -v uv &> /dev/null; then
    print_info "Using uv package manager"
    uv sync
else
    print_info "Using pip package manager"
    pip install -e .
fi
print_success "Python dependencies installed"
echo ""

# Optional: Start the app container
read -p "Do you want to start the app in Docker? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting app container..."
    docker-compose --profile full up -d app
    print_success "App container started on http://localhost:8000"
    echo ""
    
    # Wait a bit and test the endpoint
    echo "Testing app endpoint..."
    sleep 5
    if curl -s http://localhost:8000/ | grep -q "ok"; then
        print_success "App is responding correctly"
    else
        print_warning "App may not be ready yet. Check logs with: docker logs customer-service-app"
    fi
else
    print_info "Skipping app container. Run manually with: uvicorn app.main:app --reload"
fi
echo ""

# Summary
echo "======================================================================"
echo "Setup Complete! ✅"
echo "======================================================================"
echo ""
echo "Services running:"
docker-compose ps
echo ""
echo "Next steps:"
echo "  1. Run tests: pytest tests/test_app.py -v"
echo "  2. Start app locally: uvicorn app.main:app --reload"
echo "  3. Run evaluation: python evaluation/evaluate.py"
echo ""
echo "Or run everything in Docker:"
echo "  docker-compose --profile full up -d"
echo ""
echo "Useful commands:"
echo "  - View logs: docker logs ollama"
echo "  - Stop services: docker-compose down"
echo "  - List models: docker exec ollama ollama list"
echo ""
