"""
WiFi MAC layer implementation with CSMA/CA
"""

import asyncio
import random
from typing import Dict, Optional
from config.phy_profiles import WIFI_PROFILE
from utils.logging_utils import log_mac_event


class WiFiMAC:
    """WiFi 802.11n MAC layer with CSMA/CA"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.profile = WIFI_PROFILE
        self.queue = []
        self.max_queue_size = 50
        
        # Beacon management
        self.beacon_interval_ms = 100  # 802.11 standard beacon interval
        self.last_beacon = 0
        
        # Association state
        self.associated = False
        self.ap_address = None
        
        self.stats = {
            'packets_sent': 0,
            'packets_dropped': 0,
            'packets_retried': 0,
            'collisions': 0,
            'acks_received': 0,
            'beacons_sent': 0,
            'beacons_received': 0
        }
        
    async def send_packet(self, packet: bytes, dest: str) -> Dict:
        """Send packet with CSMA/CA"""
        # Check queue
        if len(self.queue) >= self.max_queue_size:
            self.stats['packets_dropped'] += 1
            return {'success': False, 'reason': 'queue_full'}
            
        # Add to queue
        self.queue.append((packet, dest))
        
        # CSMA/CA backoff
        backoff_slots = random.randint(*self.profile['csma_backoff_range'])
        backoff_time = backoff_slots * self.profile['slot_time_us'] / 1_000_000  # Convert to seconds
        await asyncio.sleep(backoff_time)
        
        # Simulate collision
        if random.random() < self.profile['collision_probability']:
            self.stats['collisions'] += 1
            # Retry with exponential backoff
            return await self._retry_packet(packet, dest)
            
        # Transmission successful
        self.stats['packets_sent'] += 1
        
        # Calculate transmission time
        packet_size = len(packet)
        tx_time_us = (packet_size * 8 * 1_000_000 / self.profile['data_rate_bps']) + \
                     self.profile['packet_overhead_us']
        
        # Wait for ACK
        await asyncio.sleep(self.profile['ack_timeout_ms'] / 1000.0)
        
        # Simulate ACK reception (success probability)
        if random.random() > 0.05:  # 95% ACK success
            self.stats['acks_received'] += 1
            return {
                'success': True,
                'tx_time_us': tx_time_us,
                'backoff_time_us': backoff_time * 1_000_000,
                'retries': 0
            }
        else:
            # ACK lost, retry
            return await self._retry_packet(packet, dest)
            
    async def _retry_packet(self, packet: bytes, dest: str, retry_count: int = 0) -> Dict:
        """Retry packet transmission"""
        if retry_count >= self.profile['retry_limit']:
            self.stats['packets_dropped'] += 1
            return {'success': False, 'reason': 'max_retries', 'retries': retry_count}
            
        self.stats['packets_retried'] += 1
        
        # Exponential backoff
        backoff_slots = random.randint(0, (2 ** (retry_count + 1)) * 31)
        backoff_time = backoff_slots * self.profile['slot_time_us'] / 1_000_000
        await asyncio.sleep(backoff_time)
        
        # Try again
        if random.random() < self.profile['collision_probability']:
            return await self._retry_packet(packet, dest, retry_count + 1)
            
        # Success
        self.stats['packets_sent'] += 1
        packet_size = len(packet)
        tx_time_us = (packet_size * 8 * 1_000_000 / self.profile['data_rate_bps']) + \
                     self.profile['packet_overhead_us']
        
        return {
            'success': True,
            'tx_time_us': tx_time_us,
            'backoff_time_us': backoff_time * 1_000_000,
            'retries': retry_count + 1
        }
        
    def get_queue_depth(self) -> int:
        """Get current queue depth"""
        return len(self.queue)
        
    async def send_beacon(self):
        """Send WiFi beacon frame"""
        import time
        current_time = time.time() * 1000
        
        if current_time - self.last_beacon >= self.beacon_interval_ms:
            self.last_beacon = current_time
            self.stats['beacons_sent'] += 1
            # Simulate beacon transmission
            await asyncio.sleep(0.001)
            log_mac_event(self.node_id, "Beacon sent")
            
    async def associate(self, ap_address: str):
        """Associate with Access Point"""
        self.associated = True
        self.ap_address = ap_address
        log_mac_event(self.node_id, f"Associated with AP {ap_address}")
        
    def receive_beacon(self):
        """Process received beacon"""
        self.stats['beacons_received'] += 1
        
    def get_queue_depth(self) -> int:
        """Get current queue depth"""
        return len(self.queue)
        
    def get_stats(self) -> Dict:
        """Get MAC statistics"""
        return {
            **self.stats,
            'queue_depth': len(self.queue),
            'associated': self.associated,
            'ap_address': self.ap_address
        }
