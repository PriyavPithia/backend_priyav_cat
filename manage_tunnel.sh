#!/bin/bash
# SSH Tunnel Manager for RDS Connection
# This script automatically manages the SSH tunnel to RDS

set -e

# Configuration
RDS_ENDPOINT="stg-sattva-database.cx4eqksy0skp.eu-west-2.rds.amazonaws.com"
BASTION_HOST="18.170.28.143"
LOCAL_PORT="5433"
RDS_PORT="5432"
SSH_KEY="/Users/raghu/Downloads/accesskey.pem"
BASTION_USER="ubuntu"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check and fix SSH key permissions
check_ssh_key() {
    if [ ! -f "${SSH_KEY}" ]; then
        echo -e "${RED}❌ SSH key not found: ${SSH_KEY}${NC}"
        exit 1
    fi
    
    # Check current permissions
    current_perms=$(stat -f "%A" "${SSH_KEY}" 2>/dev/null || stat -c "%a" "${SSH_KEY}" 2>/dev/null)
    
    if [ "$current_perms" != "600" ]; then
        echo -e "${YELLOW}🔧 Fixing SSH key permissions...${NC}"
        chmod 600 "${SSH_KEY}"
        echo -e "${GREEN}✅ SSH key permissions fixed${NC}"
    fi
}

# Function to check if tunnel is running
check_tunnel() {
    if pgrep -f "ssh.*${LOCAL_PORT}.*${RDS_ENDPOINT}" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to start tunnel
start_tunnel() {
    echo -e "${YELLOW}Starting SSH tunnel to RDS...${NC}"
    
    # Check and fix SSH key permissions first
    check_ssh_key
    
    # Kill existing tunnel if any
    pkill -f "ssh.*${LOCAL_PORT}.*${RDS_ENDPOINT}" 2>/dev/null || true
    
    # Start new tunnel with optimized settings
    ssh -L ${LOCAL_PORT}:${RDS_ENDPOINT}:${RDS_PORT} \
        -i "${SSH_KEY}" \
        ${BASTION_USER}@${BASTION_HOST} \
        -N -f \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o LogLevel=ERROR \
        -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -o Compression=no \
        -o TCPKeepAlive=yes \
        -o ControlMaster=auto \
        -o ControlPath=/tmp/%r@%h:%p \
        -o ControlPersist=60m \
        -o ExitOnForwardFailure=yes \
        -o BatchMode=yes
    
    sleep 2
    
    if check_tunnel; then
        echo -e "${GREEN}✅ SSH tunnel started successfully${NC}"
        echo -e "   Local port: ${LOCAL_PORT}"
        echo -e "   Remote: ${RDS_ENDPOINT}:${RDS_PORT}"
        return 0
    else
        echo -e "${RED}❌ Failed to start SSH tunnel${NC}"
        return 1
    fi
}

# Function to stop tunnel
stop_tunnel() {
    echo -e "${YELLOW}Stopping SSH tunnel...${NC}"
    if pkill -f "ssh.*${LOCAL_PORT}.*${RDS_ENDPOINT}" 2>/dev/null; then
        echo -e "${GREEN}✅ SSH tunnel stopped${NC}"
    else
        echo -e "${YELLOW}No tunnel was running${NC}"
    fi
}

# Function to check tunnel status
status_tunnel() {
    if check_tunnel; then
        echo -e "${GREEN}✅ SSH tunnel is running${NC}"
        ps aux | grep "ssh.*${LOCAL_PORT}.*${RDS_ENDPOINT}" | grep -v grep
    else
        echo -e "${RED}❌ SSH tunnel is not running${NC}"
    fi
}

# Function to test database connection
test_connection() {
    echo -e "${YELLOW}Testing database connection...${NC}"
    
    if ! check_tunnel; then
        echo -e "${RED}❌ SSH tunnel not running. Starting tunnel first...${NC}"
        start_tunnel
    fi
    
    # Test connection using Python
    cd "$(dirname "$0")"
    ./venv/bin/python -c "
import psycopg2
import sys
try:
    conn = psycopg2.connect(
        host='localhost',
        port=${LOCAL_PORT},
        database='postgres',
        user='rdssattvapg',
        password='(,7(UP4~U#6UadLQ'
    )
    print('${GREEN}✅ Database connection successful!${NC}')
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()[0]
    print(f'   Database version: {version[:50]}...')
    conn.close()
except Exception as e:
    print(f'${RED}❌ Database connection failed: {e}${NC}')
    sys.exit(1)
"
}

# Function to ensure tunnel is running
ensure_tunnel() {
    if ! check_tunnel; then
        start_tunnel
    else
        echo -e "${GREEN}✅ SSH tunnel already running${NC}"
    fi
}

# Main function
main() {
    case "${1:-status}" in
        start)
            start_tunnel
            ;;
        stop)
            stop_tunnel
            ;;
        restart)
            stop_tunnel
            sleep 1
            start_tunnel
            ;;
        status)
            status_tunnel
            ;;
        test)
            test_connection
            ;;
        ensure)
            ensure_tunnel
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|test|ensure}"
            echo ""
            echo "Commands:"
            echo "  start   - Start SSH tunnel to RDS"
            echo "  stop    - Stop SSH tunnel"
            echo "  restart - Restart SSH tunnel"
            echo "  status  - Check tunnel status"
            echo "  test    - Test database connection"
            echo "  ensure  - Ensure tunnel is running (start if needed)"
            exit 1
            ;;
    esac
}

main "$@"