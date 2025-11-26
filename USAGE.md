# Advanced Cryptocurrency Mining System - Usage Guide

## Quick Start

### Installation
```bash
# Clone or download the project
cd the-miner

# Run installation script
chmod +x scripts/install.sh
./scripts/install.sh
```

### Basic Usage
```bash
# Start mining with default settings
./scripts/start.sh mining

# Start with custom configuration
./scripts/start.sh mining config/user.conf

# Start web dashboard only
./scripts/start.sh dashboard

# Start mining and dashboard together
./scripts/start.sh all

# Run benchmarks
./scripts/start.sh benchmark

# Stop mining
./scripts/stop.sh
```

## Configuration

### Configuration Files
- `config/default.conf` - Default configuration
- `config/user.conf` - User-specific configuration (created on first run)
- `config/profiles/` - Named configuration profiles

### Key Configuration Options

#### Mining Settings
```ini
[mining]
default_algorithm = sha256      # sha256, ethash, randomx
mining_mode = smart              # solo, pool, smart
cpu_threads = 4                  # Number of CPU threads
intensity = 0.8                  # Mining intensity (0.0-1.0)
```

#### Profit Switching
```ini
[profit_switching]
switch_strategy = threshold      # immediate, gradual, threshold, predictive
profit_update_interval = 60      # Seconds between profit updates
switch_threshold = 0.1           # 10% improvement threshold
min_switch_interval = 300       # Minimum 5 minutes between switches
```

#### Monitoring
```ini
[monitoring]
performance_update_interval = 1.0  # Seconds
optimal_cpu_usage = 80.0           # Target CPU usage %
optimal_temperature = 75.0         # Target temperature °C
max_temperature = 85.0             # Maximum temperature °C
```

## Command Line Options

```bash
python main.py [OPTIONS]

Options:
  -c, --config FILE    Configuration file path
  -d, --dashboard      Start web dashboard
  -v, --verbose        Enable verbose logging
  -b, --benchmark      Run benchmark tests
  --help               Show help message
```

## Web Dashboard

Access the web dashboard at `http://localhost:8080`

### Dashboard Features
- Real-time mining statistics
- System performance monitoring
- Algorithm switching controls
- Optimization recommendations
- Live logs and alerts
- Historical charts and graphs

### Dashboard Controls
- **Start/Stop Mining**: Control mining operations
- **Pause/Resume**: Temporarily pause mining
- **Algorithm Selection**: Manually select mining algorithm
- **Intensity Control**: Adjust mining intensity
- **Configuration**: Modify settings through web interface

## Algorithms

### Supported Algorithms
- **SHA-256**: Bitcoin and SHA-256 based cryptocurrencies
- **Ethash**: Ethereum and Ethash based cryptocurrencies  
- **RandomX**: Monero and RandomX based cryptocurrencies

### Algorithm Performance
- **CPU Mining**: SHA-256, RandomX
- **GPU Mining**: Ethash (requires GPU drivers)
- **ASIC Mining**: SHA-256 (with appropriate hardware)

## Monitoring and Optimization

### System Metrics
- CPU usage and temperature
- Memory usage
- GPU utilization (if available)
- Power consumption
- Hashrate performance
- Share acceptance rate

### Optimization Features
- Automatic intensity adjustment
- Temperature-based throttling
- CPU affinity optimization
- Memory usage optimization
- Power efficiency monitoring

### Alerts and Recommendations
- High temperature warnings
- Low performance alerts
- Hardware optimization suggestions
- Algorithm switching recommendations

## Profit Switching

### Switching Strategies
- **Immediate**: Switch immediately when more profitable algorithm found
- **Gradual**: Consider switching costs and stability
- **Threshold**: Switch only when improvement exceeds threshold
- **Predictive**: Use trend analysis for future profitability

### Profitability Factors
- Current cryptocurrency prices
- Network difficulty
- Hardware efficiency
- Power costs
- Pool fees (if applicable)

## Logging and Reporting

### Log Files
- `logs/miner.log` - Main mining log
- `logs/performance.log` - Performance metrics
- `logs/errors.log` - Error messages only
- `logs/profit.log` - Profit switching events

### Log Levels
- **DEBUG**: Detailed debugging information
- **INFO**: General information and status updates
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical errors

### Reports
- Daily performance summaries
- Weekly profitability reports
- Monthly efficiency analysis
- Custom date range reports

## Troubleshooting

### Common Issues

#### Low Hashrate
1. Check system resources (CPU, memory)
2. Verify algorithm compatibility
3. Adjust intensity settings
4. Check for background processes

#### High Temperature
1. Improve system cooling
2. Reduce mining intensity
3. Check thermal paste
4. Clean dust from components

#### Connection Issues
1. Verify network connectivity
2. Check firewall settings
3. Validate pool configuration
4. Test with different pools

#### Algorithm Switching Problems
1. Check profit update settings
2. Verify market data connectivity
3. Adjust switching thresholds
4. Review switch history

### Debug Mode
```bash
# Enable verbose logging
python main.py --verbose

# Check logs
tail -f logs/miner.log

# Monitor system resources
htop
nvidia-smi  # For NVIDIA GPUs
```

### Performance Tuning
```bash
# Run benchmarks
python main.py --benchmark

# Test different configurations
python main.py --config config/high_performance.conf

# Monitor optimization recommendations
# Check web dashboard > Optimization Recommendations
```

## Advanced Usage

### Configuration Profiles
```bash
# Create profile
python -c "
from src.config.manager import ConfigManager
config = ConfigManager()
config.create_profile('high_performance', 'Maximum performance settings')
"

# Load profile
python -c "
from src.config.manager import ConfigManager
config = ConfigManager()
config.load_profile('high_performance')
"
```

### Custom Algorithms
1. Implement new algorithm class in `src/algorithms/`
2. Register in `src/algorithms/factory.py`
3. Update configuration options
4. Test with benchmarks

### API Integration
The system provides REST API endpoints for external integration:
- `/api/stats` - Current mining statistics
- `/api/performance` - System performance data
- `/api/algorithms` - Algorithm information
- `/api/control` - Mining control commands

## Security Considerations

### System Security
- Run as non-privileged user
- Use firewall for dashboard access
- Regular system updates
- Monitor log files for suspicious activity

### Network Security
- Secure pool connections (SSL/TLS)
- Protect wallet credentials
- Use secure configuration files
- Monitor network traffic

## Maintenance

### Regular Tasks
- Review and rotate log files
- Update cryptocurrency price data sources
- Check for system updates
- Monitor hardware health
- Backup configuration files

### Performance Monitoring
- Daily hashrate tracking
- Weekly efficiency analysis
- Monthly profitability review
- Quarterly hardware assessment

## Support

### Getting Help
- Check logs for error messages
- Review configuration settings
- Run system diagnostics
- Check web dashboard for recommendations

### System Information
```bash
# Generate system report
python -c "
from src.utils.system import create_system_report
print(create_system_report())
"
```

### Contact and Updates
- Check project repository for updates
- Review documentation for new features
- Monitor logs for improvement suggestions
- Report issues with detailed information
