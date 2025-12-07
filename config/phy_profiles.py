"""
PHY-level timing and energy models for BLE and WiFi
"""

# BLE 5.x Profile
BLE_PROFILE = {
    'name': 'BLE 5.x',
    'data_rate_bps': 1_000_000,  # 1 Mbps
    'tx_power_mw': 45.0,  # 15mA @ 3V
    'rx_power_mw': 36.0,  # 12mA @ 3V
    'sleep_power_mw': 0.0045,  # 1.5µA @ 3V
    'idle_power_mw': 0.015,  # 5µA @ 3V
    'conn_interval_ms': 60,
    'advertising_interval_ms': 100,
    'mtu': 251,  # bytes
    'range_meters': 100.0,
    'tx_sensitivity_dbm': 0,
    'rx_sensitivity_dbm': -90,
    'packet_overhead_us': 150,
    'preamble_time_us': 40
}

# WiFi 802.11n Profile
WIFI_PROFILE = {
    'name': 'WiFi 802.11n',
    'data_rate_bps': 150_000_000,  # 150 Mbps
    'tx_power_mw': 100.0,
    'rx_power_mw': 50.0,
    'sleep_power_mw': 0.1,
    'idle_power_mw': 10.0,
    'csma_backoff_range': (0, 31),  # slots
    'slot_time_us': 9,
    'ack_timeout_ms': 1,
    'retry_limit': 3,
    'mtu': 1500,  # bytes
    'range_meters': 100.0,
    'collision_probability': 0.1,
    'packet_overhead_us': 50
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
