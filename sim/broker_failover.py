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
        # Both brokers at same location (failover is logical, not physical)
        self.broker_positions = {
            primary_broker: (500, 500),  # Center
            failover_broker: (500, 500)  # Same location (logical failover)
        }
        
        # Gateway management
        self.gateways = []  # List of gateway nodes
        self.gateway_coverage_radius = 200.0  # meters
        
        self.nodes = []
        self.failover_in_progress = False
        self.relocation_in_progress = False
        
        # Track reconnection wave
        self.reconnection_wave = []  # List of (node_id, reconnect_time)
        self.failover_start_time = None
        
        self.stats = {
            'failovers': 0,
            'broker_relocations': 0,
            'primary_downtime': 0,
            'reconnection_time': 0,
            'messages_lost': 0,
            'coverage_changes': 0,
            'nodes_disconnected': 0,
            'nodes_reconnected': 0,
            'inflight_messages_preserved': 0,
            'retained_messages_preserved': 0
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
        """Trigger broker failover with full MQTT semantics"""
        if self.failover_in_progress:
            return
            
        self.failover_in_progress = True
        self.stats['failovers'] += 1
        self.failover_start_time = time.time()
        self.reconnection_wave = []
        
        log_failover_event("=" * 60)
        log_failover_event("🚨 BROKER FAILOVER INITIATED")
        log_failover_event(f"Primary broker {self.primary_broker} is DOWN")
        log_failover_event(f"Switching to failover broker {self.failover_broker}")
        log_failover_event("=" * 60)
        
        # Step 1: Nodes detect outage through missed PINGRESP/ACKs
        log_failover_event("Phase 1: Nodes detecting broker outage...")
        disconnected_count = 0
        inflight_preserved = 0
        retained_preserved = 0
        
        for node in self.nodes:
            if node.mqtt_client.connected:
                # Preserve inflight messages (QoS 1)
                inflight_count = len(node.mqtt_client.inflight_messages)
                inflight_preserved += inflight_count
                
                # Preserve retained messages
                retained_count = len(node.mqtt_client.retained_messages)
                retained_preserved += retained_count
                
                # Mark as disconnected (simulates missed PINGRESP)
                node.mqtt_client.connected = False
                disconnected_count += 1
                
                log_mqtt_event(node.node_id, f"Detected broker outage (inflight: {inflight_count}, retained: {retained_count})")
                
        self.stats['nodes_disconnected'] = disconnected_count
        self.stats['inflight_messages_preserved'] = inflight_preserved
        self.stats['retained_messages_preserved'] = retained_preserved
        
        log_failover_event(f"✓ {disconnected_count} nodes detected outage")
        log_failover_event(f"✓ {inflight_preserved} inflight messages preserved")
        log_failover_event(f"✓ {retained_preserved} retained messages preserved")
        
        # Step 2: Switch to failover broker
        self.current_broker = self.failover_broker
        log_failover_event(f"Phase 2: Switching to {self.failover_broker}")
        
        # Step 3: Nodes enter exponential backoff reconnect mode
        log_failover_event("Phase 3: Nodes reconnecting with exponential backoff...")
        
        reconnected_count = 0
        for i, node in enumerate(self.nodes):
            # Simulate exponential backoff (staggered reconnections)
            backoff_delay = min(2 ** (i % 4), 8) * 0.1  # 0.1s, 0.2s, 0.4s, 0.8s pattern
            await asyncio.sleep(backoff_delay)
            
            # Update broker address
            node.mqtt_client.broker_address = self.failover_broker
            node.broker_address = self.failover_broker
            
            # Attempt reconnection
            success = await node.mqtt_client.connect()
            
            if success:
                reconnect_time = time.time() - self.failover_start_time
                self.reconnection_wave.append((node.node_id, reconnect_time))
                reconnected_count += 1
                
                log_mqtt_event(node.node_id, f"Reconnected to failover broker (t={reconnect_time:.2f}s)")
                
                # Restore subscriptions
                if node.role in ['subscriber', 'both']:
                    if node.subscribe_to:
                        for publisher_id in node.subscribe_to:
                            await node.mqtt_client.subscribe(f"sensors/{publisher_id}/data", qos=node.qos)
                    else:
                        await node.mqtt_client.subscribe(f"sensors/+/data", qos=node.qos)
                    
                    log_mqtt_event(node.node_id, "Subscriptions restored")
                
                # Resend inflight messages (QoS 1 semantics)
                if node.mqtt_client.inflight_messages:
                    log_mqtt_event(node.node_id, f"Resending {len(node.mqtt_client.inflight_messages)} inflight messages")
                    
        self.stats['nodes_reconnected'] = reconnected_count
        
        failover_time = time.time() - self.failover_start_time
        self.stats['reconnection_time'] = failover_time
        
        log_failover_event("=" * 60)
        log_failover_event(f"✅ FAILOVER COMPLETE in {failover_time:.2f}s")
        log_failover_event(f"✓ Reconnected: {reconnected_count}/{disconnected_count} nodes")
        log_failover_event(f"✓ Reconnection wave: {len(self.reconnection_wave)} events")
        log_failover_event("=" * 60)
        
        self.failover_in_progress = False
        
    async def manual_failover(self):
        """Manually trigger failover (for testing)"""
        log_failover_event("Manual failover triggered")
        self.primary_alive = False
        await self.trigger_failover()
        
    async def relocate_broker(self, broker_address: str = None, offset_x: float = None, offset_y: float = None):
        """
        Relocate broker to new position (topology event)
        Simulates mobile/reconfigured broker or gateway
        """
        if self.relocation_in_progress:
            return
            
        self.relocation_in_progress = True
        self.stats['broker_relocations'] += 1
        
        # Use current broker if not specified
        if broker_address is None:
            broker_address = self.current_broker
            
        old_position = self.broker_positions.get(broker_address, (500, 500))
        
        # Random offset if not specified (~50m in x and y)
        if offset_x is None:
            import random
            offset_x = random.uniform(-50, 50)
        if offset_y is None:
            import random
            offset_y = random.uniform(-50, 50)
            
        new_position = (old_position[0] + offset_x, old_position[1] + offset_y)
        
        # Clamp to simulation area (0-1000)
        new_position = (
            max(0, min(1000, new_position[0])),
            max(0, min(1000, new_position[1]))
        )
        
        self.broker_positions[broker_address] = new_position
        
        log_failover_event("=" * 60)
        log_failover_event("📍 BROKER RELOCATION EVENT")
        log_failover_event(f"Broker: {broker_address}")
        log_failover_event(f"Old position: ({old_position[0]:.1f}, {old_position[1]:.1f})")
        log_failover_event(f"New position: ({new_position[0]:.1f}, {new_position[1]:.1f})")
        log_failover_event(f"Offset: ({offset_x:.1f}m, {offset_y:.1f}m)")
        log_failover_event("=" * 60)
        
        # Check impact on all nodes connected to this broker
        nodes_affected = 0
        nodes_disconnected = 0
        nodes_improved = 0
        nodes_degraded = 0
        
        for node in self.nodes:
            if node.mqtt_client.broker_address == broker_address:
                # Calculate old and new distances
                old_distance = self._calculate_distance(node.position, old_position)
                new_distance = self._calculate_distance(node.position, new_position)
                
                max_range = node.phy_profile.get('range_meters', 100)
                
                # Check if node goes out of range
                if new_distance > max_range and old_distance <= max_range:
                    nodes_disconnected += 1
                    nodes_affected += 1
                    
                    # Disconnect node
                    node.mqtt_client.connected = False
                    log_mqtt_event(node.node_id, f"DISCONNECTED: Out of range ({new_distance:.1f}m > {max_range}m)")
                    
                    # Node will attempt reconnection in its main loop
                    
                elif new_distance <= max_range:
                    nodes_affected += 1
                    
                    # Calculate PDR change
                    from utils.phy_utils import calculate_pdr
                    old_pdr = calculate_pdr(old_distance, max_range, node.protocol)
                    new_pdr = calculate_pdr(new_distance, max_range, node.protocol)
                    
                    if new_pdr > old_pdr:
                        nodes_improved += 1
                        log_mqtt_event(node.node_id, f"Link IMPROVED: {old_distance:.1f}m→{new_distance:.1f}m, PDR: {old_pdr:.1%}→{new_pdr:.1%}")
                    elif new_pdr < old_pdr:
                        nodes_degraded += 1
                        log_mqtt_event(node.node_id, f"Link DEGRADED: {old_distance:.1f}m→{new_distance:.1f}m, PDR: {old_pdr:.1%}→{new_pdr:.1%}")
                    
                    # Node will automatically use new distance in next transmission
                    
        self.stats['coverage_changes'] += 1
        
        log_failover_event("=" * 60)
        log_failover_event(f"✅ RELOCATION COMPLETE")
        log_failover_event(f"✓ Nodes affected: {nodes_affected}")
        log_failover_event(f"✓ Disconnected (out of range): {nodes_disconnected}")
        log_failover_event(f"✓ Link improved: {nodes_improved}")
        log_failover_event(f"✓ Link degraded: {nodes_degraded}")
        log_failover_event("=" * 60)
        
        self.relocation_in_progress = False
            
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
            'broker_positions': self.broker_positions,
            'failover_in_progress': self.failover_in_progress,
            'relocation_in_progress': self.relocation_in_progress,
            'reconnection_wave': self.reconnection_wave[-10:] if self.reconnection_wave else []  # Last 10 events
        }
