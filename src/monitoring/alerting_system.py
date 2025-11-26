"""
Comprehensive Monitoring and Alerting System
Production-grade monitoring with intelligent alerting and notifications
"""

import time
import threading
import json
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import requests
import websocket
from datetime import datetime, timedelta

from utils.production_logger import get_production_logger
from monitoring.resource_monitor import get_resource_monitor


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    id: str
    title: str
    message: str
    severity: AlertSeverity
    status: AlertStatus
    component: str
    timestamp: float
    resolved_timestamp: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    suppression_duration: Optional[float] = None


class AlertRule:
    """Base class for alert rules"""
    
    def __init__(self, name: str, severity: AlertSeverity, cooldown: float = 300.0):
        self.name = name
        self.severity = severity
        self.cooldown = cooldown
        self.last_triggered = 0.0
        self.trigger_count = 0
        self.suppressed_until = 0.0
    
    def should_trigger(self, metrics: Dict[str, Any]) -> bool:
        """Check if alert should be triggered"""
        current_time = time.time()
        
        # Check cooldown
        if current_time - self.last_triggered < self.cooldown:
            return False
        
        # Check suppression
        if current_time < self.suppressed_until:
            return False
        
        return self._evaluate_condition(metrics)
    
    def _evaluate_condition(self, metrics: Dict[str, Any]) -> bool:
        """Override this method to implement alert condition"""
        raise NotImplementedError
    
    def trigger(self) -> Alert:
        """Trigger alert"""
        self.last_triggered = time.time()
        self.trigger_count += 1
        
        return Alert(
            id=f"{self.name}_{int(self.last_triggered)}",
            title=self.name,
            message=self._get_message(),
            severity=self.severity,
            status=AlertStatus.ACTIVE,
            component=self._get_component(),
            timestamp=self.last_triggered,
            metadata=self._get_metadata()
        )
    
    def _get_message(self) -> str:
        """Get alert message"""
        return f"Alert: {self.name}"
    
    def _get_component(self) -> str:
        """Get component name"""
        return "system"
    
    def _get_metadata(self) -> Dict[str, Any]:
        """Get alert metadata"""
        return {
            "rule": self.name,
            "trigger_count": self.trigger_count
        }
    
    def suppress(self, duration: float):
        """Suppress alerts for specified duration"""
        self.suppressed_until = time.time() + duration


class CPUAlertRule(AlertRule):
    """CPU usage alert rule"""
    
    def __init__(self, threshold: float = 90.0, duration: float = 300.0):
        super().__init__("High CPU Usage", AlertSeverity.WARNING, cooldown=300.0)
        self.threshold = threshold
        self.duration = duration
    
    def _evaluate_condition(self, metrics: Dict[str, Any]) -> bool:
        current_metrics = metrics.get("current_metrics")
        if not current_metrics:
            return False
        
        return current_metrics.get("cpu_percent", 0) > self.threshold
    
    def _get_message(self) -> str:
        return f"CPU usage is above {self.threshold}%"
    
    def _get_component(self) -> str:
        return "cpu"
    
    def _get_metadata(self) -> Dict[str, Any]:
        metadata = super()._get_metadata()
        metadata.update({
            "threshold": self.threshold,
            "duration": self.duration
        })
        return metadata


class MemoryAlertRule(AlertRule):
    """Memory usage alert rule"""
    
    def __init__(self, threshold: float = 85.0, duration: float = 300.0):
        super().__init__("High Memory Usage", AlertSeverity.WARNING, cooldown=300.0)
        self.threshold = threshold
        self.duration = duration
    
    def _evaluate_condition(self, metrics: Dict[str, Any]) -> bool:
        current_metrics = metrics.get("current_metrics")
        if not current_metrics:
            return False
        
        return current_metrics.get("memory_percent", 0) > self.threshold
    
    def _get_message(self) -> str:
        return f"Memory usage is above {self.threshold}%"
    
    def _get_component(self) -> str:
        return "memory"
    
    def _get_metadata(self) -> Dict[str, Any]:
        metadata = super()._get_metadata()
        metadata.update({
            "threshold": self.threshold,
            "duration": self.duration
        })
        return metadata


class DiskAlertRule(AlertRule):
    """Disk space alert rule"""
    
    def __init__(self, threshold: float = 90.0):
        super().__init__("Low Disk Space", AlertSeverity.ERROR, cooldown=600.0)
        self.threshold = threshold
    
    def _evaluate_condition(self, metrics: Dict[str, Any]) -> bool:
        current_metrics = metrics.get("current_metrics")
        if not current_metrics:
            return False
        
        return current_metrics.get("disk_percent", 0) > self.threshold
    
    def _get_message(self) -> str:
        return f"Disk usage is above {self.threshold}%"
    
    def _get_component(self) -> str:
        return "disk"
    
    def _get_metadata(self) -> Dict[str, Any]:
        metadata = super()._get_metadata()
        metadata.update({
            "threshold": self.threshold
        })
        return metadata


class TemperatureAlertRule(AlertRule):
    """Temperature alert rule"""
    
    def __init__(self, threshold: float = 75.0):
        super().__init__("High Temperature", AlertSeverity.WARNING, cooldown=300.0)
        self.threshold = threshold
    
    def _evaluate_condition(self, metrics: Dict[str, Any]) -> bool:
        current_metrics = metrics.get("current_metrics")
        if not current_metrics:
            return False
        
        temp = current_metrics.get("temperature", 0)
        return temp > 0 and temp > self.threshold
    
    def _get_message(self) -> str:
        return f"System temperature is above {self.threshold}°C"
    
    def _get_component(self) -> str:
        return "temperature"
    
    def _get_metadata(self) -> Dict[str, Any]:
        metadata = super()._get_metadata()
        metadata.update({
            "threshold": self.threshold
        })
        return metadata


class MiningAlertRule(AlertRule):
    """Mining-specific alert rule"""
    
    def __init__(self):
        super().__init__("Mining Issues", AlertSeverity.ERROR, cooldown=600.0)
    
    def _evaluate_condition(self, metrics: Dict[str, Any]) -> bool:
        # Check for mining-specific issues
        return (metrics.get("mining_stopped", False) or
                metrics.get("wallet_disconnected", False) or
                metrics.get("pool_connection_lost", False))
    
    def _get_message(self) -> str:
        return "Mining operation has issues"
    
    def _get_component(self) -> str:
        return "mining"


class AlertChannel:
    """Base class for alert notification channels"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", True)
    
    def send_alert(self, alert: Alert) -> bool:
        """Send alert notification"""
        if not self.enabled:
            return False
        
        try:
            return self._send_alert(alert)
        except Exception as e:
            logger = get_production_logger()
            if logger:
                logger.log_error(f"Failed to send alert via {self.name}: {e}", component="alerting")
            return False
    
    def _send_alert(self, alert: Alert) -> bool:
        """Override this method to implement alert sending"""
        raise NotImplementedError


class EmailAlertChannel(AlertChannel):
    """Email alert notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("email", config)
        self.smtp_server = config.get("smtp_server", "localhost")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.from_email = config.get("from_email", "")
        self.to_emails = config.get("to_emails", [])
        self.use_tls = config.get("use_tls", True)
    
    def _send_alert(self, alert: Alert) -> bool:
        """Send alert via email"""
        if not self.to_emails:
            return False
        
        # Create message
        msg = MimeMultipart()
        msg['From'] = self.from_email
        msg['To'] = ', '.join(self.to_emails)
        msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
        
        # Email body
        body = f"""
Alert: {alert.title}
Severity: {alert.severity.value}
Component: {alert.component}
Time: {datetime.fromtimestamp(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S')}

Message:
{alert.message}

Metadata:
{json.dumps(alert.metadata or {}, indent=2)}
"""
        
        msg.attach(MimeText(body, 'plain'))
        
        # Send email
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            
            server.send_message(msg)
            server.quit()
            return True
            
        except Exception as e:
            raise e


class WebhookAlertChannel(AlertChannel):
    """Webhook alert notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("webhook", config)
        self.webhook_url = config.get("webhook_url", "")
        self.headers = config.get("headers", {})
        self.timeout = config.get("timeout", 10)
    
    def _send_alert(self, alert: Alert) -> bool:
        """Send alert via webhook"""
        if not self.webhook_url:
            return False
        
        payload = {
            "alert_id": alert.id,
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "component": alert.component,
            "timestamp": alert.timestamp,
            "metadata": alert.metadata or {}
        }
        
        headers = {
            "Content-Type": "application/json",
            **self.headers
        }
        
        response = requests.post(
            self.webhook_url,
            json=payload,
            headers=headers,
            timeout=self.timeout
        )
        
        return response.status_code == 200


class SlackAlertChannel(AlertChannel):
    """Slack alert notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("slack", config)
        self.webhook_url = config.get("webhook_url", "")
        self.channel = config.get("channel", "#alerts")
        self.username = config.get("username", "Miner Alert")
    
    def _send_alert(self, alert: Alert) -> bool:
        """Send alert to Slack"""
        if not self.webhook_url:
            return False
        
        # Color based on severity
        color_map = {
            AlertSeverity.INFO: "good",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.ERROR: "danger",
            AlertSeverity.CRITICAL: "#ff0000"
        }
        
        payload = {
            "channel": self.channel,
            "username": self.username,
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "warning"),
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Component",
                            "value": alert.component,
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": datetime.fromtimestamp(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                            "short": True
                        }
                    ],
                    "footer": "Mining System",
                    "ts": alert.timestamp
                }
            ]
        }
        
        response = requests.post(self.webhook_url, json=payload, timeout=10)
        return response.status_code == 200


class AlertingSystem:
    """Production-grade alerting and monitoring system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_production_logger()
        self.resource_monitor = get_resource_monitor()
        
        # Alert rules
        self.alert_rules: List[AlertRule] = []
        self._setup_default_rules()
        
        # Alert channels
        self.alert_channels: List[AlertChannel] = []
        self._setup_channels()
        
        # Alert storage
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history = 1000
        
        # Monitoring thread
        self.monitoring_thread = None
        self.running = False
        self.check_interval = 30.0  # Check every 30 seconds
        
        # Statistics
        self.total_alerts = 0
        self.alerts_by_severity = {severity: 0 for severity in AlertSeverity}
        self.alerts_by_component = {}
        
        if self.logger:
            self.logger.log_info("Alerting system initialized", component="alerting")
    
    def _setup_default_rules(self):
        """Setup default alert rules"""
        # CPU alerts
        cpu_warning = CPUAlertRule(threshold=85.0)
        cpu_critical = CPUAlertRule(threshold=95.0)
        cpu_critical.severity = AlertSeverity.CRITICAL
        
        # Memory alerts
        memory_warning = MemoryAlertRule(threshold=80.0)
        memory_critical = MemoryAlertRule(threshold=90.0)
        memory_critical.severity = AlertSeverity.CRITICAL
        
        # Disk alerts
        disk_warning = DiskAlertRule(threshold=85.0)
        disk_critical = DiskAlertRule(threshold=95.0)
        disk_critical.severity = AlertSeverity.CRITICAL
        
        # Temperature alerts
        temp_warning = TemperatureAlertRule(threshold=70.0)
        temp_critical = TemperatureAlertRule(threshold=80.0)
        temp_critical.severity = AlertSeverity.CRITICAL
        
        # Mining alerts
        mining_alert = MiningAlertRule()
        
        self.alert_rules = [
            cpu_warning, cpu_critical,
            memory_warning, memory_critical,
            disk_warning, disk_critical,
            temp_warning, temp_critical,
            mining_alert
        ]
    
    def _setup_channels(self):
        """Setup alert notification channels"""
        alerting_config = self.config.get("alerting", {})
        
        # Email channel
        email_config = alerting_config.get("email", {})
        if email_config.get("enabled", False):
            self.alert_channels.append(EmailAlertChannel(email_config))
        
        # Webhook channel
        webhook_config = alerting_config.get("webhook", {})
        if webhook_config.get("enabled", False):
            self.alert_channels.append(WebhookAlertChannel(webhook_config))
        
        # Slack channel
        slack_config = alerting_config.get("slack", {})
        if slack_config.get("enabled", False):
            self.alert_channels.append(SlackAlertChannel(slack_config))
    
    def add_alert_rule(self, rule: AlertRule):
        """Add custom alert rule"""
        self.alert_rules.append(rule)
        
        if self.logger:
            self.logger.log_info(f"Added alert rule: {rule.name}", component="alerting")
    
    def add_alert_channel(self, channel: AlertChannel):
        """Add alert notification channel"""
        self.alert_channels.append(channel)
        
        if self.logger:
            self.logger.log_info(f"Added alert channel: {channel.name}", component="alerting")
    
    def start_monitoring(self):
        """Start alert monitoring"""
        if self.running:
            return
        
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        if self.logger:
            self.logger.log_info("Alert monitoring started", component="alerting")
    
    def stop_monitoring(self):
        """Stop alert monitoring"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        if self.logger:
            self.logger.log_info("Alert monitoring stopped", component="alerting")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Get current metrics
                metrics = {}
                if self.resource_monitor:
                    resource_stats = self.resource_monitor.get_stats()
                    metrics.update(resource_stats)
                
                # Check all alert rules
                for rule in self.alert_rules:
                    try:
                        if rule.should_trigger(metrics):
                            alert = rule.trigger()
                            self._handle_alert(alert)
                    except Exception as e:
                        if self.logger:
                            self.logger.log_error(f"Alert rule {rule.name} failed: {e}", component="alerting")
                
                # Check for resolved alerts
                self._check_resolved_alerts(metrics)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Alert monitoring loop error: {e}", component="alerting")
                time.sleep(60)  # Wait longer on error
    
    def _handle_alert(self, alert: Alert):
        """Handle new alert"""
        # Add to active alerts
        self.active_alerts[alert.id] = alert
        
        # Add to history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history.pop(0)
        
        # Update statistics
        self.total_alerts += 1
        self.alerts_by_severity[alert.severity] += 1
        self.alerts_by_component[alert.component] = self.alerts_by_component.get(alert.component, 0) + 1
        
        # Log alert
        if self.logger:
            self.logger.log_warning(
                f"Alert triggered: {alert.title}",
                component="alerting",
                alert_id=alert.id,
                severity=alert.severity.value,
                component=alert.component
            )
        
        # Send notifications
        self._send_notifications(alert)
    
    def _check_resolved_alerts(self, metrics: Dict[str, Any]):
        """Check if any alerts should be resolved"""
        resolved_alerts = []
        
        for alert_id, alert in self.active_alerts.items():
            # Find the rule that triggered this alert
            rule = None
            for r in self.alert_rules:
                if r.name == alert.title:
                    rule = r
                    break
            
            if rule and not rule.should_trigger(metrics):
                # Alert is resolved
                alert.status = AlertStatus.RESOLVED
                alert.resolved_timestamp = time.time()
                resolved_alerts.append(alert_id)
                
                # Log resolution
                if self.logger:
                    self.logger.log_info(
                        f"Alert resolved: {alert.title}",
                        component="alerting",
                        alert_id=alert.id,
                        duration=alert.resolved_timestamp - alert.timestamp
                    )
                
                # Send resolution notification
                self._send_notifications(alert)
        
        # Remove resolved alerts from active list
        for alert_id in resolved_alerts:
            del self.active_alerts[alert_id]
    
    def _send_notifications(self, alert: Alert):
        """Send alert notifications through all channels"""
        for channel in self.alert_channels:
            try:
                channel.send_alert(alert)
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Failed to send notification via {channel.name}: {e}", component="alerting")
    
    def create_manual_alert(self, title: str, message: str, severity: AlertSeverity, component: str = "manual", metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a manual alert"""
        alert = Alert(
            id=f"manual_{int(time.time())}",
            title=title,
            message=message,
            severity=severity,
            status=AlertStatus.ACTIVE,
            component=component,
            timestamp=time.time(),
            metadata=metadata
        )
        
        self._handle_alert(alert)
        return alert.id
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.SUPPRESSED
            alert.suppression_duration = 3600  # Suppress for 1 hour
            
            if self.logger:
                self.logger.log_info(f"Alert acknowledged: {alert_id}", component="alerting")
            
            return True
        return False
    
    def suppress_alert_rule(self, rule_name: str, duration: float) -> bool:
        """Suppress alert rule for specified duration"""
        for rule in self.alert_rules:
            if rule.name == rule_name:
                rule.suppress(duration)
                
                if self.logger:
                    self.logger.log_info(f"Alert rule suppressed: {rule_name} for {duration}s", component="alerting")
                
                return True
        return False
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        return [asdict(alert) for alert in self.active_alerts.values()]
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alert history"""
        recent_alerts = self.alert_history[-limit:] if len(self.alert_history) > limit else self.alert_history
        return [asdict(alert) for alert in recent_alerts]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get alerting statistics"""
        return {
            "total_alerts": self.total_alerts,
            "active_alerts": len(self.active_alerts),
            "alerts_by_severity": {severity.value: count for severity, count in self.alerts_by_severity.items()},
            "alerts_by_component": self.alerts_by_component,
            "alert_rules": len(self.alert_rules),
            "alert_channels": len(self.alert_channels),
            "monitoring_active": self.running,
            "check_interval": self.check_interval
        }


# Global alerting system instance
_alerting_system = None


def setup_alerting_system(config: Dict[str, Any]) -> AlertingSystem:
    """Setup alerting system"""
    global _alerting_system
    _alerting_system = AlertingSystem(config)
    return _alerting_system


def get_alerting_system() -> Optional[AlertingSystem]:
    """Get the alerting system instance"""
    return _alerting_system
