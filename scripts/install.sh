#!/bin/bash

# Advanced Cryptocurrency Mining System - Installation Script
# This script installs all dependencies and sets up the system

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

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Run as regular user."
    fi
}

# Check Linux distribution
check_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
        log "Detected distribution: $DISTRO $VERSION"
    else
        error "Cannot detect Linux distribution"
    fi
}

# Install system dependencies
install_system_deps() {
    log "Installing system dependencies..."
    
    case $DISTRO in
        ubuntu|debian)
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv git curl wget build-essential \
                linux-headers-$(uname -r) pkg-config libssl-dev
            ;;
        fedora|centos|rhel)
            sudo dnf update -y
            sudo dnf install -y python3 python3-pip git curl wget gcc gcc-c++ make \
                kernel-devel pkgconfig openssl-devel
            ;;
        arch)
            sudo pacman -Syu --noconfirm
            sudo pacman -S --noconfirm python python-pip git curl wget base-devel \
                linux-headers pkgconf openssl
            ;;
        *)
            error "Unsupported distribution: $DISTRO"
            ;;
    esac
    
    success "System dependencies installed"
}

# Install Python dependencies
install_python_deps() {
    log "Installing Python dependencies..."
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        log "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    pip install -r requirements.txt
    
    success "Python dependencies installed"
}

# Install GPU drivers (optional)
install_gpu_drivers() {
    log "Checking for GPU and installing drivers..."
    
    # Check for NVIDIA GPU
    if lspci | grep -i nvidia > /dev/null; then
        log "NVIDIA GPU detected"
        
        read -p "Do you want to install NVIDIA drivers? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            case $DISTRO in
                ubuntu|debian)
                    sudo apt-get install -y nvidia-driver-470 nvidia-cuda-toolkit
                    ;;
                fedora|centos|rhel)
                    sudo dnf install -y nvidia-driver cuda
                    ;;
                arch)
                    sudo pacman -S --noconfirm nvidia cuda
                    ;;
            esac
            success "NVIDIA drivers installed"
        fi
    fi
    
    # Check for AMD GPU
    if lspci | grep -i amd > /dev/null; then
        log "AMD GPU detected"
        
        read -p "Do you want to install AMD drivers? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            case $DISTRO in
                ubuntu|debian)
                    sudo apt-get install -y amdgpu-pro
                    ;;
                fedora|centos|rhel)
                    sudo dnf install -y amdgpu
                    ;;
                arch)
                    sudo pacman -S --noconfirm xf86-video-amdgpu
                    ;;
            esac
            success "AMD drivers installed"
        fi
    fi
}

# Setup configuration
setup_config() {
    log "Setting up configuration..."
    
    # Create necessary directories
    mkdir -p logs data config/profiles
    
    # Copy default configuration if not exists
    if [ ! -f "config/default.conf" ]; then
        cp config/default.conf config/default.conf
    fi
    
    # Create user configuration
    if [ ! -f "config/user.conf" ]; then
        cp config/default.conf config/user.conf
        log "Created user configuration at config/user.conf"
    fi
    
    success "Configuration setup completed"
}

# Setup systemd service (optional)
setup_service() {
    log "Setting up systemd service..."
    
    read -p "Do you want to install systemd service for auto-start? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Create service file
        cat > /tmp/miner.service << EOF
[Unit]
Description=Advanced Cryptocurrency Mining System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        # Install service
        sudo mv /tmp/miner.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable miner.service
        
        success "Systemd service installed. Start with: sudo systemctl start miner"
    fi
}

# Setup firewall rules
setup_firewall() {
    log "Setting up firewall rules..."
    
    # Check if firewall is active
    if command -v ufw > /dev/null && sudo ufw status | grep -q "Status: active"; then
        log "UFW firewall detected"
        
        read -p "Do you want to allow dashboard port (8080) through firewall? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo ufw allow 8080/tcp
            success "Firewall rules updated"
        fi
    fi
}

# Run benchmarks
run_benchmarks() {
    log "Running system benchmarks..."
    
    source venv/bin/activate
    python main.py --benchmark
    
    success "Benchmarks completed"
}

# Create desktop shortcut
create_shortcut() {
    log "Creating desktop shortcut..."
    
    if [ -d "$HOME/Desktop" ]; then
        cat > "$HOME/Desktop/Advanced Mining System.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Advanced Mining System
Comment=Intelligent cryptocurrency mining system
Exec=$(pwd)/venv/bin/python $(pwd)/main.py
Icon=$(pwd)/icon.png
Terminal=true
Categories=System;
EOF
        
        chmod +x "$HOME/Desktop/Advanced Mining System.desktop"
        success "Desktop shortcut created"
    fi
}

# Final setup
final_setup() {
    log "Performing final setup..."
    
    # Set permissions
    chmod +x scripts/*.sh
    chmod +x main.py
    
    # Create log directory
    mkdir -p logs
    
    # Create data directory
    mkdir -p data
    
    success "Final setup completed"
}

# Main installation function
main() {
    log "Starting Advanced Cryptocurrency Mining System installation..."
    
    # Check prerequisites
    check_root
    check_distro
    
    # Installation steps
    install_system_deps
    install_python_deps
    install_gpu_drivers
    setup_config
    setup_service
    setup_firewall
    final_setup
    
    # Optional steps
    read -p "Do you want to run benchmarks now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_benchmarks
    fi
    
    read -p "Do you want to create desktop shortcut? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        create_shortcut
    fi
    
    success "Installation completed successfully!"
    echo
    echo "To start the mining system:"
    echo "  1. Activate virtual environment: source venv/bin/activate"
    echo "  2. Run mining system: python main.py"
    echo "  3. Start dashboard: python main.py --dashboard"
    echo
    echo "Configuration files are in config/ directory"
    echo "Logs will be stored in logs/ directory"
    echo
    echo "For help: python main.py --help"
}

# Run main function
main "$@"
