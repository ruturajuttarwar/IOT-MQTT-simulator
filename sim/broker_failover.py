"""
Broker monitoring and failover orchestration
"""

import asyncio
import time
from typing import List, Optional
from utils.logging_utils import log_failover_event, log_mqtt_event


class BrokerFailoverManager:
    """Manages broker health monitoring and failover"""
    
    def __init__(self, primary_broker: str, failover_broker: str):
        self.primary_broker = primary_broker
        self.failover_broker = failover_broker
        self.current_broker = primary_broker
        
        self.primary_alive = True
        self.failover_alive = True
        
        # Broker positions (for relocation)
        self.broker_positions = {
            primary_broker: (500, 500),  # Center
            failover_broker: (700, 300)  # Offset
        }
        
        # Gateway management
        self.gateways = []  # List of gateway nodes
        self.gateway_coverage_radius = 200.0  # meters
        
        self.nodes = []
        self.failover_in_progress = False
        
        self.stats = {
            'failovers': 0,
            'broker_relocations': 0,
            'primary_downtime': 0,
            'reconnection_time': 0,
            'messages_lost': 0,
            'coverage_changes': 0
        }
        
    def register_node(self, node):
        """Register a node for failover management"""
        self.nodes.append(node)
        
    async def monitor_brokers(self):
        """Continuously monitor broker health"""
        while True:
            await asyncio.sleep(2.0)  # Check every 2 seconds
            
            # Ping primary broker
            primary_ok = await self._ping_broker(self.primary_broker)
            
            if not primary_ok and self.primary_alive:
                # Primary just went down
                log_failover_event(f"Primary broker {self.primary_broker} is DOWN")
                self.primary_alive = False
                await self.trigger_failover()
                
            elif primary_ok and not self.primary_alive:
                # Primary came back up
                log_failover_event(f"Primary broker {self.primary_broker} is UP")
                self.primary_alive = True
                
    async def _ping_broker(self, broker_address: str) -> bool:
        """Ping broker to check if alive"""
        try:
            # Simulate ping
            await asyncio.sleep(0.01)
            
            # For simulation, broker is always alive unless manually failed
            if broker_address == self.primary_broker:
                return self.primary_alive
            else:
                return self.failover_alive
                
        except Exception:
            return False
            
    async def trigger_failover(self):
        """Trigger broker failover"""
        if self.failover_in_progress:
            return
            
        self.failover_in_progress = True
        self.stats['failovers'] += 1
        
        log_failover_event("INITIATING BROKER FAILOVER")
        log_failover_event(f"Switching from {self.current_broker} to {self.failover_broker}")
        
        failover_start = time.time()
        
        # Disconnect all nodes from primary
        disconnect_tasks = []
        for node in self.nodes:
            if node.mqtt_client.connected:
                disconnect_tasks.append(node.mqtt_client.disconnect())
                
        await asyncio.gather(*disconnect_tasks)
        
        log_failover_event(f"Disconnected {len(self.nodes)} nodes")
        
        # Switch to failover broker
        self.current_broker = self.failover_broker
        
        # Reconnect all nodes to failover broker
        log_failover_event("Reconnecting nodes to failover broker...")
        
        reconnect_tasks = []
        for node in self.nodes:
            node.mqtt_client.broker_address = self.failover_broker
            reconnect_tasks.append(node.mqtt_client.connect())
            
        results = await asyncio.gather(*reconnect_tasks)
        
        successful_reconnects = sum(1 for r in results if r)
        
        failover_time = time.time() - failover_start
        self.stats['reconnection_time'] = failover_time
        
        log_failover_event(f"Failover complete in {failover_time:.2f}s")
        log_failover_event(f"Reconnected {successful_reconnects}/{len(self.nodes)} nodes")
        
        self.failover_in_progress = False
        
    async def manual_failover(self):
        """Manually trigger failover (for testing)"""
        log_failover_event("Manual failover triggered")
        self.primary_alive = False
        await self.trigger_failover()
        
    async def relocate_broker(self, broker_address: str, new_position: tuple):
        """Relocate broker to new position (topology event)"""
        old_position = self.broker_positions.get(broker_address)
        self.broker_positions[broker_address] = new_position
        self.stats['broker_relocations'] += 1
        
        log_failover_event(f"Broker {broker_address} relocated from {old_position} to {new_position}")
        
        # Check which nodes are affected by coverage change
        affected_nodes = []
        for node in self.nodes:
            if node.mqtt_client.broker_address == broker_address:
                # Calculate if node is still in range
                distance = self._calculate_distance(node.position, new_position)
                if distance > 200:  # Out of range
                    affected_nodes.append(node)
                    
        if affected_nodes:
            log_failover_event(f"{len(affected_nodes)} nodes affected by broker relocation")
            self.stats['coverage_changes'] += 1
            
    def register_gateway(self, gateway_node):
        """Register a gateway node (can be mobile)"""
        self.gateways.append(gateway_node)
        log_failover_event(f"Gateway {gateway_node.node_id} registered")
        
    async def update_gateway_coverage(self):
        """Update coverage as gateways move"""
        for gateway in self.gateways:
            if gateway.is_mobile:
                # Check which nodes are now in/out of coverage
                for node in self.nodes:
                    distance = self._calculate_distance(node.position, gateway.position)
                    
                    if distance <= self.gateway_coverage_radius:
                        # Node is in coverage
                        if not hasattr(node, 'gateway_coverage') or not node.gateway_coverage:
                            node.gateway_coverage = True
                            self.stats['coverage_changes'] += 1
                            log_failover_event(f"Node {node.node_id} entered gateway coverage")
                    else:
                        # Node is out of coverage
                        if hasattr(node, 'gateway_coverage') and node.gateway_coverage:
                            node.gateway_coverage = False
                            self.stats['coverage_changes'] += 1
                            log_failover_event(f"Node {node.node_id} left gateway coverage")
                            
    def _calculate_distance(self, pos1: tuple, pos2: tuple) -> float:
        """Calculate Euclidean distance between two positions"""
        import math
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def get_stats(self) -> dict:
        """Get failover statistics"""
        return {
            **self.stats,
            'current_broker': self.current_broker,
            'primary_alive': self.primary_alive,
            'failover_alive': self.failover_alive,
            'nodes_registered': len(self.nodes),
            'gateways_registered': len(self.gateways),
            'broker_positions': self.broker_positions
        }
