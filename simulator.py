"""
Main simulation engine for IoT network simulation
Coordinates all components and runs the simulation
"""

import time
import threading
import random
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from events import EventScheduler, SimulationEvent, EventType
from mobility import MobilityManager, MobilityModel, Position
from topology import NetworkTopology, NetworkNode, NodeType, ConnectionStatus


@dataclass
class SimulationConfig:
    """configuration for the simulation"""
    simulation_duration: float = 3600.0  # seconds
    time_scale: float = 1.0  # 1.0 = realtime, >1.0 = faster
    area_width: float = 1000.0
    area_height: float = 1000.0
    update_interval: float = 1.0  # seconds between updates
    enable_mobility: bool = True
    enable_energy_consumption: bool = True
    random_seed: int = 42


class SimulationEngine:
    """main simulation engine that coordinates all components"""
    
    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()
        self.running = False
        self.simulation_time = 0.0
        self.real_time_start = 0.0
        
        # core components
        self.event_scheduler = EventScheduler()
        self.mobility_manager = MobilityManager(
            self.config.area_width, 
            self.config.area_height
        )
        self.topology = NetworkTopology()
        
        # external protocol modules (to be registered)
        self.protocol_handlers: Dict[str, Callable] = {}
        
        # statstics
        self.statistics = {
            'events_processed': 0,
            'position_updates': 0,
            'connections_established': 0,
            'connections_lost': 0,
            'broker_failovers': 0,
            'packets_sent': 0,
            'packets_received': 0
        }
        
        # register event handlers
        self._register_event_handlers()
        
    def _register_event_handlers(self):
        """Register handlers for simulation events"""
        self.event_scheduler.register_handler(EventType.NODE_MOVEMENT, self._handle_node_movement)
        self.event_scheduler.register_handler(EventType.CONNECTION_ESTABLISHED, self._handle_connection_established)
        self.event_scheduler.register_handler(EventType.CONNECTION_LOST, self._handle_connection_lost)
        self.event_scheduler.register_handler(EventType.BROKER_FAILOVER, self._handle_broker_failover)
        self.event_scheduler.register_handler(EventType.STATISTICS_UPDATE, self._handle_statistics_update)
        
    def register_protocol_handler(self, protocol: str, handler: Callable):
        """Register a protocol-specific handler (WiFi, BLE, etc.)"""
        self.protocol_handlers[protocol] = handler
        
    def add_node(self, node_id: str, node_type: NodeType, protocol: str, 
                initial_x: float, initial_y: float, range: float, data_rate: float,
                mobility_model: MobilityModel = MobilityModel.STATIC, 
                is_broker: bool = False, broker_priority: int = 0) -> bool:
        """Add a node to the simulation"""
        try:
            # create network node
            network_node = NetworkNode(
                node_id=node_id,
                node_type=node_type,
                protocol=protocol,
                position=(initial_x, initial_y),
                range=range,
                data_rate=data_rate,
                is_broker=is_broker,
                broker_priority=broker_priority
            )
            
            self.topology.add_node(network_node)
            
            # add to mobility manager if mobility is enabled
            if self.config.enable_mobility and mobility_model != MobilityModel.STATIC:
                self.mobility_manager.add_node(
                    node_id, initial_x, initial_y, mobility_model
                )
                
            # schedule periodic updates for this node
            if self.config.enable_mobility:
                self.event_scheduler.schedule_event(
                    EventType.NODE_MOVEMENT,
                    delay=self.config.update_interval,
                    source=node_id,
                    priority=2
                )
                
            return True
            
        except Exception as e:
            print(f"Error adding node {node_id}: {e}")
            return False
            
    def remove_node(self, node_id: str):
        """Remove a node from the simulation"""
        self.topology.remove_node(node_id)
        self.mobility_manager.remove_node(node_id)
        
    def start(self):
        """Start the simulation"""
        if self.running:
            print("Simulation already running")
            return
            
        self.running = True
        self.real_time_start = time.time()
        self.event_scheduler.start()
        
        print(f"Simulation started at time {self.simulation_time}")
        
        # start the main simulation loop in a separate thread
        self.simulation_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.simulation_thread.start()
        
    def stop(self):
        """Stop the simulation"""
        self.running = False
        self.event_scheduler.stop()
        
        if hasattr(self, 'simulation_thread'):
            self.simulation_thread.join(timeout=1.0)
            
        print(f"Simulation stopped at time {self.simulation_time}")
        
    def pause(self):
        """Pause the simulation"""
        self.running = False
        print("Simulation paused")
        
    def resume(self):
        """Resume the simulation"""
        self.start()
        
    def _simulation_loop(self):
        """Main simulation loop"""
        last_update_time = self.simulation_time
        
        while self.running and self.simulation_time < self.config.simulation_duration:
            current_real_time = time.time()
            real_time_elapsed = current_real_time - self.real_time_start
            simulation_time_elapsed = real_time_elapsed * self.config.time_scale
            
            self.simulation_time = simulation_time_elapsed
            
            # process events up to current simulation time
            events_processed = self.event_scheduler.process_events(
                time_limit=0.01  # Don't spend more than 10ms processing events
            )
            self.statistics['events_processed'] += events_processed
            
            # Update Energy Consumption (disabled for simulation - nodes don't die)
            # Energy tracking is done per-operation in BLE/WiFi modules
            # This prevents nodes from dying during short experiments

            # update mobility if enabled
            if self.config.enable_mobility:
                time_delta = self.simulation_time - last_update_time
                if time_delta > 0:
                    updates = self.mobility_manager.update_all_positions(
                        self.simulation_time, time_delta
                    )
                    
                    # update topology with new positions
                    for node_id, updated in updates.items():
                        if updated:
                            node = self.mobility_manager.nodes[node_id]
                            self.topology.update_node_position(
                                node_id, (node.position.x, node.position.y)
                            )
                            self.statistics['position_updates'] += 1
                            
                    last_update_time = self.simulation_time
                    
            # schedule next update
            next_update_delay = self.config.update_interval / self.config.time_scale
            self.event_scheduler.schedule_event(
                EventType.STATISTICS_UPDATE,
                delay=next_update_delay,
                source="simulation_engine",
                data=self.get_statistics(),
                priority=3
            )
            
            # sleep to prevent busy waiting
            time.sleep(0.001)
            
    def _handle_node_movement(self, event: SimulationEvent):
        """Handle node movement event"""
        if self.config.enable_mobility:
            # reschedule the next movement update
            self.event_scheduler.schedule_event(
                EventType.NODE_MOVEMENT,
                delay=self.config.update_interval,
                source=event.source,
                priority=2
            )
            
    def _handle_connection_established(self, event: SimulationEvent):
        """Handle connection established event"""
        self.statistics['connections_established'] += 1
        print(f"Connection established: {event.source} -> {event.target}")
        
    def _handle_connection_lost(self, event: SimulationEvent):
        """Handle connection lost event"""
        self.statistics['connections_lost'] += 1
        print(f"Connection lost: {event.source} -> {event.target}")
        
    def _handle_broker_failover(self, event: SimulationEvent):
        """Handle broker failover event"""
        self.statistics['broker_failovers'] += 1
        broker_id = event.data.get('broker_id')
        self.topology.broker_failover(broker_id)
        print(f"!!! Broker failover triggered for: {broker_id} !!!")
        
    def _handle_statistics_update(self, event: SimulationEvent):
        """Handle statistics update event"""
        pass
        
    def send_packet(self, source_id: str, target_id: str, data: bytes, protocol: str) -> bool:
        """Send a packet between nodes"""
        if protocol not in self.protocol_handlers:
            print(f"No handler registered for protocol: {protocol}")
            return False
            
        # check if path exists
        path = self.topology.find_path(source_id, target_id)
        if not path:
            print(f"No path found from {source_id} to {target_id}")
            return False
            
        # use protocol-specific handler
        handler = self.protocol_handlers[protocol]
        success = handler(source_id, target_id, data, path)
        
        if success:
            self.statistics['packets_sent'] += 1
        else:
            print(f"Packet transmission failed: {source_id} -> {target_id}")
            
        return success
        
    def get_node_positions(self) -> Dict[str, tuple]:
        """Get current positions of all nodes"""
        positions = {}
        
        # get positions from mobility manager for mobile nodes
        mobility_positions = self.mobility_manager.get_all_positions()
        positions.update({node_id: (pos.x, pos.y) for node_id, pos in mobility_positions.items()})
        
        # get positions from topology for static nodes
        for node_id, node in self.topology.nodes.items():
            if node_id not in positions:
                positions[node_id] = node.position
                
        return positions
        
    def get_connections(self) -> List[tuple]:
        """Get all active connections"""
        connections = []
        for node1_id, connected_nodes in self.topology.connections.items():
            for node2_id in connected_nodes:
                if node1_id < node2_id:  # Avoid duplicates
                    status = self.topology.get_connection_status(node1_id, node2_id)
                    connections.append((node1_id, node2_id, status))
                    
        return connections
        
    def get_statistics(self) -> Dict:
        """Get comprehensive simulation statistics"""
        topology_stats = self.topology.get_topology_stats()
        
        return {
            'simulation_time': self.simulation_time,
            'real_time_elapsed': time.time() - self.real_time_start,
            'topology': topology_stats,
            'events': self.event_scheduler.get_statistics(),
            'simulation': self.statistics
        }
        
    def trigger_broker_failure(self, broker_id: str):
        """Trigger a broker failure (for testing)"""
        if broker_id in self.topology.nodes and self.topology.nodes[broker_id].is_broker:
            self.topology.nodes[broker_id].is_active = False
            self.event_scheduler.schedule_event(
                EventType.BROKER_FAILOVER,
                delay=0.1,
                source="simulation_engine",
                data={'broker_id': broker_id},
                priority=1
            )


# example usage and test
if __name__ == "__main__":
    
    # creates simulation configuration
    config = SimulationConfig(
        simulation_duration=300.0,  # 5 minutes
        time_scale=10.0,  # 10x realtime
        area_width=500.0,
        area_height=500.0,
        update_interval=0.5
    )
    
    # create simulation engine
    simulator = SimulationEngine(config)
    
    # Add dummy protocol handlers so send_packet doesn't fail
    def wifi_handler(source, target, data, path):
        # Simple simulation: Success probability based on path length
        return random.random() > 0.05 * len(path)
    
    simulator.register_protocol_handler("wifi", wifi_handler)
    simulator.register_protocol_handler("ble", wifi_handler)

    # add nodes
    # Main Broker (High Priority)
    simulator.add_node(
        "broker1", NodeType.BROKER, "wifi", 250, 250, 200, 150_000_000,
        MobilityModel.STATIC, is_broker=True, broker_priority=10
    )
    # Backup Broker (Lower Priority)
    simulator.add_node(
        "broker2", NodeType.BROKER, "wifi", 350, 350, 200, 150_000_000,
        MobilityModel.STATIC, is_broker=True, broker_priority=5
    )
    
    simulator.add_node(
        "sensor1", NodeType.SENSOR, "ble", 100, 100, 50, 1_000_000,
        MobilityModel.RANDOM_WAYPOINT
    )
    
    simulator.add_node(
        "sensor2", NodeType.SENSOR, "wifi", 400, 400, 100, 150_000_000,
        MobilityModel.GRID
    )
    
    # start simulation
    simulator.start()
    
    try:
        print("\n--- Phase 1: Initial Movement & Stability (5s) ---")
        time.sleep(5)
        
        print("\n--- Phase 2: Triggering Main Broker Failure ---")
        simulator.trigger_broker_failure("broker1")
        time.sleep(1) # Wait for failover event to process
        
        print("\n--- Phase 3: Post-Failure Stability (5s) ---")
        time.sleep(5)
        
        # print statistics
        stats = simulator.get_statistics()
        print("\n=== Final Simulation Statistics ===")
        for category, data in stats.items():
            print(f"\n{category}:")
            if isinstance(data, dict):
                for key, value in data.items():
                    print(f"  {key}: {value}")
            else:
                print(f"  {data}")
                
    finally:
        simulator.stop()