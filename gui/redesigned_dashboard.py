"""
Redesigned IoT/MQTT Simulation Dashboard
Features: Start/Stop, Node Count Control, Visual Links, Message Logs
"""

import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import json
import time
from typing import List
from collections import deque

app = FastAPI()

nodes_ref = None
metrics_ref = None
active_connections: List[WebSocket] = []
message_log = deque(maxlen=200)
simulation_start_time = None

async def start_dashboard(nodes, metrics, failover_manager, port: int):
    global nodes_ref, metrics_ref, simulation_start_time
    nodes_ref = nodes
    metrics_ref = metrics
    simulation_start_time = time.time()
    
    # Start background tasks
    asyncio.create_task(broadcast_updates())
    asyncio.create_task(monitor_mqtt_messages())
    
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

async def monitor_mqtt_messages():
    """Monitor MQTT messages from nodes"""
    last_stats = {}
    
    while True:
        await asyncio.sleep(0.2)
        
        if not nodes_ref:
            continue
        
        for node in nodes_ref:
            if not hasattr(node, 'mqtt_client') or not node.mqtt_client:
                continue
            
            stats = node.mqtt_client.stats
            node_id = node.node_id
            
            # Check for new messages
            if node_id not in last_stats:
                last_stats[node_id] = {
                    'messages_sent': 0,
                    'qos0_messages': 0,
                    'qos1_messages': 0
                }
            
            # Detect new publishes
            if stats['messages_sent'] > last_stats[node_id]['messages_sent']:
                # Generate a sample topic based on node type
                if 'temp' in node_id or 'sensor' in node_id:
                    topic = f"sensors/{node_id}/temperature"
                    payload = f"temp={20 + (hash(node_id) % 15)}°C"
                else:
                    topic = f"nodes/{node_id}/data"
                    payload = f"value={hash(node_id + str(time.time())) % 100}"
                
                log_message('PUBLISH', node_id, topic, payload)
            
            last_stats[node_id] = stats.copy()

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

async def broadcast_updates():
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
                    'connected': state['connected']
                })
                
                # Count subscriptions
                if hasattr(n, 'mqtt_client') and n.mqtt_client:
                    total_subs += len(n.mqtt_client.subscriptions)
            except Exception as e:
                # Fallback if get_state fails
                node_states.append({
                    'id': n.node_id,
                    'protocol': n.protocol.upper() if hasattr(n, 'protocol') else 'UNKNOWN',
                    'connected': n.mqtt_client.connected if hasattr(n, 'mqtt_client') and n.mqtt_client else False
                })
        
        # Get metrics
        stats_data = {
            'total_messages': 0,
            'total_subscriptions': total_subs,
            'active_nodes': sum(1 for n in node_states if n['connected'])
        }
        
        if metrics_ref:
            try:
                summary = metrics_ref.get_summary()
                stats_data['total_messages'] = summary.get('total_messages_sent', 0)
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

def log_message(msg_type: str, from_node: str, topic: str = "", payload: str = ""):
    """Log MQTT messages for display"""
    message_log.append({
        'type': 'message',
        'msg_type': msg_type,
        'from': from_node,
        'topic': topic,
        'payload': payload,
        'timestamp': time.time()
    })
    
    # Broadcast to all connections
    for conn in active_connections[:]:
        try:
            asyncio.create_task(conn.send_json({
                'type': 'message',
                'msg_type': msg_type,
                'from': from_node,
                'topic': topic,
                'payload': payload
            }))
        except:
            pass

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
            min-width: 380px;
            max-width: 450px;
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
        
        /* Controls */
        .controls {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .control-row {
            display: flex;
            gap: 10px;
        }
        
        button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            flex: 1;
        }
        
        #start-btn {
            background: #16a34a;
            color: white;
        }
        
        #start-btn:hover:not(:disabled) {
            background: #15803d;
        }
        
        #stop-btn {
            background: #dc2626;
            color: white;
        }
        
        #stop-btn:hover:not(:disabled) {
            background: #b91c1c;
        }
        
        button:disabled {
            background: #d1d5db;
            cursor: not-allowed;
            opacity: 0.6;
        }
        
        .input-group {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .input-group label {
            font-size: 14px;
            color: #374151;
            font-weight: 500;
            min-width: 120px;
        }
        
        .input-group input {
            flex: 1;
            padding: 10px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 14px;
        }
        
        .status-row {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #6b7280;
            padding: 8px;
            background: white;
            border-radius: 6px;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
        }
        
        .status-running {
            background: #16a34a;
            box-shadow: 0 0 8px rgba(22, 163, 74, 0.6);
        }
        
        .status-stopped {
            background: #dc2626;
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
            max-height: 450px;
            min-height: 300px;
        }
        
        .log-entry {
            padding: 6px 0;
            border-bottom: 1px solid #f3f4f6;
            line-height: 1.5;
        }
        
        .log-entry:last-child {
            border-bottom: none;
        }
        
        .log-time {
            color: #9ca3af;
            margin-right: 8px;
        }
        
        .log-publish {
            color: #2563eb;
            font-weight: 600;
        }
        
        .log-subscribe {
            color: #16a34a;
            font-weight: 600;
        }
        
        .log-connect {
            color: #f59e0b;
            font-weight: 600;
        }
        
        .log-data {
            color: #6b7280;
            font-size: 10px;
            display: block;
            margin-left: 70px;
            margin-top: 2px;
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
                <h3>🎮 Controls</h3>
                <div class="controls">
                    <div class="control-row">
                        <button id="start-btn">▶ Start Simulation</button>
                        <button id="stop-btn" disabled>⏹ Stop</button>
                    </div>
                    <div class="input-group">
                        <label>Number of Nodes:</label>
                        <input type="number" id="node-count-input" min="2" max="50" value="10">
                    </div>
                    <div class="status-row">
                        <span class="status-indicator status-stopped" id="status-indicator"></span>
                        <span id="status-text">Stopped</span>
                    </div>
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
                <h3>📱 Nodes</h3>
                <div class="node-list" id="node-list"></div>
            </div>
            
            <div class="panel" style="flex: 1;">
                <h3>📝 Message Log</h3>
                <div id="message-log"></div>
            </div>
        </div>
    </div>

<script>
    let ws = null;
    const canvas = document.getElementById('network-canvas');
    const ctx = canvas.getContext('2d');
    
    let nodes = [];
    let broker = null;
    let messages = [];
    let stats = {};
    let startTime = Date.now();
    let isRunning = false;
    let animationFrame = null;
    
    // Set canvas size
    function resizeCanvas() {
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    
    // Control buttons
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const nodeCountInput = document.getElementById('node-count-input');
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    
    startBtn.addEventListener('click', startSimulation);
    stopBtn.addEventListener('click', stopSimulation);
    
    function startSimulation() {
        const nodeCount = parseInt(nodeCountInput.value);
        if (nodeCount < 2 || nodeCount > 50) {
            alert('Please enter a node count between 2 and 50');
            return;
        }
        
        startBtn.disabled = true;
        stopBtn.disabled = false;
        nodeCountInput.disabled = true;
        isRunning = true;
        statusIndicator.className = 'status-indicator status-running';
        statusText.textContent = 'Running';
        
        // Connect WebSocket
        connectWebSocket();
        startTime = Date.now();
    }
    
    function stopSimulation() {
        startBtn.disabled = false;
        stopBtn.disabled = true;
        nodeCountInput.disabled = false;
        isRunning = false;
        statusIndicator.className = 'status-indicator status-stopped';
        statusText.textContent = 'Stopped';
        
        if (ws) {
            ws.close();
            ws = null;
        }
        
        // Clear display
        nodes = [];
        messages = [];
        document.getElementById('message-log').innerHTML = '';
        document.getElementById('node-list').innerHTML = '';
    }
    
    function connectWebSocket() {
        ws = new WebSocket('ws://localhost:8000/ws');
        
        ws.onopen = () => {
            console.log('Connected to simulation');
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        ws.onclose = () => {
            console.log('Disconnected from simulation');
        };
        
        ws.onmessage = handleMessage;
    }
    
    function handleMessage(event) {
        const data = JSON.parse(event.data);
        
        if (data.type === 'init') {
            nodes = data.nodes;
            broker = data.broker;
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
    }
    
    function updateStats() {
        document.getElementById('msg-count').textContent = stats.total_messages || 0;
        document.getElementById('active-nodes').textContent = nodes.filter(n => n.connected).length;
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
        entry.className = 'log-entry';
        
        const time = new Date().toLocaleTimeString();
        let msgClass = 'log-publish';
        let msgText = '';
        let dataText = '';
        
        if (data.msg_type === 'PUBLISH') {
            msgClass = 'log-publish';
            msgText = `${data.from} → PUBLISH`;
            dataText = `topic="${data.topic}" ${data.payload || ''}`;
        } else if (data.msg_type === 'SUBSCRIBE') {
            msgClass = 'log-subscribe';
            msgText = `${data.from} → SUBSCRIBE`;
            dataText = `topic="${data.topic}"`;
        } else if (data.msg_type === 'CONNECT') {
            msgClass = 'log-connect';
            msgText = `${data.from} → CONNECTED`;
        }
        
        entry.innerHTML = `
            <span class="log-time">${time}</span>
            <span class="${msgClass}">${msgText}</span>
            ${dataText ? `<span class="log-data">${dataText}</span>` : ''}
        `;
        log.appendChild(entry);
        log.scrollTop = log.scrollHeight;
        
        // Keep only last 150 entries
        while (log.children.length > 150) {
            log.removeChild(log.firstChild);
        }
    }
    
    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (!isRunning || !broker || nodes.length === 0) {
            animationFrame = requestAnimationFrame(draw);
            return;
        }
        
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = Math.min(canvas.width, canvas.height) * 0.35;
        
        // Draw connection lines first (behind nodes)
        nodes.forEach((node, i) => {
            const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
            const x = centerX + Math.cos(angle) * radius;
            const y = centerY + Math.sin(angle) * radius;
            
            // Draw connection line to broker
            if (node.connected) {
                ctx.strokeStyle = '#9ca3af';
                ctx.lineWidth = 2;
            } else {
                ctx.strokeStyle = '#e5e7eb';
                ctx.lineWidth = 1;
            }
            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(x, y);
            ctx.stroke();
        });
        
        // Draw broker (red circle in center)
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
        
        // Draw nodes as circles
        nodes.forEach((node, i) => {
            const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
            const x = centerX + Math.cos(angle) * radius;
            const y = centerY + Math.sin(angle) * radius;
            
            // Draw node circle
            ctx.fillStyle = node.protocol === 'BLE' ? '#2563eb' : '#16a34a';
            ctx.beginPath();
            ctx.arc(x, y, 22, 0, Math.PI * 2);
            ctx.fill();
            
            // Draw border
            ctx.strokeStyle = node.connected ? '#1f2937' : '#9ca3af';
            ctx.lineWidth = 3;
            ctx.stroke();
            
            // Draw node label
            ctx.fillStyle = '#1f2937';
            ctx.font = 'bold 12px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(node.id, x, y + 36);
            
            // Draw protocol label
            ctx.font = '10px Arial';
            ctx.fillStyle = '#6b7280';
            ctx.fillText(node.protocol, x, y + 50);
        });
        
        // Draw message pulses (animated dots)
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
            
            // Draw pulse
            const pulseColor = msg.type === 'PUBLISH' ? '#f59e0b' : '#16a34a';
            ctx.fillStyle = pulseColor;
            ctx.globalAlpha = 1 - msg.progress * 0.6;
            ctx.beginPath();
            ctx.arc(x, y, 7, 0, Math.PI * 2);
            ctx.fill();
            ctx.globalAlpha = 1;
            
            return true;
        });
        
        animationFrame = requestAnimationFrame(draw);
    }
    
    draw();
</script>
</body>
</html>
"""
