"""
Improved IoT/MQTT Simulation Dashboard
- Dynamic node count control
- Clear message display with actual data
- Real-time transmission details
"""

import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import json
import time
from typing import List, Dict
from collections import deque

app = FastAPI()

nodes_ref = None
metrics_ref = None
active_connections: List[WebSocket] = []
message_log = deque(maxlen=200)
simulation_start_time = None

# Track actual MQTT operations
mqtt_operations = deque(maxlen=500)

def hook_mqtt_client(node):
    """Hook into MQTT client to capture actual messages"""
    if not hasattr(node, 'mqtt_client') or not node.mqtt_client:
        return
    
    client = node.mqtt_client
    original_publish = client.publish
    original_subscribe = client.subscribe
    
    async def hooked_publish(topic, payload, qos=0, retain=False):
        # Log the actual publish
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
        # Log the actual subscribe
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

async def start_dashboard(nodes, metrics, failover_manager, port: int):
    global nodes_ref, metrics_ref, simulation_start_time
    nodes_ref = nodes
    metrics_ref = metrics
    simulation_start_time = time.time()
    
    # Hook all nodes to capture messages
    for node in nodes:
        hook_mqtt_client(node)
    
    # Start background tasks
    asyncio.create_task(broadcast_updates())
    asyncio.create_task(broadcast_messages())
    
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

async def broadcast_messages():
    """Broadcast MQTT operations to all clients"""
    last_sent = 0
    
    while True:
        await asyncio.sleep(0.1)
        
        if not active_connections:
            continue
        
        # Send new operations
        new_ops = [op for op in mqtt_operations if op['timestamp'] > last_sent]
        
        for op in new_ops:
            data = {
                'type': 'message',
                'msg_type': op['type'],
                'from': op['node'],
                'topic': op['topic'],
                'payload': op.get('payload', ''),
                'qos': op.get('qos', 0),
                'retain': op.get('retain', False)
            }
            
            for conn in active_connections[:]:
                try:
                    await conn.send_json(data)
                except:
                    if conn in active_connections:
                        active_connections.remove(conn)
        
        if new_ops:
            last_sent = new_ops[-1]['timestamp']

async def broadcast_updates():
    """Broadcast node states and statistics"""
    while True:
        await asyncio.sleep(0.5)
        if not active_connections or not nodes_ref:
            continue
        
        # Get node states
        node_states = []
        total_subs = 0
        
        for n in nodes_ref:
            try:
                state = n.get_state()
                node_states.append({
                    'id': state['node_id'],
                    'protocol': state['protocol'].upper(),
                    'connected': state['connected'],
                    'battery': int(state.get('battery', 100))
                })
                
                if hasattr(n, 'mqtt_client') and n.mqtt_client:
                    total_subs += len(n.mqtt_client.subscriptions)
            except Exception as e:
                node_states.append({
                    'id': n.node_id,
                    'protocol': n.protocol.upper() if hasattr(n, 'protocol') else 'UNKNOWN',
                    'connected': n.mqtt_client.connected if hasattr(n, 'mqtt_client') and n.mqtt_client else False,
                    'battery': 100
                })
        
        # Get metrics
        stats_data = {
            'total_messages': len(mqtt_operations),
            'total_subscriptions': total_subs,
            'active_nodes': sum(1 for n in node_states if n['connected'])
        }
        
        if metrics_ref:
            try:
                summary = metrics_ref.get_summary()
                stats_data['total_messages'] = summary.get('total_messages_sent', len(mqtt_operations))
            except:
                pass
        
        data = {
            'type': 'update',
            'nodes': node_states,
            'stats': stats_data
        }
        
        for conn in active_connections[:]:
            try:
                await conn.send_json(data)
            except Exception as e:
                if conn in active_connections:
                    active_connections.remove(conn)

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return HTMLResponse(content=HTML_CONTENT)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    # Send initial data
    initial_nodes = []
    if nodes_ref:
        for n in nodes_ref:
            try:
                initial_nodes.append({
                    'id': n.node_id,
                    'protocol': n.protocol.upper(),
                    'connected': n.mqtt_client.connected if hasattr(n, 'mqtt_client') and n.mqtt_client else False
                })
            except Exception as e:
                print(f"Error getting node data: {e}")
    
    await websocket.send_json({
        'type': 'init',
        'nodes': initial_nodes,
        'broker': {'id': 'broker', 'x': 0, 'y': 0}
    })
    
    print(f"WebSocket connected. Sent {len(initial_nodes)} nodes")
    
    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)

HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>IoT/MQTT Simulation Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: #ffffff; 
            color: #1a1a1a;
            padding: 20px;
        }
        
        h1 { 
            font-size: 28px; 
            margin-bottom: 20px; 
            color: #2563eb;
        }
        
        #container {
            display: flex;
            gap: 20px;
            height: calc(100vh - 100px);
        }
        
        #canvas-container {
            flex: 2;
            background: #ffffff;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            position: relative;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        
        #network-canvas {
            width: 100%;
            height: 100%;
        }
        
        #sidebar {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 16px;
            overflow-y: auto;
            min-width: 400px;
            max-width: 500px;
        }
        
        .panel {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        
        .panel h3 {
            margin: 0 0 16px 0;
            color: #1f2937;
            font-size: 16px;
            font-weight: 600;
        }
        
        /* Info box */
        .info-box {
            background: #dbeafe;
            border: 1px solid #3b82f6;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 16px;
            font-size: 13px;
            color: #1e40af;
        }
        
        .info-box strong {
            display: block;
            margin-bottom: 4px;
        }
        
        /* Stats */
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        
        .stat-item {
            background: white;
            padding: 14px;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }
        
        .stat-label {
            font-size: 12px;
            color: #6b7280;
            margin-bottom: 6px;
            font-weight: 500;
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: 700;
            color: #1f2937;
        }
        
        /* Nodes */
        .node-list {
            max-height: 220px;
            overflow-y: auto;
        }
        
        .node-item {
            padding: 10px;
            margin: 6px 0;
            background: white;
            border-radius: 6px;
            border: 1px solid #e5e7eb;
            font-size: 13px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .node-ble {
            border-left: 4px solid #2563eb;
        }
        
        .node-wifi {
            border-left: 4px solid #16a34a;
        }
        
        .node-status {
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
        }
        
        .node-connected {
            background: #dcfce7;
            color: #166534;
        }
        
        .node-disconnected {
            background: #fee2e2;
            color: #991b1b;
        }
        
        /* Message Log */
        #message-log {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 12px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 11px;
            max-height: 500px;
            min-height: 350px;
        }
        
        .log-entry {
            padding: 8px;
            margin: 4px 0;
            border-radius: 4px;
            border-left: 3px solid #e5e7eb;
            background: #f9fafb;
        }
        
        .log-entry.log-publish {
            border-left-color: #2563eb;
            background: #eff6ff;
        }
        
        .log-entry.log-subscribe {
            border-left-color: #16a34a;
            background: #f0fdf4;
        }
        
        .log-entry.log-connect {
            border-left-color: #f59e0b;
            background: #fffbeb;
        }
        
        .log-time {
            color: #9ca3af;
            font-size: 10px;
            display: block;
            margin-bottom: 2px;
        }
        
        .log-header {
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .log-publish .log-header {
            color: #1e40af;
        }
        
        .log-subscribe .log-header {
            color: #166534;
        }
        
        .log-connect .log-header {
            color: #92400e;
        }
        
        .log-detail {
            color: #4b5563;
            font-size: 10px;
            margin-left: 8px;
            line-height: 1.6;
        }
        
        .log-detail strong {
            color: #1f2937;
        }
    </style>
</head>
<body>
    <h1>🌐 IoT/MQTT Network Simulation</h1>
    
    <div id="container">
        <div id="canvas-container">
            <canvas id="network-canvas"></canvas>
        </div>
        
        <div id="sidebar">
            <div class="panel">
                <h3>ℹ️ Simulation Info</h3>
                <div class="info-box">
                    <strong>Current Configuration:</strong>
                    <span id="config-info">Loading...</span>
                </div>
                <div style="font-size: 12px; color: #6b7280;">
                    To change node count, edit <code>NUM_NODES</code> in <code>config/simulation_config.py</code> and restart.
                </div>
            </div>
            
            <div class="panel">
                <h3>📊 Statistics</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-label">Messages</div>
                        <div class="stat-value" id="msg-count">0</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Active Nodes</div>
                        <div class="stat-value" id="active-nodes">0</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Uptime</div>
                        <div class="stat-value" id="uptime">0s</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Subscribers</div>
                        <div class="stat-value" id="sub-count">0</div>
                    </div>
                </div>
            </div>
            
            <div class="panel">
                <h3>📱 Nodes (<span id="node-count-display">0</span>)</h3>
                <div class="node-list" id="node-list"></div>
            </div>
            
            <div class="panel" style="flex: 1;">
                <h3>📝 MQTT Message Log</h3>
                <div id="message-log"></div>
            </div>
        </div>
    </div>

<script>
    const ws = new WebSocket('ws://localhost:8000/ws');
    const canvas = document.getElementById('network-canvas');
    const ctx = canvas.getContext('2d');
    
    let nodes = [];
    let broker = null;
    let messages = [];
    let stats = {};
    let startTime = Date.now();
    
    // Set canvas size
    function resizeCanvas() {
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    
    ws.onopen = () => {
        console.log('Connected to simulation');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'init') {
            nodes = data.nodes;
            broker = data.broker;
            updateConfigInfo();
        } else if (data.type === 'update') {
            nodes = data.nodes;
            stats = data.stats;
            updateStats();
            updateNodeList();
        } else if (data.type === 'message') {
            addMessageLog(data);
            // Add visual message pulse
            messages.push({
                from: data.from,
                to: 'broker',
                progress: 0,
                type: data.msg_type
            });
        }
    };
    
    function updateConfigInfo() {
        const bleCount = nodes.filter(n => n.protocol === 'BLE').length;
        const wifiCount = nodes.filter(n => n.protocol === 'WIFI').length;
        document.getElementById('config-info').textContent = 
            `${nodes.length} nodes (${bleCount} BLE, ${wifiCount} WiFi)`;
        document.getElementById('node-count-display').textContent = nodes.length;
    }
    
    function updateStats() {
        document.getElementById('msg-count').textContent = stats.total_messages || 0;
        document.getElementById('active-nodes').textContent = stats.active_nodes || 0;
        document.getElementById('sub-count').textContent = stats.total_subscriptions || 0;
        
        const uptime = Math.floor((Date.now() - startTime) / 1000);
        document.getElementById('uptime').textContent = uptime + 's';
    }
    
    function updateNodeList() {
        const list = document.getElementById('node-list');
        list.innerHTML = '';
        
        nodes.forEach(node => {
            const item = document.createElement('div');
            item.className = `node-item node-${node.protocol.toLowerCase()}`;
            
            const statusClass = node.connected ? 'node-connected' : 'node-disconnected';
            const statusText = node.connected ? 'Connected' : 'Disconnected';
            
            item.innerHTML = `
                <span><strong>${node.id}</strong> (${node.protocol})</span>
                <span class="node-status ${statusClass}">${statusText}</span>
            `;
            list.appendChild(item);
        });
    }
    
    function addMessageLog(data) {
        const log = document.getElementById('message-log');
        const entry = document.createElement('div');
        
        const time = new Date().toLocaleTimeString();
        
        if (data.msg_type === 'PUBLISH') {
            entry.className = 'log-entry log-publish';
            entry.innerHTML = `
                <span class="log-time">${time}</span>
                <div class="log-header">📤 PUBLISH from ${data.from}</div>
                <div class="log-detail">
                    <strong>Topic:</strong> ${data.topic}<br>
                    <strong>Payload:</strong> ${data.payload}<br>
                    <strong>QoS:</strong> ${data.qos} | <strong>Retain:</strong> ${data.retain}
                </div>
            `;
        } else if (data.msg_type === 'SUBSCRIBE') {
            entry.className = 'log-entry log-subscribe';
            entry.innerHTML = `
                <span class="log-time">${time}</span>
                <div class="log-header">📥 SUBSCRIBE from ${data.from}</div>
                <div class="log-detail">
                    <strong>Topic:</strong> ${data.topic}<br>
                    <strong>QoS:</strong> ${data.qos}
                </div>
            `;
        } else if (data.msg_type === 'CONNECT') {
            entry.className = 'log-entry log-connect';
            entry.innerHTML = `
                <span class="log-time">${time}</span>
                <div class="log-header">🔌 CONNECTED: ${data.from}</div>
            `;
        }
        
        log.appendChild(entry);
        log.scrollTop = log.scrollHeight;
        
        // Keep only last 100 entries
        while (log.children.length > 100) {
            log.removeChild(log.firstChild);
        }
    }
    
    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (!broker || nodes.length === 0) {
            requestAnimationFrame(draw);
            return;
        }
        
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = Math.min(canvas.width, canvas.height) * 0.35;
        
        // Draw connection lines first
        nodes.forEach((node, i) => {
            const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
            const x = centerX + Math.cos(angle) * radius;
            const y = centerY + Math.sin(angle) * radius;
            
            if (node.connected) {
                ctx.strokeStyle = '#9ca3af';
                ctx.lineWidth = 2;
            } else {
                ctx.strokeStyle = '#e5e7eb';
                ctx.lineWidth = 1;
            }
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(x, y);
            ctx.stroke();
        });
        
        // Draw broker
        ctx.fillStyle = '#dc2626';
        ctx.beginPath();
        ctx.arc(centerX, centerY, 35, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#991b1b';
        ctx.lineWidth = 3;
        ctx.stroke();
        
        ctx.fillStyle = 'white';
        ctx.font = 'bold 16px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('MQTT', centerX, centerY - 6);
        ctx.font = '12px Arial';
        ctx.fillText('Broker', centerX, centerY + 10);
        
        // Draw nodes
        nodes.forEach((node, i) => {
            const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
            const x = centerX + Math.cos(angle) * radius;
            const y = centerY + Math.sin(angle) * radius;
            
            ctx.fillStyle = node.protocol === 'BLE' ? '#2563eb' : '#16a34a';
            ctx.beginPath();
            ctx.arc(x, y, 22, 0, Math.PI * 2);
            ctx.fill();
            
            ctx.strokeStyle = node.connected ? '#1f2937' : '#9ca3af';
            ctx.lineWidth = 3;
            ctx.stroke();
            
            ctx.fillStyle = '#1f2937';
            ctx.font = 'bold 11px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(node.id.split('_').pop(), x, y + 36);
            
            ctx.font = '9px Arial';
            ctx.fillStyle = '#6b7280';
            ctx.fillText(node.protocol, x, y + 48);
        });
        
        // Draw message pulses
        messages = messages.filter(msg => {
            msg.progress += 0.018;
            if (msg.progress > 1) return false;
            
            const fromNode = nodes.find(n => n.id === msg.from);
            if (!fromNode) return false;
            
            const fromIdx = nodes.indexOf(fromNode);
            const angle = (fromIdx / nodes.length) * Math.PI * 2 - Math.PI / 2;
            const fromX = centerX + Math.cos(angle) * radius;
            const fromY = centerY + Math.sin(angle) * radius;
            
            const x = fromX + (centerX - fromX) * msg.progress;
            const y = fromY + (centerY - fromY) * msg.progress;
            
            const pulseColor = msg.type === 'PUBLISH' ? '#f59e0b' : '#16a34a';
            ctx.fillStyle = pulseColor;
            ctx.globalAlpha = 1 - msg.progress * 0.6;
            ctx.beginPath();
            ctx.arc(x, y, 7, 0, Math.PI * 2);
            ctx.fill();
            ctx.globalAlpha = 1;
            
            return true;
        });
        
        requestAnimationFrame(draw);
    }
    
    draw();
</script>
</body>
</html>
"""
