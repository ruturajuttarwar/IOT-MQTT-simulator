"""
Mobility models for IoT device movement
Grid-based and random waypoint movement patterns
"""

import math
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class MobilityModel(Enum):
    """Types of mobility models"""
    STATIC = "static"
    GRID = "grid"
    RANDOM_WAYPOINT = "random_waypoint"
    RANDOM_DIRECTION = "random_direction"


@dataclass
class Position:
    """2D position with coordinates"""
    x: float
    y: float
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate Euclidean distance to another position"""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
    
    def __str__(self):
        return f"({self.x:.2f}, {self.y:.2f})"


@dataclass
class MovementConfig:
    """Configuration for mobility models"""
    model: MobilityModel
    speed_range: Tuple[float, float] = (1.0, 5.0)  # m/s
    pause_range: Tuple[float, float] = (0.0, 10.0)  # seconds
    area_width: float = 1000.0  # meters
    area_height: float = 1000.0  # meters
    grid_cell_size: float = 100.0  # meters for grid model


class MobileNode:
    """A node that can move according to mobility models"""
    
    def __init__(self, node_id: str, initial_position: Position, config: MovementConfig):
        self.node_id = node_id
        self.position = initial_position
        self.config = config
        self.destination: Optional[Position] = None
        self.speed: float = 0.0
        self.pause_time_remaining: float = 0.0
        self.total_distance_traveled: float = 0.0
        self.movement_history: List[Tuple[float, Position]] = []  # (timestamp, position)
        
    def update_position(self, current_time: float, time_delta: float) -> bool:
        """Update node position based on mobility model"""
        self.movement_history.append((current_time, Position(self.position.x, self.position.y)))
        
        # limit history size to prevent memory issues
        if len(self.movement_history) > 1000:
            self.movement_history.pop(0)
            
        if self.pause_time_remaining > 0:
            self.pause_time_remaining -= time_delta
            return False  # no position change
            
        if self.destination is None:
            self._choose_new_destination()
            return False
            
        # move toward destination
        distance_to_dest = self.position.distance_to(self.destination)
        movement_this_step = self.speed * time_delta
        
        if movement_this_step >= distance_to_dest:
            # reached destination
            self.position = self.destination
            self.total_distance_traveled += distance_to_dest
            self._start_pause()
            return True
        else:
            # move partway toward destination
            ratio = movement_this_step / distance_to_dest
            new_x = self.position.x + (self.destination.x - self.position.x) * ratio
            new_y = self.position.y + (self.destination.y - self.position.y) * ratio
            self.position = Position(new_x, new_y)
            self.total_distance_traveled += movement_this_step
            return True
            
    def _choose_new_destination(self):
        """Choose new destination based on mobility model"""
        if self.config.model == MobilityModel.STATIC:
            self.destination = None
            self.speed = 0.0
            
        elif self.config.model == MobilityModel.GRID:
            self._choose_grid_destination()
            
        elif self.config.model == MobilityModel.RANDOM_WAYPOINT:
            self._choose_random_destination()
            
        elif self.config.model == MobilityModel.RANDOM_DIRECTION:
            self._choose_random_direction()
            
    def _choose_grid_destination(self):
        """Choose destination in grid pattern"""
        grid_x = math.floor(self.position.x / self.config.grid_cell_size)
        grid_y = math.floor(self.position.y / self.config.grid_cell_size)
        
        # move to adjacent grid cell
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        dx, dy = random.choice(directions)
        
        new_grid_x = max(0, min(grid_x + dx, math.floor(self.config.area_width / self.config.grid_cell_size) - 1))
        new_grid_y = max(0, min(grid_y + dy, math.floor(self.config.area_height / self.config.grid_cell_size) - 1))
        
        # random position within the grid cell
        dest_x = random.uniform(
            new_grid_x * self.config.grid_cell_size,
            (new_grid_x + 1) * self.config.grid_cell_size
        )
        dest_y = random.uniform(
            new_grid_y * self.config.grid_cell_size,
            (new_grid_y + 1) * self.config.grid_cell_size
        )
        
        self.destination = Position(dest_x, dest_y)
        self.speed = random.uniform(*self.config.speed_range)
        
    def _choose_random_destination(self):
        """Choose random destination within area"""
        dest_x = random.uniform(0, self.config.area_width)
        dest_y = random.uniform(0, self.config.area_height)
        self.destination = Position(dest_x, dest_y)
        self.speed = random.uniform(*self.config.speed_range)
        
    def _choose_random_direction(self):
        """Choose random direction with current speed"""
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(50, 200)  # travel 50-200 meters in this direction
        
        dest_x = self.position.x + math.cos(angle) * distance
        dest_y = self.position.y + math.sin(angle) * distance
        
        # bound within area
        dest_x = max(0, min(dest_x, self.config.area_width))
        dest_y = max(0, min(dest_y, self.config.area_height))
        
        self.destination = Position(dest_x, dest_y)
        self.speed = random.uniform(*self.config.speed_range)
        
    def _start_pause(self):
        """Start pause at destination"""
        self.destination = None
        self.pause_time_remaining = random.uniform(*self.config.pause_range)
        
    def get_movement_stats(self) -> Dict:
        """Get movement statistics"""
        return {
            'node_id': self.node_id,
            'current_position': (self.position.x, self.position.y),
            'destination': (self.destination.x, self.destination.y) if self.destination else None,
            'speed': self.speed,
            'pause_time_remaining': self.pause_time_remaining,
            'total_distance_traveled': self.total_distance_traveled,
            'position_history_length': len(self.movement_history)
        }


class MobilityManager:
    """Manages movement of all mobile nodes"""
    
    def __init__(self, area_width: float = 1000.0, area_height: float = 1000.0):
        self.area_width = area_width
        self.area_height = area_height
        self.nodes: Dict[str, MobileNode] = {}
        self.update_interval = 1.0  # seconds
        
    def add_node(self, node_id: str, initial_x: float, initial_y: float, 
                model: MobilityModel, **kwargs) -> MobileNode:
        """Add a mobile node"""
        config = MovementConfig(
            model=model,
            area_width=self.area_width,
            area_height=self.area_height,
            **kwargs
        )
        
        position = Position(initial_x, initial_y)
        node = MobileNode(node_id, position, config)
        self.nodes[node_id] = node
        return node
        
    def remove_node(self, node_id: str):
        """Remove a mobile node"""
        if node_id in self.nodes:
            del self.nodes[node_id]
            
    def update_all_positions(self, current_time: float, time_delta: float) -> Dict[str, bool]:
        """Update all node positions"""
        updates = {}
        for node_id, node in self.nodes.items():
            updated = node.update_position(current_time, time_delta)
            updates[node_id] = updated
        return updates
        
    def get_node_position(self, node_id: str) -> Optional[Position]:
        """Get current position of a node"""
        if node_id in self.nodes:
            return self.nodes[node_id].position
        return None
        
    def get_all_positions(self) -> Dict[str, Position]:
        """Get all node positions"""
        return {node_id: node.position for node_id, node in self.nodes.items()}
        
    def get_distance_between(self, node1_id: str, node2_id: str) -> Optional[float]:
        """Get distance between two nodes"""
        pos1 = self.get_node_position(node1_id)
        pos2 = self.get_node_position(node2_id)
        
        if pos1 and pos2:
            return pos1.distance_to(pos2)
        return None