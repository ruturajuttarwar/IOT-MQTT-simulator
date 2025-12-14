"""
Physical layer utility functions for distance-based calculations
"""

import math


def calculate_pdr(distance: float, max_range: float, protocol: str = 'wifi') -> float:
    """
    Calculate Packet Delivery Ratio based on distance using log-distance path loss model
    
    Args:
        distance: Distance to destination in meters
        max_range: Maximum range of the protocol in meters
        protocol: 'wifi' or 'ble'
    
    Returns:
        PDR value between 0.0 and 1.0
    """
    if distance <= 0:
        return 1.0
    
    if distance > max_range:
        return 0.0
    
    # Log-distance path loss model
    # PDR decreases more rapidly as we approach max range
    # Use different path loss exponents for different protocols
    if protocol == 'ble':
        # BLE: More resilient at close range, drops faster at edge
        path_loss_exponent = 3.0
    else:  # wifi
        # WiFi: More gradual degradation
        path_loss_exponent = 2.5
    
    # Normalized distance (0 to 1)
    normalized_distance = distance / max_range
    
    # Calculate PDR with path loss
    # At 0m: PDR = 1.0 (100%)
    # At max_range: PDR = 0.1 (10% - some packets still get through)
    pdr = 1.0 - (normalized_distance ** path_loss_exponent) * 0.9
    
    # Ensure minimum PDR of 10% within range
    return max(0.1, min(1.0, pdr))


def calculate_retry_probability(distance: float, max_range: float, protocol: str = 'wifi') -> float:
    """
    Calculate probability that a packet will need retry based on distance
    
    Args:
        distance: Distance to destination in meters
        max_range: Maximum range of the protocol in meters
        protocol: 'wifi' or 'ble'
    
    Returns:
        Retry probability between 0.0 and 1.0
    """
    pdr = calculate_pdr(distance, max_range, protocol)
    # Retry probability is inverse of PDR
    return 1.0 - pdr


def calculate_expected_retries(distance: float, max_range: float, protocol: str = 'wifi', max_retries: int = 3) -> float:
    """
    Calculate expected number of retries based on distance
    
    Args:
        distance: Distance to destination in meters
        max_range: Maximum range of the protocol in meters
        protocol: 'wifi' or 'ble'
        max_retries: Maximum number of retries allowed
    
    Returns:
        Expected number of retries (float)
    """
    retry_prob = calculate_retry_probability(distance, max_range, protocol)
    
    # Expected retries = sum of geometric series
    # E[retries] = p + p^2 + p^3 + ... (up to max_retries)
    expected = 0.0
    for i in range(1, max_retries + 1):
        expected += (retry_prob ** i)
    
    return expected


def calculate_rssi(distance: float, tx_power_dbm: float = 0, path_loss_exponent: float = 2.5) -> float:
    """
    Calculate RSSI (Received Signal Strength Indicator) based on distance
    
    Args:
        distance: Distance in meters
        tx_power_dbm: Transmit power in dBm
        path_loss_exponent: Path loss exponent (2.0 = free space, 3-4 = indoor)
    
    Returns:
        RSSI in dBm
    """
    if distance <= 0:
        return tx_power_dbm
    
    # Log-distance path loss model
    # RSSI = TX_power - 10 * n * log10(d/d0) - X
    # where d0 = 1m reference distance, X = shadow fading (ignored for simplicity)
    
    path_loss_db = 10 * path_loss_exponent * math.log10(distance)
    rssi = tx_power_dbm - path_loss_db
    
    return rssi
