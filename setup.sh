#!/bin/bash
# Django Starter Setup Script

set -e

echo "🚀 Django Starter Setup"
echo "========================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env created${NC}"
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

# Install dependencies
if command -v python3 &> /dev/null; then
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${YELLOW}Python not found. Please install Python 3.12+${NC}"
    exit 1
fi

# Create virtual environment if using local setup
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Run migrations
echo -e "${BLUE}Running migrations...${NC}"
python manage.py migrate
echo -e "${GREEN}✓ Migrations completed${NC}"

# Create demo data
echo -e "${BLUE}Creating demo data...${NC}"
python manage.py create_demo_data
echo -e "${GREEN}✓ Demo data created${NC}"

# Collect static files
echo -e "${BLUE}Collecting static files...${NC}"
python manage.py collectstatic --noinput
echo -e "${GREEN}✓ Static files collected${NC}"

echo ""
echo -e "${GREEN}Setup Complete! 🎉${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Start the development server:"
echo "   python manage.py runserver"
echo ""
echo "2. In another terminal, start Celery:"
echo "   celery -A config worker -l info"
echo ""
echo "3. In another terminal, start Celery Beat:"
echo "   celery -A config beat -l info"
echo ""
echo -e "${BLUE}Demo credentials:${NC}"
echo "Email: owner@example.com"
echo "Password: password123"
echo ""
echo -e "${BLUE}URLs:${NC}"
echo "Dashboard: http://localhost:8000/dashboard/"
echo "Admin: http://localhost:8000/admin/"
echo "API Docs: http://localhost:8000/api/docs/"
