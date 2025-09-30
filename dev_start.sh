#!/bin/bash
# Development Server Startup Script
# Automatically manages SSH tunnel and starts the backend server

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🚀 Starting CA Tadley Development Environment${NC}"
echo "=" * 50

# Step 1: Ensure SSH tunnel is running
echo -e "${YELLOW}1. Checking SSH tunnel...${NC}"
./manage_tunnel.sh ensure

# Step 2: Wait a moment for tunnel to stabilize
sleep 2

# Step 3: Test database connection
echo -e "${YELLOW}2. Testing database connection...${NC}"
if ./manage_tunnel.sh test; then
    echo -e "${GREEN}✅ Database ready${NC}"
else
    echo -e "${RED}❌ Database connection failed${NC}"
    exit 1
fi

# Step 4: Start backend server
echo -e "${YELLOW}3. Starting backend server...${NC}"
echo -e "${GREEN}Backend will be available at: http://localhost:8000${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server and tunnel${NC}"
echo ""

# Trap to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    echo -e "${YELLOW}Stopping SSH tunnel...${NC}"
    ./manage_tunnel.sh stop
    exit 0
}

trap cleanup INT TERM

# Start the server
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload