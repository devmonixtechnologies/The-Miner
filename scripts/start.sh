#!/bin/bash

# Advanced Cryptocurrency Mining System - Start Script
# This script starts the mining system with various options

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directory where script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

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

# Check if virtual environment exists
check_venv() {
    if [ ! -d "$PROJECT_DIR/venv" ]; then
        error "Virtual environment not found. Please run install.sh first."
    fi
}

# Activate virtual environment
activate_venv() {
    log "Activating virtual environment..."
    source "$PROJECT_DIR/venv/bin/activate"
    success "Virtual environment activated"
}

# Check if mining is already running
check_running() {
    if pgrep -f "python.*main.py" > /dev/null; then
        warning "Mining system is already running!"
        read -p "Do you want to stop it and restart? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            pkill -f "python.*main.py"
            sleep 2
        else
            exit 0
        fi
    fi
}

# Start mining with default configuration
start_mining() {
    log "Starting mining system with default configuration..."
    cd "$PROJECT_DIR"
    python main.py
}

# Start mining with custom configuration
start_mining_config() {
    local config_file="$1"
    if [ -z "$config_file" ]; then
        error "Configuration file not specified"
    fi
    
    if [ ! -f "$PROJECT_DIR/$config_file" ]; then
        error "Configuration file not found: $config_file"
    fi
    
    log "Starting mining system with configuration: $config_file"
    cd "$PROJECT_DIR"
    python main.py --config "$config_file"
}

# Start terminal GUI
start_terminal() {
    log "Starting terminal GUI..."
    cd "$PROJECT_DIR"
    python3 main.py --terminal
}

# Start mining and dashboard
start_all() {
    log "Starting mining system and dashboard..."
    
    # Start mining in background
    cd "$PROJECT_DIR"
    python main.py &
    MINING_PID=$!
    
    # Wait a moment for mining to start
    sleep 3
    
    # Start dashboard
    python main.py --dashboard &
    DASHBOARD_PID=$!
    
    log "Mining system (PID: $MINING_PID) and dashboard (PID: $DASHBOARD_PID) started"
    log "Press Ctrl+C to stop both"
    
    # Wait for Ctrl+C
    trap "kill $MINING_PID $DASHBOARD_PID 2>/dev/null; exit" INT
    wait
}

# Run benchmarks
run_benchmarks() {
    log "Running system benchmarks..."
    cd "$PROJECT_DIR"
    python main.py --benchmark
}

# Show help
show_help() {
    echo "Advanced Cryptocurrency Mining System - Start Script"
    echo
    echo "Usage: $0 [OPTION]"
    echo
    echo "Options:"
    echo "  mining                 Start mining with default configuration"
    echo "  mining <config>        Start mining with specified configuration"
    echo "  terminal               Start terminal GUI"
    echo "  benchmark              Run system benchmarks"
    echo "  help                   Show this help message"
    echo
    echo "Examples:"
    echo "  $0 mining"
    echo "  $0 mining config/user.conf"
    echo "  $0 terminal"
    echo "  $0 benchmark"
}

# Main function
main() {
    # Change to project directory
    cd "$PROJECT_DIR"
    
    # Check prerequisites
    check_venv
    activate_venv
    
    # Parse command line arguments
    case "${1:-help}" in
        mining)
            if [ -n "$2" ]; then
                start_mining_config "$2"
            else
                check_running
                start_mining
            fi
            ;;
        terminal)
            start_terminal
            ;;
        benchmark)
            run_benchmarks
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
