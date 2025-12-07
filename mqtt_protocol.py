"""
MQTT Protocol Implementation for IoT Simulation
Implements QoS 0/1, DUP handling, retained messages, keep-alive, reconnect with exponential backoff
"""

import time
import random
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from queue import Queue, Empty

logger = logging.getLogger(__name__)


class QoSLevel(Enum):
    """MQTT Quality of Service levels"""
    QOS_0 = 0  # At most once
    QOS_1 = 1  # At least once


class MessageType(Enum):
    """MQTT message types"""
    CONNECT = "CONNECT"
    CONNACK = "CONNACK"
    PUBLISH = "PUBLISH"
    PUBACK = "PUBACK"
    SUBSCRIBE = "SUBSCRIBE"
    SUBACK = "SUBACK"
    PINGREQ = "PINGREQ"
    PINGRESP = "PINGRESP"
    DISCONNECT = "DISCONNECT"


@dataclass
class MQTTMessage:
    """MQTT message structure"""
    msg_type: MessageType
    topic: str = ""
    payload: bytes = b""
    qos: QoSLevel = QoSLevel.QOS_0
    retain: bool = False
    dup: bool = False
    msg_id: int = 0
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class MQTTConfig:
    """MQTT client configuration"""
    keep_alive_interval: int = 60  # seconds
    clean_session: bool = True
    reconnect_min_delay: float = 1.0  # seconds
    reconnect_max_delay: float = 60.0  # seconds
    max_reconnect_attempts: int = 10
    qos_default: QoSLevel = QoSLevel.QOS_0


class MQTTBroker:
    """MQTT Broker implementation"""
    
    def __init__(self, broker_id: str):
        self.broker_id = broker_id
        self.clients: Dict[str, 'MQTTClient'] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # topic -> set of client_ids
        self.retained_messages: Dict[str, MQTTMessage] = {}  # topic -> message
        self.message_queue: Queue = Queue()
        
        # Statistics
        self.stats = {
            'messages_received': 0,
            'messages_published': 0,
            'clients_connected': 0,
            'clients_disconnected': 0,
            'subscriptions_total': 0,
            'queue_depth': 0,
            'messages_per_topic': {}
        }
        
    def register_client(self, client: 'MQTTClient'):
        """Register a client with the broker"""
        self.clients[client.client_id] = client
        self.stats['clients_connected'] += 1
        logger.info(f"Broker {self.broker_id}: Client {client.client_id} registered")
        
    def unregister_client(self, client_id: str):
        """Unregister a client"""
        if client_id in self.clients:
            del self.clients[client_id]
            self.stats['clients_disconnected'] += 1
            
            # Remove subscriptions
            for topic in list(self.subscriptions.keys()):
                if client_id in self.subscriptions[topic]:
                    self.subscriptions[topic].remove(client_id)
                    if not self.subscriptions[topic]:
                        del self.subscriptions[topic]
                        
    def subscribe(self, client_id: str, topic: str):
        """Subscribe a client to a topic"""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        self.subscriptions[topic].add(client_id)
        self.stats['subscriptions_total'] = sum(len(subs) for subs in self.subscriptions.values())
        
        # Send retained message if exists
        if topic in self.retained_messages:
            if client_id in self.clients:
                self.clients[client_id].receive_message(self.retained_messages[topic])
                
        logger.debug(f"Broker {self.broker_id}: Client {client_id} subscribed to {topic}")
        
    def publish(self, message: MQTTMessage, publisher_id: str):
        """Publish a message to subscribers"""
        self.stats['messages_received'] += 1
        
        # Track messages per topic
        if message.topic not in self.stats['messages_per_topic']:
            self.stats['messages_per_topic'][message.topic] = 0
        self.stats['messages_per_topic'][message.topic] += 1
        
        # Handle retained messages
        if message.retain:
            self.retained_messages[message.topic] = message
            
        # Find subscribers
        subscribers = self.subscriptions.get(message.topic, set())
        
        # Publish to all subscribers except the publisher
        for client_id in subscribers:
            if client_id != publisher_id and client_id in self.clients:
                self.clients[client_id].receive_message(message)
                self.stats['messages_published'] += 1
                
        # Update queue depth
        self.stats['queue_depth'] = sum(
            client.message_queue.qsize() for client in self.clients.values()
        )
        
    def get_stats(self) -> Dict:
        """Get broker statistics"""
        return {
            **self.stats,
            'active_clients': len(self.clients),
            'active_topics': len(self.subscriptions),
            'retained_messages': len(self.retained_messages)
        }


class MQTTClient:
    """MQTT Client implementation"""
    
    def __init__(self, client_id: str, config: Optional[MQTTConfig] = None):
        self.client_id = client_id
        self.config = config or MQTTConfig()
        self.broker: Optional[MQTTBroker] = None
        self.connected = False
        
        # Connection state
        self.last_ping_time = 0.0
        self.reconnect_attempts = 0
        self.reconnect_delay = self.config.reconnect_min_delay
        self.last_reconnect_attempt = 0.0
        
        # Message handling
        self.message_queue = Queue()
        self.pending_acks: Dict[int, MQTTMessage] = {}  # msg_id -> message
        self.next_msg_id = 1
        self.received_msg_ids: Set[int] = set()  # For duplicate detection
        
        # Subscriptions
        self.subscriptions: Set[str] = set()
        
        # Session state (for clean_session=False)
        self.session_messages: List[MQTTMessage] = []
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'duplicates_received': 0,
            'reconnections': 0,
            'publish_failures': 0,
            'qos1_messages': 0,
            'qos0_messages': 0
        }
        
    def connect(self, broker: MQTTBroker) -> bool:
        """Connect to MQTT broker"""
        try:
            self.broker = broker
            broker.register_client(self)
            self.connected = True
            self.last_ping_time = time.time()
            self.reconnect_attempts = 0
            self.reconnect_delay = self.config.reconnect_min_delay
            
            # Restore session if clean_session=False
            if not self.config.clean_session:
                for topic in self.subscriptions:
                    broker.subscribe(self.client_id, topic)
                    
            logger.info(f"Client {self.client_id} connected to broker {broker.broker_id}")
            return True
            
        except Exception as e:
            logger.error(f"Client {self.client_id} connection failed: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from broker"""
        if self.broker:
            self.broker.unregister_client(self.client_id)
            self.broker = None
        self.connected = False
        logger.info(f"Client {self.client_id} disconnected")
        
    def reconnect(self) -> bool:
        """Attempt to reconnect with exponential backoff"""
        current_time = time.time()
        
        # Check if enough time has passed since last attempt
        if current_time - self.last_reconnect_attempt < self.reconnect_delay:
            return False
            
        self.last_reconnect_attempt = current_time
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.config.max_reconnect_attempts:
            logger.error(f"Client {self.client_id} exceeded max reconnect attempts")
            return False
            
        # Exponential backoff
        self.reconnect_delay = min(
            self.reconnect_delay * 2,
            self.config.reconnect_max_delay
        )
        
        logger.info(f"Client {self.client_id} reconnect attempt {self.reconnect_attempts}")
        self.stats['reconnections'] += 1
        
        # Reconnect logic would go here (requires broker reference)
        return False
        
    def subscribe(self, topic: str):
        """Subscribe to a topic"""
        if not self.connected or not self.broker:
            logger.warning(f"Client {self.client_id} not connected, cannot subscribe")
            return False
            
        self.subscriptions.add(topic)
        self.broker.subscribe(self.client_id, topic)
        return True
        
    def publish(self, topic: str, payload: bytes, qos: QoSLevel = None, retain: bool = False) -> bool:
        """Publish a message"""
        if not self.connected or not self.broker:
            logger.warning(f"Client {self.client_id} not connected, cannot publish")
            self.stats['publish_failures'] += 1
            return False
            
        if qos is None:
            qos = self.config.qos_default
            
        message = MQTTMessage(
            msg_type=MessageType.PUBLISH,
            topic=topic,
            payload=payload,
            qos=qos,
            retain=retain,
            msg_id=self.next_msg_id if qos == QoSLevel.QOS_1 else 0
        )
        
        if qos == QoSLevel.QOS_1:
            self.pending_acks[self.next_msg_id] = message
            self.next_msg_id += 1
            self.stats['qos1_messages'] += 1
        else:
            self.stats['qos0_messages'] += 1
            
        self.broker.publish(message, self.client_id)
        self.stats['messages_sent'] += 1
        
        return True
        
    def receive_message(self, message: MQTTMessage):
        """Receive a message from broker"""
        # Duplicate detection for QoS 1
        if message.qos == QoSLevel.QOS_1:
            if message.msg_id in self.received_msg_ids:
                self.stats['duplicates_received'] += 1
                logger.debug(f"Client {self.client_id} received duplicate message {message.msg_id}")
                return
            self.received_msg_ids.add(message.msg_id)
            
            # Send PUBACK
            if self.broker:
                ack = MQTTMessage(
                    msg_type=MessageType.PUBACK,
                    msg_id=message.msg_id
                )
                # In real implementation, would send ACK back through network
                
        self.message_queue.put(message)
        self.stats['messages_received'] += 1
        
    def process_ack(self, msg_id: int):
        """Process acknowledgment for QoS 1 message"""
        if msg_id in self.pending_acks:
            del self.pending_acks[msg_id]
            
    def send_ping(self):
        """Send keep-alive ping"""
        current_time = time.time()
        if current_time - self.last_ping_time >= self.config.keep_alive_interval:
            self.last_ping_time = current_time
            # In real implementation, would send PINGREQ
            logger.debug(f"Client {self.client_id} sent keep-alive ping")
            
    def check_connection(self) -> bool:
        """Check if connection is still alive"""
        if not self.connected:
            return False
            
        current_time = time.time()
        timeout = self.config.keep_alive_interval * 1.5
        
        if current_time - self.last_ping_time > timeout:
            logger.warning(f"Client {self.client_id} keep-alive timeout")
            self.disconnect()
            return False
            
        return True
        
    def get_stats(self) -> Dict:
        """Get client statistics"""
        return {
            **self.stats,
            'connected': self.connected,
            'pending_acks': len(self.pending_acks),
            'subscriptions': len(self.subscriptions),
            'queue_size': self.message_queue.qsize()
        }
