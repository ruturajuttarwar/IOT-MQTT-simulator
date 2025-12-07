"""
BLE 5.x PHY/MAC Implementation for IoT/MQTT Project
Simplified simulation focusing on core BLE mechanisms
"""

import time
import random
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
import threading
from queue import Queue, Empty

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BLEState(Enum):
    """BLE device states"""
    STANDBY = "standby"
    ADVERTISING = "advertising"
    SCANNING = "scanning" 
    INITIATING = "initiating"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class BLEPacketType(Enum):
    """BLE packet types"""
    ADV_IND = "adv_ind"
    SCAN_REQ = "scan_req"
    SCAN_RSP = "scan_rsp"
    CONNECT_REQ = "connect_req"
    DATA = "data"
    ACK = "ack"


@dataclass
class BLEPacket:
    """BLE packet structure"""
    packet_type: BLEPacketType
    source_addr: str
    dest_addr: str
    payload: bytes
    timestamp: float
    seq_num: int = 0
    ack_required: bool = False
    retransmit_count: int = 0


@dataclass
class BLEConnectionParams:
    """BLE connection parameters"""
    conn_interval_ms: int = 100  # Connection interval in ms
    slave_latency: int = 0       # Number of connection events slave can skip
    supervision_timeout_ms: int = 2000  # Supervision timeout in ms
    max_retransmits: int = 3     # Maximum retransmission attempts


@dataclass
class BLEPhyParams:
    """BLE 5.x PHY parameters"""
    # BLE 5.x supports multiple PHYs - using 1M PHY as default
    data_rate_bps: int = 1_000_000     # 1 Mbps
    tx_power_dbm: int = 0              # 0 dBm default
    rx_sensitivity_dbm: int = -90      # -90 dBm sensitivity
    range_meters: float = 100.0        # Approximate range in open space
    
    # Energy consumption (mA)
    tx_current_ma: float = 15.0        # Transmit current
    rx_current_ma: float = 12.0        # Receive current
    sleep_current_ua: float = 1.5      # Sleep current (microamps)
    
    # Timing parameters (microseconds)
    preamble_time_us: int = 40         # Preamble + access address
    packet_overhead_us: int = 150      # Headers, CRC, IFS


class BLEEnergyTracker:
    """Tracks energy consumption for BLE operations"""
    
    def __init__(self, phy_params: BLEPhyParams):
        self.phy_params = phy_params
        self.total_energy_uj = 0.0  # Total energy in microjoules
        self.tx_time_us = 0
        self.rx_time_us = 0 
        self.sleep_time_us = 0
        self.last_timestamp = time.time()
        
    def add_tx_energy(self, packet_size_bytes: int) -> float:
        """Add energy consumed for transmission"""
        # Calculate transmission time
        tx_time_us = (packet_size_bytes * 8 * 1_000_000 / self.phy_params.data_rate_bps) + \
                     self.phy_params.packet_overhead_us
        
        # Energy = Power * Time (P = V * I, assuming 3V supply)
        energy_uj = 3.0 * self.phy_params.tx_current_ma * tx_time_us / 1000.0
        
        self.total_energy_uj += energy_uj
        self.tx_time_us += tx_time_us
        return energy_uj
        
    def add_rx_energy(self, packet_size_bytes: int) -> float:
        """Add energy consumed for reception"""
        rx_time_us = (packet_size_bytes * 8 * 1_000_000 / self.phy_params.data_rate_bps) + \
                     self.phy_params.packet_overhead_us
        
        energy_uj = 3.0 * self.phy_params.rx_current_ma * rx_time_us / 1000.0
        
        self.total_energy_uj += energy_uj
        self.rx_time_us += rx_time_us
        return energy_uj
        
    def add_sleep_energy(self, sleep_time_us: int) -> float:
        """Add energy consumed during sleep"""
        energy_uj = 3.0 * self.phy_params.sleep_current_ua * sleep_time_us / 1_000_000.0
        
        self.total_energy_uj += energy_uj
        self.sleep_time_us += sleep_time_us
        return energy_uj
        
    def get_stats(self) -> Dict:
        """Get energy consumption statistics"""
        total_time_us = self.tx_time_us + self.rx_time_us + self.sleep_time_us
        
        return {
            'total_energy_uj': self.total_energy_uj,
            'tx_time_us': self.tx_time_us,
            'rx_time_us': self.rx_time_us, 
            'sleep_time_us': self.sleep_time_us,
            'total_time_us': total_time_us,
            'avg_power_mw': self.total_energy_uj / (total_time_us / 1000.0) if total_time_us > 0 else 0,
            'duty_cycle_percent': ((self.tx_time_us + self.rx_time_us) / total_time_us * 100) if total_time_us > 0 else 0
        }


class BLEDevice:
    """Base BLE device implementation"""
    
    def __init__(self, address: str, phy_params: Optional[BLEPhyParams] = None):
        self.address = address
        self.state = BLEState.STANDBY
        self.phy_params = phy_params or BLEPhyParams()
        self.energy_tracker = BLEEnergyTracker(self.phy_params)
        
        # Connection state
        self.connected_peer: Optional[str] = None
        self.connection_params = BLEConnectionParams()
        self.last_connection_event = 0.0
        self.supervision_timer = 0.0
        
        # Packet handling
        self.tx_queue = Queue()
        self.rx_queue = Queue()
        self.pending_acks: Dict[int, BLEPacket] = {}
        self.next_seq_num = 0
        
        # Statistics
        self.stats = {
            'packets_sent': 0,
            'packets_received': 0,
            'packets_retransmitted': 0,
            'connection_events': 0,
            'supervision_timeouts': 0
        }
        
        # Threading
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        
    def start(self):
        """Start the BLE device"""
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
    def stop(self):
        """Stop the BLE device"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)
            
    def _worker_loop(self):
        """Main worker loop for the BLE device"""
        while self.running:
            current_time = time.time() * 1000  # Convert to ms
            
            try:
                # Handle connection events
                if self.state == BLEState.CONNECTED:
                    self._handle_connection_event(current_time)
                    
                # Handle supervision timeout (only if connected)
                if self.state == BLEState.CONNECTED:
                    self._check_supervision_timeout(current_time)
                
                # Process incoming packets
                self._process_rx_queue()
                
                # Add sleep energy consumption
                sleep_time_us = 1000  # 1ms sleep
                self.energy_tracker.add_sleep_energy(sleep_time_us)
                
                # Sleep to prevent busy waiting
                time.sleep(0.001)  # 1ms sleep
                
            except Exception as e:
                logger.error(f"BLE device {self.address} worker error: {e}")
                
    def _handle_connection_event(self, current_time: float):
        """Handle connection event timing"""
        if current_time - self.last_connection_event >= self.connection_params.conn_interval_ms:
            self.last_connection_event = current_time
            self.supervision_timer = current_time  # Reset supervision timer on connection event
            self.stats['connection_events'] += 1
            
            # Process pending retransmissions
            self._handle_retransmissions()
            
            # Try to send queued packets
            self._send_queued_packets()
            
    def _handle_retransmissions(self):
        """Handle packet retransmissions"""
        current_time = time.time()
        expired_packets = []
        
        for seq_num, packet in self.pending_acks.items():
            # Retransmit if packet is old enough
            if current_time - packet.timestamp > self.connection_params.conn_interval_ms / 1000.0:
                if packet.retransmit_count < self.connection_params.max_retransmits:
                    packet.retransmit_count += 1
                    packet.timestamp = current_time
                    self._transmit_packet(packet)
                    self.stats['packets_retransmitted'] += 1
                else:
                    # Max retransmits exceeded, drop packet
                    expired_packets.append(seq_num)
                    
        # Remove expired packets
        for seq_num in expired_packets:
            del self.pending_acks[seq_num]
            
    def _send_queued_packets(self):
        """Send packets from the TX queue"""
        try:
            while not self.tx_queue.empty():
                packet = self.tx_queue.get_nowait()
                self._transmit_packet(packet)
                
                # Add to pending ACKs if required
                if packet.ack_required:
                    self.pending_acks[packet.seq_num] = packet
                    
        except Empty:
            pass
            
    def _transmit_packet(self, packet: BLEPacket):
        """Transmit a BLE packet"""
        packet_size = len(packet.payload) + 20  # Estimate header size
        energy = self.energy_tracker.add_tx_energy(packet_size)
        
        self.stats['packets_sent'] += 1
        logger.debug(f"BLE {self.address} TX: {packet.packet_type} to {packet.dest_addr}")
        
        # Simulate packet transmission - in real implementation, this would 
        # interface with a channel/medium simulation
        
    def _process_rx_queue(self):
        """Process received packets"""
        try:
            while not self.rx_queue.empty():
                packet = self.rx_queue.get_nowait()
                self._handle_received_packet(packet)
        except Empty:
            pass
            
    def _handle_received_packet(self, packet: BLEPacket):
        """Handle a received packet"""
        packet_size = len(packet.payload) + 20
        self.energy_tracker.add_rx_energy(packet_size)
        self.stats['packets_received'] += 1
        
        logger.debug(f"BLE {self.address} RX: {packet.packet_type} from {packet.source_addr}")
        
        # Handle ACK packets
        if packet.packet_type == BLEPacketType.ACK:
            if packet.seq_num in self.pending_acks:
                del self.pending_acks[packet.seq_num]
                
        # Send ACK if required
        elif packet.ack_required:
            ack_packet = BLEPacket(
                packet_type=BLEPacketType.ACK,
                source_addr=self.address,
                dest_addr=packet.source_addr,
                payload=b'',
                timestamp=time.time(),
                seq_num=packet.seq_num
            )
            self.tx_queue.put(ack_packet)
            
    def _check_supervision_timeout(self, current_time: float):
        """Check for supervision timeout"""
        if (self.state == BLEState.CONNECTED and 
            self.supervision_timer > 0 and
            current_time - self.supervision_timer > self.connection_params.supervision_timeout_ms):
            
            logger.warning(f"BLE {self.address}: Supervision timeout")
            self.stats['supervision_timeouts'] += 1
            self.disconnect()
            
    def send_data(self, data: bytes, dest_addr: str, require_ack: bool = True) -> int:
        """Send data to a connected peer"""
        if self.state != BLEState.CONNECTED:
            raise RuntimeError("Device not connected")
            
        packet = BLEPacket(
            packet_type=BLEPacketType.DATA,
            source_addr=self.address,
            dest_addr=dest_addr,
            payload=data,
            timestamp=time.time(),
            seq_num=self.next_seq_num,
            ack_required=require_ack
        )
        
        self.next_seq_num += 1
        self.tx_queue.put(packet)
        return packet.seq_num
        
    def receive_packet(self, packet: BLEPacket):
        """Receive a packet from the channel"""
        self.rx_queue.put(packet)
        
    def disconnect(self):
        """Disconnect from peer"""
        self.state = BLEState.DISCONNECTED
        self.connected_peer = None
        self.pending_acks.clear()
        
    def get_stats(self) -> Dict:
        """Get device statistics"""
        energy_stats = self.energy_tracker.get_stats()
        return {**self.stats, **energy_stats}


class BLECentral(BLEDevice):
    """BLE Central device (initiates connections)"""
    
    def __init__(self, address: str, phy_params: Optional[BLEPhyParams] = None):
        super().__init__(address, phy_params)
        self.scan_results: List[str] = []
        
    def start_scanning(self, duration_ms: int = 1000):
        """Start scanning for advertising devices"""
        self.state = BLEState.SCANNING
        logger.info(f"BLE Central {self.address}: Started scanning")
        
        # Simulate scanning energy consumption
        scan_energy = self.energy_tracker.add_rx_energy(100)  # Estimate scan packet size
        
        # In a real implementation, this would listen for advertising packets
        # For simulation, we'll populate scan_results externally
        
    def connect_to_device(self, peripheral_addr: str, conn_params: Optional[BLEConnectionParams] = None):
        """Connect to a peripheral device"""
        if self.state != BLEState.SCANNING:
            raise RuntimeError("Must be scanning to connect")
            
        self.state = BLEState.INITIATING
        
        if conn_params:
            self.connection_params = conn_params
            
        # Send connection request
        connect_packet = BLEPacket(
            packet_type=BLEPacketType.CONNECT_REQ,
            source_addr=self.address,
            dest_addr=peripheral_addr,
            payload=b'',
            timestamp=time.time()
        )
        
        self._transmit_packet(connect_packet)
        
        # Simulate connection establishment
        self.state = BLEState.CONNECTED
        self.connected_peer = peripheral_addr
        self.last_connection_event = time.time() * 1000
        self.supervision_timer = time.time() * 1000
        
        logger.info(f"BLE Central {self.address}: Connected to {peripheral_addr}")


class BLEPeripheral(BLEDevice):
    """BLE Peripheral device (advertises and accepts connections)"""
    
    def __init__(self, address: str, phy_params: Optional[BLEPhyParams] = None):
        super().__init__(address, phy_params)
        self.advertising_interval_ms = 100
        self.last_advertisement = 0.0
        
    def start_advertising(self, interval_ms: int = 100):
        """Start advertising"""
        self.state = BLEState.ADVERTISING
        self.advertising_interval_ms = interval_ms
        logger.info(f"BLE Peripheral {self.address}: Started advertising")
        
    def _worker_loop(self):
        """Extended worker loop with advertising"""
        while self.running:
            current_time = time.time() * 1000
            
            try:
                # Handle advertising
                if (self.state == BLEState.ADVERTISING and 
                    current_time - self.last_advertisement >= self.advertising_interval_ms):
                    self._send_advertisement()
                    
                # Handle connection events
                if self.state == BLEState.CONNECTED:
                    self._handle_connection_event(current_time)
                    
                # Handle supervision timeout (only if connected)
                if self.state == BLEState.CONNECTED:
                    self._check_supervision_timeout(current_time)
                
                # Process incoming packets
                self._process_rx_queue()
                
                # Add sleep energy consumption
                sleep_time_us = 1000  # 1ms sleep
                self.energy_tracker.add_sleep_energy(sleep_time_us)
                
                # Sleep to prevent busy waiting
                time.sleep(0.001)  # 1ms sleep
                
            except Exception as e:
                logger.error(f"BLE peripheral {self.address} worker error: {e}")
                
    def _send_advertisement(self):
        """Send advertising packet"""
        self.last_advertisement = time.time() * 1000
        
        adv_packet = BLEPacket(
            packet_type=BLEPacketType.ADV_IND,
            source_addr=self.address,
            dest_addr="FF:FF:FF:FF:FF:FF",  # Broadcast
            payload=b'BLE_DEVICE',
            timestamp=time.time()
        )
        
        self._transmit_packet(adv_packet)
        
    def accept_connection(self, central_addr: str, conn_params: Optional[BLEConnectionParams] = None):
        """Accept connection from central"""
        if self.state != BLEState.ADVERTISING:
            raise RuntimeError("Must be advertising to accept connection")
            
        if conn_params:
            self.connection_params = conn_params
            
        self.state = BLEState.CONNECTED
        self.connected_peer = central_addr
        self.last_connection_event = time.time() * 1000
        self.supervision_timer = time.time() * 1000
        
        logger.info(f"BLE Peripheral {self.address}: Accepted connection from {central_addr}")


class BLESimulator:
    """Simple BLE network simulator"""
    
    def __init__(self):
        self.devices: Dict[str, BLEDevice] = {}
        self.packet_loss_rate = 0.01  # 1% packet loss
        
    def add_device(self, device: BLEDevice):
        """Add a device to the simulation"""
        self.devices[device.address] = device
        
    def remove_device(self, address: str):
        """Remove a device from the simulation"""
        if address in self.devices:
            self.devices[address].stop()
            del self.devices[address]
            
    def start_simulation(self):
        """Start all devices"""
        for device in self.devices.values():
            device.start()
            
    def stop_simulation(self):
        """Stop all devices"""
        for device in self.devices.values():
            device.stop()
            
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all devices"""
        return {addr: device.get_stats() for addr, device in self.devices.items()}


def calculate_packet_latency(conn_interval_ms: int, retransmit_count: int = 0) -> float:
    """Calculate expected packet latency"""
    # Base latency is half the connection interval (on average)
    base_latency_ms = conn_interval_ms / 2.0
    
    # Add retransmission delays
    retransmit_latency_ms = retransmit_count * conn_interval_ms
    
    return base_latency_ms + retransmit_latency_ms


if __name__ == "__main__":
    # Simple test
    central = BLECentral("C1:23:45:67:89:AB")
    peripheral = BLEPeripheral("P1:23:45:67:89:AB")
    
    simulator = BLESimulator()
    simulator.add_device(central)
    simulator.add_device(peripheral)
    
    simulator.start_simulation()
    
    # Test connection
    peripheral.start_advertising()
    time.sleep(0.1)
    
    central.start_scanning()
    time.sleep(0.1)
    
    central.connect_to_device(peripheral.address)
    peripheral.accept_connection(central.address)
    
    # Send some data
    for i in range(5):
        central.send_data(f"Message {i}".encode(), peripheral.address)
        time.sleep(0.05)
        
    time.sleep(1.0)
    
    # Print statistics
    stats = simulator.get_all_stats()
    for addr, device_stats in stats.items():
        print(f"\nDevice {addr} stats:")
        for key, value in device_stats.items():
            print(f"  {key}: {value}")
            
    simulator.stop_simulation()