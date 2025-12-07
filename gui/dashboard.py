"""
FastAPI dashboard for live simulation visualization
"""

import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import time
from typing import List
from collections import deque

app = FastAPI(title="IoT/MQTT Simulation Dashboard")

# Global references (set by main.py)
nodes_ref = None
metrics_ref = None
failover_ref = None

# WebSocket connections
active_connections: List[WebSocket] = []

# Log buffer for UI
log_buffer = deque(maxlen=500)

def add_log(log_type: str, message: str):
    """Add log entry for UI"""
    log_buffer.append({
        'timestamp': time.time(),
        'type': log_type,
        'message': message
    })


async def start_dashboard(nodes, metrics, failover_manager, port: int):
    """Start the FastAPI dashboard"""
    global nodes_ref, metrics_ref, failover_ref
    
    nodes_ref = nodes
    metrics_ref = metrics
    failover_ref = failover_manager
    
    # Mount static files
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    
    # Start background task to push updates
    asyncio.create_task(broadcast_updates())
    
    # Run server
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve main dashboard HTML"""
    html_path = Path(__file__).parent / "templates" / "dashboard.html"
    
    if html_path.exists():
        return FileResponse(html_path)
    else:
        # Return inline HTML if file doesn't exist
        return HTMLResponse(content=get_inline_html())


@app.get("/api/metrics")
async def get_metrics():
    """Get current metrics"""
    if metrics_ref:
        return metrics_ref.get_summary()
    return {}


@app.get("/api/nodes")
async def get_nodes():
    """Get all node states"""
    if nodes_ref:
        return [node.get_state() for node in nodes_ref]
    return []


@app.post("/api/failover")
async def trigger_failover():
    """Trigger broker failover"""
    if failover_ref:
        await failover_ref.manual_failover()
        return {"status": "failover_triggered"}
    return {"status": "error", "message": "Failover manager not available"}


@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for live updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast_updates():
    """Broadcast updates to all connected clients"""
    while True:
        await asyncio.sleep(0.5)  # Update every 0.5 seconds
        
        if not active_connections:
            continue
            
        # Gather data
        data = {
            'metrics': metrics_ref.get_summary() if metrics_ref else {},
            'nodes': [node.get_state() for node in nodes_ref] if nodes_ref else [],
            'failover': failover_ref.get_stats() if failover_ref else {},
            'logs': list(log_buffer)[-50:],  # Last 50 logs
            'timestamp': time.time()
        }
        
        # Broadcast to all connections
        disconnected = []
        for connection in active_connections:
            try:
                await connection.send_json(data)
            except:
                disconnected.append(connection)
                
        # Remove disconnected clients
        for conn in disconnected:
            active_connections.remove(conn)


def get_inline_html() -> str:
    """Return inline HTML for dashboard"""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>IoT/MQTT Simulation Dashboard</title>
    <meta charset="utf-8">
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background: #0f172a; color: #e2e8f0; overflow: hidden; }
        
        .header { background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 16px 24px; box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3); display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 24px; color: white; font-weight: 600; }
        .header .status { font-size: 14px; color: #cbd5e1; }
        
        .main-container { display: grid; grid-template-columns: 1fr 400px; height: calc(100vh - 70px); }
        
        .left-panel { display: flex; flex-direction: column; gap: 16px; padding: 16px; overflow-y: auto; }
        .right-panel { background: #1e293b; border-left: 1px solid #334155; display: flex; flex-direction: column; }
        
        .card { background: #1e293b; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); border: 1px solid #334155; }
        .card-title { font-size: 16px; font-weight: 600; color: #f1f5f9; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
        
        .controls { display: flex; gap: 12px; flex-wrap: wrap; }
        button { background: #6366f1; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s; }
        button:hover { background: #4f46e5; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4); }
        button.danger { background: #ef4444; }
        button.danger:hover { background: #dc2626; }
        button.success { background: #10b981; }
        button.success:hover { background: #059669; }
        
        #network-graph { width: 100%; height: 500px; background: #0f172a; border-radius: 8px; position: relative; border: 1px solid #334155; }
        
        .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
        .metric-card { background: #0f172a; padding: 16px; border-radius: 8px; text-align: center; border: 1px solid #334155; }
        .metric-value { font-size: 28px; font-weight: 700; color: #6366f1; margin-bottom: 4px; }
        .metric-label { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }
        
        .tabs { display: flex; border-bottom: 1px solid #334155; }
        .tab { padding: 12px 20px; cursor: pointer; color: #94a3b8; font-size: 14px; font-weight: 500; border-bottom: 2px solid transparent; transition: all 0.2s; }
        .tab.active { color: #6366f1; border-bottom-color: #6366f1; }
        .tab:hover { color: #e2e8f0; }
        
        .tab-content { flex: 1; overflow-y: auto; padding: 16px; }
        .tab-panel { display: none; }
        .tab-panel.active { display: block; }
        
        .node-item { background: #0f172a; padding: 12px; margin-bottom: 8px; border-radius: 6px; border-left: 3px solid #6366f1; font-size: 13px; }
        .node-item.connected { border-left-color: #10b981; }
        .node-item.disconnected { border-left-color: #ef4444; }
        .node-item .node-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
        .node-item .node-id { font-weight: 600; color: #f1f5f9; }
        .node-item .node-protocol { background: #334155; padding: 2px 8px; border-radius: 4px; font-size: 11px; color: #cbd5e1; }
        .node-item .node-stats { color: #94a3b8; font-size: 12px; }
        
        .log-container { font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.6; }
        .log-entry { padding: 6px 12px; border-bottom: 1px solid #1e293b; }
        .log-entry.info { color: #60a5fa; }
        .log-entry.success { color: #34d399; }
        .log-entry.warning { color: #fbbf24; }
        .log-entry.error { color: #f87171; }
        .log-entry.mqtt { color: #a78bfa; }
        .log-entry .timestamp { color: #64748b; margin-right: 8px; }
        
        .status-badge { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
        .status-badge.connected { background: #10b981; box-shadow: 0 0 8px #10b981; }
        .status-badge.disconnected { background: #ef4444; }
        
        /* D3 Network Graph Styles */
        .node-circle { cursor: pointer; transition: all 0.2s; }
        .node-circle:hover { stroke-width: 3px; }
        .node-label { font-size: 10px; fill: #cbd5e1; pointer-events: none; }
        .link { stroke: #334155; stroke-opacity: 0.6; }
        .link.active { stroke: #6366f1; stroke-opacity: 1; stroke-width: 2px; animation: pulse 2s infinite; }
        
        @keyframes pulse {
            0%, 100% { stroke-opacity: 0.6; }
            50% { stroke-opacity: 1; }
        }
        
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #1e293b; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #475569; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🌐 IoT/MQTT Simulation Dashboard</h1>
            <div class="status">Real-time Network Monitoring</div>
        </div>
        <div class="controls">
            <button onclick="triggerFailover()" class="danger">⚠️ Trigger Failover</button>
            <button onclick="exportMetrics()">📊 Export Data</button>
        </div>
    </div>
    
    <div class="main-container">
        <div class="left-panel">
            <div class="card">
                <div class="card-title">📊 Metrics</div>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value" id="totalMessages">0</div>
                        <div class="metric-label">Messages</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="deliveryRatio">0%</div>
                        <div class="metric-label">Delivery</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="avgLatency">0ms</div>
                        <div class="metric-label">Latency</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="nodeCount">0</div>
                        <div class="metric-label">Nodes</div>
                    </div>
                </div>
            </div>
            
            <div class="card" style="flex: 1;">
                <div class="card-title">🗺️ Network Topology</div>
                <div id="network-graph"></div>
            </div>
        </div>
        
        <div class="right-panel">
            <div class="tabs">
                <div class="tab active" onclick="switchTab('nodes')">Nodes</div>
                <div class="tab" onclick="switchTab('logs')">Logs</div>
            </div>
            <div class="tab-content">
                <div id="nodes-panel" class="tab-panel active">
                    <div id="nodeList"></div>
                </div>
                <div id="logs-panel" class="tab-panel">
                    <div class="log-container" id="logContainer"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let simulation, svg, nodes = [], links = [];
        
        // Initialize D3 network graph
        function initGraph() {
            const container = document.getElementById('network-graph');
            const width = container.clientWidth;
            const height = container.clientHeight;
            
            svg = d3.select('#network-graph')
                .append('svg')
                .attr('width', width)
                .attr('height', height);
            
            simulation = d3.forceSimulation()
                .force('link', d3.forceLink().id(d => d.id).distance(100))
                .force('charge', d3.forceManyBody().strength(-300))
                .force('center', d3.forceCenter(width / 2, height / 2))
                .force('collision', d3.forceCollide().radius(30));
        }
        
        function updateGraph(nodeData) {
            if (!svg) return;
            
            // Update nodes
            nodes = nodeData.map(n => ({
                id: n.node_id,
                protocol: n.protocol,
                connected: n.connected,
                x: n.position[0] / 5,
                y: n.position[1] / 5
            }));
            
            // Create links (simplified - connect to nearest nodes)
            links = [];
            
            svg.selectAll('*').remove();
            
            const link = svg.append('g')
                .selectAll('line')
                .data(links)
                .enter().append('line')
                .attr('class', 'link');
            
            const node = svg.append('g')
                .selectAll('circle')
                .data(nodes)
                .enter().append('circle')
                .attr('class', 'node-circle')
                .attr('r', d => d.protocol === 'broker' ? 12 : 8)
                .attr('fill', d => {
                    if (!d.connected) return '#ef4444';
                    return d.protocol === 'ble' ? '#3b82f6' : '#10b981';
                })
                .attr('stroke', '#1e293b')
                .attr('stroke-width', 2)
                .call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended));
            
            const label = svg.append('g')
                .selectAll('text')
                .data(nodes)
                .enter().append('text')
                .attr('class', 'node-label')
                .text(d => d.id.split('_')[0]);
            
            simulation.nodes(nodes).on('tick', () => {
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
                
                node
                    .attr('cx', d => d.x)
                    .attr('cy', d => d.y);
                
                label
                    .attr('x', d => d.x)
                    .attr('y', d => d.y - 15);
            });
            
            simulation.force('link').links(links);
            simulation.alpha(0.3).restart();
        }
        
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        // WebSocket connection
        const ws = new WebSocket(`ws://${window.location.host}/ws/live`);
        
        ws.onopen = () => console.log('Connected to simulation');
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        };
        
        function updateDashboard(data) {
            // Update metrics
            const metrics = data.metrics || {};
            document.getElementById('totalMessages').textContent = metrics.total_messages_sent || 0;
            document.getElementById('deliveryRatio').textContent = ((metrics.delivery_ratio || 0) * 100).toFixed(1) + '%';
            document.getElementById('avgLatency').textContent = (metrics.avg_latency_ms || 0).toFixed(1) + 'ms';
            
            // Update nodes
            const nodeData = data.nodes || [];
            document.getElementById('nodeCount').textContent = nodeData.length;
            
            const nodeList = document.getElementById('nodeList');
            nodeList.innerHTML = nodeData.map(node => `
                <div class="node-item ${node.connected ? 'connected' : 'disconnected'}">
                    <div class="node-header">
                        <span class="node-id">
                            <span class="status-badge ${node.connected ? 'connected' : 'disconnected'}"></span>
                            ${node.node_id}
                        </span>
                        <span class="node-protocol">${node.protocol.toUpperCase()}</span>
                    </div>
                    <div class="node-stats">
                        🔋 ${node.battery.toFixed(0)}% | 📤 ${node.stats.messages_sent} | 📥 ${node.mqtt_stats.messages_received}
                    </div>
                </div>
            `).join('');
            
            // Update graph
            updateGraph(nodeData);
            
            // Update logs
            if (data.logs) {
                updateLogs(data.logs);
            }
        }
        
        function updateLogs(logs) {
            const logContainer = document.getElementById('logContainer');
            logContainer.innerHTML = logs.map(log => {
                const time = new Date(log.timestamp * 1000).toLocaleTimeString();
                return `<div class="log-entry ${log.type}"><span class="timestamp">${time}</span>${log.message}</div>`;
            }).join('');
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tab + '-panel').classList.add('active');
        }
        
        async function triggerFailover() {
            const response = await fetch('/api/failover', { method: 'POST' });
            alert('Failover triggered!');
        }
        
        async function exportMetrics() {
            const response = await fetch('/api/metrics');
            const metrics = await response.json();
            const blob = new Blob([JSON.stringify(metrics, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `metrics_${Date.now()}.json`;
            a.click();
        }
        
        // Initialize
        initGraph();
        setInterval(() => ws.send('ping'), 30000);
    </script>
</body>
</html>
    """
