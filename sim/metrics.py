"""
Metrics collection and tracking for simulation
"""

import asyncio
import time
from typing import Dict, List
from collections import defaultdict


# Global metrics instance for easy access
global_metrics = None

class MetricsCollector:
    """Collects and tracks all simulation metrics"""
    
    def __init__(self):
        global global_metrics
        global_metrics = self
        self.start_time = time.time()
        
        # Global metrics
        self.total_messages_sent = 0
        self.total_messages_received = 0
        self.total_duplicates = 0
        self.total_failures = 0
        
        # Latency tracking
        self.latencies = []
        
        # Per-topic metrics
        self.topic_messages: Dict[str, int] = defaultdict(int)
        self.topic_rates: Dict[str, float] = defaultdict(float)
        
        # Per-node metrics
        self.node_metrics: Dict[str, Dict] = {}
        
        # Broker metrics
        self.broker_queue_depths = []
        
        # Delivery ratio
        self.delivery_attempts = 0
        self.delivery_successes = 0
        
    async def collect_loop(self, nodes: List):
        """Continuous metrics collection"""
        while True:
            await self.collect_metrics(nodes)
            await asyncio.sleep(1.0)
            
    async def collect_metrics(self, nodes: List):
        """Collect metrics from all nodes"""
        self.total_messages_sent = 0
        self.total_messages_received = 0
        self.total_duplicates = 0
        
        for node in nodes:
            # Collect from MQTT client
            mqtt_stats = node.mqtt_client.get_stats()
            
            self.total_messages_sent += mqtt_stats['messages_sent']
            self.total_messages_received += mqtt_stats['messages_received']
            self.total_duplicates += mqtt_stats['duplicates_received']
            
            # Store per-node metrics
            self.node_metrics[node.node_id] = {
                'mqtt': mqtt_stats,
                'mac': node.mac.get_stats(),
                'energy': node.energy_tracker.get_stats(),
                'position': node.position
            }
            
    def record_latency(self, latency_ms: float):
        """Record end-to-end latency"""
        self.latencies.append(latency_ms)
        
    def record_topic_message(self, topic: str):
        """Record message for topic"""
        self.topic_messages[topic] += 1
        
    def record_delivery_attempt(self, success: bool):
        """Record delivery attempt"""
        self.delivery_attempts += 1
        if success:
            self.delivery_successes += 1
            
    def get_delivery_ratio(self) -> float:
        """Calculate delivery ratio"""
        if self.delivery_attempts == 0:
            return 0.0
        return self.delivery_successes / self.delivery_attempts
        
    def get_avg_latency(self) -> float:
        """Get average latency"""
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)
        
    def get_topic_heatmap(self) -> Dict[str, float]:
        """Get messages/sec per topic"""
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return {}
            
        return {
            topic: count / elapsed
            for topic, count in self.topic_messages.items()
        }
        
    def get_summary(self) -> Dict:
        """Get comprehensive metrics summary"""
        return {
            'total_messages_sent': self.total_messages_sent,
            'total_messages_received': self.total_messages_received,
            'total_duplicates': self.total_duplicates,
            'delivery_ratio': self.get_delivery_ratio(),
            'avg_latency_ms': self.get_avg_latency(),
            'topic_heatmap': self.get_topic_heatmap(),
            'node_count': len(self.node_metrics),
            'uptime_seconds': time.time() - self.start_time
        }
