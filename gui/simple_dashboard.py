"""
Simple, clear dashboard matching the topology diagram
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
failover_ref = None
active_connections: List[WebSocket] = []
log_buffer = deque(maxlen=100)

def add_log(log_type: str, message: str):
    log_buffer.append({
        'timestamp': time.time(),
        'type': log_type,
        'message': message
    })

async def start_dashboard(nodes, metrics, failover_manager, port: int):
    global nodes_ref, metrics_ref, failover_ref
    nodes_ref = nodes
    metrics_ref = metrics
    failover_ref = failover_manager
    
    asyncio.create_task(broadcast_updates())
    
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return HTMLResponse(content=get_html())

@app.post("/api/failover")
async def trigger_failover():
    if failover_ref:
        await failover_ref.manual_failover()
        return {"status": "ok"}
    return {"status": "error"}

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        active_connections.remove(websocket)

async def broadcast_updates():
    while True:
        await asyncio.sleep(1.0)
        if not active_connections:
            continue
        
        data = {
            'nodes': [n.get_state() for n in nodes_ref] if nodes_ref else [],
            'metrics': metrics_ref.get_summary() if metrics_ref else {},
            'logs': list(log_buffer)[-20:],
            'timestamp': time.time()
        }
        
        for conn in active_connections[:]:
            try:
                await conn.send_json(data)
            except:
                active_connections.remove(conn)

def get_html():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>IoT MQTT Simulation - Complete Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #1a1a2e; color: #fff; }
        
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; }
        .header h1 { font-size: 24px; margin-bottom: 5px; }
        
        .container { display: grid; grid-template-columns: 1fr 350px; height: calc(100vh - 80px); }
        
        .main-area { padding: 30px; position: relative; }
        .sidebar { background: #16213e; padding: 20px; overflow-y: auto; border-left: 2px solid #0f4c75; }
        
        /* Topology Layout */
        .topology { position: relative; height: 600px; background: #0f172a; border-radius: 12px; border: 2px solid #334155; }
        
        .broker { position: absolute; left: 50%; top: 20%; transform: translateX(-50%); width: 140px; height: 80px; background: #ef4444; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 4px 20px rgba(239, 68, 68, 0.4); z-index: 10; }
        .broker-label { font-weight: bold; font-size: 14px; }
        .broker-status { font-size: 11px; color: #fecaca; margin-top: 4px; }
        
        .node { position: absolute; width: 120px; height: 70px; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.3); transition: all 0.3s; }
        .node.ble { background: #3b82f6; }
        .node.wifi { background: #10b981; }
        .node-label { font-weight: bold; font-size: 13px; }
        .node-protocol { font-size: 10px; opacity: 0.8; margin-top: 3px; }
        .node-stats { font-size: 9px; margin-top: 3px; }
        
        /* Position nodes in a circle around broker */
        .node:nth-child(2) { left: 10%; top: 50%; }
        .node:nth-child(3) { left: 30%; top: 75%; }
        .node:nth-child(4) { right: 30%; top: 75%; }
        .node:nth-child(5) { right: 10%; top: 50%; }
        .node:nth-child(6) { left: 50%; top: 85%; transform: translateX(-50%); }
        
        /* Connection lines */
        .connections { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }
        .connection-line { stroke: #475569; stroke-width: 2; opacity: 0.4; }
        .connection-line.active { stroke: #6366f1; stroke-width: 3; opacity: 1; animation: pulse 2s infinite; }
        
        @keyframes pulse {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
        }
        
        /* Topics box */
        .topics-box { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); background: #1e293b; padding: 15px 25px; border-radius: 8px; border: 2px dashed #475569; }
        .topics-box h3 { font-size: 12px; color: #94a3b8; margin-bottom: 8px; text-align: center; }
        .topic-item { background: #0f172a; padding: 6px 12px; margin: 4px; border-radius: 4px; font-size: 11px; display: inline-block; color: #60a5fa; }
        
        /* Metrics */
        .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
        .metric-card { background: #16213e; padding: 15px; border-radius: 8px; text-align: center; }
        .metric-value { font-size: 28px; font-weight: bold; color: #667eea; }
        .metric-label { font-size: 11px; color: #94a3b8; margin-top: 5px; }
        
        /* Sidebar */
        .section { margin-bottom: 25px; }
        .section-title { font-size: 14px; font-weight: bold; color: #667eea; margin-bottom: 12px; }
        
        .node-item { background: #0f172a; padding: 10px; margin-bottom: 8px; border-radius: 6px; border-left: 3px solid #667eea; }
        .node-item.connected { border-left-color: #10b981; }
        .node-item.disconnected { border-left-color: #ef4444; }
        
        .log-entry { padding: 6px 10px; font-size: 11px; font-family: 'Courier New', monospace; border-bottom: 1px solid #1e293b; }
        .log-entry.mqtt { color: #a78bfa; }
        .log-entry.info { color: #60a5fa; }
        .log-entry.success { color: #34d399; }
        
        button { background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 13px; margin: 5px; }
        button:hover { background: #5568d3; }
        button.danger { background: #ef4444; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌐 IoT MQTT Simulation</h1>
        <div>
            <button onclick="triggerFailover()" class="danger">⚠️ Trigger Failover</button>
        </div>
    </div>
    
    <div class="container">
        <div class="main-area">
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-value" id="nodeCount">0</div>
                    <div class="metric-label">Nodes</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="messages">0</div>
                    <div class="metric-label">Messages</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="delivery">0%</div>
                    <div class="metric-label">Delivery</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="latency">0ms</div>
                    <div class="metric-label">Latency</div>
                </div>
            </div>
            
            <div class="topology" id="topology">
                <svg class="connections" id="connections"></svg>
                
                <div class="broker">
                    <div class="broker-label">MQTT Broker</div>
                    <div class="broker-status">localhost:1883</div>
                </div>
                
                <div id="nodes-container"></div>
                
                <div class="topics-box">
                    <h3>📋 TOPICS</h3>
                    <div id="topics"></div>
                </div>
            </div>
        </div>
        
        <div class="sidebar">
            <div class="section">
                <div class="section-title">📡 Nodes</div>
                <div id="nodeList"></div>
            </div>
            
            <div class="section">
                <div class="section-title">📝 Live Logs</div>
                <div id="logs"></div>
            </div>
        </div>
    </div>
    
    <script>
        const ws = new WebSocket(`ws://${window.location.host}/ws/live`);
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        };
        
        function updateDashboard(data) {
            const nodes = data.nodes || [];
            const metrics = data.metrics || {};
            
            // Update metrics
            document.getElementById('nodeCount').textContent = nodes.length;
            document.getElementById('messages').textContent = metrics.total_messages_sent || 0;
            document.getElementById('delivery').textContent = ((metrics.delivery_ratio || 0) * 100).toFixed(0) + '%';
            document.getElementById('latency').textContent = (metrics.avg_latency_ms || 0).toFixed(0) + 'ms';
            
            // Update nodes in topology
            const container = document.getElementById('nodes-container');
            container.innerHTML = nodes.map((node, i) => `
                <div class="node ${node.protocol}" style="animation-delay: ${i * 0.1}s">
                    <div class="node-label">${node.node_id}</div>
                    <div class="node-protocol">${node.protocol.toUpperCase()}</div>
                    <div class="node-stats">📤 ${node.stats.messages_sent} | 🔋 ${node.battery.toFixed(0)}%</div>
                </div>
            `).join('');
            
            // Draw connection lines
            drawConnections(nodes);
            
            // Update topics
            const topics = new Set();
            nodes.forEach(n => {
                topics.add(`sensors/${n.node_id}/data`);
            });
            document.getElementById('topics').innerHTML = Array.from(topics).map(t => 
                `<span class="topic-item">${t}</span>`
            ).join('');
            
            // Update node list
            document.getElementById('nodeList').innerHTML = nodes.map(node => `
                <div class="node-item ${node.connected ? 'connected' : 'disconnected'}">
                    <strong>${node.node_id}</strong> (${node.protocol.toUpperCase()})
                    <br><small>📤 ${node.stats.messages_sent} | 🔋 ${node.battery.toFixed(0)}%</small>
                </div>
            `).join('');
            
            // Update logs
            if (data.logs) {
                document.getElementById('logs').innerHTML = data.logs.slice(-10).map(log => {
                    const time = new Date(log.timestamp * 1000).toLocaleTimeString();
                    return `<div class="log-entry ${log.type}">[${time}] ${log.message}</div>`;
                }).join('');
            }
        }
        
        function drawConnections(nodes) {
            const svg = document.getElementById('connections');
            const topology = document.getElementById('topology');
            const rect = topology.getBoundingClientRect();
            
            // Broker position (center top)
            const brokerX = rect.width / 2;
            const brokerY = rect.height * 0.2;
            
            // Clear existing lines
            svg.innerHTML = '';
            
            // Draw lines from broker to each node
            const nodeElements = document.querySelectorAll('.node');
            nodeElements.forEach((nodeEl, i) => {
                const nodeRect = nodeEl.getBoundingClientRect();
                const topologyRect = topology.getBoundingClientRect();
                
                const nodeX = nodeRect.left - topologyRect.left + nodeRect.width / 2;
                const nodeY = nodeRect.top - topologyRect.top + nodeRect.height / 2;
                
                const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line.setAttribute('x1', brokerX);
                line.setAttribute('y1', brokerY + 40);
                line.setAttribute('x2', nodeX);
                line.setAttribute('y2', nodeY);
                line.setAttribute('class', 'connection-line active');
                svg.appendChild(line);
            });
        }
        
        async function triggerFailover() {
            await fetch('/api/failover', { method: 'POST' });
            alert('Failover triggered!');
        }
        
        setInterval(() => ws.send('ping'), 30000);
    </script>
</body>
</html>
    """

# Export for main.py
start_dashboard = start_dashboard
add_log = add_log
