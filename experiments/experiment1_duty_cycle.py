"""
Experiment 1: Duty Cycle Impact
Study how sleep ratio affects latency and battery life
"""

import asyncio
from typing import List
from sim.node import Node
from sim.metrics import MetricsCollector
from config.phy_profiles import BLE_PROFILE


async def run_experiment(duration: int = 60):
    """Run duty cycle experiment"""
    print("=" * 60)
    print("EXPERIMENT 1: Duty Cycle Impact")
    print("=" * 60)
    
    # Test different connection intervals
    intervals = [20, 60, 100, 200, 500, 1000]  # milliseconds
    results = []
    
    for interval_ms in intervals:
        print(f"\nTesting connection interval: {interval_ms}ms")
        
        # Create test node
        node = Node(
            node_id=f"test_ble_{interval_ms}",
            protocol='ble',
            is_mobile=False,
            broker_address="localhost:1883"
        )
        
        # Set connection interval
        if hasattr(node.mac, 'set_connection_interval'):
            node.mac.set_connection_interval(interval_ms)
        
        # Run for test duration
        task = asyncio.create_task(node.run())
        await asyncio.sleep(duration)
        await node.stop()
        
        # Collect results
        energy_stats = node.energy_tracker.get_stats()
        mqtt_stats = node.mqtt_client.get_stats()
        
        result = {
            'interval_ms': interval_ms,
            'duty_cycle': energy_stats['duty_cycle_percent'],
            'avg_power_mw': energy_stats['avg_power_mw'],
            'messages_sent': mqtt_stats['messages_sent'],
            'battery_life_hours': node.energy_tracker.estimate_battery_life_hours(),
            'avg_latency_ms': interval_ms / 2.0  # Approximate
        }
        
        results.append(result)
        
        print(f"  Duty cycle: {result['duty_cycle']:.2f}%")
        print(f"  Avg power: {result['avg_power_mw']:.2f}mW")
        print(f"  Battery life: {result['battery_life_hours']:.1f} hours")
        print(f"  Avg latency: {result['avg_latency_ms']:.1f}ms")
    
    # Summary
    print("\n" + "=" * 60)
    print("EXPERIMENT 1 RESULTS")
    print("=" * 60)
    print(f"{'Interval':<12} {'Duty Cycle':<12} {'Power (mW)':<12} {'Battery (h)':<12} {'Latency (ms)':<12}")
    print("-" * 60)
    
    for r in results:
        print(f"{r['interval_ms']:<12} {r['duty_cycle']:<12.2f} {r['avg_power_mw']:<12.2f} "
              f"{r['battery_life_hours']:<12.1f} {r['avg_latency_ms']:<12.1f}")
    
    print("\nKey Insights:")
    print("- Shorter intervals = Lower latency but higher power consumption")
    print("- Longer intervals = Better battery life but higher latency")
    print("- Optimal interval depends on application requirements")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_experiment())
