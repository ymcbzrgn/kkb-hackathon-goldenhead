#!/bin/bash
# KKB Firma İstihbarat - Deploy Script
# Production deployment

set -e

echo "================================================"
echo "KKB Firma İstihbarat - Deploy Script"
echo "================================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
DOCKER_COMPOSE_FILE="docker/docker-compose.yml"
ENV_FILE=".env"

# Check if running from project root
if [ ! -f "Makefile" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

# Check .env file
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: .env file not found. Please create it from .env.example${NC}"
    exit 1
fi

# Load environment variables
source $ENV_FILE

# Check required environment variables
if [ -z "$KKB_API_KEY" ]; then
    echo -e "${RED}Error: KKB_API_KEY is not set in .env${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 1: Building Docker images...${NC}"

# Build images
docker-compose -f $DOCKER_COMPOSE_FILE build --no-cache

echo -e "${GREEN}✓ Docker images built${NC}"

echo ""
echo -e "${YELLOW}Step 2: Stopping existing services...${NC}"

# Stop existing containers
docker-compose -f $DOCKER_COMPOSE_FILE down || true

echo -e "${GREEN}✓ Existing services stopped${NC}"

echo ""
echo -e "${YELLOW}Step 3: Starting services...${NC}"

# Start services
docker-compose -f $DOCKER_COMPOSE_FILE up -d

echo -e "${GREEN}✓ Services started${NC}"

echo ""
echo -e "${YELLOW}Step 4: Waiting for services to be healthy...${NC}"

# Wait for backend to be ready
echo -n "  Checking backend... "
for i in {1..60}; do
    if curl -s http://localhost:8000/api/health &> /dev/null; then
        echo -e "${GREEN}Ready${NC}"
        break
    fi
    if [ $i -eq 60 ]; then
        echo -e "${RED}Timeout - Check logs with: docker-compose -f $DOCKER_COMPOSE_FILE logs backend${NC}"
        exit 1
    fi
    sleep 2
done

# Wait for frontend to be ready
echo -n "  Checking frontend... "
for i in {1..30}; do
    if curl -s http://localhost:3000 &> /dev/null; then
        echo -e "${GREEN}Ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Timeout - Check logs with: docker-compose -f $DOCKER_COMPOSE_FILE logs frontend${NC}"
        exit 1
    fi
    sleep 2
done

echo ""
echo -e "${YELLOW}Step 5: Running post-deploy tasks...${NC}"

# Initialize Qdrant collections (if needed)
docker exec kkb-backend python -c "
from scripts.init_qdrant import init_collections
init_collections()
print('Qdrant collections initialized')
" 2>/dev/null || echo "  Qdrant init skipped"

echo ""
echo "================================================"
echo -e "${GREEN}Deployment complete!${NC}"
echo "================================================"
echo ""
echo "Services running:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Qdrant Dashboard: http://localhost:6333/dashboard"
echo ""
echo "Useful commands:"
echo "  View logs: docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
echo "  Stop: docker-compose -f $DOCKER_COMPOSE_FILE down"
echo "  Restart: docker-compose -f $DOCKER_COMPOSE_FILE restart"
echo ""
