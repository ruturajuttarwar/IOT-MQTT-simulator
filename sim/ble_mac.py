"""
BLE MAC layer implementation with connection scheduling
"""

import asyncio
import random
from typing import Dict, Optional
from config.phy_profiles import BLE_PROFILE
from utils.logging_utils import log_mac_event


class BLEMAC:
    """BLE 5.x MAC layer with full connection management"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.profile = BLE_PROFILE
        
        # Connection parameters
        self.conn_interval_ms = self.profile['conn_interval_ms']
        self.supervision_timeout_ms = self.conn_interval_ms * 6  # 6 intervals
        self.last_conn_event = 0
        self.last_supervision_check = 0
        
        # State management
        self.state = 'STANDBY'  # STANDBY, ADVERTISING, SCANNING, CONNECTED
        self.sleeping = False
        self.connected_peer = None
        
        # Advertising
        self.advertising_interval_ms = self.profile['advertising_interval_ms']
        self.last_advertisement = 0
        
        # Queue
        self.queue = []
        self.max_queue_size = 20
        
        # Statistics
        self.stats = {
            'packets_sent': 0,
            'packets_dropped': 0,
            'packets_retried': 0,
            'connection_events': 0,
            'sleep_cycles': 0,
            'advertisements_sent': 0,
            'supervision_timeouts': 0
        }
        
    async def send_packet(self, packet: bytes, dest: str) -> Dict:
        """Send packet during connection event"""
        # Check queue
        if len(self.queue) >= self.max_queue_size:
            self.stats['packets_dropped'] += 1
            return {'success': False, 'reason': 'queue_full'}
            
        # Add to queue
        self.queue.append((packet, dest))
        
        # Wait for next connection event
        await self._wait_for_connection_event()
        
        # Transmission
        packet_size = len(packet)
        tx_time_us = (packet_size * 8 * 1_000_000 / self.profile['data_rate_bps']) + \
                     self.profile['packet_overhead_us'] + self.profile['preamble_time_us']
        
        # Simulate packet loss (5%)
        if random.random() < 0.05:
            # Retry in next connection event
            return await self._retry_packet(packet, dest)
            
        self.stats['packets_sent'] += 1
        
        return {
            'success': True,
            'tx_time_us': tx_time_us,
            'conn_interval_ms': self.conn_interval_ms,
            'retries': 0
        }
        
    async def _wait_for_connection_event(self):
        """Wait for next connection event"""
        # Sleep until next connection event
        sleep_time = self.conn_interval_ms / 1000.0
        self.sleeping = True
        self.stats['sleep_cycles'] += 1
        
        await asyncio.sleep(sleep_time)
        
        self.sleeping = False
        self.stats['connection_events'] += 1
        
    async def _retry_packet(self, packet: bytes, dest: str, retry_count: int = 0) -> Dict:
        """Retry packet in next connection event"""
        if retry_count >= 3:  # Max 3 retries for BLE
            self.stats['packets_dropped'] += 1
            return {'success': False, 'reason': 'max_retries', 'retries': retry_count}
            
        self.stats['packets_retried'] += 1
        
        # Wait for next connection event
        await self._wait_for_connection_event()
        
        # Try again
        if random.random() < 0.05:
            return await self._retry_packet(packet, dest, retry_count + 1)
            
        # Success
        self.stats['packets_sent'] += 1
        packet_size = len(packet)
        tx_time_us = (packet_size * 8 * 1_000_000 / self.profile['data_rate_bps']) + \
                     self.profile['packet_overhead_us']
        
        return {
            'success': True,
            'tx_time_us': tx_time_us,
            'conn_interval_ms': self.conn_interval_ms,
            'retries': retry_count + 1
        }
        
    def set_connection_interval(self, interval_ms: int):
        """Set BLE connection interval"""
        self.conn_interval_ms = interval_ms
        
    def is_sleeping(self) -> bool:
        """Check if node is in sleep mode"""
        return self.sleeping
        
    def get_queue_depth(self) -> int:
        """Get current queue depth"""
        return len(self.queue)
        
    async def start_advertising(self):
        """Start BLE advertising"""
        self.state = 'ADVERTISING'
        log_mac_event(self.node_id, "Started advertising")
        
    async def advertise(self):
        """Send advertisement packet"""
        import time
        current_time = time.time() * 1000
        
        if current_time - self.last_advertisement >= self.advertising_interval_ms:
            self.last_advertisement = current_time
            self.stats['advertisements_sent'] += 1
            # Simulate advertisement transmission
            await asyncio.sleep(0.001)
            
    async def start_scanning(self):
        """Start scanning for advertisements"""
        self.state = 'SCANNING'
        log_mac_event(self.node_id, "Started scanning")
        
    async def connect(self, peer_address: str):
        """Establish BLE connection"""
        self.state = 'CONNECTED'
        self.connected_peer = peer_address
        self.last_supervision_check = 0
        log_mac_event(self.node_id, f"Connected to {peer_address}")
        
    def check_supervision_timeout(self) -> bool:
        """Check if supervision timeout occurred"""
        import time
        current_time = time.time() * 1000
        
        if self.state == 'CONNECTED':
            if current_time - self.last_supervision_check > self.supervision_timeout_ms:
                self.stats['supervision_timeouts'] += 1
                self.state = 'STANDBY'
                self.connected_peer = None
                log_mac_event(self.node_id, "Supervision timeout - disconnected")
                return True
        return False
        
    def get_stats(self) -> Dict:
        """Get MAC statistics"""
        return {
            **self.stats,
            'state': self.state,
            'connected_peer': self.connected_peer
        }
