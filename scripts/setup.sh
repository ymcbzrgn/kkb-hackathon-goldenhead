#!/bin/bash
# KKB Firma İstihbarat - Setup Script
# Proje kurulumu için gerekli adımlar

set -e

echo "================================================"
echo "KKB Firma İstihbarat - Setup Script"
echo "================================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from project root
if [ ! -f "Makefile" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose is installed${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}Warning: Node.js is not installed. Required for frontend development.${NC}"
else
    echo -e "${GREEN}✓ Node.js $(node --version) is installed${NC}"
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Warning: Python 3 is not installed. Required for backend development.${NC}"
else
    echo -e "${GREEN}✓ Python $(python3 --version) is installed${NC}"
fi

echo ""
echo -e "${YELLOW}Step 2: Creating environment files...${NC}"

# Create .env from .env.example if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env from .env.example${NC}"
        echo -e "${YELLOW}  Please update .env with your actual values${NC}"
    else
        echo -e "${YELLOW}Warning: .env.example not found${NC}"
    fi
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

# Create backend .env
if [ ! -f "backend/.env" ]; then
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        echo -e "${GREEN}✓ Created backend/.env from backend/.env.example${NC}"
    fi
else
    echo -e "${GREEN}✓ backend/.env already exists${NC}"
fi

echo ""
echo -e "${YELLOW}Step 3: Starting Docker services...${NC}"

# Start development services (postgres, redis, qdrant)
docker-compose -f docker/docker-compose.dev.yml up -d

echo -e "${GREEN}✓ Docker services started${NC}"

# Wait for services to be ready
echo ""
echo -e "${YELLOW}Step 4: Waiting for services to be ready...${NC}"
sleep 5

# Check PostgreSQL
echo -n "  Checking PostgreSQL... "
for i in {1..30}; do
    if docker exec kkb-postgres-dev pg_isready -U kkb -d firma_istihbarat &> /dev/null; then
        echo -e "${GREEN}Ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Timeout${NC}"
        exit 1
    fi
    sleep 1
done

# Check Redis
echo -n "  Checking Redis... "
for i in {1..30}; do
    if docker exec kkb-redis-dev redis-cli ping &> /dev/null; then
        echo -e "${GREEN}Ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Timeout${NC}"
        exit 1
    fi
    sleep 1
done

# Check Qdrant
echo -n "  Checking Qdrant... "
for i in {1..30}; do
    if curl -s http://localhost:6333/health &> /dev/null; then
        echo -e "${GREEN}Ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Timeout${NC}"
        exit 1
    fi
    sleep 1
done

echo ""
echo -e "${YELLOW}Step 5: Setting up backend...${NC}"

# Create Python virtual environment if it doesn't exist
if [ ! -d "backend/venv" ]; then
    echo "  Creating virtual environment..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    cd ..
    echo -e "${GREEN}✓ Virtual environment created and dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

echo ""
echo -e "${YELLOW}Step 6: Setting up frontend...${NC}"

# Install frontend dependencies
if [ -d "frontend" ]; then
    cd frontend
    if [ ! -d "node_modules" ]; then
        echo "  Installing npm dependencies..."
        npm install
        echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
    else
        echo -e "${GREEN}✓ Frontend dependencies already installed${NC}"
    fi
    cd ..
fi

echo ""
echo -e "${YELLOW}Step 7: Initializing Qdrant collections...${NC}"
python3 scripts/init_qdrant.py 2>/dev/null || echo -e "${YELLOW}  Skipped (run manually if needed)${NC}"

echo ""
echo "================================================"
echo -e "${GREEN}Setup complete!${NC}"
echo "================================================"
echo ""
echo "Next steps:"
echo "  1. Update .env with your KKB API key"
echo "  2. Start backend: cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo "  3. Start frontend: cd frontend && npm run dev"
echo ""
echo "Or use make commands:"
echo "  make dev-backend  - Start backend in development mode"
echo "  make dev-frontend - Start frontend in development mode"
echo "  make dev          - Start full stack with Docker"
echo ""
