"""
Event handling system for IoT simulation
Discrete event simulation core with priority queue
"""

import heapq
import time
from typing import Callable, Any, Dict, List
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    """Types of events in the simulation"""
    NODE_MOVEMENT = "node_movement"
    PACKET_TRANSMISSION = "packet_transmission"
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_LOST = "connection_lost"
    BROKER_FAILOVER = "broker_failover"
    ENERGY_UPDATE = "energy_update"
    STATISTICS_UPDATE = "statistics_update"


@dataclass
class SimulationEvent:
    """Event in the discrete event simulation"""
    event_id: int
    event_type: EventType
    timestamp: float
    source: str
    target: str = None
    data: Any = None
    priority: int = 1  # lower number = higher priority
    
    def __lt__(self, other):
        # for heapq to maintain order by timestamp then priority
        if self.timestamp == other.timestamp:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


class EventScheduler:
    """Discrete event scheduler using priority queue"""
    
    def __init__(self):
        self.event_queue = []
        self.current_time = 0.0
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.running = False
        self.next_event_id = 0
        
    def schedule_event(self, event_type: EventType, delay: float, source: str, 
                      target: str = None, data: Any = None, priority: int = 1) -> int:
        """Schedule a new event"""
        event_id = self.next_event_id
        self.next_event_id += 1
        
        event = SimulationEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=self.current_time + delay,
            source=source,
            target=target,
            data=data,
            priority=priority
        )
        
        heapq.heappush(self.event_queue, event)
        return event_id
        
    def register_handler(self, event_type: EventType, handler: Callable):
        """Register an event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        
    def unregister_handler(self, event_type: EventType, handler: Callable):
        """Unregister an event handler"""
        if event_type in self.event_handlers:
            if handler in self.event_handlers[event_type]:
                self.event_handlers[event_type].remove(handler)
                
    def process_events(self, max_events: int = None, time_limit: float = None):
        """Process events from the queue"""
        processed = 0
        start_time = self.current_time
        
        while self.event_queue and self.running:
            if max_events and processed >= max_events:
                break
            if time_limit and (self.current_time - start_time) >= time_limit:
                break
                
            event = heapq.heappop(self.event_queue)
            self.current_time = event.timestamp
            
            # call all registered handlers for this event type
            if event.event_type in self.event_handlers:
                for handler in self.event_handlers[event.event_type]:
                    try:
                        handler(event)
                    except Exception as e:
                        print(f"Error in event handler for {event.event_type}: {e}")
                        
            processed += 1
            
        return processed
        
    def get_next_event_time(self) -> float:
        """Get timestamp of next event, or infinity if queue is empty"""
        if self.event_queue:
            return self.event_queue[0].timestamp
        return float('inf')
        
    def cancel_event(self, event_id: int) -> bool:
        """Cancel a scheduled event"""
        for i, event in enumerate(self.event_queue):
            if event.event_id == event_id:
                self.event_queue[i] = self.event_queue[-1]
                self.event_queue.pop()
                heapq.heapify(self.event_queue)
                return True
        return False
        
    def start(self):
        """Start the event scheduler"""
        self.running = True
        
    def stop(self):
        """Stop the event scheduler"""
        self.running = False
        
    def reset(self):
        """Reset the scheduler"""
        self.event_queue.clear()
        self.current_time = 0.0
        self.next_event_id = 0
        
    def get_statistics(self) -> Dict:
        """Get scheduler statistics"""
        return {
            'current_time': self.current_time,
            'events_processed': self.next_event_id,
            'pending_events': len(self.event_queue),
            'event_types_pending': {event.event_type.value for event in self.event_queue}
        }