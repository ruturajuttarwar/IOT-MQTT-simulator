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

def hook_mqtt_client(node):
    """Hook into MQTT client to capture actual messages"""
    if not hasattr(node, 'mqtt_client') or not node.mqtt_client:
        return
    
    client = node.mqtt_client
    original_publish = client.publish
    original_subscribe = client.subscribe
    
    async def hooked_publish(topic, payload, qos=0, retain=False):
        mqtt_operations.append({
            'type': 'PUBLISH',
            'node': node.node_id,
            'topic': topic,
            'payload': payload.decode() if isinstance(payload, bytes) else str(payload),
            'qos': qos,
            'retain': retain,
            'timestamp': time.time()
        })
        return await original_publish(topic, payload, qos, retain)
    
    async def hooked_subscribe(topic, qos=0):
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
        total_subs = 0
        
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
                    'stats': state.get('stats', {}),
                    'mqtt_stats': state.get('mqtt_stats', {}),
                    'mac_stats': state.get('mac_stats', {}),
                    'energy_stats': state.get('energy_stats', {})
                })
                
                if hasattr(n, 'mqtt_client') and n.mqtt_client:
                    total_subs += len(n.mqtt_client.subscriptions)
            except Exception as e:
                print(f"Error getting node state: {e}")
                node_states.append({
                    'id': n.node_id,
                    'protocol': n.protocol.upper() if hasattr(n, 'protocol') else 'UNKNOWN',
                    'connected': n.mqtt_client.connected if hasattr(n, 'mqtt_client') and n.mqtt_client else False,
                    'battery': 100,
                    'is_mobile': False,
                    'position': [0, 0],
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
            'total_subscriptions': total_subs,
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
        
        socketio.emit('update', {
            'nodes': node_states,
            'stats': stats_data,
            'metrics': metrics_data,
            'failover_stats': failover_data
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
                'from': op['node'],
                'topic': op['topic'],
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
        
        # Set node role
        node.role = node_role
        node.subscribe_to = subscribe_to
        
        nodes_ref.append(node)
        
        # Hook MQTT client
        hook_mqtt_client(node)
        
        # Register with failover manager
        if failover_ref:
            failover_ref.register_node(node)
        
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
