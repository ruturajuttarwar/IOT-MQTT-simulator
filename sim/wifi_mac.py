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
        
    async def send_packet(self, packet: bytes, dest: str, distance: float = 0, max_range: float = 600) -> Dict:
        """Send packet with CSMA/CA and distance-based PDR"""
        from utils.phy_utils import calculate_pdr
        
        # Check queue
        if len(self.queue) >= self.max_queue_size:
            self.stats['packets_dropped'] += 1
            return {'success': False, 'reason': 'queue_full'}
            
        # Add to queue
        self.queue.append((packet, dest))
        
        # Calculate PDR based on distance
        pdr = calculate_pdr(distance, max_range, 'wifi')
        print(f"[MAC-TX] Node {self.node_id}: distance={distance:.1f}m, PDR={pdr:.2%}")
        
        # CSMA/CA backoff
        backoff_slots = random.randint(*self.profile['csma_backoff_range'])
        backoff_time = backoff_slots * self.profile['slot_time_us'] / 1_000_000  # Convert to seconds
        await asyncio.sleep(backoff_time)
        
        # Simulate collision (increases with distance due to hidden terminal problem)
        collision_prob = self.profile['collision_probability'] * (1.0 + (1.0 - pdr) * 0.5)
        if random.random() < collision_prob:
            self.stats['collisions'] += 1
            print(f"[MAC-COLLISION] Node {self.node_id}: Collision detected, retrying...")
            # Retry with exponential backoff
            return await self._retry_packet(packet, dest, distance, max_range, 0)
            
        # Calculate transmission time
        packet_size = len(packet)
        tx_time_us = (packet_size * 8 * 1_000_000 / self.profile['data_rate_bps']) + \
                     self.profile['packet_overhead_us']
        
        # Wait for ACK
        await asyncio.sleep(self.profile['ack_timeout_ms'] / 1000.0)
        
        # Simulate ACK reception based on PDR (distance-dependent)
        if random.random() < pdr:
            self.stats['acks_received'] += 1
            self.stats['packets_sent'] += 1
            print(f"[MAC-SUCCESS] Node {self.node_id}: ACK received, no retries needed")
            return {
                'success': True,
                'tx_time_us': tx_time_us,
                'backoff_time_us': backoff_time * 1_000_000,
                'retries': 0,
                'pdr': pdr
            }
        else:
            # ACK lost due to distance, retry
            print(f"[MAC-RETRY] Node {self.node_id}: ACK lost (PDR={pdr:.2%}), retrying...")
            return await self._retry_packet(packet, dest, distance, max_range, 0)
            
    async def _retry_packet(self, packet: bytes, dest: str, distance: float, max_range: float, retry_count: int = 0) -> Dict:
        """Retry packet transmission with distance-based PDR"""
        from utils.phy_utils import calculate_pdr
        
        if retry_count >= self.profile['retry_limit']:
            self.stats['packets_dropped'] += 1
            print(f"[MAC-DROPPED] Node {self.node_id}: Max retries ({retry_count}) reached, packet dropped")
            return {'success': False, 'reason': 'max_retries', 'retries': retry_count}
            
        self.stats['packets_retried'] += 1
        print(f"[MAC-RETRY] Node {self.node_id}: Retry attempt {retry_count + 1}")
        
        # Exponential backoff
        backoff_slots = random.randint(0, (2 ** (retry_count + 1)) * 31)
        backoff_time = backoff_slots * self.profile['slot_time_us'] / 1_000_000
        await asyncio.sleep(backoff_time)
        
        # Calculate PDR for retry
        pdr = calculate_pdr(distance, max_range, 'wifi')
        
        # Calculate transmission time (each retry costs energy!)
        packet_size = len(packet)
        tx_time_us = (packet_size * 8 * 1_000_000 / self.profile['data_rate_bps']) + \
                     self.profile['packet_overhead_us']
        
        # Try again with distance-based success probability
        collision_prob = self.profile['collision_probability'] * (1.0 + (1.0 - pdr) * 0.5)
        if random.random() < collision_prob or random.random() > pdr:
            # Failed, retry again
            print(f"[MAC-RETRY] Node {self.node_id}: Retry {retry_count + 1} failed (PDR={pdr:.2%}), trying again...")
            return await self._retry_packet(packet, dest, distance, max_range, retry_count + 1)
            
        # Success
        self.stats['packets_sent'] += 1
        print(f"[MAC-SUCCESS] Node {self.node_id}: Retry {retry_count + 1} succeeded!")
        
        return {
            'success': True,
            'tx_time_us': tx_time_us,
            'backoff_time_us': backoff_time * 1_000_000,
            'retries': retry_count + 1,
            'pdr': pdr
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
        
    def is_sleeping(self) -> bool:
        """WiFi doesn't truly sleep - always in idle listening mode"""
        return False
    
    def get_stats(self) -> Dict:
        """Get MAC statistics"""
        return {
            **self.stats,
            'queue_depth': len(self.queue),
            'associated': self.associated,
            'ap_address': self.ap_address,
            'packets_received': self.stats.get('packets_received', 0)
        }
