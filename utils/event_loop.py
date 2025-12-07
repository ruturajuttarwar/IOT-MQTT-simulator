"""
Simulation event loop with pause/resume capability
"""

import asyncio
import time
from typing import Callable, List


class SimulationEventLoop:
    """Manages simulation timing and events"""
    
    def __init__(self):
        self.running = False
        self.paused = False
        self.start_time = 0
        self.simulation_time = 0
        self.time_scale = 1.0
        self.scheduled_events = []
        
    def start(self):
        """Start the simulation"""
        self.running = True
        self.paused = False
        self.start_time = time.time()
        
    def pause(self):
        """Pause the simulation"""
        self.paused = True
        
    def resume(self):
        """Resume the simulation"""
        self.paused = False
        
    def stop(self):
        """Stop the simulation"""
        self.running = False
        
    def get_time(self) -> float:
        """Get current simulation time"""
        if self.paused:
            return self.simulation_time
        return (time.time() - self.start_time) * self.time_scale
        
    async def sleep(self, duration: float):
        """Sleep for simulation time"""
        await asyncio.sleep(duration / self.time_scale)
