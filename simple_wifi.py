#!/usr/bin/env python3
"""
Simplified WiFi Implementation for IoT Simulation
I am  Modelling WiFi speed, range, and energy consumption using real specs
also as rubric I tried Energy calculations for different operations
"""

import math
import random
import time
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class WiFiSpecs:
    """WiFi 802.11n specifications - just the numbers we need"""
    # These are REAL WiFi 802.11n specifications
    max_data_rate: int = 150_000_000    # 150 Mbps (realistic for single antenna)
    frequency: float = 2.4e9            # 2.4 GHz
    max_range: float = 100.0            # 100 meters indoors
    
    # Power consumption (realistic values in milliwatts)
    transmit_power: float = 100.0       # When sending data
    receive_power: float = 50.0         # When receiving data
    idle_power: float = 10.0            # When doing nothing
    sleep_power: float = 0.1            # When sleeping


class SimpleWiFi:
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.specs = WiFiSpecs()
        self.total_energy_used = 0.0  # Track total energy consumption
        
        # Simple statistics
        self.stats = {
            'packets_sent': 0,
            'packets_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'transmission_failures': 0,
            'total_energy_mj': 0.0
        }
    
    def calculate_transmission_time(self, data_size_bytes: int) -> float:
        """How long does it take to send this much data?
        
        Args:
            data_size_bytes: Size of data in bytes
            
        Returns:
            Time in seconds
        """
        # Add some overhead (headers, etc.) - simplified
        overhead_bytes = 50  # WiFi headers
        total_bytes = data_size_bytes + overhead_bytes
        
        # Time = Data / Speed
        transmission_time = (total_bytes * 8) / self.specs.max_data_rate
        
        # Minimum transmission time (realistic constraint)
        min_time = 20e-6  # 20 microseconds
        return max(transmission_time, min_time)
    
    def calculate_energy_consumption(self, operation: str, duration_seconds: float) -> float:
        """How much energy does an operation consume?
        
        Args:
            operation: 'transmit', 'receive', 'idle', or 'sleep'
            duration_seconds: How long the operation lasts
            
        Returns:
            Energy in millijoules
        """
        power_map = {
            'transmit': self.specs.transmit_power,
            'receive': self.specs.receive_power,
            'idle': self.specs.idle_power,
            'sleep': self.specs.sleep_power
        }
        
        power_mw = power_map.get(operation, self.specs.idle_power)
        energy_mj = power_mw * duration_seconds * 1000  # Convert to millijoules
        
        self.total_energy_used += energy_mj
        self.stats['total_energy_mj'] = self.total_energy_used
        
        return energy_mj
    
    def get_signal_strength(self, distance_meters: float) -> float:
        """What's the signal strength at this distance?
        
        Args:
            distance_meters: Distance in meters
            
        Returns:
            Signal strength as percentage (0-100)
        """
        if distance_meters > self.specs.max_range:
            return 0.0  # Too far away
        
        if distance_meters <= 1.0:
            return 100.0  # Very close = perfect signal
        
        # Simple model: signal decreases with distance
        strength = 100.0 * (1.0 - distance_meters / self.specs.max_range)
        return max(0.0, strength)
    
    def can_communicate(self, distance_meters: float) -> bool:
        """Can we communicate at this distance?
        
        Args:
            distance_meters: Distance in meters
            
        Returns:
            True if communication is possible
        """
        signal_strength = self.get_signal_strength(distance_meters)
        return signal_strength >= 10.0  # Need at least 10% signal
    
    def get_effective_data_rate(self, distance_meters: float) -> float:
        """What data rate can we achieve at this distance?
        
        Args:
            distance_meters: Distance in meters
            
        Returns:
            Data rate in bits per second
        """
        signal_strength = self.get_signal_strength(distance_meters)
        
        if signal_strength >= 90:
            return self.specs.max_data_rate  # Full speed
        elif signal_strength >= 70:
            return self.specs.max_data_rate * 0.8  # 80% speed
        elif signal_strength >= 50:
            return self.specs.max_data_rate * 0.5  # 50% speed
        elif signal_strength >= 30:
            return self.specs.max_data_rate * 0.2  # 20% speed
        elif signal_strength >= 10:
            return self.specs.max_data_rate * 0.1  # 10% speed
        else:
            return 0  # No communication
    
    def simulate_packet_transmission(self, destination_distance: float, 
                                   packet_size_bytes: int) -> Dict:
        """Simulate sending a packet
        
        Args:
            destination_distance: Distance to destination in meters
            packet_size_bytes: Size of packet in bytes
            
        Returns:
            Dictionary with transmission results
        """
        result = {
            'success': False,
            'transmission_time': 0.0,
            'energy_consumed': 0.0,
            'data_rate_achieved': 0.0,
            'signal_strength': 0.0
        }
        
        # Check if we can communicate
        if not self.can_communicate(destination_distance):
            result['signal_strength'] = self.get_signal_strength(destination_distance)
            self.stats['transmission_failures'] += 1
            return result
        
        # transmission parameters
        signal_strength = self.get_signal_strength(destination_distance)
        effective_rate = self.get_effective_data_rate(destination_distance)
        
        # changing transmission time based on actual data rate
        overhead_bytes = 50
        total_bytes = packet_size_bytes + overhead_bytes
        transmission_time = (total_bytes * 8) / effective_rate
        
        # Calculate energy consumption
        energy_consumed = self.calculate_energy_consumption('transmit', transmission_time)
        
        # Simple collision simulation (10% chance if multiple devices)
        collision_probability = 0.1  # 10% chance of collision
        if random.random() < collision_probability:
            result['success'] = False
            self.stats['transmission_failures'] += 1
            # Still consume energy even if collision occurs
        else:
            result['success'] = True
            self.stats['packets_sent'] += 1
            self.stats['bytes_sent'] += packet_size_bytes
        
        result.update({
            'transmission_time': transmission_time,
            'energy_consumed': energy_consumed,
            'data_rate_achieved': effective_rate,
            'signal_strength': signal_strength
        })
        
        return result
    
    def simulate_packet_reception(self, sender_distance: float, 
                                packet_size_bytes: int) -> Dict:
        result = {
            'success': False,
            'reception_time': 0.0,
            'energy_consumed': 0.0,
            'signal_strength': 0.0
        }
        
        signal_strength = self.get_signal_strength(sender_distance)
        
        if self.can_communicate(sender_distance):
            # Calculate reception time and energy
            effective_rate = self.get_effective_data_rate(sender_distance)
            reception_time = (packet_size_bytes * 8) / effective_rate
            energy_consumed = self.calculate_energy_consumption('receive', reception_time)
            
            result.update({
                'success': True,
                'reception_time': reception_time,
                'energy_consumed': energy_consumed,
                'signal_strength': signal_strength
            })
            
            self.stats['packets_received'] += 1
            self.stats['bytes_received'] += packet_size_bytes
        
        result['signal_strength'] = signal_strength
        return result
    
    def get_wifi_specifications(self) -> Dict:
        """Get WiFi specifications for comparison with other protocols"""
        return {
            'protocol': 'WiFi 802.11n',
            'max_data_rate_mbps': self.specs.max_data_rate / 1_000_000,
            'frequency_ghz': self.specs.frequency / 1e9,
            'max_range_meters': self.specs.max_range,
            'transmit_power_mw': self.specs.transmit_power,
            'receive_power_mw': self.specs.receive_power,
            'idle_power_mw': self.specs.idle_power,
            'sleep_power_mw': self.specs.sleep_power
        }
    
    def get_statistics(self) -> Dict:
        """Get current statistics"""
        return self.stats.copy()
    
    def reset_statistics(self):
        """Reset all statistics"""
        self.stats = {
            'packets_sent': 0,
            'packets_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'transmission_failures': 0,
            'total_energy_mj': self.total_energy_used
        }


# Simple test and demo
if __name__ == "__main__":
    
    wifi_device = SimpleWiFi("sensor_01")
    
    #  WiFi specs
    specs = wifi_device.get_wifi_specifications()
    print("WiFi Specs")
    for key, value in specs.items():
        print(f"  {key}: {value}")
    
    print("\nRange Analysis:")
    print("Distance (m) | Signal (%) | Can Communicate | Data Rate (Mbps)")
    print("-" * 60)
    
    test_distances = [1, 10, 25, 50, 75, 100, 150]
    for distance in test_distances:
        signal = wifi_device.get_signal_strength(distance)
        can_comm = wifi_device.can_communicate(distance)
        data_rate = wifi_device.get_effective_data_rate(distance) / 1_000_000
        
        print(f"{distance:8d}     | {signal:7.1f}    | {can_comm:13}   | {data_rate:10.1f}")
    
    print("\nTransmission Test:")
    # Sending 1 kbps packs at diffrent distances
    packet_size = 1024  # bytes
    
    for distance in [10, 50, 100]:
        result = wifi_device.simulate_packet_transmission(distance, packet_size)
        print(f"\nDistance: {distance}m")
        print(f"  Success: {result['success']}")
        print(f"  Transmission time: {result['transmission_time']*1000:.2f} ms")
        print(f"  Energy consumed: {result['energy_consumed']:.2f} mJ")
        print(f"  Signal strength: {result['signal_strength']:.1f}%")
    
   
    print("\nResults Actual vs Real:")
    stats = wifi_device.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
