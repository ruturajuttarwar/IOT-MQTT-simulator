"""
Mobility models for mobile nodes
"""

import random
import math
from typing import Tuple
from config.simulation_config import AREA_WIDTH, AREA_HEIGHT


class MobilityModel:
    """Base mobility model"""
    
    def __init__(self, initial_position: Tuple[float, float] = None):
        if initial_position:
            self.position = initial_position
        else:
            self.position = (
                random.uniform(0, AREA_WIDTH),
                random.uniform(0, AREA_HEIGHT)
            )
        self.destination = None
        self.speed_mps = 0.0
        self.pause_time_remaining = 0.0
        
    def update(self, time_delta: float) -> Tuple[float, float]:
        """Update position, return new position"""
        return self.position


class RandomWaypointMobility(MobilityModel):
    """Random Waypoint mobility model"""
    
    def __init__(self, initial_position: Tuple[float, float] = None,
                 speed_range: Tuple[float, float] = (0.5, 2.0),
                 pause_range: Tuple[float, float] = (0.0, 10.0)):
        super().__init__(initial_position)
        self.speed_range = speed_range
        self.pause_range = pause_range
        self._choose_new_destination()
        
    def _choose_new_destination(self):
        """Choose a new random destination"""
        self.destination = (
            random.uniform(0, AREA_WIDTH),
            random.uniform(0, AREA_HEIGHT)
        )
        self.speed_mps = random.uniform(*self.speed_range)
        
    def update(self, time_delta: float) -> Tuple[float, float]:
        """Update position based on random waypoint"""
        # Handle pause
        if self.pause_time_remaining > 0:
            self.pause_time_remaining -= time_delta
            return self.position
            
        # No destination, choose one
        if self.destination is None:
            self._choose_new_destination()
            return self.position
            
        # Calculate distance to destination
        dx = self.destination[0] - self.position[0]
        dy = self.destination[1] - self.position[1]
        distance = math.sqrt(dx**2 + dy**2)
        
        # Calculate movement this step
        movement = self.speed_mps * time_delta
        
        if movement >= distance:
            # Reached destination
            self.position = self.destination
            self.destination = None
            self.pause_time_remaining = random.uniform(*self.pause_range)
        else:
            # Move toward destination
            ratio = movement / distance
            self.position = (
                self.position[0] + dx * ratio,
                self.position[1] + dy * ratio
            )
            
        return self.position


class GridMobility(MobilityModel):
    """Grid-based mobility model"""
    
    def __init__(self, initial_position: Tuple[float, float] = None,
                 grid_size: float = 100.0,
                 speed_range: Tuple[float, float] = (0.5, 2.0)):
        super().__init__(initial_position)
        self.grid_size = grid_size
        self.speed_range = speed_range
        self._choose_grid_destination()
        
    def _choose_grid_destination(self):
        """Choose destination in adjacent grid cell"""
        # Current grid cell
        grid_x = int(self.position[0] / self.grid_size)
        grid_y = int(self.position[1] / self.grid_size)
        
        # Choose adjacent cell
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        dx, dy = random.choice(directions)
        
        new_grid_x = max(0, min(grid_x + dx, int(AREA_WIDTH / self.grid_size) - 1))
        new_grid_y = max(0, min(grid_y + dy, int(AREA_HEIGHT / self.grid_size) - 1))
        
        # Random position in new cell
        self.destination = (
            random.uniform(new_grid_x * self.grid_size, (new_grid_x + 1) * self.grid_size),
            random.uniform(new_grid_y * self.grid_size, (new_grid_y + 1) * self.grid_size)
        )
        self.speed_mps = random.uniform(*self.speed_range)
        
    def update(self, time_delta: float) -> Tuple[float, float]:
        """Update position based on grid movement"""
        if self.destination is None:
            self._choose_grid_destination()
            return self.position
            
        # Calculate distance to destination
        dx = self.destination[0] - self.position[0]
        dy = self.destination[1] - self.position[1]
        distance = math.sqrt(dx**2 + dy**2)
        
        # Calculate movement
        movement = self.speed_mps * time_delta
        
        if movement >= distance:
            self.position = self.destination
            self._choose_grid_destination()
        else:
            ratio = movement / distance
            self.position = (
                self.position[0] + dx * ratio,
                self.position[1] + dy * ratio
            )
            
        return self.position


def create_mobility_model(model_type: str, initial_position: Tuple[float, float] = None):
    """Factory function to create mobility models"""
    if model_type == 'random_waypoint':
        return RandomWaypointMobility(initial_position)
    elif model_type == 'grid':
        return GridMobility(initial_position)
    else:
        return MobilityModel(initial_position)  # Static
