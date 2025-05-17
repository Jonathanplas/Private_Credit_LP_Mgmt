#!/bin/bash

# i80 Application Launcher
# This script launches both the backend and frontend components of the i80 application

# Set colors for better visibility
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}Starting i80 LP Management System${NC}"
echo -e "${BLUE}=======================================${NC}"

# Check if Python virtual environment exists, if not create it
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    cd "$PROJECT_ROOT"
    python -m venv .venv
    
    echo -e "${YELLOW}Installing backend dependencies...${NC}"
    source .venv/bin/activate
    pip install -r requirements.txt
    deactivate
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to stop processes when script is terminated
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    if [ -n "$backend_pid" ]; then
        echo "Stopping backend server (PID: $backend_pid)"
        kill $backend_pid 2>/dev/null
    fi
    if [ -n "$frontend_pid" ]; then
        echo "Stopping frontend server (PID: $frontend_pid)"
        kill $frontend_pid 2>/dev/null
    fi
    echo -e "${GREEN}Cleanup complete. Goodbye!${NC}"
    exit 0
}

# Set the cleanup function to run when the script receives these signals
trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${YELLOW}Starting backend server...${NC}"
cd "$PROJECT_ROOT"  # Change to project root directory instead of backend directory
source "$PROJECT_ROOT/.venv/bin/activate"
python -m uvicorn backend.main:app --reload &
backend_pid=$!
deactivate

# Check if backend is running
sleep 2
if kill -0 $backend_pid 2>/dev/null; then
    echo -e "${GREEN}Backend server started successfully! (PID: $backend_pid)${NC}"
    echo -e "${BLUE}Backend available at: ${YELLOW}http://localhost:8000${NC}"
else
    echo -e "${RED}Failed to start backend server.${NC}"
    exit 1
fi

# Start frontend
echo -e "${YELLOW}Starting frontend development server...${NC}"
cd "$FRONTEND_DIR"

if command_exists npm; then
    npm start &
    frontend_pid=$!
else
    echo -e "${RED}npm not found. Please install Node.js and npm to run the frontend.${NC}"
    cleanup
fi

# Check if frontend is running
sleep 5
if kill -0 $frontend_pid 2>/dev/null; then
    echo -e "${GREEN}Frontend development server started successfully! (PID: $frontend_pid)${NC}"
    echo -e "${BLUE}Frontend available at: ${YELLOW}http://localhost:3000${NC}"
else
    echo -e "${RED}Failed to start frontend server.${NC}"
    cleanup
fi

echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}i80 LP Management System is running!${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo -e "${BLUE}=======================================${NC}"

# Keep the script running
wait