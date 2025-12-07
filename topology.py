"""
Network topology management for IoT simulation
Node placement, connectivity, and broker failover
"""

import random
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class NodeType(Enum):
    """types of nodes in the topology"""
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    GATEWAY = "gateway"
    BROKER = "broker"
    CONTROLLER = "controller"


class ConnectionStatus(Enum):
    """connection status between nodes"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    WEAK_SIGNAL = "weak_signal"


@dataclass
class NetworkNode:
    """A node in the network topology"""
    node_id: str
    node_type: NodeType
    protocol: str  # "wifi", "ble", "zigbee"
    position: Tuple[float, float]  # (x, y)
    range: float  # communication range in meters
    data_rate: float  # maximum data rate in bps
    energy_level: float = 100.0  # percentage
    is_active: bool = True
    
    # broker-specific attributes
    is_broker: bool = False
    broker_priority: int = 0  # for failover (higher = better)
    connected_clients: Set[str] = None
    
    def __post_init__(self):
        if self.connected_clients is None:
            self.connected_clients = set()


class NetworkTopology:
    """Manages network topology and connectivity"""
    
    def __init__(self):
        self.nodes: Dict[str, NetworkNode] = {}
        self.connections: Dict[str, Set[str]] = {}  # adjacency list
        self.active_brokers: List[str] = []
        
    def add_node(self, node: NetworkNode):
        """Add a node to the topology"""
        self.nodes[node.node_id] = node
        self.connections[node.node_id] = set()
        
        if node.is_broker and node.is_active:
            self.active_brokers.append(node.node_id)
            self.active_brokers.sort(
                key=lambda broker_id: self.nodes[broker_id].broker_priority, 
                reverse=True
            )
            
    def remove_node(self, node_id: str):
        """Remove a node from the topology"""
        if node_id in self.nodes:
            # remove from connections
            for connected_node in self.connections.get(node_id, set()):
                if connected_node in self.connections:
                    self.connections[connected_node].discard(node_id)
                    
            # remove node's own connections
            if node_id in self.connections:
                del self.connections[node_id]
                
            # remove from nodes
            del self.nodes[node_id]
            
            # remove from active brokers if applicable
            if node_id in self.active_brokers:
                self.active_brokers.remove(node_id)
                
    def update_node_position(self, node_id: str, new_position: Tuple[float, float]):
        """Update node position and recalculate connections"""
        if node_id in self.nodes:
            self.nodes[node_id].position = new_position
            self._recalculate_connections()
            
    def _recalculate_connections(self):
        """Recalculate all connections based on positions and ranges"""
        # clear existing connections
        for node_id in self.connections:
            self.connections[node_id].clear()
            
        # calculate new connections
        node_ids = list(self.nodes.keys())
        
        for i, node1_id in enumerate(node_ids):
            node1 = self.nodes[node1_id]
            if not node1.is_active:
                continue
                
            for j in range(i + 1, len(node_ids)):
                node2_id = node2_id = node_ids[j]
                node2 = self.nodes[node2_id]
                if not node2.is_active:
                    continue
                    
                # calculate distance
                distance = self._calculate_distance(node1.position, node2.position)
                
                # check if nodes are in range (both directions)
                if (distance <= node1.range and distance <= node2.range and
                    node1.protocol == node2.protocol):  # same protocol required
                    
                    self.connections[node1_id].add(node2_id)
                    self.connections[node2_id].add(node1_id)
                    
    def _calculate_distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two positions"""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5
        
    def get_connection_status(self, node1_id: str, node2_id: str) -> ConnectionStatus:
        """Get connection status between two nodes"""
        if (node1_id in self.connections and 
            node2_id in self.connections[node1_id]):
            
            # calculate signal strength based on distance
            node1 = self.nodes[node1_id]
            node2 = self.nodes[node2_id]
            distance = self._calculate_distance(node1.position, node2.position)
            
            # signal strength decreases with distance
            max_range = min(node1.range, node2.range)
            signal_strength = 1.0 - (distance / max_range)
            
            if signal_strength > 0.7:
                return ConnectionStatus.CONNECTED
            elif signal_strength > 0.3:
                return ConnectionStatus.WEAK_SIGNAL
            else:
                return ConnectionStatus.DISCONNECTED
                
        return ConnectionStatus.DISCONNECTED
        
    def find_path(self, source_id: str, target_id: str, max_hops: int = 10) -> List[str]:
        """Find a path between two nodes using BFS"""
        if source_id not in self.nodes or target_id not in self.nodes:
            return []
            
        if source_id == target_id:
            return [source_id]
            
        visited = set()
        queue = [(source_id, [source_id])]
        
        while queue:
            current_id, path = queue.pop(0)
            
            if len(path) > max_hops:
                continue
                
            if current_id == target_id:
                return path
                
            visited.add(current_id)
            
            for neighbor in self.connections.get(current_id, set()):
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))
                    
        return []  # no path found
        
    def get_best_broker_for_node(self, node_id: str) -> Optional[str]:
        """Find the best available broker for a node"""
        if not self.active_brokers:
            return None
            
        # try to find a broker that's directly connected
        for broker_id in self.active_brokers:
            if broker_id in self.connections.get(node_id, set()):
                return broker_id
                
        # if no direct connection, find the closest broker via path
        shortest_path = None
        best_broker = None
        
        for broker_id in self.active_brokers:
            path = self.find_path(node_id, broker_id)
            if path and (shortest_path is None or len(path) < len(shortest_path)):
                shortest_path = path
                best_broker = broker_id
                
        return best_broker
        
    def broker_failover(self, failed_broker_id: str):
        """Handle broker failure by reassigning clients"""
        if failed_broker_id not in self.active_brokers:
            return
            
        self.active_brokers.remove(failed_broker_id)
        failed_broker = self.nodes.get(failed_broker_id)
        
        if failed_broker:
            # reassign connected clients to other brokers
            for client_id in list(failed_broker.connected_clients):
                new_broker = self.get_best_broker_for_node(client_id)
                if new_broker:
                    self.nodes[new_broker].connected_clients.add(client_id)
                    failed_broker.connected_clients.remove(client_id)
                    
    def get_topology_stats(self) -> Dict:
        """Get topology statistics"""
        total_nodes = len(self.nodes)
        active_nodes = sum(1 for node in self.nodes.values() if node.is_active)
        total_connections = sum(len(conns) for conns in self.connections.values()) // 2  # undirected
        
        node_types = {}
        protocols = {}
        
        for node in self.nodes.values():
            node_types[node.node_type.value] = node_types.get(node.node_type.value, 0) + 1
            protocols[node.protocol] = protocols.get(node.protocol, 0) + 1
            
        return {
            'total_nodes': total_nodes,
            'active_nodes': active_nodes,
            'total_connections': total_connections,
            'active_brokers': len(self.active_brokers),
            'node_types': node_types,
            'protocols': protocols,
            'network_density': total_connections / (total_nodes * (total_nodes - 1) / 2) if total_nodes > 1 else 0
        }