#!/bin/bash

# Production Deployment Script
# DevMonix Technologies - Advanced Cryptocurrency Mining System

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="miner"
SERVICE_USER="miner"
LOG_DIR="/var/log/miner"
CONFIG_DIR="/etc/miner"
BACKUP_DIR="/var/backups/miner"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

check_system() {
    log_info "Checking system requirements..."
    
    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        log_error "Cannot determine OS version"
        exit 1
    fi
    
    source /etc/os-release
    log_info "Detected OS: $PRETTY_NAME"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_info "Python version: $python_version"
    
    if [[ $(echo "$python_version < 3.8" | bc -l) -eq 1 ]]; then
        log_error "Python 3.8+ is required"
        exit 1
    fi
    
    # Check system resources
    memory_gb=$(free -g | awk '/^Mem:/{print $2}')
    cpu_cores=$(nproc)
    
    log_info "System resources: ${cpu_cores} CPU cores, ${memory_gb}GB RAM"
    
    if [[ $memory_gb -lt 2 ]]; then
        log_warning "Low memory detected (< 2GB). Performance may be limited."
    fi
    
    if [[ $cpu_cores -lt 2 ]]; then
        log_warning "Low CPU cores detected (< 2). Performance may be limited."
    fi
}

create_user() {
    log_info "Creating service user..."
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -r -s /bin/false -d /var/lib/miner "$SERVICE_USER"
        log_success "Created user: $SERVICE_USER"
    else
        log_info "User $SERVICE_USER already exists"
    fi
}

create_directories() {
    log_info "Creating directories..."
    
    # Create directories
    mkdir -p "$LOG_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$BACKUP_DIR"
    mkdir -p "/var/lib/miner"
    
    # Set permissions
    chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "/var/lib/miner"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$BACKUP_DIR"
    chmod 755 "$CONFIG_DIR"
    
    log_success "Created and configured directories"
}

install_dependencies() {
    log_info "Installing system dependencies..."
    
    # Detect package manager
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y python3-pip python3-venv systemd curl htop iotool
    elif command -v yum &> /dev/null; then
        yum update -y
        yum install -y python3-pip python3-venv systemd curl htop iotool
    else
        log_error "Unsupported package manager"
        exit 1
    fi
    
    log_success "Installed system dependencies"
}

setup_python_env() {
    log_info "Setting up Python virtual environment..."
    
    cd "$PROJECT_DIR"
    
    # Create virtual environment
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        log_success "Created virtual environment"
    fi
    
    # Activate and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log_success "Installed Python dependencies"
}

deploy_config() {
    log_info "Deploying configuration files..."
    
    # Copy production config
    if [[ -f "$PROJECT_DIR/config/production.conf" ]]; then
        cp "$PROJECT_DIR/config/production.conf" "$CONFIG_DIR/default.conf"
        log_success "Deployed production configuration"
    else
        log_warning "Production config not found, using default"
        cp "$PROJECT_DIR/config/default.conf" "$CONFIG_DIR/default.conf"
    fi
    
    # Set permissions
    chmod 644 "$CONFIG_DIR/default.conf"
    chown root:root "$CONFIG_DIR/default.conf"
    
    log_success "Configuration deployed"
}

create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=Advanced Cryptocurrency Mining System
Documentation=https://github.com/devmonix/miner
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/main.py --config $CONFIG_DIR/default.conf
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$LOG_DIR $CONFIG_DIR /var/lib/miner $BACKUP_DIR
Restart=always
RestartSec=10
SyslogIdentifier=$SERVICE_NAME

# Security settings
NoNewPrivileges=true
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    log_success "Created and enabled systemd service"
}

setup_log_rotation() {
    log_info "Setting up log rotation..."
    
    cat > "/etc/logrotate.d/$SERVICE_NAME" << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
    postrotate
        systemctl reload $SERVICE_NAME || true
    endscript
}

$BACKUP_DIR/*.tar.gz {
    weekly
    missingok
    rotate 12
    compress
    delaycompress
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
}
EOF
    
    log_success "Configured log rotation"
}

setup_monitoring() {
    log_info "Setting up monitoring scripts..."
    
    # Create monitoring script
    cat > "$PROJECT_DIR/scripts/monitor.sh" << 'EOF'
#!/bin/bash

# Monitoring script for the mining system

SERVICE_NAME="miner"
LOG_DIR="/var/log/miner"
CONFIG_DIR="/etc/miner"

# Check if service is running
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "Service $SERVICE_NAME is not running"
    systemctl start "$SERVICE_NAME"
    echo "Started $SERVICE_NAME service"
fi

# Check log size
if [[ -d "$LOG_DIR" ]]; then
    log_size=$(du -sh "$LOG_DIR" | cut -f1)
    echo "Log directory size: $log_size"
fi

# Check system resources
cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
memory_usage=$(free | grep Mem | awk '{printf("%.1f"), $3/$2 * 100.0}')
disk_usage=$(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)

echo "CPU: ${cpu_usage}%, Memory: ${memory_usage}%, Disk: ${disk_usage}%"

# Check for errors in logs
if [[ -f "$LOG_DIR/errors.log" ]]; then
    error_count=$(wc -l < "$LOG_DIR/errors.log")
    if [[ $error_count -gt 0 ]]; then
        echo "Found $error_count errors in log file"
    fi
fi
EOF
    
    chmod +x "$PROJECT_DIR/scripts/monitor.sh"
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "*/5 * * * * $PROJECT_DIR/scripts/monitor.sh >> /var/log/miner/monitor.log 2>&1") | crontab -
    
    log_success "Set up monitoring"
}

create_backup_script() {
    log_info "Creating backup script..."
    
    cat > "$PROJECT_DIR/scripts/backup.sh" << EOF
#!/bin/bash

# Backup script for the mining system

BACKUP_DIR="$BACKUP_DIR"
CONFIG_DIR="$CONFIG_DIR"
LOG_DIR="$LOG_DIR"
PROJECT_DIR="$PROJECT_DIR"
DATE=\$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="\$BACKUP_DIR/miner_backup_\$DATE.tar.gz"

# Create backup
tar -czf "\$BACKUP_FILE" \
    -C "$PROJECT_DIR" \
    config/ \
    src/ \
    requirements.txt \
    main.py \
    README.md \
    -C "$CONFIG_DIR" . \
    -C "$LOG_DIR" .

# Keep only last 7 days of backups
find "\$BACKUP_DIR" -name "miner_backup_*.tar.gz" -mtime +7 -delete

echo "Backup created: \$BACKUP_FILE"
EOF
    
    chmod +x "$PROJECT_DIR/scripts/backup.sh"
    
    # Add to crontab (daily backup at 2 AM)
    (crontab -l 2>/dev/null; echo "0 2 * * * $PROJECT_DIR/scripts/backup.sh >> /var/log/miner/backup.log 2>&1") | crontab -
    
    log_success "Created backup script"
}

run_tests() {
    log_info "Running deployment tests..."
    
    cd "$PROJECT_DIR"
    source venv/bin/activate
    
    # Test imports
    python3 -c "
import sys
sys.path.insert(0, 'src')
try:
    from utils.production_logger import setup_production_logging
    from utils.error_recovery import setup_error_recovery
    from monitoring.resource_monitor import setup_resource_monitor
    print('✓ All production modules imported successfully')
except ImportError as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)
"
    
    # Test configuration
    if [[ -f "$CONFIG_DIR/default.conf" ]]; then
        python3 -c "
import configparser
config = configparser.ConfigParser()
config.read('$CONFIG_DIR/default.conf')
if 'blockchain' in config:
    print('✓ Configuration loaded successfully')
else:
    print('✗ Configuration error')
    exit(1)
"
    fi
    
    log_success "All tests passed"
}

main() {
    log_info "Starting production deployment..."
    log_info "DevMonix Technologies - Advanced Cryptocurrency Mining System"
    echo
    
    check_root
    check_system
    create_user
    create_directories
    install_dependencies
    setup_python_env
    deploy_config
    create_systemd_service
    setup_log_rotation
    setup_monitoring
    create_backup_script
    run_tests
    
    echo
    log_success "Deployment completed successfully!"
    echo
    log_info "Service management:"
    echo "  Start:   sudo systemctl start $SERVICE_NAME"
    echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
    echo "  Status:  sudo systemctl status $SERVICE_NAME"
    echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
    echo
    log_info "Configuration: $CONFIG_DIR/default.conf"
    log_info "Logs: $LOG_DIR/"
    log_info "Backups: $BACKUP_DIR/"
    echo
    log_info "Start the service with: sudo systemctl start $SERVICE_NAME"
}

# Run main function
main "$@"
