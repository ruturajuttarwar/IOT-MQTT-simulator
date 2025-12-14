"""
IoT Node - represents each simulated device
Integrates MAC, MQTT, Energy, and Mobility
"""

import asyncio
import random
import time
from typing import Tuple, Optional
from config.phy_profiles import get_profile
from config.simulation_config import AREA_WIDTH, AREA_HEIGHT, MOBILITY_MODEL
from sim.energy import EnergyTracker
from sim.wifi_mac import WiFiMAC
from sim.ble_mac import BLEMAC
from sim.mqtt_client_sim import MQTTClientSim
from sim.mobility import create_mobility_model
from utils.logging_utils import log_info
import math


class Node:
    """Simulated IoT device node"""
    
    def __init__(self, node_id: str, protocol: str, is_mobile: bool, broker_address: str):
        self.node_id = node_id
        self.protocol = protocol.lower()
        self.is_mobile = is_mobile
        self.broker_address = broker_address
        self.role = 'both'  # publisher, subscriber, both
        self.subscribe_to = []  # List of specific node IDs to subscribe to
        self.qos = 1  # Default QoS level (will be set by user)
        self.sensor_interval = 10.0  # Default sensor interval (will be set by user)
        
        # PHY profiles (node knows both)
        self.ble_profile = get_profile('ble')
        self.wifi_profile = get_profile('wifi')
        self.phy_profile = get_profile(self.protocol)  # Currently selected
        
        # Position
        self.position: Tuple[float, float] = (
            random.uniform(0, AREA_WIDTH),
            random.uniform(0, AREA_HEIGHT)
        )
        
        # Components
        self.energy_tracker = EnergyTracker(self.phy_profile)
        
        if self.protocol == 'ble':
            self.mac = BLEMAC(node_id)
        else:  # wifi
            self.mac = WiFiMAC(node_id)
            
        self.mqtt_client = MQTTClientSim(node_id, broker_address)
        
        # Mobility
        if is_mobile:
            self.mobility = create_mobility_model(MOBILITY_MODEL, self.position)
        else:
            self.mobility = None
            
        # State
        self.running = False
        self.connected = False
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'sensor_readings': 0,
            'position_updates': 0
        }
        
        # Sensor data generation (will be set by user or use default)
        self.last_sensor_reading = time.time()  # Initialize to current time to prevent immediate publish
        
    def calculate_distance_to_broker(self, broker_pos: tuple = None) -> float:
        """Calculate distance to broker"""
        # Use provided broker position or get from failover manager or default
        if broker_pos is None:
            # Try to get from failover manager if available
            if hasattr(self, 'failover_manager') and self.failover_manager:
                broker_address = self.broker_address
                broker_pos = self.failover_manager.broker_positions.get(broker_address, (500, 500))
            else:
                broker_pos = (500, 500)  # Default center
        
        dx = self.position[0] - broker_pos[0]
        dy = self.position[1] - broker_pos[1]
        return math.sqrt(dx*dx + dy*dy)
    
    def is_in_range(self) -> bool:
        """Check if node is within range of broker"""
        distance = self.calculate_distance_to_broker()
        max_range = self.phy_profile.get('range_meters', 100)
        return distance <= max_range
    
    def calculate_latency_ms(self) -> float:
        """Calculate latency based on distance and protocol"""
        distance = self.calculate_distance_to_broker()
        base_latency = self.phy_profile.get('base_latency_ms', 10)
        
        # Add distance-based latency (signal propagation + processing)
        # WiFi: distance increases latency/jitter
        # BLE: connection interval dominates
        if self.protocol == 'wifi':
            distance_latency = distance * 0.1  # 0.1ms per meter
        else:  # BLE
            distance_latency = distance * 0.05  # Less affected by distance
        
        return base_latency + distance_latency
    
    async def run(self):
        """Main node loop"""
        self.running = True
        
        # Check if in range before connecting
        if not self.is_in_range():
            distance = self.calculate_distance_to_broker()
            max_range = self.phy_profile.get('range_meters', 100)
            print(f"[RANGE] Node {self.node_id} out of range: {distance:.1f}m > {max_range}m")
            self.connected = False
            return
        
        # Connect to broker
        await self.mqtt_client.connect()
        self.connected = True
        
        # Subscribe to topics based on role
        if self.role in ['subscriber', 'both']:
            # Set up message callback to track RX energy
            async def on_message_received(message):
                # Track RX energy when receiving messages
                payload_size = len(message.get('payload', b''))
                self.energy_tracker.set_state('rx')
                rx_energy = self.energy_tracker.add_rx_energy(payload_size)
                self.stats['messages_received'] += 1
                print(f"[RX] Node {self.node_id} received {payload_size}B, RX energy: {rx_energy:.4f} mJ, Battery: {self.energy_tracker.battery_level:.2f}%")
                # Back to idle
                self.energy_tracker.set_state('idle')
            
            self.mqtt_client.on_message_callback = on_message_received
            
            if self.subscribe_to:
                # Subscribe to specific publishers with node's QoS
                for publisher_id in self.subscribe_to:
                    await self.mqtt_client.subscribe(f"sensors/{publisher_id}/data", qos=self.qos)
            else:
                # Subscribe to all with node's QoS
                await self.mqtt_client.subscribe(f"sensors/+/data", qos=self.qos)
            
            # Always subscribe to own command topic
            await self.mqtt_client.subscribe(f"nodes/{self.node_id}/command", qos=self.qos)
        
        # Main loop
        while self.running:
            try:
                # Check if node is dead (no battery)
                if self.energy_tracker.battery_level <= 0:
                    print(f"[DEAD] Node {self.node_id} has died (0% battery)")
                    self.running = False
                    self.connected = False
                    # Publish death message
                    try:
                        death_msg = f"Node {self.node_id} DEAD - Battery depleted".encode()
                        await self.mqtt_client.publish(f"nodes/{self.node_id}/status", death_msg, qos=0)
                    except:
                        pass
                    await self.mqtt_client.disconnect(send_lwt=True)
                    break
                
                # Check if simulation is stopped
                if not self.running:
                    await asyncio.sleep(0.5)
                    continue
                
                # Update mobility
                if self.is_mobile and self.mobility:
                    old_pos = self.position
                    self.position = self.mobility.update(1.0)  # 1 second update
                    
                    if old_pos != self.position:
                        self.stats['position_updates'] += 1
                        
                        # Check if still in range after moving
                        if not self.is_in_range():
                            distance = self.calculate_distance_to_broker()
                            max_range = self.phy_profile.get('range_meters', 100)
                            print(f"[DISCONNECT] Node {self.node_id} moved out of range: {distance:.1f}m > {max_range}m")
                            self.connected = False
                            await self.mqtt_client.disconnect(send_lwt=True)
                            break
                        
                # Intelligent protocol selection DISABLED - keep user's choice
                # Users can manually set protocol via UI
                pass
                
                # Ensure we're in idle state at start of loop
                self.energy_tracker.set_state('idle')
                
                # Generate sensor data only if publisher
                if self.role in ['publisher', 'both']:
                    await self._generate_sensor_data()
                
                # Send keep-alive
                await self.mqtt_client.send_ping()
                
                # Check connection
                if not await self.mqtt_client.check_connection():
                    # Try to reconnect
                    await self.mqtt_client.reconnect()
                    
                # Update energy state - use sleep if supported, otherwise idle
                if self.mac.is_sleeping() if hasattr(self.mac, 'is_sleeping') else False:
                    self.energy_tracker.set_state('sleep')
                else:
                    self.energy_tracker.set_state('idle')
                    
                await asyncio.sleep(1.0)
                
            except Exception as e:
                print(f"Node {self.node_id} error: {e}")
                await asyncio.sleep(1.0)
                
    async def _generate_sensor_data(self):
        """Generate and publish sensor data"""
        current_time = time.time()
        
        # Check if enough time has passed since last reading
        time_since_last = current_time - self.last_sensor_reading
        if time_since_last >= self.sensor_interval:
            # Debug: Log when we're about to publish
            print(f"[DEBUG] Node {self.node_id}: Publishing (interval={self.sensor_interval}s, time_since_last={time_since_last:.1f}s)")
            
            # Generate sensor reading
            temperature = random.uniform(20.0, 30.0)
            humidity = random.uniform(40.0, 60.0)
            
            payload = f"temp:{temperature:.1f},humidity:{humidity:.1f}".encode()
            topic = f"sensors/{self.node_id}/data"
            
            # Track topic for heatmap
            from sim.metrics import global_metrics
            if global_metrics:
                global_metrics.record_topic_message(topic)
            
            # Check if node has enough battery
            if self.energy_tracker.battery_level <= 0:
                print(f"[ENERGY] Node {self.node_id} is DEAD (0% battery)")
                self.running = False
                return
            
            # Set energy state to TX
            self.energy_tracker.set_state('tx')
            
            # Calculate distance to broker for MAC layer
            distance = self.calculate_distance_to_broker()
            max_range = self.phy_profile.get('range_meters', 100)
            
            # Send via MAC layer with distance
            result = await self.mac.send_packet(payload, "broker", distance, max_range)
            
            if result.get('success'):
                # Publish via MQTT with configured QoS (ensure it's used)
                qos_level = int(self.qos) if hasattr(self, 'qos') else 1
                await self.mqtt_client.publish(topic, payload, qos=qos_level)
                
                # Track TX energy for initial transmission
                energy_used = self.energy_tracker.add_tx_energy(len(payload))
                
                # Track ADDITIONAL energy for retries (critical fix!)
                num_retries = result.get('retries', 0)
                if num_retries > 0:
                    for _ in range(num_retries):
                        retry_energy = self.energy_tracker.add_tx_energy(len(payload))
                        energy_used += retry_energy
                    print(f"[ENERGY] Node {self.node_id} TX with {num_retries} retries: {energy_used:.4f} mJ, Battery: {self.energy_tracker.battery_level:.2f}%")
                else:
                    print(f"[ENERGY] Node {self.node_id} TX: {energy_used:.4f} mJ, Battery: {self.energy_tracker.battery_level:.2f}%")
                
                # Log PDR if available
                if 'pdr' in result:
                    print(f"[PDR] Node {self.node_id} at {distance:.1f}m: PDR={result['pdr']:.2%}")
                
                self.stats['messages_sent'] += 1
                self.stats['sensor_readings'] += 1
                
                # IMPORTANT: Update last_sensor_reading AFTER successful publish
                self.last_sensor_reading = current_time
                
            # Back to idle
            self.energy_tracker.set_state('idle')
            
    async def stop(self):
        """Stop the node"""
        self.running = False
        await self.mqtt_client.disconnect()
        
    def select_best_phy(self, distance_to_broker: float, data_rate_needed: float) -> str:
        """Intelligently select BLE or WiFi based on conditions"""
        # Decision factors
        battery_low = self.energy_tracker.battery_level < 20
        high_data_rate = data_rate_needed > 1_000_000  # > 1 Mbps
        long_distance = distance_to_broker > 50  # > 50 meters
        
        # Decision logic
        if battery_low and not high_data_rate:
            # Save power with BLE
            return 'ble'
        elif high_data_rate or long_distance:
            # Need WiFi performance
            return 'wifi'
        elif distance_to_broker < 30:
            # Close range, use BLE for efficiency
            return 'ble'
        else:
            # Default to current protocol
            return self.protocol
            
    def switch_protocol(self, new_protocol: str):
        """Switch between BLE and WiFi"""
        if new_protocol == self.protocol:
            return
            
        old_protocol = self.protocol
        self.protocol = new_protocol
        self.phy_profile = get_profile(new_protocol)
        
        # Recreate MAC layer
        if new_protocol == 'ble':
            self.mac = BLEMAC(self.node_id)
        else:
            self.mac = WiFiMAC(self.node_id)
            
        # Update energy tracker
        self.energy_tracker = EnergyTracker(self.phy_profile)
        
        log_info(f"Node {self.node_id} switched from {old_protocol.upper()} to {new_protocol.upper()}")
    
    def get_state(self) -> dict:
        """Get current node state"""
        return {
            'node_id': self.node_id,
            'protocol': self.protocol,
            'is_mobile': self.is_mobile,
            'position': self.position,
            'connected': self.mqtt_client.connected,
            'battery': self.energy_tracker.battery_level,
            'qos': self.qos,
            'sensor_interval': self.sensor_interval,
            'distance_to_broker': self.calculate_distance_to_broker(),
            'max_range': self.phy_profile.get('range_meters', 100),
            'latency_ms': self.calculate_latency_ms(),
            'stats': self.stats,
            'mqtt_stats': self.mqtt_client.get_stats(),
            'mac_stats': self.mac.get_stats(),
            'energy_stats': self.energy_tracker.get_stats(),
            'phy_options': {
                'ble': self.ble_profile['name'],
                'wifi': self.wifi_profile['name']
            }
        }
