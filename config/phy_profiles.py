"""
PHY-level timing and energy models for BLE and WiFi
"""

# BLE 5.x Profile
BLE_PROFILE = {
    'name': 'BLE 5.x',
    'data_rate_bps': 1_000_000,  # 1 Mbps
    'tx_power_mw': 45.0,  # 15mA @ 3V
    'rx_power_mw': 36.0,  # 12mA @ 3V
    'sleep_power_mw': 0.0045,  # 1.5µA @ 3V (VERY LOW)
    'idle_power_mw': 0.015,  # 5µA @ 3V (VERY LOW)
    'conn_interval_ms': 60,
    'advertising_interval_ms': 100,
    'mtu': 251,  # bytes
    'range_meters': 400.0,  # Simulation range (real: 30-50m)
    'base_latency_ms': 60,  # Connection interval dominates latency
    'tx_sensitivity_dbm': 0,
    'rx_sensitivity_dbm': -90,
    'packet_overhead_us': 2000,  # Increased for demo visibility (2ms overhead per packet)
    'preamble_time_us': 40
}

# WiFi 802.11n Profile
WIFI_PROFILE = {
    'name': 'WiFi 802.11n',
    'data_rate_bps': 150_000_000,  # 150 Mbps
    'tx_power_mw': 120.0,  # VERY HIGH
    'rx_power_mw': 70.0,  # HIGH
    'sleep_power_mw': 0.1,  # Rarely used
    'idle_power_mw': 15.0,  # HIGH (always listening)
    'csma_backoff_range': (0, 31),  # slots
    'slot_time_us': 9,
    'ack_timeout_ms': 1,
    'retry_limit': 3,
    'mtu': 1500,  # bytes
    'range_meters': 600.0,  # Simulation range (real: 50-70m)
    'base_latency_ms': 5,  # Lower base latency than BLE
    'collision_probability': 0.1,
    'packet_overhead_us': 5000  # Increased for demo visibility (5ms overhead per packet)
}

# Zigbee 802.15.4 Profile (optional)
ZIGBEE_PROFILE = {
    'name': 'Zigbee 802.15.4',
    'data_rate_bps': 250_000,  # 250 Kbps
    'tx_power_mw': 30.0,
    'rx_power_mw': 25.0,
    'sleep_power_mw': 0.003,
    'idle_power_mw': 0.01,
    'range_meters': 75.0,
    'mtu': 127,
    'duty_cycle_limit': 0.01  # 1% duty cycle
}

def get_profile(protocol_name):
    """Get PHY profile by protocol name"""
    profiles = {
        'ble': BLE_PROFILE,
        'wifi': WIFI_PROFILE,
        'zigbee': ZIGBEE_PROFILE
    }
    return profiles.get(protocol_name.lower(), WIFI_PROFILE)
