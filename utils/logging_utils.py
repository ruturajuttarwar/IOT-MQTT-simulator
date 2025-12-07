"""
Colored logging utilities for simulation events
"""

import logging
import sys
from datetime import datetime

# ANSI color codes
COLORS = {
    'RESET': '\033[0m',
    'RED': '\033[91m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'MAGENTA': '\033[95m',
    'CYAN': '\033[96m',
    'WHITE': '\033[97m',
    'BOLD': '\033[1m'
}

def setup_logging(level=logging.INFO):
    """Setup logging configuration"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

# GUI log buffer (imported by dashboard)
_gui_log_callback = None

def set_gui_log_callback(callback):
    """Set callback for GUI logging"""
    global _gui_log_callback
    _gui_log_callback = callback

def _send_to_gui(log_type: str, msg: str):
    """Send log to GUI if callback is set"""
    if _gui_log_callback:
        _gui_log_callback(log_type, msg)

def log_info(msg: str):
    """Log info message"""
    print(f"{COLORS['CYAN']}ℹ {msg}{COLORS['RESET']}")
    _send_to_gui('info', msg)

def log_success(msg: str):
    """Log success message"""
    print(f"{COLORS['GREEN']}✓ {msg}{COLORS['RESET']}")
    _send_to_gui('success', msg)

def log_warning(msg: str):
    """Log warning message"""
    print(f"{COLORS['YELLOW']}⚠ {msg}{COLORS['RESET']}")
    _send_to_gui('warning', msg)

def log_error(msg: str):
    """Log error message"""
    print(f"{COLORS['RED']}✗ {msg}{COLORS['RESET']}")
    _send_to_gui('error', msg)

def log_mac_event(node_id: str, event: str):
    """Log MAC layer event"""
    msg = f"[MAC] {node_id}: {event}"
    print(f"{COLORS['BLUE']}{msg}{COLORS['RESET']}")
    _send_to_gui('info', msg)

def log_mqtt_event(node_id: str, event: str):
    """Log MQTT event"""
    msg = f"[MQTT] {node_id}: {event}"
    print(f"{COLORS['MAGENTA']}{msg}{COLORS['RESET']}")
    _send_to_gui('mqtt', msg)

def log_failover_event(event: str):
    """Log failover event"""
    msg = f"[FAILOVER] {event}"
    print(f"{COLORS['RED']}{COLORS['BOLD']}{msg}{COLORS['RESET']}")
    _send_to_gui('error', msg)

def log_mobility_event(node_id: str, event: str):
    """Log mobility event"""
    msg = f"[MOBILITY] {node_id}: {event}"
    print(f"{COLORS['CYAN']}{msg}{COLORS['RESET']}")
    _send_to_gui('info', msg)
