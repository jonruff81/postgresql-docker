#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐘 Starting PostgreSQL 15 Docker Container for Ubuntu 24.04 VPS${NC}"
echo -e "${YELLOW}================================================${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if container is already running
if docker ps | grep -q takeoff_postgres; then
    echo -e "${YELLOW}⚠️  Container 'takeoff_postgres' is already running.${NC}"
    echo -e "${BLUE}📊 Container status:${NC}"
    docker ps --filter "name=takeoff_postgres" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    exit 0
fi

# Check if container exists but is stopped
if docker ps -a | grep -q takeoff_postgres; then
    echo -e "${YELLOW}🔄 Starting existing container...${NC}"
    docker start takeoff_postgres
else
    echo -e "${GREEN}🚀 Creating and starting new container...${NC}"
    docker compose up -d
fi

# Wait for PostgreSQL to be ready
echo -e "${BLUE}⏳ Waiting for PostgreSQL to be ready...${NC}"
timeout=60
count=0
until docker exec takeoff_postgres pg_isready -U Jon -d takeoff_pricing_db > /dev/null 2>&1; do
    if [ $count -ge $timeout ]; then
        echo -e "${RED}❌ Timeout waiting for PostgreSQL to start${NC}"
        docker compose logs
        exit 1
    fi
    echo -n "."
    sleep 1
    count=$((count + 1))
done

echo -e "\n${GREEN}✅ PostgreSQL 15 is ready!${NC}"
echo -e "${BLUE}📊 Container Information:${NC}"
docker ps --filter "name=takeoff_postgres" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n${GREEN}🎉 Setup Complete!${NC}"
echo -e "${BLUE}Connection Details:${NC}"
echo -e "  Host: 127.0.0.1"
echo -e "  Port: 5432"
echo -e "  Database: takeoff_pricing_db"
echo -e "  Username: Jon"
echo -e "\n${YELLOW}🔧 Useful Commands:${NC}"
echo -e "  View logs: ${BLUE}docker compose logs -f${NC}"
echo -e "  Connect to DB: ${BLUE}docker exec -it takeoff_postgres psql -U Jon -d takeoff_pricing_db${NC}"
echo -e "  Stop container: ${BLUE}docker compose down${NC}"
echo -e "  Database backup: ${BLUE}./backup.sh${NC}"
