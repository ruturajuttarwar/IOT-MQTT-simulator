#!/usr/bin/env python3
"""
IoT/MQTT Simulation - Main Entry Point
Project Groups 2&6
"""

import asyncio
import sys
from typing import List

# Configuration
from config.simulation_config import *
from config.phy_profiles import get_profile

# Simulation components
from sim.node import Node
from sim.broker_failover import BrokerFailoverManager
from sim.metrics import MetricsCollector
from utils.event_loop import SimulationEventLoop
from utils.logging_utils import setup_logging, log_info, log_success, log_warning
# GUI
from gui.flask_dashboard import start_dashboard

# Global state
nodes: List[Node] = []
event_loop: SimulationEventLoop = None
metrics: MetricsCollector = None
failover_manager: BrokerFailoverManager = None


async def initialize_simulation():
    """Initialize all simulation components"""
    global nodes, event_loop, metrics, failover_manager
    
    log_info("=" * 60)
    log_info("IoT/MQTT Simulation Initializing")
    log_info("Project Groups 2&6")
    log_info("=" * 60)
    
    # Setup logging
    setup_logging()
    
    # Initialize event loop
    event_loop = SimulationEventLoop()
    
    # Initialize metrics collector
    metrics = MetricsCollector()
    
    # Initialize broker failover manager
    failover_manager = BrokerFailoverManager(
        primary_broker=BROKER_PRIMARY,
        failover_broker=BROKER_FAILOVER
    )
    
    # Create initial nodes (just 1 node to start)
    log_info(f"Creating initial node...")
    
    # Create one initial node
    node = Node(
        node_id=f"node_0",
        protocol='wifi',
        is_mobile=False,
        broker_address=BROKER_PRIMARY
    )
    nodes.append(node)
        
    log_success(f"Created {len(nodes)} initial node")
    log_info(f"  - Use the dashboard to add more nodes dynamically")
    
    # Register nodes with failover manager
    for node in nodes:
        failover_manager.register_node(node)
        
    log_success("Simulation initialized successfully")
    

async def run_simulation():
    """Main simulation loop"""
    global nodes, event_loop, metrics
    
    log_info("Starting simulation...")
    
    # Start all nodes
    tasks = []
    for node in nodes:
        task = asyncio.create_task(node.run())
        tasks.append(task)
        
    # Start broker health checker
    tasks.append(asyncio.create_task(failover_manager.monitor_brokers()))
    
    # Start metrics collector
    tasks.append(asyncio.create_task(metrics.collect_loop(nodes)))
    
    # Run simulation
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        log_warning("Simulation interrupted by user")
    finally:
        # Cleanup
        for node in nodes:
            await node.stop()
            
        log_info("Simulation stopped")


async def main():
    """Main entry point"""
    try:
        # Initialize
        await initialize_simulation()
        
        # Start dashboard in background
        log_info(f"Starting dashboard on port {GUI_PORT}...")
        
        dashboard_task = asyncio.create_task(
            start_dashboard(nodes, metrics, failover_manager, GUI_PORT)
        )
        
        # Run simulation
        await run_simulation()
        
        # Wait for dashboard
        await dashboard_task
        
    except Exception as e:
        log_warning(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("IoT/MQTT Simulation")
    print("=" * 60)
    print(f"Nodes: {NUM_NODES} ({int(NUM_NODES * PERCENT_STATIONARY)} static, {NUM_NODES - int(NUM_NODES * PERCENT_STATIONARY)} mobile)")
    print(f"Dashboard: http://localhost:{GUI_PORT}")
    print("=" * 60)
    print()
    
    asyncio.run(main())
