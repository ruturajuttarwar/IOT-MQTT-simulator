"""
Global simulation configuration parameters
"""

# Network Configuration
NUM_NODES = 5  # 10 nodes for better demonstration
PERCENT_STATIONARY = 0.7  # 70% stationary, 30% mobile (requirement)
MOBILITY_MODEL = "random_waypoint"  # Default for mobile nodes

# Area Configuration
AREA_WIDTH = 1000.0  # meters
AREA_HEIGHT = 1000.0  # meters

# Protocol Configuration
BLE_CONN_INTERVAL_MS = 60
WIFI_BASE_DELAY_MS = 5
WAN_LATENCY_MS = 100
PACKET_LOSS_RATE = 0.01

# MQTT Broker Configuration
BROKER_PRIMARY = "localhost:1883"
BROKER_FAILOVER = "localhost:2883"

# Simulation Timing
SIMULATION_DURATION = 300  # seconds
TIME_SCALE = 1.0  # 1.0 = realtime
UPDATE_INTERVAL = 1.0  # seconds

# MQTT Configuration
MQTT_KEEP_ALIVE = 60  # seconds
MQTT_QOS_DEFAULT = 1  # QoS 1 by default
MQTT_CLEAN_SESSION = False  # Persistent sessions

# Energy Configuration
ENABLE_ENERGY_TRACKING = True
INITIAL_BATTERY_LEVEL = 100.0  # percentage

# GUI Configuration
GUI_UPDATE_RATE = 1.0  # seconds
GUI_PORT = 5001  # Backend API port (avoiding macOS AirPlay on 5000)
