"""
Flask-based IoT/MQTT Simulation Dashboard
Modern UI with real-time updates via Socket.IO
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import asyncio
import time
from typing import List, Dict
from collections import deque
import threading

app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')
app.config['SECRET_KEY'] = 'iot-mqtt-simulation-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global references
nodes_ref = None
metrics_ref = None
failover_ref = None
simulation_start_time = None
simulation_paused_time = 0  # Track total paused time
simulation_last_pause = None  # Track when simulation was paused
mqtt_operations = deque(maxlen=500)
simulation_running = False  # Start with simulation stopped

def broadcast_system_event(event_type: str, message: str, details: dict = None):
    """Broadcast system events (failover, relocation) to message log"""
    mqtt_operations.append({
        'type': 'SYSTEM',
        'event_type': event_type,
        'node': 'SYSTEM',
        'topic': event_type,
        'payload': message,
        'details': details or {},
        'timestamp': time.time()
    })

def hook_mqtt_client(node):
    """Hook into MQTT client to capture actual messages"""
    if not hasattr(node, 'mqtt_client') or not node.mqtt_client:
        return
    
    client = node.mqtt_client
    original_publish = client.publish
    original_subscribe = client.subscribe
    
    async def hooked_publish(topic, payload, qos=0, retain=False):
        payload_str = payload.decode() if isinstance(payload, bytes) else str(payload)
        
        # Filter out status messages - only log sensor data
        if 'status' not in topic:
            mqtt_operations.append({
                'type': 'PUBLISH',
                'node': node.node_id,
                'topic': topic,
                'payload': payload_str,
                'qos': qos,
                'retain': retain,
                'timestamp': time.time()
            })
        
        result = await original_publish(topic, payload, qos, retain)
        
        # For QoS 1 ONLY, add ACK from broker to publisher (only for sensor data)
        if qos == 1 and result and 'status' not in topic:
            mqtt_operations.append({
                'type': 'PUBACK',
                'node': 'broker',  # From broker
                'to_node': node.node_id,  # To publisher
                'from_node': 'broker',  # For display consistency
                'topic': topic,
                'payload': payload_str,
                'qos': qos,
                'timestamp': time.time() + 0.05  # ACK comes slightly after
            })
            
            # Actually handle the PUBACK to prevent retransmissions
            # Get the message ID from the last publish
            if hasattr(node, 'mqtt_client') and node.mqtt_client:
                # The message ID is the last one used
                msg_id = node.mqtt_client.next_msg_id - 1
                import asyncio
                asyncio.create_task(node.mqtt_client.handle_puback(msg_id))
        
        # Simulate subscribers receiving the message (only sensor data)
        if 'status' not in topic:
            for subscriber in nodes_ref:
                if subscriber.node_id != node.node_id and subscriber.role in ['subscriber', 'both']:
                    # Check if subscriber is subscribed to this topic
                    if not subscriber.subscribe_to or node.node_id in subscriber.subscribe_to:
                        # Subscriber receives the message
                        mqtt_operations.append({
                            'type': 'RECEIVED',
                            'node': subscriber.node_id,
                            'from_node': node.node_id,
                            'topic': topic,
                            'payload': payload_str,
                            'qos': qos,
                            'timestamp': time.time() + 0.1  # Received after publish
                        })
                        
                        # Deliver message to subscriber's MQTT client (triggers on_message_callback)
                        # This will properly track RX energy in the subscriber node
                        if hasattr(subscriber, 'mqtt_client') and subscriber.mqtt_client:
                            message = {
                                'topic': topic,
                                'payload': payload,
                                'qos': qos,
                                'msg_id': node.mqtt_client.next_msg_id - 1 if qos == 1 else 0
                            }
                            # Call handle_message asynchronously
                            import asyncio
                            try:
                                asyncio.create_task(subscriber.mqtt_client.handle_message(message))
                            except:
                                # If no event loop, energy will be tracked in node's callback
                                pass
                        
                        # Track stats only
                        if hasattr(subscriber, 'stats'):
                            subscriber.stats['messages_received'] = subscriber.stats.get('messages_received', 0) + 1
                        
                        # Track MAC layer RX for subscriber
                        if hasattr(subscriber, 'mac') and hasattr(subscriber.mac, 'stats'):
                            # Increment packets received counter
                            subscriber.mac.stats['packets_received'] = subscriber.mac.stats.get('packets_received', 0) + 1
                        
                        # For QoS 1, subscriber sends ACK back to broker
                        if qos == 1:
                            mqtt_operations.append({
                                'type': 'PUBACK',
                                'node': subscriber.node_id,  # From subscriber
                                'to_node': 'broker',  # To broker
                                'from_node': subscriber.node_id,  # For display consistency
                                'topic': topic,
                                'payload': payload_str,
                                'qos': qos,
                                'timestamp': time.time() + 0.15  # Subscriber ACK comes after receiving
                            })
        
        return result
    
    async def hooked_subscribe(topic, qos=0):
        # Filter out status subscriptions - only log sensor data subscriptions
        if 'status' not in topic and 'command' not in topic:
            mqtt_operations.append({
                'type': 'SUBSCRIBE',
                'node': node.node_id,
                'topic': topic,
                'qos': qos,
                'timestamp': time.time()
            })
        return await original_subscribe(topic, qos)
    
    client.publish = hooked_publish
    client.subscribe = hooked_subscribe

def broadcast_updates():
    """Background thread to broadcast updates"""
    while True:
        time.sleep(0.5)
        
        if not nodes_ref:
            continue
        
        # Don't update uptime if simulation is stopped
        global simulation_running
        
        # Get comprehensive node states
        node_states = []
        subscriber_count = 0  # Count subscriber nodes, not subscriptions
        
        for n in nodes_ref:
            try:
                state = n.get_state()
                node_states.append({
                    'id': state['node_id'],
                    'protocol': state['protocol'].upper(),
                    'connected': state['connected'],
                    'battery': state.get('battery', 100),
                    'is_mobile': state.get('is_mobile', False),
                    'position': state.get('position', [0, 0]),
                    'qos': state.get('qos', 1),
                    'sensor_interval': state.get('sensor_interval', 10),
                    'distance_to_broker': state.get('distance_to_broker', 0),
                    'max_range': state.get('max_range', 100),
                    'latency_ms': state.get('latency_ms', 0),
                    'stats': state.get('stats', {}),
                    'mqtt_stats': state.get('mqtt_stats', {}),
                    'mac_stats': state.get('mac_stats', {}),
                    'energy_stats': state.get('energy_stats', {})
                })
                
                # Count nodes that are subscribers (role = 'subscriber' or 'both')
                if hasattr(n, 'role') and n.role in ['subscriber', 'both']:
                    subscriber_count += 1
            except Exception as e:
                print(f"Error getting node state: {e}")
                node_states.append({
                    'id': n.node_id,
                    'protocol': n.protocol.upper() if hasattr(n, 'protocol') else 'UNKNOWN',
                    'connected': n.mqtt_client.connected if hasattr(n, 'mqtt_client') and n.mqtt_client else False,
                    'battery': 100,
                    'is_mobile': False,
                    'position': [0, 0],
                    'qos': getattr(n, 'qos', 1),
                    'sensor_interval': getattr(n, 'sensor_interval', 10),
                    'stats': {},
                    'mqtt_stats': {},
                    'mac_stats': {},
                    'energy_stats': {}
                })
        
        # Calculate uptime - simple: time since start when running, 0 when stopped
        uptime = 0
        if simulation_running and simulation_start_time:
            uptime = int(time.time() - simulation_start_time)
        
        # Get metrics
        stats_data = {
            'total_messages': len(mqtt_operations),
            'total_subscriptions': subscriber_count,  # Number of subscriber nodes
            'active_nodes': sum(1 for n in node_states if n['connected']),
            'uptime': uptime,
            'running': simulation_running
        }
        
        metrics_data = None
        failover_data = None
        
        if metrics_ref:
            try:
                summary = metrics_ref.get_summary()
                stats_data['total_messages'] = summary.get('total_messages_sent', len(mqtt_operations))
                metrics_data = summary
            except:
                pass
        
        if failover_ref:
            try:
                failover_data = failover_ref.get_stats()
            except:
                pass
        
        # Get broker position from failover manager
        broker_position = (500, 500)  # Default center
        if failover_ref and hasattr(failover_ref, 'broker_positions'):
            current_broker = failover_ref.current_broker
            broker_position = failover_ref.broker_positions.get(current_broker, (500, 500))
        
        socketio.emit('update', {
            'nodes': node_states,
            'stats': stats_data,
            'metrics': metrics_data,
            'failover_stats': failover_data,
            'broker_position': broker_position
        })

def broadcast_messages():
    """Background thread to broadcast MQTT messages"""
    last_sent = 0
    
    while True:
        time.sleep(0.1)
        
        # Send new operations regardless of simulation state (for visualization)
        # The actual message sending is controlled by node.running flag
        
        # Send new operations
        new_ops = [op for op in mqtt_operations if op['timestamp'] > last_sent]
        
        for op in new_ops:
            socketio.emit('message', {
                'msg_type': op['type'],
                'from': op.get('node', ''),
                'to': op.get('to_node', ''),
                'from_node': op.get('from_node', ''),
                'topic': op.get('topic', ''),
                'payload': op.get('payload', ''),
                'qos': op.get('qos', 0),
                'retain': op.get('retain', False),
                'timestamp': op['timestamp']
            })
        
        if new_ops:
            last_sent = new_ops[-1]['timestamp']

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/config')
def get_config():
    """Get current configuration"""
    if nodes_ref:
        ble_count = sum(1 for n in nodes_ref if n.protocol.lower() == 'ble')
        wifi_count = len(nodes_ref) - ble_count
        return jsonify({
            'total_nodes': len(nodes_ref),
            'ble_nodes': ble_count,
            'wifi_nodes': wifi_count
        })
    return jsonify({'total_nodes': 0, 'ble_nodes': 0, 'wifi_nodes': 0})

@app.route('/api/metrics')
def get_metrics():
    """Get comprehensive metrics"""
    if metrics_ref:
        try:
            return jsonify(metrics_ref.get_summary())
        except:
            pass
    return jsonify({})

@app.route('/api/failover/stats')
def get_failover_stats():
    """Get failover statistics"""
    if failover_ref:
        try:
            return jsonify(failover_ref.get_stats())
        except:
            pass
    return jsonify({})

@app.route('/api/failover/trigger', methods=['POST'])
def trigger_failover():
    """Manually trigger broker failover"""
    if failover_ref:
        try:
            import asyncio
            import threading
            
            # Broadcast failover start event
            broadcast_system_event('FAILOVER', f'🚨 Broker failover initiated: {failover_ref.primary_broker} → {failover_ref.failover_broker}')
            
            def run_failover():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(failover_ref.trigger_failover())
                
                # Broadcast failover complete event
                broadcast_system_event('FAILOVER', f'✅ Broker failover complete: {failover_ref.stats["nodes_reconnected"]} nodes reconnected')
            
            thread = threading.Thread(target=run_failover, daemon=True)
            thread.start()
            
            return jsonify({'success': True, 'message': 'Broker failover initiated'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Failover manager not available'}), 400

@app.route('/api/broker/relocate', methods=['POST'])
def relocate_broker():
    """Trigger broker relocation"""
    if failover_ref:
        try:
            import asyncio
            import threading
            
            data = request.get_json() if request.is_json else {}
            offset_x = data.get('offset_x')
            offset_y = data.get('offset_y')
            
            # Get old position
            current_broker = failover_ref.current_broker
            old_pos = failover_ref.broker_positions.get(current_broker, (500, 500))
            
            # Broadcast relocation start event
            broadcast_system_event('RELOCATION', f'📍 Broker relocation initiated from ({old_pos[0]:.0f}, {old_pos[1]:.0f})')
            
            def run_relocation():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(failover_ref.relocate_broker(offset_x=offset_x, offset_y=offset_y))
                
                # Get new position and broadcast complete event
                new_pos = failover_ref.broker_positions.get(current_broker, (500, 500))
                offset_dist = ((new_pos[0] - old_pos[0])**2 + (new_pos[1] - old_pos[1])**2)**0.5
                broadcast_system_event('RELOCATION', f'✅ Broker relocated to ({new_pos[0]:.0f}, {new_pos[1]:.0f}) - moved {offset_dist:.1f}m')
            
            thread = threading.Thread(target=run_relocation, daemon=True)
            thread.start()
            
            return jsonify({'success': True, 'message': 'Broker relocation initiated'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Failover manager not available'}), 400

@app.route('/api/nodes', methods=['POST'])
def add_node():
    """Add a new node dynamically"""
    from sim.node import Node
    from config.phy_profiles import get_profile
    import asyncio
    
    try:
        # Validate Content-Type
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        node_id = data.get('node_id', f'node_{len(nodes_ref)}')
        protocol = data.get('protocol', 'wifi').lower()
        is_mobile = data.get('is_mobile', False)
        broker_address = data.get('broker_address', 'localhost:1883')
        position_x = data.get('position_x', None)
        position_y = data.get('position_y', None)
        node_role = data.get('role', 'both')  # publisher, subscriber, both
        subscribe_to = data.get('subscribe_to', [])  # List of node IDs to subscribe to
        qos = data.get('qos', 1)  # QoS level: 0 or 1
        sensor_interval = data.get('sensor_interval', 10.0)  # Sensor reading interval in seconds
        
        # Create new node - IMPORTANT: Keep protocol as-is
        node = Node(node_id, protocol, is_mobile, broker_address)
        
        # FORCE protocol to stay as selected (prevent auto-switching)
        node.protocol = protocol.lower()
        node.phy_profile = get_profile(protocol.lower())
        
        # Set node to not running initially (will start when simulation starts)
        node.running = False
        if hasattr(node, 'mqtt_client') and node.mqtt_client:
            node.mqtt_client.running = False
        
        # Set custom position if provided
        if position_x is not None and position_y is not None:
            node.position = (float(position_x), float(position_y))
        
        # Set node role, QoS, and sensor interval
        node.role = node_role
        node.subscribe_to = subscribe_to
        node.qos = int(qos)  # Ensure it's an integer
        node.sensor_interval = float(sensor_interval)  # Ensure it's a float
        
        # Also set QoS on MQTT client for consistency
        if hasattr(node, 'mqtt_client') and node.mqtt_client:
            node.mqtt_client.default_qos = int(qos)
        
        nodes_ref.append(node)
        
        # Hook MQTT client
        hook_mqtt_client(node)
        
        # Register with failover manager and link to node
        if failover_ref:
            failover_ref.register_node(node)
            node.failover_manager = failover_ref  # Give node reference to failover manager
        
        # Start node in background only if simulation is running
        if simulation_running:
            import threading
            def run_node():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(node.run())
            
            thread = threading.Thread(target=run_node, daemon=True)
            thread.start()
        
        return jsonify({
            'success': True,
            'node': {
                'id': node.node_id,
                'protocol': node.protocol.upper(),
                'is_mobile': node.is_mobile,
                'position': node.position,
                'role': node_role
            }
        }), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/nodes/<node_id>', methods=['DELETE'])
def delete_node(node_id):
    """Delete a node dynamically"""
    try:
        # Find and remove node
        node_to_remove = None
        for i, node in enumerate(nodes_ref):
            if node.node_id == node_id:
                node_to_remove = node
                nodes_ref.pop(i)
                break
        
        if node_to_remove:
            # Stop the node
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(node_to_remove.stop())
            except:
                pass
            
            return jsonify({'success': True, 'node_id': node_id})
        else:
            return jsonify({'success': False, 'error': 'Node not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/simulation/restart', methods=['POST'])
def restart_simulation():
    """Restart simulation - delete all nodes and reload"""
    global simulation_running, simulation_start_time, simulation_paused_time, simulation_last_pause, mqtt_operations
    
    try:
        import asyncio
        # Stop all nodes
        for node in nodes_ref[:]:
            try:
                node.running = False
                if hasattr(node, 'mqtt_client') and node.mqtt_client:
                    node.mqtt_client.running = False
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(node.stop())
            except Exception as e:
                print(f"Error stopping node: {e}")
        
        # Clear nodes list
        nodes_ref.clear()
        
        # Clear all messages and operations
        mqtt_operations.clear()
        
        # Reset simulation state completely
        simulation_running = False
        simulation_start_time = None
        simulation_paused_time = 0
        simulation_last_pause = None
        
        return jsonify({'success': True, 'message': 'Simulation restarted', 'reload': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/simulation/start', methods=['POST'])
def start_simulation():
    """Start/resume simulation"""
    global simulation_running, simulation_start_time, simulation_paused_time, simulation_last_pause
    
    simulation_running = True
    
    # Always reset start time when starting (fresh start each time)
    simulation_start_time = time.time()
    simulation_paused_time = 0
    simulation_last_pause = None
    
    # Restart all nodes
    import asyncio
    import threading
    for node in nodes_ref:
        if not node.running:
            node.running = True
            # Also restart MQTT client
            if hasattr(node, 'mqtt_client') and node.mqtt_client:
                node.mqtt_client.running = True
            
            def run_node(n):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(n.run())
            
            thread = threading.Thread(target=run_node, args=(node,), daemon=True)
            thread.start()
    
    return jsonify({'success': True, 'running': True})

@app.route('/api/simulation/stop', methods=['POST'])
def stop_simulation():
    """Stop/pause simulation"""
    global simulation_running, simulation_start_time, simulation_paused_time, simulation_last_pause
    
    simulation_running = False
    # Reset timing when stopped
    simulation_start_time = None
    simulation_paused_time = 0
    simulation_last_pause = None
    
    # Stop all nodes - set running flag to False
    for node in nodes_ref:
        try:
            node.running = False
            # Also stop the MQTT client from sending
            if hasattr(node, 'mqtt_client') and node.mqtt_client:
                node.mqtt_client.running = False
        except Exception as e:
            print(f"Error stopping node: {e}")
    
    return jsonify({'success': True, 'running': False})

@app.route('/api/simulation/status', methods=['GET'])
def simulation_status():
    """Get simulation status"""
    return jsonify({'success': True, 'running': simulation_running})

@app.route('/api/nodes/list', methods=['GET'])
def list_nodes():
    """Get list of all node IDs for subscription selection"""
    try:
        node_list = [{'id': n.node_id, 'protocol': n.protocol.upper()} for n in nodes_ref]
        return jsonify({'success': True, 'nodes': node_list})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/export/logs', methods=['GET'])
def export_logs():
    """Export message logs as CSV"""
    try:
        from flask import Response
        import csv
        from io import StringIO
        
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Timestamp', 'Type', 'From Node', 'To Node', 'Topic', 'Payload', 'QoS', 'Protocol'])
        
        # Write message data
        for op in mqtt_operations:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(op['timestamp']))
            msg_type = op.get('type', '')
            from_node = op.get('node', op.get('from_node', ''))
            to_node = op.get('to_node', '')
            topic = op.get('topic', '')
            payload = op.get('payload', '')
            qos = op.get('qos', 0)
            
            # Get protocol from node
            protocol = ''
            if from_node and from_node != 'broker':
                for n in nodes_ref:
                    if n.node_id == from_node:
                        protocol = n.protocol.upper()
                        break
            
            writer.writerow([timestamp, msg_type, from_node, to_node, topic, payload, qos, protocol])
        
        # Create response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=mqtt_logs.csv'}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/duty-cycle', methods=['GET'])
def export_duty_cycle():
    """Export duty cycle impact data (E1)"""
    try:
        from flask import Response
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['node_id', 'protocol', 'sleep_ratio(%)', 'avg_latency_ms', 'battery_drop(%)'])
        
        # Write data for each node
        for node in nodes_ref:
            try:
                state = node.get_state()
                energy_stats = state.get('energy_stats', {})
                
                # Calculate sleep ratio
                total_time_us = (energy_stats.get('tx_time_us', 0) + 
                                energy_stats.get('rx_time_us', 0) + 
                                energy_stats.get('sleep_time_us', 0) + 
                                energy_stats.get('idle_time_us', 0))
                
                sleep_ratio = 0
                if total_time_us > 0:
                    sleep_ratio = (energy_stats.get('sleep_time_us', 0) / total_time_us) * 100
                
                # Get latency
                avg_latency_ms = state.get('latency_ms', 0)
                
                # Calculate battery drop
                battery_drop = 100 - state.get('battery', 100)
                
                writer.writerow([
                    state['node_id'],
                    state['protocol'].upper(),
                    f"{sleep_ratio:.2f}",
                    f"{avg_latency_ms:.2f}",
                    f"{battery_drop:.2f}"
                ])
            except Exception as e:
                print(f"Error exporting node {node.node_id}: {e}")
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=duty_cycle_results.csv'}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/protocol-comparison', methods=['GET'])
def export_protocol_comparison():
    """Export protocol comparison data (E2)"""
    try:
        from flask import Response
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'node_id', 'protocol', 'distance(m)', 'messages_sent', 'messages_received',
            'delivery_ratio', 'avg_latency_ms', 'energy_used_mJ', 'battery_drop(%)',
            'retries_count', 'duplicates', 'tx_energy_mJ', 'rx_energy_mJ'
        ])
        
        # Write data for each node
        for node in nodes_ref:
            try:
                state = node.get_state()
                stats = state.get('stats', {})
                mqtt_stats = state.get('mqtt_stats', {})
                mac_stats = state.get('mac_stats', {})
                energy_stats = state.get('energy_stats', {})
                
                # Calculate delivery ratio
                messages_sent = stats.get('messages_sent', 0)
                messages_received = stats.get('messages_received', 0)
                delivery_ratio = 0
                if messages_sent > 0:
                    delivery_ratio = (messages_received / messages_sent) * 100
                
                # Calculate TX and RX energy
                tx_time_us = energy_stats.get('tx_time_us', 0)
                rx_time_us = energy_stats.get('rx_time_us', 0)
                tx_power_mw = node.phy_profile.get('tx_power_mw', 0)
                rx_power_mw = node.phy_profile.get('rx_power_mw', 0)
                
                tx_energy_mj = (tx_time_us / 1_000_000) * tx_power_mw
                rx_energy_mj = (rx_time_us / 1_000_000) * rx_power_mw
                
                writer.writerow([
                    state['node_id'],
                    state['protocol'].upper(),
                    f"{state.get('distance_to_broker', 0):.2f}",
                    messages_sent,
                    messages_received,
                    f"{delivery_ratio:.2f}",
                    f"{state.get('latency_ms', 0):.2f}",
                    f"{energy_stats.get('total_energy_mj', 0):.2f}",
                    f"{100 - state.get('battery', 100):.2f}",
                    mac_stats.get('packets_retried', 0),
                    mqtt_stats.get('duplicates_received', 0),
                    f"{tx_energy_mj:.2f}",
                    f"{rx_energy_mj:.2f}"
                ])
            except Exception as e:
                print(f"Error exporting node {node.node_id}: {e}")
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=protocol_comparison.csv'}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/failover', methods=['GET'])
def export_failover():
    """Export failover and topology change data (E3)"""
    try:
        from flask import Response
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'event', 'timestamp', 'node_id', 'state_change', 'time_to_restore_ms',
            'duplicated_messages', 'broker_position_x', 'broker_position_y'
        ])
        
        # Get failover stats
        if failover_ref:
            failover_stats = failover_ref.get_stats()
            reconnection_wave = failover_stats.get('reconnection_wave', [])
            broker_positions = failover_stats.get('broker_positions', {})
            current_broker = failover_stats.get('current_broker', 'localhost:1883')
            broker_pos = broker_positions.get(current_broker, (500, 500))
            
            # Export reconnection wave data
            for node_id, restore_time in reconnection_wave:
                # Get node duplicates
                duplicates = 0
                for node in nodes_ref:
                    if node.node_id == node_id:
                        mqtt_stats = node.mqtt_client.get_stats() if hasattr(node, 'mqtt_client') else {}
                        duplicates = mqtt_stats.get('duplicates_received', 0)
                        break
                
                writer.writerow([
                    'FAILOVER',
                    time.strftime('%Y-%m-%d %H:%M:%S'),
                    node_id,
                    'reconnected',
                    f"{restore_time * 1000:.2f}",  # Convert to ms
                    duplicates,
                    f"{broker_pos[0]:.2f}",
                    f"{broker_pos[1]:.2f}"
                ])
            
            # Export current node states
            for node in nodes_ref:
                try:
                    state = node.get_state()
                    mqtt_stats = state.get('mqtt_stats', {})
                    
                    writer.writerow([
                        'CURRENT_STATE',
                        time.strftime('%Y-%m-%d %H:%M:%S'),
                        state['node_id'],
                        'connected' if state['connected'] else 'disconnected',
                        '0',
                        mqtt_stats.get('duplicates_received', 0),
                        f"{broker_pos[0]:.2f}",
                        f"{broker_pos[1]:.2f}"
                    ])
                except Exception as e:
                    print(f"Error exporting node {node.node_id}: {e}")
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=failover_results.csv'}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    
    # Send initial data
    if nodes_ref:
        initial_nodes = []
        for n in nodes_ref:
            try:
                initial_nodes.append({
                    'id': n.node_id,
                    'protocol': n.protocol.upper(),
                    'connected': n.mqtt_client.connected if hasattr(n, 'mqtt_client') and n.mqtt_client else False
                })
            except:
                pass
        
        emit('init', {'nodes': initial_nodes})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

def start_dashboard(nodes, metrics, failover_manager, port: int):
    """Start Flask dashboard"""
    global nodes_ref, metrics_ref, failover_ref, simulation_start_time, simulation_running, simulation_paused_time, simulation_last_pause
    nodes_ref = nodes
    metrics_ref = metrics
    failover_ref = failover_manager
    # Don't set simulation_start_time here - let user click Start
    simulation_start_time = None
    simulation_running = False
    simulation_paused_time = 0
    simulation_last_pause = None
    
    # Hook all nodes
    for node in nodes:
        hook_mqtt_client(node)
    
    # Start background threads
    update_thread = threading.Thread(target=broadcast_updates, daemon=True)
    update_thread.start()
    
    message_thread = threading.Thread(target=broadcast_messages, daemon=True)
    message_thread.start()
    
    print(f"Starting Flask dashboard on http://localhost:{port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
