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
        
        # Sensor data generation
        self.sensor_interval = random.uniform(5.0, 15.0)  # seconds
        self.last_sensor_reading = 0
        
    async def run(self):
        """Main node loop"""
        self.running = True
        
        # Connect to broker
        await self.mqtt_client.connect()
        self.connected = True
        
        # Subscribe to topics based on role
        if self.role in ['subscriber', 'both']:
            if self.subscribe_to:
                # Subscribe to specific publishers
                for publisher_id in self.subscribe_to:
                    await self.mqtt_client.subscribe(f"sensors/{publisher_id}/data")
            else:
                # Subscribe to all
                await self.mqtt_client.subscribe(f"sensors/+/data")
            
            # Always subscribe to own command topic
            await self.mqtt_client.subscribe(f"nodes/{self.node_id}/command")
        
        # Main loop
        while self.running:
            try:
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
                        
                # Intelligent protocol selection DISABLED - keep user's choice
                # Users can manually set protocol via UI
                pass
                
                # Generate sensor data only if publisher
                if self.role in ['publisher', 'both']:
                    await self._generate_sensor_data()
                
                # Send keep-alive
                await self.mqtt_client.send_ping()
                
                # Check connection
                if not await self.mqtt_client.check_connection():
                    # Try to reconnect
                    await self.mqtt_client.reconnect()
                    
                # Update energy state
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
        
        if current_time - self.last_sensor_reading >= self.sensor_interval:
            self.last_sensor_reading = current_time
            
            # Generate sensor reading
            temperature = random.uniform(20.0, 30.0)
            humidity = random.uniform(40.0, 60.0)
            
            payload = f"temp:{temperature:.1f},humidity:{humidity:.1f}".encode()
            topic = f"sensors/{self.node_id}/data"
            
            # Track topic for heatmap
            from sim.metrics import global_metrics
            if global_metrics:
                global_metrics.record_topic_message(topic)
            
            # Set energy state to TX
            self.energy_tracker.set_state('tx')
            
            # Send via MAC layer
            result = await self.mac.send_packet(payload, "broker")
            
            if result.get('success'):
                # Publish via MQTT
                await self.mqtt_client.publish(topic, payload, qos=1)
                
                # Track energy
                self.energy_tracker.add_tx_energy(len(payload))
                
                self.stats['messages_sent'] += 1
                self.stats['sensor_readings'] += 1
                
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
            'stats': self.stats,
            'mqtt_stats': self.mqtt_client.get_stats(),
            'mac_stats': self.mac.get_stats(),
            'energy_stats': self.energy_tracker.get_stats(),
            'phy_options': {
                'ble': self.ble_profile['name'],
                'wifi': self.wifi_profile['name']
            }
        }
