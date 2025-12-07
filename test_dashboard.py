#!/usr/bin/env python3
"""
Quick test to verify dashboard displays nodes
"""

import asyncio
import sys

# Add current directory to path
sys.path.insert(0, '.')

from config.simulation_config import *
from sim.node import Node
from sim.metrics import MetricsCollector
from sim.broker_failover import BrokerFailoverManager
from gui.redesigned_dashboard import start_dashboard

async def test_dashboard():
    """Test dashboard with minimal setup"""
    print("Creating test nodes...")
    
    # Create a few test nodes
    nodes = []
    for i in range(5):
        protocol = 'ble' if i % 2 == 0 else 'wifi'
        node = Node(
            node_id=f"test_{protocol}_{i}",
            protocol=protocol,
            is_mobile=False,
            broker_address="localhost:1883"
        )
        nodes.append(node)
    
    print(f"Created {len(nodes)} nodes")
    
    # Create metrics collector
    metrics = MetricsCollector()
    
    # Create failover manager
    failover = BrokerFailoverManager("localhost:1883", "localhost:1884")
    
    # Start nodes
    print("Starting nodes...")
    node_tasks = []
    for node in nodes:
        task = asyncio.create_task(node.run())
        node_tasks.append(task)
    
    # Give nodes time to connect
    await asyncio.sleep(2)
    
    print(f"Dashboard starting on http://localhost:{GUI_PORT}")
    print("Open your browser and check if nodes appear!")
    print("Press Ctrl+C to stop")
    
    # Start dashboard
    try:
        await start_dashboard(nodes, metrics, failover, GUI_PORT)
    except KeyboardInterrupt:
        print("\nStopping...")
        for node in nodes:
            await node.stop()

if __name__ == "__main__":
    asyncio.run(test_dashboard())
