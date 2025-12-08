"""
Software-only MQTT client implementation
Implements QoS 0/1, DUP handling, keep-alive, reconnect with exponential backoff
"""

import asyncio
import time
import random
from typing import Dict, Set, Optional, Callable
from config.simulation_config import MQTT_KEEP_ALIVE, MQTT_QOS_DEFAULT, MQTT_CLEAN_SESSION
from utils.logging_utils import log_mqtt_event


class MQTTClientSim:
    """Simulated MQTT client with full protocol support"""
    
    def __init__(self, client_id: str, broker_address: str):
        self.client_id = client_id
        self.broker_address = broker_address
        self.connected = False
        self.running = True  # Control flag for simulation start/stop
        
        # Connection parameters
        self.keep_alive = MQTT_KEEP_ALIVE
        self.clean_session = MQTT_CLEAN_SESSION
        self.last_ping = 0
        self.default_qos = 1  # Default QoS for this client
        
        # Last Will Testament (LWT)
        self.lwt_topic = f"nodes/{client_id}/status"
        self.lwt_message = b"offline"
        self.lwt_qos = 1
        self.lwt_retain = True
        
        # Message handling
        self.next_msg_id = 1
        self.inflight_messages: Dict[int, Dict] = {}  # msg_id -> message
        self.received_msg_ids: Set[int] = set()  # For DUP detection
        self.subscriptions: Set[str] = set()
        
        # Reconnection
        self.reconnect_delay = 1.0  # Start with 1 second
        self.max_reconnect_delay = 60.0
        self.reconnect_attempts = 0
        
        # Session state (for clean_session=False)
        self.session_messages = []
        
        # Retained messages cache
        self.retained_messages: Dict[str, Dict] = {}  # topic -> message
        
        # WAN latency
        self.wan_latency_ms = 0
        self.wan_packet_loss = 0.0
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'duplicates_received': 0,
            'reconnections': 0,
            'qos0_messages': 0,
            'qos1_messages': 0,
            'publish_failures': 0
        }
        
        # Callbacks
        self.on_message_callback: Optional[Callable] = None
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None
        
    async def connect(self, lwt_topic: str = None, lwt_message: bytes = None) -> bool:
        """Connect to MQTT broker with optional LWT"""
        try:
            # Set LWT if provided
            if lwt_topic:
                self.lwt_topic = lwt_topic
            if lwt_message:
                self.lwt_message = lwt_message
            
            # Simulate connection delay + WAN latency
            await asyncio.sleep(0.01 + self.wan_latency_ms / 1000.0)
            
            # Simulate WAN packet loss
            if random.random() < self.wan_packet_loss:
                log_mqtt_event(self.client_id, "Connection packet lost (WAN)")
                return False
            
            self.connected = True
            self.last_ping = time.time()
            self.reconnect_delay = 1.0
            self.reconnect_attempts = 0
            
            log_mqtt_event(self.client_id, f"Connected to {self.broker_address}")
            
            # Send online status (opposite of LWT)
            await self.publish(self.lwt_topic, b"online", qos=1, retain=True)
            
            # Restore session if clean_session=False
            if not self.clean_session and self.session_messages:
                log_mqtt_event(self.client_id, f"Restoring {len(self.session_messages)} session messages")
                # Resend inflight messages
                for msg in self.session_messages:
                    await self.publish(msg['topic'], msg['payload'], msg['qos'], msg['retain'])
                
            if self.on_connect_callback:
                await self.on_connect_callback()
                
            return True
            
        except Exception as e:
            log_mqtt_event(self.client_id, f"Connection failed: {e}")
            return False
            
    async def disconnect(self, send_lwt: bool = False):
        """Disconnect from broker"""
        self.connected = False
        
        # If abnormal disconnect, broker will send LWT
        if send_lwt:
            log_mqtt_event(self.client_id, f"Abnormal disconnect - LWT will be sent: {self.lwt_topic}")
            # In real implementation, broker sends LWT to subscribers
        
        log_mqtt_event(self.client_id, "Disconnected")
        
        if self.on_disconnect_callback:
            await self.on_disconnect_callback()
            
    async def reconnect(self) -> bool:
        """Reconnect with exponential backoff"""
        self.reconnect_attempts += 1
        
        log_mqtt_event(self.client_id, 
                      f"Reconnect attempt {self.reconnect_attempts} (delay: {self.reconnect_delay}s)")
        
        # Wait with exponential backoff
        await asyncio.sleep(self.reconnect_delay)
        
        # Try to connect
        success = await self.connect()
        
        if success:
            self.stats['reconnections'] += 1
            return True
        else:
            # Increase backoff delay
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
            return False
            
    async def publish(self, topic: str, payload: bytes, qos: int = None, retain: bool = False) -> bool:
        """Publish message with QoS 0/1 and retain support"""
        # Check if simulation is running
        if not self.running:
            return False
            
        if not self.connected:
            self.stats['publish_failures'] += 1
            # Store in session if clean_session=False
            if not self.clean_session:
                self.session_messages.append({
                    'topic': topic,
                    'payload': payload,
                    'qos': qos or MQTT_QOS_DEFAULT,
                    'retain': retain
                })
            return False
            
        if qos is None:
            qos = MQTT_QOS_DEFAULT
            
        msg_id = self.next_msg_id if qos == 1 else 0
        self.next_msg_id += 1
        
        message = {
            'msg_id': msg_id,
            'topic': topic,
            'payload': payload,
            'qos': qos,
            'retain': retain,
            'timestamp': time.time(),
            'dup': False
        }
        
        # Handle retained messages
        if retain:
            self.retained_messages[topic] = message
            log_mqtt_event(self.client_id, f"Retained message on {topic}")
        
        # Track QoS 1 messages for retransmission
        if qos == 1:
            self.inflight_messages[msg_id] = message
            self.stats['qos1_messages'] += 1
            
            # Start retransmission timer (will retry if no ACK)
            asyncio.create_task(self._handle_qos1_retransmit(msg_id, topic, payload, qos, retain))
        else:
            # QoS 0: fire and forget, no ACK needed
            self.stats['qos0_messages'] += 1
            
        self.stats['messages_sent'] += 1
        
        # Simulate network delay + WAN latency
        total_delay = 0.001 + (self.wan_latency_ms / 1000.0)
        await asyncio.sleep(total_delay)
        
        # Simulate WAN packet loss
        if random.random() < self.wan_packet_loss:
            log_mqtt_event(self.client_id, f"Message lost in WAN (topic: {topic}, QoS: {qos})")
            if qos == 1:
                # Will be retried automatically
                message['dup'] = True
            else:
                # QoS 0: message is lost forever
                log_mqtt_event(self.client_id, f"QoS 0 message lost - no retry")
            return False
        
        return True
        
    async def subscribe(self, topic: str, qos: int = 1):
        """Subscribe to topic"""
        if not self.connected:
            return False
            
        self.subscriptions.add(topic)
        log_mqtt_event(self.client_id, f"Subscribed to {topic}")
        
        await asyncio.sleep(0.001)
        return True
        
    async def handle_message(self, message: Dict):
        """Handle received message"""
        msg_id = message.get('msg_id', 0)
        qos = message.get('qos', 0)
        
        # DUP detection for QoS 1
        if qos == 1:
            if msg_id in self.received_msg_ids:
                self.stats['duplicates_received'] += 1
                log_mqtt_event(self.client_id, f"Duplicate message {msg_id} detected")
                return
            self.received_msg_ids.add(msg_id)
            
            # Send PUBACK
            await self._send_puback(msg_id)
            
        self.stats['messages_received'] += 1
        
        # Call message callback
        if self.on_message_callback:
            await self.on_message_callback(message)
            
    async def _send_puback(self, msg_id: int):
        """Send PUBACK for QoS 1 message"""
        await asyncio.sleep(0.001)
        # In real implementation, would send actual PUBACK packet
        
    async def _handle_qos1_retransmit(self, msg_id: int, topic: str, payload: bytes, qos: int, retain: bool):
        """Handle QoS 1 retransmission if ACK not received"""
        retry_delay = 3.0  # Wait 3 seconds for ACK
        await asyncio.sleep(retry_delay)
        
        # Check if message still in flight (ACK not received)
        if msg_id in self.inflight_messages:
            msg = self.inflight_messages[msg_id]
            msg['dup'] = True  # Set DUP flag
            
            log_mqtt_event(self.client_id, f"QoS 1 retransmit (DUP=1) for msg_id {msg_id}")
            
            # Retransmit
            await self.publish(topic, payload, qos, retain)
    
    async def handle_puback(self, msg_id: int):
        """Handle PUBACK reception - removes message from inflight queue"""
        if msg_id in self.inflight_messages:
            log_mqtt_event(self.client_id, f"PUBACK received for msg_id {msg_id}")
            del self.inflight_messages[msg_id]
            
    async def send_ping(self):
        """Send PINGREQ keep-alive"""
        if not self.connected or not self.running:
            return
            
        current_time = time.time()
        if current_time - self.last_ping >= self.keep_alive:
            self.last_ping = current_time
            await asyncio.sleep(0.001)
            # In real implementation, would send PINGREQ
            
    async def check_connection(self) -> bool:
        """Check if connection is alive"""
        if not self.connected:
            return False
            
        current_time = time.time()
        timeout = self.keep_alive * 1.5
        
        if current_time - self.last_ping > timeout:
            log_mqtt_event(self.client_id, "Keep-alive timeout")
            await self.disconnect()
            return False
            
        return True
        
    def set_wan_latency(self, latency_ms: float, packet_loss: float = 0.01):
        """Set WAN latency and packet loss for gateway/cloud hop"""
        self.wan_latency_ms = latency_ms
        self.wan_packet_loss = packet_loss
        log_mqtt_event(self.client_id, f"WAN configured: {latency_ms}ms latency, {packet_loss*100}% loss")
        
    def set_lwt(self, topic: str, message: bytes, qos: int = 1, retain: bool = True):
        """Configure Last Will Testament"""
        self.lwt_topic = topic
        self.lwt_message = message
        self.lwt_qos = qos
        self.lwt_retain = retain
        log_mqtt_event(self.client_id, f"LWT configured: {topic}")
        
    def get_stats(self) -> Dict:
        """Get client statistics"""
        return {
            **self.stats,
            'connected': self.connected,
            'inflight_messages': len(self.inflight_messages),
            'subscriptions': len(self.subscriptions),
            'reconnect_attempts': self.reconnect_attempts
        }
