#!/bin/bash

# Advanced Cryptocurrency Mining System - Stop Script
# This script stops the mining system gracefully

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if mining processes are running
check_processes() {
    local processes=$(pgrep -f "python.*main.py" | wc -l)
    echo $processes
}

# Stop mining processes gracefully
stop_mining() {
    log "Stopping mining processes..."
    
    local processes=$(check_processes)
    
    if [ "$processes" -eq 0 ]; then
        warning "No mining processes found running"
        return 0
    fi
    
    # Send SIGTERM for graceful shutdown
    log "Sending graceful shutdown signal..."
    pkill -TERM -f "python.*main.py"
    
    # Wait for processes to stop
    local count=0
    while [ $count -lt 30 ]; do
        processes=$(check_processes)
        if [ "$processes" -eq 0 ]; then
            success "Mining processes stopped gracefully"
            return 0
        fi
        
        log "Waiting for processes to stop... ($count/30)"
        sleep 1
        count=$((count + 1))
    done
    
    # Force kill if still running
    warning "Processes didn't stop gracefully, force killing..."
    pkill -KILL -f "python.*main.py"
    
    # Final check
    processes=$(check_processes)
    if [ "$processes" -eq 0 ]; then
        success "Mining processes stopped forcefully"
    else
        error "Failed to stop mining processes"
    fi
}

# Stop systemd service if installed
stop_service() {
    if systemctl is-active --quiet miner.service 2>/dev/null; then
        log "Stopping systemd service..."
        sudo systemctl stop miner.service
        success "Systemd service stopped"
    fi
}

# Show status
show_status() {
    local processes=$(check_processes)
    
    echo "Mining System Status:"
    echo "===================="
    
    if [ "$processes" -gt 0 ]; then
        echo "Status: RUNNING"
        echo "Processes: $processes"
        echo "PIDs:"
        pgrep -f "python.*main.py" | while read pid; do
            echo "  - PID: $pid (Command: $(ps -p $pid -o comm=))"
        done
    else
        echo "Status: STOPPED"
    fi
    
    if systemctl is-active --quiet miner.service 2>/dev/null; then
        echo "Systemd Service: ACTIVE"
    elif systemctl list-unit-files miner.service 2>/dev/null | grep -q "miner.service"; then
        echo "Systemd Service: INACTIVE"
    else
        echo "Systemd Service: NOT INSTALLED"
    fi
    
    echo
}

# Show help
show_help() {
    echo "Advanced Cryptocurrency Mining System - Stop Script"
    echo
    echo "Usage: $0 [OPTION]"
    echo
    echo "Options:"
    echo "  stop                   Stop mining processes"
    echo "  force                  Force stop mining processes"
    echo "  service                Stop systemd service"
    echo "  status                 Show current status"
    echo "  help                   Show this help message"
    echo
    echo "Examples:"
    echo "  $0 stop"
    echo "  $0 force"
    echo "  $0 status"
}

# Force stop mining processes
force_stop() {
    log "Force stopping mining processes..."
    
    local processes=$(check_processes)
    
    if [ "$processes" -eq 0 ]; then
        warning "No mining processes found running"
        return 0
    fi
    
    # Send SIGKILL immediately
    pkill -KILL -f "python.*main.py"
    
    # Verify
    sleep 1
    processes=$(check_processes)
    
    if [ "$processes" -eq 0 ]; then
        success "Mining processes force stopped"
    else
        error "Failed to force stop mining processes"
    fi
}

# Main function
main() {
    # Parse command line arguments
    case "${1:-stop}" in
        stop)
            stop_mining
            ;;
        force)
            force_stop
            ;;
        service)
            stop_service
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "Unknown option: $1. Use '$0 help' for usage information."
            ;;
    esac
}

# Run main function with all arguments
main "$@"
