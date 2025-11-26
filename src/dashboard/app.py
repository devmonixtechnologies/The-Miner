"""
Web Dashboard
Real-time monitoring dashboard for the mining system
"""

import json
import time
import random
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from typing import Dict, Any, Optional
import threading

from utils.logger import get_logger

logger = get_logger(__name__)


class MockMiner:
    """Mock miner for standalone dashboard mode"""
    
    def __init__(self):
        self.running = False
        self.start_time = time.time()
        self.stats = {
            "hashrate": random.uniform(800, 1200),
            "accepted_shares": random.randint(100, 500),
            "rejected_shares": random.randint(0, 20),
            "uptime": 0,
            "power_usage": random.uniform(150, 250),
            "temperature": random.uniform(45, 75),
            "efficiency": random.uniform(3, 8)
        }
    
    def get_stats(self):
        """Get mock statistics"""
        self.stats["uptime"] = time.time() - self.start_time
        self.stats["hashrate"] += random.uniform(-10, 10)
        self.stats["power_usage"] += random.uniform(-5, 5)
        self.stats["temperature"] += random.uniform(-1, 1)
        return type('Stats', (), self.stats)()
    
    def start(self):
        self.running = True
        self.start_time = time.time()
    
    def stop(self):
        self.running = False
    
    def pause(self):
        self.running = False
    
    def resume(self):
        self.running = True


class MiningDashboard:
    """Web dashboard for monitoring mining operations"""
    
    def __init__(self, miner_instance: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
        self.miner = miner_instance or MockMiner()
        self.config = config or {}
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'mining_dashboard_secret'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Dashboard state
        self.connected_clients = 0
        self.update_interval = config.get("dashboard_update_interval", 1.0) if config else 1.0
        
        self._setup_routes()
        self._setup_socketio_events()
        
        logger.info("Mining Dashboard initialized")
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main dashboard page"""
            return render_template('dashboard.html')
        
        @self.app.route('/api/stats')
        def get_stats():
            """Get current mining statistics"""
            try:
                stats = self.miner.get_stats()
                return jsonify({
                    "success": True,
                    "data": {
                        "hashrate": stats.hashrate,
                        "accepted_shares": stats.accepted_shares,
                        "rejected_shares": stats.rejected_shares,
                        "uptime": stats.uptime,
                        "power_usage": stats.power_usage,
                        "temperature": stats.temperature,
                        "efficiency": stats.efficiency
                    }
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/performance')
        def get_performance():
            """Get performance monitoring data"""
            try:
                # Mock performance data for standalone mode
                perf_data = {
                    "hashrate": random.uniform(800, 1200),
                    "max_hashrate": 1500,
                    "avg_hashrate": 1000,
                    "hash_attempts": random.randint(10000, 50000),
                    "power_usage": random.uniform(150, 250),
                    "temperature": random.uniform(45, 75),
                    "cpu_percent": random.uniform(60, 90),
                    "memory_percent": random.uniform(40, 70),
                    "gpu_stats": []
                }
                
                system_info = {
                    "platform": "Linux",
                    "processor": "Mock CPU",
                    "cpu_count": 8,
                    "memory_total": 16777216000,
                    "gpu_count": 0
                }
                
                recommendations = []
                if perf_data["temperature"] > 70:
                    recommendations.append("Temperature is getting high, consider reducing intensity")
                if perf_data["cpu_percent"] > 85:
                    recommendations.append("CPU usage is high, close other applications")
                
                return jsonify({
                    "success": True,
                    "data": {
                        "performance": perf_data,
                        "system_info": system_info,
                        "recommendations": recommendations
                    }
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/algorithms')
        def get_algorithms():
            """Get algorithm information and profitability"""
            try:
                # Mock algorithm info for standalone mode
                current_algo = {
                    "name": "SHA-256",
                    "type": "CPU",
                    "performance": {
                        "hashrate": random.uniform(800, 1200),
                        "total_hashes": random.randint(100000, 500000),
                        "uptime": time.time(),
                        "algorithm_type": "CPU"
                    }
                }
                
                profit_summary = {
                    "current_algorithm": "sha256",
                    "last_update": time.time(),
                    "algorithms": {
                        "sha256": {
                            "hashrate": random.uniform(800, 1200),
                            "power_usage": random.uniform(150, 200),
                            "profit_per_hour": random.uniform(0.5, 1.5),
                            "efficiency": random.uniform(4, 8)
                        },
                        "ethash": {
                            "hashrate": random.uniform(200000, 400000),
                            "power_usage": random.uniform(200, 300),
                            "profit_per_hour": random.uniform(0.8, 2.0),
                            "efficiency": random.uniform(800, 1200)
                        },
                        "randomx": {
                            "hashrate": random.uniform(500, 800),
                            "power_usage": random.uniform(120, 180),
                            "profit_per_hour": random.uniform(0.3, 0.8),
                            "efficiency": random.uniform(3, 6)
                        }
                    }
                }
                
                switch_history = [
                    {"timestamp": time.time() - 3600, "from": "ethash", "to": "sha256"},
                    {"timestamp": time.time() - 7200, "from": "randomx", "to": "ethash"}
                ]
                
                return jsonify({
                    "success": True,
                    "data": {
                        "current_algorithm": current_algo,
                        "profitability": profit_summary,
                        "switch_history": switch_history
                    }
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/config')
        def get_config():
            """Get current configuration"""
            try:
                config_dict = self.miner.config if hasattr(self.miner, 'config') else {}
                return jsonify({
                    "success": True,
                    "data": config_dict
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/control', methods=['GET', 'POST'])
        def control_miner():
            """Control miner operations"""
            try:
                if request.method == 'POST':
                    action = request.json.get('action')
                else:
                    action = request.args.get('action')
                
                if not self.miner:
                    return jsonify({
                        "success": False, 
                        "error": "No miner instance available in standalone mode"
                    }), 503
                
                if action == 'start':
                    self.miner.start()
                elif action == 'stop':
                    self.miner.stop()
                elif action == 'pause':
                    self.miner.pause()
                elif action == 'resume':
                    self.miner.resume()
                else:
                    return jsonify({"success": False, "error": "Invalid action"}), 400
                
                return jsonify({"success": True, "message": f"Action {action} executed"})
                
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/logs')
        def get_logs():
            """Get recent logs"""
            try:
                # In a real implementation, this would read from log files
                logs = [
                    {"timestamp": time.time(), "level": "INFO", "message": "Mining operation running"},
                    {"timestamp": time.time() - 60, "level": "INFO", "message": "Algorithm switched to SHA-256"},
                    {"timestamp": time.time() - 120, "level": "WARNING", "message": "Temperature above optimal"}
                ]
                
                return jsonify({
                    "success": True,
                    "data": logs
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
    
    def _setup_socketio_events(self):
        """Setup SocketIO events for real-time updates"""
        
        @self.socketio.on('connect')
        def handle_connect():
            self.connected_clients += 1
            logger.info(f"Dashboard client connected. Total: {self.connected_clients}")
            emit('status', {'message': 'Connected to mining dashboard'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.connected_clients -= 1
            logger.info(f"Dashboard client disconnected. Total: {self.connected_clients}")
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """Handle subscription to specific data streams"""
            stream = data.get('stream', 'all')
            logger.info(f"Client subscribed to {stream} stream")
            emit('subscribed', {'stream': stream})
    
    def start_broadcast_thread(self):
        """Start thread for broadcasting real-time updates"""
        def broadcast_loop():
            while True:
                try:
                    if self.connected_clients > 0:
                        # Broadcast mining stats
                        stats = self.miner.get_stats()
                        self.socketio.emit('stats_update', {
                            'hashrate': stats.hashrate,
                            'accepted_shares': stats.accepted_shares,
                            'rejected_shares': stats.rejected_shares,
                            'uptime': stats.uptime,
                            'power_usage': stats.power_usage,
                            'temperature': stats.temperature,
                            'efficiency': stats.efficiency
                        })
                        
                        # Broadcast performance data
                        perf_data = self.miner.performance_monitor.get_current_stats()
                        self.socketio.emit('performance_update', perf_data)
                        
                        # Broadcast algorithm info
                        algo_info = self.miner.get_algorithm_info()
                        if algo_info:
                            self.socketio.emit('algorithm_update', algo_info)
                    
                    time.sleep(self.update_interval)
                    
                except Exception as e:
                    logger.error(f"Error broadcasting updates: {e}")
                    time.sleep(5)
        
        broadcast_thread = threading.Thread(target=broadcast_loop, daemon=True)
        broadcast_thread.start()
    
    def run(self, host='0.0.0.0', port=8080, debug=False):
        """Start the dashboard server"""
        logger.info(f"Starting dashboard on {host}:{port}")
        
        # Start broadcast thread
        self.start_broadcast_thread()
        
        # Run Flask app
        self.socketio.run(self.app, host=host, port=port, debug=debug)


def start_dashboard(miner_instance=None, config: Optional[Dict[str, Any]] = None):
    """Start the mining dashboard"""
    dashboard = MiningDashboard(miner_instance, config)
    dashboard.run()


# Create HTML template for the dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Advanced Mining Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .status-indicator { 
            display: inline-block; 
            width: 12px; height: 12px; 
            border-radius: 50%; 
            margin-left: 10px;
            background: #4CAF50;
            animation: pulse 2s infinite;
        }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        
        .dashboard-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px;
        }
        
        .card { 
            background: rgba(255, 255, 255, 0.1); 
            backdrop-filter: blur(10px);
            border-radius: 15px; 
            padding: 20px; 
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease;
        }
        .card:hover { transform: translateY(-5px); }
        
        .card h3 { margin-bottom: 15px; color: #64B5F6; }
        .metric { 
            display: flex; 
            justify-content: space-between; 
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        .metric:last-child { border-bottom: none; }
        .metric-value { font-weight: bold; color: #81C784; }
        
        .chart-container { 
            background: rgba(255, 255, 255, 0.1); 
            border-radius: 15px; 
            padding: 20px; 
            margin-bottom: 20px;
            height: 300px;
        }
        
        .controls { 
            display: flex; 
            gap: 10px; 
            justify-content: center; 
            margin: 20px 0;
        }
        
        .btn { 
            padding: 10px 20px; 
            border: none; 
            border-radius: 25px; 
            cursor: pointer; 
            font-weight: bold;
            transition: all 0.3s ease;
        }
        .btn-start { background: #4CAF50; color: white; }
        .btn-stop { background: #f44336; color: white; }
        .btn-pause { background: #FF9800; color: white; }
        .btn:hover { transform: scale(1.05); opacity: 0.9; }
        
        .algorithm-info { 
            background: rgba(255, 255, 255, 0.05); 
            border-radius: 10px; 
            padding: 15px; 
            margin: 10px 0;
        }
        
        .recommendations { 
            background: rgba(255, 152, 0, 0.1); 
            border-left: 4px solid #FF9800; 
            padding: 15px; 
            margin: 10px 0;
        }
        
        .logs { 
            background: rgba(0, 0, 0, 0.3); 
            border-radius: 10px; 
            padding: 15px; 
            height: 200px; 
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        
        .log-entry { margin: 5px 0; }
        .log-info { color: #4CAF50; }
        .log-warning { color: #FF9800; }
        .log-error { color: #f44336; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Advanced Mining Dashboard 
                <span class="status-indicator"></span>
            </h1>
            <p>Real-time monitoring and control</p>
        </div>
        
        <div class="controls">
            <button class="btn btn-start" onclick="controlMiner('start')">Start Mining</button>
            <button class="btn btn-stop" onclick="controlMiner('stop')">Stop Mining</button>
            <button class="btn btn-pause" onclick="controlMiner('pause')">Pause</button>
            <button class="btn btn-pause" onclick="controlMiner('resume')">Resume</button>
        </div>
        
        <div class="dashboard-grid">
            <div class="card">
                <h3>Mining Statistics</h3>
                <div class="metric">
                    <span>Hashrate</span>
                    <span class="metric-value" id="hashrate">0 H/s</span>
                </div>
                <div class="metric">
                    <span>Accepted Shares</span>
                    <span class="metric-value" id="accepted">0</span>
                </div>
                <div class="metric">
                    <span>Rejected Shares</span>
                    <span class="metric-value" id="rejected">0</span>
                </div>
                <div class="metric">
                    <span>Uptime</span>
                    <span class="metric-value" id="uptime">0s</span>
                </div>
                <div class="metric">
                    <span>Efficiency</span>
                    <span class="metric-value" id="efficiency">0 H/W</span>
                </div>
            </div>
            
            <div class="card">
                <h3>System Performance</h3>
                <div class="metric">
                    <span>CPU Usage</span>
                    <span class="metric-value" id="cpu">0%</span>
                </div>
                <div class="metric">
                    <span>Memory Usage</span>
                    <span class="metric-value" id="memory">0%</span>
                </div>
                <div class="metric">
                    <span>Temperature</span>
                    <span class="metric-value" id="temperature">0°C</span>
                </div>
                <div class="metric">
                    <span>Power Usage</span>
                    <span class="metric-value" id="power">0W</span>
                </div>
                <div class="metric">
                    <span>GPU Load</span>
                    <span class="metric-value" id="gpu">0%</span>
                </div>
            </div>
            
            <div class="card">
                <h3>Algorithm Information</h3>
                <div id="algorithm-info">
                    <div class="algorithm-info">
                        <strong>Current Algorithm:</strong> <span id="current-algo">Loading...</span>
                    </div>
                    <div class="algorithm-info">
                        <strong>Algorithm Type:</strong> <span id="algo-type">-</span>
                    </div>
                    <div class="algorithm-info">
                        <strong>Performance:</strong> <span id="algo-performance">-</span>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="chart-container">
            <canvas id="hashrateChart"></canvas>
        </div>
        
        <div class="card">
            <h3>Optimization Recommendations</h3>
            <div id="recommendations">
                <p>Monitoring system for recommendations...</p>
            </div>
        </div>
        
        <div class="card">
            <h3>Recent Logs</h3>
            <div class="logs" id="logs">
                <div class="log-entry log-info">Dashboard initialized</div>
            </div>
        </div>
    </div>
    
    <script>
        // Socket.IO connection
        const socket = io();
        
        // Chart setup
        const ctx = document.getElementById('hashrateChart').getContext('2d');
        const hashrateChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Hashrate (H/s)',
                    data: [],
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
        
        // Socket event handlers
        socket.on('connect', function() {
            addLog('Connected to mining server', 'info');
        });
        
        socket.on('stats_update', function(data) {
            updateStats(data);
        });
        
        socket.on('performance_update', function(data) {
            updatePerformance(data);
        });
        
        socket.on('algorithm_update', function(data) {
            updateAlgorithm(data);
        });
        
        // Update functions
        function updateStats(data) {
            document.getElementById('hashrate').textContent = formatHashrate(data.hashrate);
            document.getElementById('accepted').textContent = data.accepted_shares;
            document.getElementById('rejected').textContent = data.rejected_shares;
            document.getElementById('uptime').textContent = formatUptime(data.uptime);
            document.getElementById('efficiency').textContent = formatHashrate(data.efficiency) + '/W';
            
            // Update chart
            const now = new Date().toLocaleTimeString();
            hashrateChart.data.labels.push(now);
            hashrateChart.data.datasets[0].data.push(data.hashrate);
            
            // Keep only last 20 data points
            if (hashrateChart.data.labels.length > 20) {
                hashrateChart.data.labels.shift();
                hashrateChart.data.datasets[0].data.shift();
            }
            
            hashrateChart.update();
        }
        
        function updatePerformance(data) {
            document.getElementById('cpu').textContent = data.cpu_percent.toFixed(1) + '%';
            document.getElementById('memory').textContent = data.memory_percent.toFixed(1) + '%';
            document.getElementById('temperature').textContent = data.temperature.toFixed(1) + '°C';
            document.getElementById('power').textContent = data.power_usage.toFixed(1) + 'W';
            
            if (data.gpu_stats && data.gpu_stats.length > 0) {
                document.getElementById('gpu').textContent = data.gpu_stats[0].load.toFixed(1) + '%';
            }
        }
        
        function updateAlgorithm(data) {
            document.getElementById('current-algo').textContent = data.name || 'Unknown';
            document.getElementById('algo-type').textContent = data.type || 'Unknown';
            
            if (data.performance) {
                const perf = data.performance;
                document.getElementById('algo-performance').textContent = 
                    formatHashrate(perf.hashrate) + ' (' + perf.algorithm_type + ')';
            }
        }
        
        // Control functions
        function controlMiner(action) {
            fetch('/api/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: action })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    addLog(data.message, 'info');
                } else {
                    addLog('Error: ' + data.error, 'error');
                }
            })
            .catch(error => {
                addLog('Network error: ' + error.message, 'error');
            });
        }
        
        // Utility functions
        function formatHashrate(value) {
            if (value >= 1000000000) return (value / 1000000000).toFixed(2) + ' GH/s';
            if (value >= 1000000) return (value / 1000000).toFixed(2) + ' MH/s';
            if (value >= 1000) return (value / 1000).toFixed(2) + ' KH/s';
            return value.toFixed(2) + ' H/s';
        }
        
        function formatUptime(seconds) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            return `${hours}h ${minutes}m ${secs}s`;
        }
        
        function addLog(message, level = 'info') {
            const logs = document.getElementById('logs');
            const entry = document.createElement('div');
            entry.className = `log-entry log-${level}`;
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            logs.appendChild(entry);
            logs.scrollTop = logs.scrollHeight;
            
            // Keep only last 50 logs
            while (logs.children.length > 50) {
                logs.removeChild(logs.firstChild);
            }
        }
        
        // Load initial data
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateStats(data.data);
                }
            });
            
        fetch('/api/performance')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updatePerformance(data.data.performance);
                    updateRecommendations(data.data.recommendations);
                }
            });
            
        fetch('/api/algorithms')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateAlgorithm(data.data.current_algorithm);
                }
            });
        
        function updateRecommendations(recommendations) {
            const container = document.getElementById('recommendations');
            if (recommendations.length === 0) {
                container.innerHTML = '<p>System is running optimally.</p>';
            } else {
                container.innerHTML = recommendations.map(rec => 
                    `<div class="recommendations">• ${rec}</div>`
                ).join('');
            }
        }
    </script>
</body>
</html>
"""


def create_template_file():
    """Create the dashboard HTML template file"""
    import os
    template_dir = "src/dashboard/templates"
    os.makedirs(template_dir, exist_ok=True)
    
    with open(os.path.join(template_dir, "dashboard.html"), "w") as f:
        f.write(DASHBOARD_HTML)
