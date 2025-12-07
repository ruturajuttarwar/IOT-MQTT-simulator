"""
BLE Test Suite - Connection Interval Sweep
Tests latency and energy consumption across different connection intervals
"""

import time
import threading
import statistics
from typing import List, Dict, Tuple
try:
    import matplotlib.pyplot as plt
    import numpy as np
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("Warning: matplotlib not available. Plots will be skipped.")
    print("To enable plots: pip install matplotlib numpy seaborn")

from ble import (
    BLECentral, BLEPeripheral, BLESimulator, BLEConnectionParams, 
    BLEPhyParams, calculate_packet_latency
)


class BLELatencyTester:
    """Test BLE latency and energy consumption"""
    
    def __init__(self):
        self.results: List[Dict] = []
        
    def test_connection_interval_sweep(self, 
                                     intervals_ms: List[int], 
                                     test_duration_s: float = 5.0,
                                     num_messages: int = 100) -> List[Dict]:
        """
        Test different connection intervals and measure performance
        
        Args:
            intervals_ms: List of connection intervals to test (in milliseconds)
            test_duration_s: Duration of each test (seconds)
            num_messages: Number of messages to send per test
            
        Returns:
            List of test results
        """
        results = []
        
        print("=" * 60)
        print("BLE Connection Interval Sweep Test")
        print("=" * 60)
        print(f"Testing {len(intervals_ms)} connection intervals")
        print(f"Test duration: {test_duration_s}s per interval")
        print(f"Messages per test: {num_messages}")
        print("-" * 60)
        
        for interval_ms in intervals_ms:
            print(f"\nTesting connection interval: {interval_ms}ms")
            result = self._test_single_interval(interval_ms, test_duration_s, num_messages)
            results.append(result)
            
            # Print immediate results
            print(f"  Average latency: {result['avg_latency_ms']:.2f}ms")
            print(f"  Energy per message: {result['energy_per_message_uj']:.2f}µJ")
            print(f"  Throughput: {result['throughput_msgs_per_s']:.2f} msgs/s")
            print(f"  Duty cycle: {result['duty_cycle_percent']:.2f}%")
            
        self.results = results
        return results
        
    def _test_single_interval(self, conn_interval_ms: int, duration_s: float, num_messages: int) -> Dict:
        """Test a single connection interval"""
        
        # Create test devices with specific connection parameters
        conn_params = BLEConnectionParams(
            conn_interval_ms=conn_interval_ms,
            supervision_timeout_ms=conn_interval_ms * 6,  # 6 intervals timeout
            max_retransmits=3
        )
        
        phy_params = BLEPhyParams()
        central = BLECentral("TEST:CENTRAL", phy_params)
        peripheral = BLEPeripheral("TEST:PERIPHERAL", phy_params)
        
        # Set up simulator
        simulator = BLESimulator()
        simulator.add_device(central)
        simulator.add_device(peripheral)
        
        try:
            # Start simulation
            simulator.start_simulation()
            
            # Establish connection
            peripheral.start_advertising(interval_ms=100)
            time.sleep(0.1)
            
            central.start_scanning()
            time.sleep(0.1)
            
            central.connect_to_device(peripheral.address, conn_params)
            peripheral.accept_connection(central.address, conn_params)
            
            # Wait for connection to stabilize
            time.sleep(conn_interval_ms / 1000.0 * 2)
            
            # Record start time and energy
            start_time = time.time()
            start_stats_central = central.get_stats()
            start_stats_peripheral = peripheral.get_stats()
            
            # Send messages and measure latency
            message_times = []
            for i in range(num_messages):
                msg_start = time.time()
                central.send_data(f"Test message {i}".encode(), peripheral.address)
                
                # Approximate latency (in real system, would measure actual ACK reception)
                estimated_latency = calculate_packet_latency(conn_interval_ms)
                message_times.append(estimated_latency)
                
                # Wait based on connection interval
                time.sleep(conn_interval_ms / 1000.0)
                
                # Stop early if duration exceeded
                if time.time() - start_time > duration_s:
                    break
                    
            # Wait for any pending transmissions
            time.sleep(conn_interval_ms / 1000.0 * 3)
            
            # Calculate statistics
            end_time = time.time()
            end_stats_central = central.get_stats()
            end_stats_peripheral = peripheral.get_stats()
            
            # Energy consumption
            central_energy = end_stats_central['total_energy_uj'] - start_stats_central['total_energy_uj']
            peripheral_energy = end_stats_peripheral['total_energy_uj'] - start_stats_peripheral['total_energy_uj']
            total_energy = central_energy + peripheral_energy
            
            # Message statistics
            actual_messages = len(message_times)
            actual_duration = end_time - start_time
            
            result = {
                'conn_interval_ms': conn_interval_ms,
                'duration_s': actual_duration,
                'messages_sent': actual_messages,
                'avg_latency_ms': statistics.mean(message_times) if message_times else 0,
                'max_latency_ms': max(message_times) if message_times else 0,
                'min_latency_ms': min(message_times) if message_times else 0,
                'latency_std_ms': statistics.stdev(message_times) if len(message_times) > 1 else 0,
                'throughput_msgs_per_s': actual_messages / actual_duration if actual_duration > 0 else 0,
                'energy_per_message_uj': total_energy / actual_messages if actual_messages > 0 else 0,
                'total_energy_uj': total_energy,
                'central_energy_uj': central_energy,
                'peripheral_energy_uj': peripheral_energy,
                'duty_cycle_percent': (end_stats_central['duty_cycle_percent'] + 
                                     end_stats_peripheral['duty_cycle_percent']) / 2,
                'packets_retransmitted': (end_stats_central['packets_retransmitted'] + 
                                        end_stats_peripheral['packets_retransmitted']),
                'central_stats': end_stats_central,
                'peripheral_stats': end_stats_peripheral
            }
            
            return result
            
        finally:
            simulator.stop_simulation()
            
    def test_packet_loss_impact(self, conn_interval_ms: int = 100, loss_rates: List[float] = None) -> List[Dict]:
        """Test impact of packet loss on latency and energy"""
        if loss_rates is None:
            loss_rates = [0.0, 0.01, 0.05, 0.1, 0.2]
            
        print("\n" + "=" * 60)
        print("BLE Packet Loss Impact Test")
        print("=" * 60)
        
        results = []
        for loss_rate in loss_rates:
            print(f"\nTesting packet loss rate: {loss_rate*100:.1f}%")
            
            # This would require extending the simulator to inject packet loss
            # For now, estimate the impact
            
            # Estimate retransmissions based on loss rate
            avg_retransmits = loss_rate / (1 - loss_rate) if loss_rate < 1.0 else 3
            estimated_latency = calculate_packet_latency(conn_interval_ms, int(avg_retransmits))
            
            result = {
                'loss_rate': loss_rate,
                'conn_interval_ms': conn_interval_ms,
                'estimated_retransmits': avg_retransmits,
                'estimated_latency_ms': estimated_latency,
                'latency_increase_percent': (estimated_latency / conn_interval_ms - 0.5) * 100
            }
            
            results.append(result)
            print(f"  Estimated avg retransmits: {avg_retransmits:.2f}")
            print(f"  Estimated latency: {estimated_latency:.2f}ms")
            print(f"  Latency increase: {result['latency_increase_percent']:.1f}%")
            
        return results
        
    def test_energy_vs_duty_cycle(self, conn_intervals_ms: List[int] = None) -> Dict:
        """Test relationship between connection interval and duty cycle/energy"""
        if conn_intervals_ms is None:
            conn_intervals_ms = [20, 50, 100, 200, 500, 1000]
            
        print("\n" + "=" * 60)
        print("BLE Energy vs Duty Cycle Analysis")
        print("=" * 60)
        
        # Theoretical analysis based on BLE timing
        phy_params = BLEPhyParams()
        results = {
            'intervals_ms': [],
            'duty_cycles': [],
            'avg_power_mw': [],
            'battery_life_days': []  # Assuming 200mAh battery
        }
        
        for interval_ms in conn_intervals_ms:
            # Estimate connection event duration (transmission + reception + processing)
            event_duration_ms = 2.0  # Typical connection event duration
            duty_cycle = event_duration_ms / interval_ms
            
            # Calculate average current consumption
            active_current_ma = (phy_params.tx_current_ma + phy_params.rx_current_ma) / 2
            sleep_current_ma = phy_params.sleep_current_ua / 1000.0
            
            avg_current_ma = duty_cycle * active_current_ma + (1 - duty_cycle) * sleep_current_ma
            avg_power_mw = avg_current_ma * 3.0  # 3V supply
            
            # Battery life estimation (200mAh battery)
            battery_capacity_mah = 200
            battery_life_hours = battery_capacity_mah / avg_current_ma
            battery_life_days = battery_life_hours / 24
            
            results['intervals_ms'].append(interval_ms)
            results['duty_cycles'].append(duty_cycle * 100)  # Convert to percentage
            results['avg_power_mw'].append(avg_power_mw)
            results['battery_life_days'].append(battery_life_days)
            
            print(f"Interval: {interval_ms:4d}ms | Duty cycle: {duty_cycle*100:5.2f}% | "
                  f"Avg power: {avg_power_mw:6.3f}mW | Battery life: {battery_life_days:6.1f} days")
                  
        return results
        
    def print_summary(self):
        """Print summary of all test results"""
        if not self.results:
            print("No test results available")
            return
            
        print("\n" + "=" * 60)
        print("BLE TEST SUMMARY")
        print("=" * 60)
        
        print(f"{'Interval (ms)':<12} {'Latency (ms)':<12} {'Energy (µJ)':<12} {'Throughput':<12} {'Duty Cycle':<10}")
        print("-" * 60)
        
        for result in self.results:
            print(f"{result['conn_interval_ms']:<12} "
                  f"{result['avg_latency_ms']:<12.2f} "
                  f"{result['energy_per_message_uj']:<12.2f} "
                  f"{result['throughput_msgs_per_s']:<12.2f} "
                  f"{result['duty_cycle_percent']:<10.2f}%")
                  
        # Find optimal intervals
        min_latency = min(self.results, key=lambda x: x['avg_latency_ms'])
        min_energy = min(self.results, key=lambda x: x['energy_per_message_uj'])
        max_throughput = max(self.results, key=lambda x: x['throughput_msgs_per_s'])
        
        print("\nOptimal Configurations:")
        print(f"  Lowest latency: {min_latency['conn_interval_ms']}ms ({min_latency['avg_latency_ms']:.2f}ms)")
        print(f"  Lowest energy: {min_energy['conn_interval_ms']}ms ({min_energy['energy_per_message_uj']:.2f}µJ)")
        print(f"  Highest throughput: {max_throughput['conn_interval_ms']}ms ({max_throughput['throughput_msgs_per_s']:.2f} msgs/s)")
        
    def plot_results(self, save_path: str = "ble_test_results.png"):
        """Plot test results"""
        if not PLOTTING_AVAILABLE:
            print("Plotting not available. Install matplotlib to enable plots.")
            return
            
        if not self.results:
            print("No results to plot")
            return
            
        # Set up matplotlib for non-interactive plotting
        import matplotlib
        matplotlib.use('Agg')
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
        
        intervals = [r['conn_interval_ms'] for r in self.results]
        latencies = [r['avg_latency_ms'] for r in self.results]
        energies = [r['energy_per_message_uj'] for r in self.results]
        throughputs = [r['throughput_msgs_per_s'] for r in self.results]
        duty_cycles = [r['duty_cycle_percent'] for r in self.results]
        
        # Latency vs Connection Interval
        ax1.plot(intervals, latencies, 'b-o', linewidth=2, markersize=6)
        ax1.set_xlabel('Connection Interval (ms)')
        ax1.set_ylabel('Average Latency (ms)')
        ax1.set_title('Latency vs Connection Interval')
        ax1.grid(True, alpha=0.3)
        
        # Energy vs Connection Interval
        ax2.plot(intervals, energies, 'r-o', linewidth=2, markersize=6)
        ax2.set_xlabel('Connection Interval (ms)')
        ax2.set_ylabel('Energy per Message (µJ)')
        ax2.set_title('Energy Consumption vs Connection Interval')
        ax2.grid(True, alpha=0.3)
        
        # Throughput vs Connection Interval
        ax3.plot(intervals, throughputs, 'g-o', linewidth=2, markersize=6)
        ax3.set_xlabel('Connection Interval (ms)')
        ax3.set_ylabel('Throughput (msgs/s)')
        ax3.set_title('Throughput vs Connection Interval')
        ax3.grid(True, alpha=0.3)
        
        # Duty Cycle vs Connection Interval
        ax4.plot(intervals, duty_cycles, 'm-o', linewidth=2, markersize=6)
        ax4.set_xlabel('Connection Interval (ms)')
        ax4.set_ylabel('Duty Cycle (%)')
        ax4.set_title('Duty Cycle vs Connection Interval')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Results plotted and saved to {save_path}")


def setup_matplotlib_for_plotting():
    """
    Setup matplotlib for plotting with proper configuration.
    Call this function before creating any plots to ensure proper rendering.
    """
    if not PLOTTING_AVAILABLE:
        return
        
    import warnings
    import matplotlib.pyplot as plt
    
    try:
        import seaborn as sns
        has_seaborn = True
    except ImportError:
        has_seaborn = False

    # Ensure warnings are printed
    warnings.filterwarnings('default')  # Show all warnings

    # Configure matplotlib for non-interactive mode
    plt.switch_backend("Agg")

    # Set chart style
    if has_seaborn:
        try:
            plt.style.use("seaborn-v0_8")
            sns.set_palette("husl")
        except:
            plt.style.use("default")
    else:
        plt.style.use("default")

    # Configure platform-appropriate fonts for cross-platform compatibility
    plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def main():
    """Run BLE test suite"""
    print("BLE 5.x Performance Test Suite")
    print("Testing latency and energy consumption across connection intervals")
    
    # Setup matplotlib for plotting
    setup_matplotlib_for_plotting()
    
    # Initialize tester
    tester = BLELatencyTester()
    
    # Test 1: Connection interval sweep
    test_intervals = [20, 50, 100, 200, 400, 800, 1600]  # BLE standard intervals
    results = tester.test_connection_interval_sweep(
        intervals_ms=test_intervals,
        test_duration_s=3.0,
        num_messages=50
    )
    
    # Test 2: Packet loss impact
    loss_results = tester.test_packet_loss_impact(conn_interval_ms=100)
    
    # Test 3: Energy vs duty cycle analysis
    energy_results = tester.test_energy_vs_duty_cycle()
    
    # Print comprehensive summary
    tester.print_summary()
    
    # Generate plots
    try:
        tester.plot_results()
    except Exception as e:
        print(f"Could not generate plots: {e}")
    
    print("\n" + "=" * 60)
    print("BLE PERFORMANCE ANALYSIS COMPLETE")
    print("=" * 60)
    
    # Key insights
    print("\nKey Insights:")
    print("1. Lower connection intervals provide better latency but higher energy consumption")
    print("2. Duty cycle decreases with longer intervals, extending battery life")
    print("3. Packet loss significantly impacts effective latency due to retransmissions")
    print("4. Optimal interval depends on application requirements (latency vs battery life)")
    
    return results, loss_results, energy_results


if __name__ == "__main__":
    results, loss_results, energy_results = main()