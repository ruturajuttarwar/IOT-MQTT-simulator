"""
Energy consumption model for IoT nodes
"""

import time
from typing import Dict


class EnergyTracker:
    """Tracks energy consumption for a node"""
    
    def __init__(self, phy_profile: Dict):
        self.phy_profile = phy_profile
        self.battery_level = 100.0  # percentage
        self.total_energy_mj = 0.0  # millijoules
        
        # Battery capacity (typical CR2032 coin cell = 200mAh @ 3V = 2160 Joules = 2,160,000 mJ)
        # ACCELERATED 10x for simulation visibility (real: 2,160,000 mJ)
        self.battery_capacity_mj = 216_000.0  # millijoules (10x faster depletion for demo)
        
        # Time tracking (microseconds)
        self.tx_time_us = 0
        self.rx_time_us = 0
        self.sleep_time_us = 0
        self.idle_time_us = 0
        
        self.last_update = time.time()
        self.current_state = 'idle'  # idle, tx, rx, sleep
        
    def set_state(self, state: str):
        """Change energy state"""
        # Calculate energy for previous state
        now = time.time()
        duration_us = (now - self.last_update) * 1_000_000
        
        # Only track energy if duration is reasonable (< 60 seconds)
        # This prevents huge energy drain from initial startup
        if duration_us < 60_000_000:  # Less than 60 seconds
            if self.current_state == 'tx':
                self.tx_time_us += duration_us
                energy_mj = self.phy_profile['tx_power_mw'] * duration_us / 1_000_000.0
            elif self.current_state == 'rx':
                self.rx_time_us += duration_us
                energy_mj = self.phy_profile['rx_power_mw'] * duration_us / 1_000_000.0
            elif self.current_state == 'sleep':
                self.sleep_time_us += duration_us
                energy_mj = self.phy_profile['sleep_power_mw'] * duration_us / 1_000_000.0
            else:  # idle
                self.idle_time_us += duration_us
                energy_mj = self.phy_profile['idle_power_mw'] * duration_us / 1_000_000.0
                
            self.total_energy_mj += energy_mj
            
            # Update battery level
            self._update_battery_level()
        
        # Update state
        self.current_state = state
        self.last_update = now
        
    def add_tx_energy(self, packet_size_bytes: int) -> float:
        """Add energy for transmission"""
        tx_time_us = (packet_size_bytes * 8 * 1_000_000 / self.phy_profile['data_rate_bps']) + \
                     self.phy_profile.get('packet_overhead_us', 0)
        
        # Energy in millijoules
        energy_mj = self.phy_profile['tx_power_mw'] * tx_time_us / 1_000_000.0
        
        self.total_energy_mj += energy_mj
        self.tx_time_us += tx_time_us
        
        # Update battery level
        self._update_battery_level()
        
        return energy_mj
        
    def add_rx_energy(self, packet_size_bytes: int) -> float:
        """Add energy for reception"""
        rx_time_us = (packet_size_bytes * 8 * 1_000_000 / self.phy_profile['data_rate_bps']) + \
                     self.phy_profile.get('packet_overhead_us', 0)
        
        # Energy in millijoules
        energy_mj = self.phy_profile['rx_power_mw'] * rx_time_us / 1_000_000.0
        
        self.total_energy_mj += energy_mj
        self.rx_time_us += rx_time_us
        
        # Update battery level
        self._update_battery_level()
        
        return energy_mj
    
    def _update_battery_level(self):
        """Update battery level based on energy consumed"""
        # Battery level as percentage of remaining capacity
        self.battery_level = max(0.0, 100.0 * (1.0 - self.total_energy_mj / self.battery_capacity_mj))
        
    def get_stats(self) -> Dict:
        """Get energy statistics"""
        total_time_us = self.tx_time_us + self.rx_time_us + self.sleep_time_us + self.idle_time_us
        
        if total_time_us > 0:
            duty_cycle = ((self.tx_time_us + self.rx_time_us) / total_time_us) * 100
            avg_power_mw = self.total_energy_mj / (total_time_us / 1_000_000)
        else:
            duty_cycle = 0
            avg_power_mw = 0
            
        return {
            'battery_level': self.battery_level,
            'total_energy_mj': self.total_energy_mj,
            'tx_time_us': self.tx_time_us,
            'rx_time_us': self.rx_time_us,
            'sleep_time_us': self.sleep_time_us,
            'idle_time_us': self.idle_time_us,
            'duty_cycle_percent': duty_cycle,
            'avg_power_mw': avg_power_mw,
            'current_state': self.current_state
        }
        
    def estimate_battery_life_hours(self, battery_capacity_mah: float = 200.0) -> float:
        """Estimate remaining battery life in hours"""
        if self.total_energy_mj == 0:
            return float('inf')
            
        # Calculate average current draw
        total_time_hours = (self.tx_time_us + self.rx_time_us + self.sleep_time_us + self.idle_time_us) / (1_000_000 * 3600)
        if total_time_hours == 0:
            return float('inf')
            
        # Energy in mWh
        energy_mwh = self.total_energy_mj / 3600.0
        
        # Average power
        avg_power_mw = energy_mwh / total_time_hours
        
        # Current at 3V
        avg_current_ma = avg_power_mw / 3.0
        
        # Battery life
        if avg_current_ma > 0:
            return battery_capacity_mah / avg_current_ma
        return float('inf')
