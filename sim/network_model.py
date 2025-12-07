"""
Network delay and loss model
"""

import random
from typing import Tuple
from config.simulation_config import WIFI_BASE_DELAY_MS, BLE_CONN_INTERVAL_MS, WAN_LATENCY_MS, PACKET_LOSS_RATE


class NetworkModel:
    """Applies delay and packet loss to transmissions with IP network simulation"""
    
    def __init__(self):
        self.packet_loss_rate = PACKET_LOSS_RATE
        self.wan_latency_ms = WAN_LATENCY_MS
        
        # IP network parameters
        self.gateway_latency_ms = 5.0  # Local gateway hop
        self.cloud_latency_ms = 50.0   # Cloud/internet hop
        self.wan_packet_loss = 0.02    # 2% loss on WAN
        
        # Routing table (simplified)
        self.routes = {
            'local': {'hops': 1, 'latency_ms': 1.0},
            'gateway': {'hops': 2, 'latency_ms': self.gateway_latency_ms},
            'cloud': {'hops': 5, 'latency_ms': self.cloud_latency_ms}
        }
        
    def get_latency(self, protocol: str, is_wan: bool = False) -> float:
        """Calculate transmission latency in milliseconds"""
        # Base delay based on protocol
        if protocol == 'ble':
            # BLE has connection interval delay
            base_delay = BLE_CONN_INTERVAL_MS / 2.0  # Average half interval
        elif protocol == 'wifi':
            base_delay = WIFI_BASE_DELAY_MS
        else:
            base_delay = 10.0  # Default
            
        # Add random jitter (±20%)
        jitter = random.uniform(-0.2, 0.2) * base_delay
        delay = base_delay + jitter
        
        # Add WAN latency if going through gateway/cloud
        if is_wan:
            delay += self.wan_latency_ms
            
        return max(0, delay)
        
    def should_drop(self) -> bool:
        """Determine if packet should be dropped"""
        return random.random() < self.packet_loss_rate
        
    def apply_wan_penalty(self, latency_ms: float) -> float:
        """Add WAN latency and jitter"""
        wan_jitter = random.uniform(-10, 10)  # ±10ms jitter
        return latency_ms + self.wan_latency_ms + wan_jitter
        
    def calculate_distance_loss(self, distance: float, max_range: float) -> float:
        """Calculate signal strength based on distance"""
        if distance > max_range:
            return 1.0  # 100% loss
            
        # Simple path loss model
        loss_rate = (distance / max_range) ** 2 * self.packet_loss_rate
        return min(1.0, loss_rate)
        
    def get_effective_throughput(self, protocol: str, distance: float, max_range: float) -> float:
        """Get effective throughput considering distance"""
        if distance > max_range:
            return 0.0
            
        # Signal strength degradation
        signal_strength = 1.0 - (distance / max_range)
        
        if protocol == 'ble':
            max_throughput = 1_000_000  # 1 Mbps
        elif protocol == 'wifi':
            max_throughput = 150_000_000  # 150 Mbps
        else:
            max_throughput = 1_000_000
            
        # Throughput degrades with distance
        if signal_strength > 0.9:
            return max_throughput
        elif signal_strength > 0.7:
            return max_throughput * 0.8
        elif signal_strength > 0.5:
            return max_throughput * 0.5
        elif signal_strength > 0.3:
            return max_throughput * 0.2
        else:
            return max_throughput * 0.1
            
    def route_packet(self, source: str, destination: str, via_cloud: bool = False) -> dict:
        """Simulate IP routing with latency calculation"""
        if via_cloud:
            route = self.routes['cloud']
            total_latency = route['latency_ms'] + self.wan_latency_ms
            packet_loss = self.wan_packet_loss
        elif 'gateway' in destination or 'broker' in destination:
            route = self.routes['gateway']
            total_latency = route['latency_ms']
            packet_loss = self.packet_loss_rate
        else:
            route = self.routes['local']
            total_latency = route['latency_ms']
            packet_loss = self.packet_loss_rate
            
        # Add jitter
        jitter = random.uniform(-0.1, 0.1) * total_latency
        total_latency += jitter
        
        # Check if packet is dropped
        dropped = random.random() < packet_loss
        
        return {
            'latency_ms': total_latency,
            'hops': route['hops'],
            'dropped': dropped,
            'route_type': 'cloud' if via_cloud else 'gateway' if 'gateway' in destination else 'local'
        }
