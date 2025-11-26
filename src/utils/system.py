"""
System Utilities
System checks, optimizations and utilities
"""

import os
import sys
import platform
import subprocess
import psutil
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

from .logger import get_logger

logger = get_logger(__name__)


def check_system_requirements() -> bool:
    """Check if system meets minimum requirements"""
    logger.info("Checking system requirements...")
    
    requirements_met = True
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        logger.error(f"Python 3.8+ required. Found: {python_version.major}.{python_version.minor}")
        requirements_met = False
    else:
        logger.info(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro} ✓")
    
    # Check operating system
    if platform.system() != "Linux":
        logger.warning("This system is optimized for Linux. Other OS may have limited functionality.")
    
    # Check memory
    memory = psutil.virtual_memory()
    if memory.total < 2 * 1024 * 1024 * 1024:  # 2GB minimum
        logger.error(f"Insufficient memory: {memory.total / (1024**3):.1f} GB (minimum: 2 GB)")
        requirements_met = False
    else:
        logger.info(f"Memory: {memory.total / (1024**3):.1f} GB ✓")
    
    # Check disk space
    disk = psutil.disk_usage('/')
    if disk.free < 1 * 1024 * 1024 * 1024:  # 1GB minimum free space
        logger.error(f"Insufficient disk space: {disk.free / (1024**3):.1f} GB free (minimum: 1 GB)")
        requirements_met = False
    else:
        logger.info(f"Disk space: {disk.free / (1024**3):.1f} GB free ✓")
    
    # Check CPU
    cpu_count = psutil.cpu_count()
    if cpu_count < 2:
        logger.warning(f"Low CPU count: {cpu_count} cores (recommended: 4+ cores)")
    else:
        logger.info(f"CPU: {cpu_count} cores ✓")
    
    # Check for GPU support (optional)
    gpu_info = detect_gpu()
    if gpu_info:
        logger.info(f"GPU detected: {gpu_info.get('name', 'Unknown')} ✓")
    else:
        logger.info("No GPU detected - CPU mining only")
    
    # Check for required system tools
    required_tools = ['git', 'curl', 'wget']
    missing_tools = []
    
    for tool in required_tools:
        if not check_command_exists(tool):
            missing_tools.append(tool)
    
    if missing_tools:
        logger.warning(f"Missing recommended tools: {', '.join(missing_tools)}")
    
    # Check permissions
    if not check_write_permissions():
        logger.error("Insufficient write permissions")
        requirements_met = False
    
    if requirements_met:
        logger.info("System requirements met ✓")
    else:
        logger.error("System requirements not met")
    
    return requirements_met


def check_command_exists(command: str) -> bool:
    """Check if a command exists in the system"""
    try:
        subprocess.run(['which', command], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_write_permissions() -> bool:
    """Check if we have write permissions in current directory"""
    try:
        test_file = Path(".__test_write_permission__")
        test_file.write_text("test")
        test_file.unlink()
        return True
    except Exception:
        return False


def detect_gpu() -> Optional[Dict[str, Any]]:
    """Detect GPU information"""
    gpu_info = None
    
    # Try to detect NVIDIA GPU
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', 
                               '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            if lines:
                name, memory = lines[0].split(', ')
                gpu_info = {
                    'type': 'NVIDIA',
                    'name': name.strip(),
                    'memory_mb': int(memory.strip()),
                    'cuda_available': True
                }
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Try to detect AMD GPU
    if not gpu_info:
        try:
            result = subprocess.run(['lspci'], capture_output=True, text=True)
            if 'AMD' in result.stdout or 'Radeon' in result.stdout:
                gpu_info = {
                    'type': 'AMD',
                    'name': 'AMD GPU',
                    'memory_mb': 0,
                    'opencl_available': True
                }
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    
    return gpu_info


def optimize_system() -> Dict[str, Any]:
    """Apply system optimizations for mining"""
    optimizations = {}
    
    logger.info("Applying system optimizations...")
    
    # Set CPU governor to performance
    if check_command_exists('cpufreq-set'):
        try:
            subprocess.run(['cpufreq-set', '-g', 'performance'], check=True)
            optimizations['cpu_governor'] = 'performance'
            logger.info("CPU governor set to performance")
        except subprocess.CalledProcessError:
            logger.warning("Could not set CPU governor")
    
    # Disable swap (if recommended)
    try:
        with open('/proc/swaps', 'r') as f:
            swap_content = f.read().strip()
        
        if swap_content and not swap_content.endswith('Filename\tType\tSize\tUsed\tPriority'):
            # Swap is enabled, consider disabling for performance
            logger.info("Swap is enabled - consider disabling for better performance")
            optimizations['swap_status'] = 'enabled'
        else:
            optimizations['swap_status'] = 'disabled'
    except Exception:
        pass
    
    # Check and set process priority
    try:
        current_process = psutil.Process()
        current_process.nice(psutil.HIGH_PRIORITY_CLASS if platform.system() == 'Windows' else -10)
        optimizations['process_priority'] = 'high'
        logger.info("Process priority set to high")
    except Exception:
        logger.warning("Could not set process priority")
    
    # Network optimization
    network_optimizations = optimize_network()
    optimizations.update(network_optimizations)
    
    logger.info(f"Applied {len(optimizations)} optimizations")
    return optimizations


def optimize_network() -> Dict[str, Any]:
    """Apply network optimizations"""
    optimizations = {}
    
    # Check network interface
    try:
        result = subprocess.run(['ip', 'route', 'show', 'default'], 
                              capture_output=True, text=True)
        if result.stdout:
            interface = result.stdout.split()[4]
            optimizations['network_interface'] = interface
            logger.info(f"Network interface: {interface}")
    except Exception:
        pass
    
    # Check DNS settings
    try:
        with open('/etc/resolv.conf', 'r') as f:
            dns_servers = [line.strip() for line in f if line.startswith('nameserver')]
        optimizations['dns_servers'] = len(dns_servers)
    except Exception:
        pass
    
    return optimizations


def get_system_metrics() -> Dict[str, Any]:
    """Get comprehensive system metrics"""
    metrics = {}
    
    # CPU metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_freq = psutil.cpu_freq()
    metrics['cpu'] = {
        'percent': cpu_percent,
        'count': psutil.cpu_count(),
        'freq_current': cpu_freq.current if cpu_freq else 0,
        'freq_min': cpu_freq.min if cpu_freq else 0,
        'freq_max': cpu_freq.max if cpu_freq else 0
    }
    
    # Memory metrics
    memory = psutil.virtual_memory()
    metrics['memory'] = {
        'total': memory.total,
        'available': memory.available,
        'percent': memory.percent,
        'used': memory.used,
        'free': memory.free
    }
    
    # Disk metrics
    disk = psutil.disk_usage('/')
    metrics['disk'] = {
        'total': disk.total,
        'used': disk.used,
        'free': disk.free,
        'percent': (disk.used / disk.total) * 100
    }
    
    # Network metrics
    network = psutil.net_io_counters()
    metrics['network'] = {
        'bytes_sent': network.bytes_sent,
        'bytes_recv': network.bytes_recv,
        'packets_sent': network.packets_sent,
        'packets_recv': network.packets_recv
    }
    
    # GPU metrics (if available)
    gpu_info = detect_gpu()
    if gpu_info:
        metrics['gpu'] = gpu_info
    
    # Temperature (if available)
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            temperatures = {}
            for name, entries in temps.items():
                temperatures[name] = [{'label': entry.label or 'temp', 
                                      'current': entry.current} for entry in entries]
            metrics['temperatures'] = temperatures
    except Exception:
        pass
    
    return metrics


def benchmark_system() -> Dict[str, Any]:
    """Run system benchmarks"""
    logger.info("Running system benchmarks...")
    
    benchmarks = {}
    
    # CPU benchmark (simple hash calculation)
    import time
    import hashlib
    
    start_time = time.time()
    for i in range(100000):
        hashlib.sha256(f"benchmark_{i}".encode()).hexdigest()
    cpu_time = time.time() - start_time
    benchmarks['cpu_hashrate'] = 100000 / cpu_time
    
    # Memory benchmark
    start_time = time.time()
    test_data = bytearray(1024 * 1024)  # 1MB
    for i in range(100):
        test_data[:] = os.urandom(1024 * 1024)
    memory_time = time.time() - start_time
    benchmarks['memory_bandwidth'] = (100 * 1024 * 1024) / memory_time / (1024 * 1024)  # MB/s
    
    # Disk benchmark
    test_file = Path(".__disk_benchmark__")
    try:
        start_time = time.time()
        test_data = os.urandom(1024 * 1024)  # 1MB
        with open(test_file, 'wb') as f:
            for i in range(10):
                f.write(test_data)
        write_time = time.time() - start_time
        
        start_time = time.time()
        with open(test_file, 'rb') as f:
            while f.read(1024 * 1024):
                pass
        read_time = time.time() - start_time
        
        benchmarks['disk_write'] = (10 * 1024 * 1024) / write_time / (1024 * 1024)  # MB/s
        benchmarks['disk_read'] = (10 * 1024 * 1024) / read_time / (1024 * 1024)  # MB/s
        
        test_file.unlink()
    except Exception as e:
        logger.error(f"Disk benchmark failed: {e}")
    
    logger.info("Benchmarks completed")
    return benchmarks


def cleanup_system():
    """Clean up system resources"""
    logger.info("Cleaning up system resources...")
    
    # Clean temporary files
    temp_patterns = [
        ".__test_write_permission__",
        ".__disk_benchmark__",
        "*.tmp",
        "*.temp"
    ]
    
    for pattern in temp_patterns:
        try:
            for file in Path('.').glob(pattern):
                if file.is_file():
                    file.unlink()
        except Exception:
            pass
    
    # Reset CPU governor
    if check_command_exists('cpufreq-set'):
        try:
            subprocess.run(['cpufreq-set', '-g', 'ondemand'], check=True)
            logger.info("CPU governor reset to ondemand")
        except subprocess.CalledProcessError:
            pass
    
    logger.info("System cleanup completed")


def create_system_report() -> str:
    """Generate comprehensive system report"""
    report = []
    report.append("=" * 60)
    report.append("SYSTEM REPORT")
    report.append("=" * 60)
    
    # Basic system info
    report.append(f"Platform: {platform.platform()}")
    report.append(f"Architecture: {platform.architecture()[0]}")
    report.append(f"Processor: {platform.processor()}")
    report.append(f"Python: {platform.python_version()}")
    report.append("")
    
    # System metrics
    metrics = get_system_metrics()
    
    report.append("CPU:")
    cpu = metrics['cpu']
    report.append(f"  Cores: {cpu['count']}")
    report.append(f"  Usage: {cpu['percent']:.1f}%")
    report.append(f"  Frequency: {cpu['freq_current']:.0f} MHz")
    report.append("")
    
    report.append("Memory:")
    memory = metrics['memory']
    report.append(f"  Total: {memory['total'] / (1024**3):.1f} GB")
    report.append(f"  Used: {memory['used'] / (1024**3):.1f} GB ({memory['percent']:.1f}%)")
    report.append("")
    
    report.append("Disk:")
    disk = metrics['disk']
    report.append(f"  Total: {disk['total'] / (1024**3):.1f} GB")
    report.append(f"  Used: {disk['used'] / (1024**3):.1f} GB ({disk['percent']:.1f}%)")
    report.append("")
    
    if 'gpu' in metrics:
        report.append("GPU:")
        gpu = metrics['gpu']
        report.append(f"  Type: {gpu['type']}")
        report.append(f"  Name: {gpu['name']}")
        if gpu.get('memory_mb'):
            report.append(f"  Memory: {gpu['memory_mb']} MB")
        report.append("")
    
    # Benchmarks
    benchmarks = benchmark_system()
    report.append("Benchmarks:")
    report.append(f"  CPU Hash Rate: {benchmarks['cpu_hashrate']:.0f} H/s")
    report.append(f"  Memory Bandwidth: {benchmarks['memory_bandwidth']:.1f} MB/s")
    if 'disk_write' in benchmarks:
        report.append(f"  Disk Write: {benchmarks['disk_write']:.1f} MB/s")
        report.append(f"  Disk Read: {benchmarks['disk_read']:.1f} MB/s")
    report.append("")
    
    report.append("=" * 60)
    
    return "\n".join(report)
