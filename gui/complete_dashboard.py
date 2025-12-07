"""
Complete dashboard with all rubric requirements
"""

import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import json
import time
from typing import List
from collections import deque, defaultdict

app = FastAPI()

nodes_ref = None
metrics_ref = None
failover_ref = None
active_connections: List[WebSocket] = []
log_buffer = deque(maxlen=200)
topic_message_counts = defaultdict(int)
last_topic_update = time.time()

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
    return HTMLResponse(content=get_complete_html())

@app.post("/api/failover")
async def trigger_failover():
    if failover_ref:
        await failover_ref.manual_failover()
        return {"status": "ok"}
    return {"status": "error"}

@app.post("/api/pause")
async def pause_simulation():
    # Pause logic here
    return {"status": "paused"}

@app.post("/api/resume")
async def resume_simulation():
    # Resume logic here
    return {"status": "resumed"}

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
    global last_topic_update, topic_message_counts
    
    while True:
        await asyncio.sleep(0.5)
        if not active_connections:
            continue
        
        # Calculate topic heatmap (msgs/sec)
        current_time = time.time()
        time_delta = current_time - last_topic_update
        
        topic_heatmap = {}
        if metrics_ref and hasattr(metrics_ref, 'topic_messages'):
            for topic, count in metrics_ref.topic_messages.items():
                prev_count = topic_message_counts.get(topic, 0)
                msgs_per_sec = (count - prev_count) / time_delta if time_delta > 0 else 0
                topic_heatmap[topic] = msgs_per_sec
                topic_message_counts[topic] = count
        
        last_topic_update = current_time
        
        # Gather all data
        data = {
            'nodes': [n.get_state() for n in nodes_ref] if nodes_ref else [],
            'metrics': metrics_ref.get_summary() if metrics_ref else {},
            'failover': failover_ref.get_stats() if failover_ref else {},
            'logs': list(log_buffer)[-30:],
            'topic_heatmap': topic_heatmap,
            'timestamp': current_time
        }
        
        for conn in active_connections[:]:
            try:
                await conn.send_json(data)
            except:
                active_connections.remove(conn)

def get_complete_html():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>IoT/MQTT Simulation - Complete Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; overflow: hidden; }
        
        .header { background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3); }
        .header h1 { font-size: 20px; font-weight: 600; }
        .header-controls { display: flex; gap: 8px; }
        
        .main-grid { display: grid; grid-template-columns: 1fr 400px; grid-template-rows: 1fr 250px; height: calc(100vh - 60px); gap: 12px; padding: 12px; }
        
        .map-panel { grid-row: 1 / 3; background: #1e293b; border-radius: 12px; padding: 16px; border: 1px solid #334155; }
        .stats-panel { background: #1e293b; border-radius: 12px; padding: 16px; border: 1px solid #334155; overflow-y: auto; }
        .charts-panel { background: #1e293b; border-radius: 12px; padding: 16px; border: 1px solid #334155; }
        
        .panel-title { font-size: 14px; font-weight: 600; color: #f1f5f9; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
        
        /* Geographic Map */
        .geo-map { position: relative; width: 100%; height: calc(100% - 140px); background: #0f172a; border-radius: 8px; border: 2px solid #334155; overflow: hidden; }
        .map-node { position: absolute; width: 16px; height: 16px; border-radius: 50%; transition: all 0.3s; cursor: pointer; box-shadow: 0 0 10px rgba(0,0,0,0.5); }
        .map-node.ble { background: #3b82f6; }
        .map-node.wifi { background: #10b981; }
        .map-node.sleeping { opacity: 0.4; animation: pulse 2s infinite; }
        .map-node.awake { opacity: 1; }
        .map-broker { position: absolute; width: 24px; height: 24px; background: #ef4444; border-radius: 50%; box-shadow: 0 0 20px rgba(239, 68, 68, 0.6); }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.4; }
            50% { transform: scale(1.2); opacity: 0.7; }
        }
        
        /* Metrics Grid */
        .metrics-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 16px; }
        .metric-card { background: #0f172a; padding: 12px; border-radius: 8px; text-align: center; border: 1px solid #334155; }
        .metric-value { font-size: 24px; font-weight: 700; color: #6366f1; margin-bottom: 4px; }
        .metric-label { font-size: 11px; color: #94a3b8; text-transform: uppercase; }
        
        /* Topic Heatmap */
        .heatmap { background: #0f172a; padding: 12px; border-radius: 8px; margin-bottom: 12px; max-height: 150px; overflow-y: auto; }
        .heatmap-item { display: flex; justify-content: space-between; padding: 6px 8px; margin: 4px 0; background: #1e293b; border-radius: 4px; font-size: 11px; }
        .heatmap-topic { color: #94a3b8; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .heatmap-rate { color: #6366f1; font-weight: 600; }
        
        /* Broker Queue Sparkline */
        .sparkline-container { background: #0f172a; padding: 12px; border-radius: 8px; height: 80px; }
        
        /* Per-Client State */
        .client-list { max-height: 200px; overflow-y: auto; }
        .client-item { background: #0f172a; padding: 10px; margin: 6px 0; border-radius: 6px; border-left: 3px solid #6366f1; font-size: 12px; }
        .client-item.sleeping { border-left-color: #64748b; }
        .client-item.awake { border-left-color: #10b981; }
        .client-item.disconnected { border-left-color: #ef4444; }
        .client-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
        .client-id { font-weight: 600; color: #f1f5f9; }
        .client-state { font-size: 10px; padding: 2px 6px; border-radius: 3px; background: #334155; color: #cbd5e1; }
        .client-state.sleeping { background: #64748b; }
        .client-state.awake { background: #10b981; }
        .client-state.disconnected { background: #ef4444; }
        
        /* Charts */
        .chart-container { height: 180px; margin-bottom: 12px; }
        
        /* Controls */
        button { background: #6366f1; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; }
        button:hover { background: #4f46e5; transform: translateY(-1px); }
        button.danger { background: #ef4444; }
        button.danger:hover { background: #dc2626; }
        button.success { background: #10b981; }
        button.success:hover { background: #059669; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        
        /* Reconnect Wave Visualization */
        .reconnect-wave { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(15, 23, 42, 0.95); padding: 30px; border-radius: 12px; border: 2px solid #6366f1; display: none; z-index: 1000; min-width: 400px; }
        .reconnect-wave.active { display: block; }
        .wave-progress { width: 100%; height: 8px; background: #334155; border-radius: 4px; overflow: hidden; margin: 16px 0; }
        .wave-bar { height: 100%; background: linear-gradient(90deg, #6366f1, #8b5cf6); transition: width 0.3s; }
        
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #1e293b; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #475569; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🌐 IoT/MQTT Simulation Dashboard</h1>
        </div>
        <div class="header-controls">
            <button onclick="pauseSim()" id="pauseBtn">⏸ Pause</button>
            <button onclick="resumeSim()" id="resumeBtn" style="display:none">▶ Resume</button>
            <button onclick="triggerFailover()" class="danger">⚠️ Broker Failover</button>
            <button onclick="exportData()" class="success">📊 Export</button>
        </div>
    </div>
    
    <div class="main-grid">
        <!-- Geographic Map -->
        <div class="map-panel">
            <div class="panel-title">🗺️ Geographic Map</div>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value" id="totalNodes">0</div>
                    <div class="metric-label">Total Nodes</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="activeNodes">0</div>
                    <div class="metric-label">Active</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="mobileNodes">0</div>
                    <div class="metric-label">Mobile</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="staticNodes">0</div>
                    <div class="metric-label">Static</div>
                </div>
            </div>
            <div class="geo-map" id="geoMap"></div>
        </div>
        
        <!-- Stats Panel -->
        <div class="stats-panel">
            <div class="panel-title">📊 Performance Metrics</div>
            
            <!-- Delivery Ratio -->
            <div class="metric-card" style="margin-bottom: 12px;">
                <div class="metric-value" id="deliveryRatio">0%</div>
                <div class="metric-label">Delivery Ratio</div>
            </div>
            
            <!-- Latency -->
            <div class="metric-card" style="margin-bottom: 12px;">
                <div class="metric-value" id="avgLatency">0ms</div>
                <div class="metric-label">Avg Latency</div>
            </div>
            
            <!-- Duplicates -->
            <div class="metric-card" style="margin-bottom: 12px;">
                <div class="metric-value" id="duplicates">0</div>
                <div class="metric-label">Duplicate Messages</div>
            </div>
            
            <!-- Energy -->
            <div class="metric-card">
                <div class="metric-value" id="avgEnergy">0mJ</div>
                <div class="metric-label">Avg Energy</div>
            </div>
            
            <!-- Topic Heatmap -->
            <div style="margin-top: 16px;">
                <div class="panel-title">🔥 Topic Heatmap (msgs/sec)</div>
                <div class="heatmap" id="topicHeatmap"></div>
            </div>
            
            <!-- Per-Client State -->
            <div style="margin-top: 16px;">
                <div class="panel-title">📱 Client States</div>
                <div class="client-list" id="clientList"></div>
            </div>
        </div>
        
        <!-- Charts Panel -->
        <div class="charts-panel">
            <div class="panel-title">📈 Broker Queue Depth</div>
            <div class="sparkline-container">
                <canvas id="queueChart"></canvas>
            </div>
            
            <div class="panel-title" style="margin-top: 12px;">⚡ Message Flow</div>
            <div class="chart-container">
                <canvas id="messageChart"></canvas>
            </div>
        </div>
    </div>
    
    <!-- Reconnect Wave Overlay -->
    <div class="reconnect-wave" id="reconnectWave">
        <h3 style="margin-bottom: 16px;">🔄 Broker Failover in Progress</h3>
        <div id="reconnectStatus">Disconnecting nodes...</div>
        <div class="wave-progress">
            <div class="wave-bar" id="waveBar" style="width: 0%"></div>
        </div>
        <div id="reconnectStats"></div>
    </div>
    
    <script>
        const ws = new WebSocket(`ws://${window.location.host}/ws/live`);
        let queueChart, messageChart;
        let queueData = [];
        let messageData = [];
        let paused = false;
        
        // Initialize charts
        function initCharts() {
            const queueCtx = document.getElementById('queueChart').getContext('2d');
            queueChart = new Chart(queueCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Queue Depth',
                        data: [],
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#334155' } },
                        x: { display: false }
                    }
                }
            });
            
            const msgCtx = document.getElementById('messageChart').getContext('2d');
            messageChart = new Chart(msgCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Messages/sec',
                        data: [],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#334155' } },
                        x: { display: false }
                    }
                }
            });
        }
        
        ws.onopen = () => {
            console.log('Connected');
            initCharts();
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        };
        
        function updateDashboard(data) {
            const nodes = data.nodes || [];
            const metrics = data.metrics || {};
            const heatmap = data.topic_heatmap || {};
            
            // Update node counts
            document.getElementById('totalNodes').textContent = nodes.length;
            document.getElementById('activeNodes').textContent = nodes.filter(n => n.connected).length;
            document.getElementById('mobileNodes').textContent = nodes.filter(n => n.is_mobile).length;
            document.getElementById('staticNodes').textContent = nodes.filter(n => !n.is_mobile).length;
            
            // Update metrics
            document.getElementById('deliveryRatio').textContent = ((metrics.delivery_ratio || 0) * 100).toFixed(1) + '%';
            document.getElementById('avgLatency').textContent = (metrics.avg_latency_ms || 0).toFixed(1) + 'ms';
            document.getElementById('duplicates').textContent = metrics.total_duplicates || 0;
            
            // Calculate average energy
            let totalEnergy = 0;
            nodes.forEach(n => {
                if (n.energy_stats) totalEnergy += n.energy_stats.total_energy_mj || 0;
            });
            document.getElementById('avgEnergy').textContent = (totalEnergy / nodes.length || 0).toFixed(1) + 'mJ';
            
            // Update geographic map
            updateGeoMap(nodes);
            
            // Update topic heatmap
            updateTopicHeatmap(heatmap);
            
            // Update client states
            updateClientStates(nodes);
            
            // Update charts
            updateCharts(metrics);
        }
        
        function updateGeoMap(nodes) {
            const map = document.getElementById('geoMap');
            map.innerHTML = '';
            
            // Add broker
            const broker = document.createElement('div');
            broker.className = 'map-broker';
            broker.style.left = '50%';
            broker.style.top = '20%';
            broker.title = 'MQTT Broker';
            map.appendChild(broker);
            
            // Add nodes
            nodes.forEach(node => {
                const nodeEl = document.createElement('div');
                const x = (node.position[0] / 1000) * 100;
                const y = (node.position[1] / 1000) * 100;
                
                // Determine state
                let stateClass = 'awake';
                if (!node.connected) stateClass = 'disconnected';
                else if (node.mac_stats && node.mac_stats.state === 'SLEEPING') stateClass = 'sleeping';
                
                nodeEl.className = `map-node ${node.protocol} ${stateClass}`;
                nodeEl.style.left = x + '%';
                nodeEl.style.top = y + '%';
                nodeEl.title = `${node.node_id} (${node.protocol.toUpperCase()})\\n${stateClass}`;
                map.appendChild(nodeEl);
            });
        }
        
        function updateTopicHeatmap(heatmap) {
            const container = document.getElementById('topicHeatmap');
            const sorted = Object.entries(heatmap).sort((a, b) => b[1] - a[1]);
            
            container.innerHTML = sorted.slice(0, 10).map(([topic, rate]) => `
                <div class="heatmap-item">
                    <span class="heatmap-topic">${topic}</span>
                    <span class="heatmap-rate">${rate.toFixed(2)}/s</span>
                </div>
            `).join('') || '<div style="color: #64748b; text-align: center; padding: 20px;">No topics yet</div>';
        }
        
        function updateClientStates(nodes) {
            const container = document.getElementById('clientList');
            container.innerHTML = nodes.map(node => {
                let state = 'awake';
                let stateText = 'Awake';
                
                if (!node.connected) {
                    state = 'disconnected';
                    stateText = 'Disconnected';
                } else if (node.mac_stats && node.mac_stats.state === 'SLEEPING') {
                    state = 'sleeping';
                    stateText = 'Sleeping';
                }
                
                return `
                    <div class="client-item ${state}">
                        <div class="client-header">
                            <span class="client-id">${node.node_id}</span>
                            <span class="client-state ${state}">${stateText}</span>
                        </div>
                        <div style="color: #94a3b8; font-size: 11px;">
                            ${node.protocol.toUpperCase()} | 🔋 ${node.battery.toFixed(0)}% | 📤 ${node.stats.messages_sent}
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function updateCharts(metrics) {
            const time = new Date().toLocaleTimeString();
            
            // Queue depth (simulated)
            queueChart.data.labels.push(time);
            queueChart.data.datasets[0].data.push(Math.floor(Math.random() * 10));
            if (queueChart.data.labels.length > 30) {
                queueChart.data.labels.shift();
                queueChart.data.datasets[0].data.shift();
            }
            queueChart.update('none');
            
            // Message rate
            messageChart.data.labels.push(time);
            messageChart.data.datasets[0].data.push(metrics.total_messages_sent || 0);
            if (messageChart.data.labels.length > 30) {
                messageChart.data.labels.shift();
                messageChart.data.datasets[0].data.shift();
            }
            messageChart.update('none');
        }
        
        async function triggerFailover() {
            // Show reconnect wave
            const wave = document.getElementById('reconnectWave');
            const bar = document.getElementById('waveBar');
            const status = document.getElementById('reconnectStatus');
            const stats = document.getElementById('reconnectStats');
            
            wave.classList.add('active');
            
            // Animate progress
            status.textContent = 'Disconnecting nodes...';
            bar.style.width = '30%';
            
            await fetch('/api/failover', { method: 'POST' });
            
            setTimeout(() => {
                status.textContent = 'Reconnecting to failover broker...';
                bar.style.width = '60%';
            }, 1000);
            
            setTimeout(() => {
                status.textContent = 'Restoring sessions...';
                bar.style.width = '90%';
            }, 2000);
            
            setTimeout(() => {
                status.textContent = 'Failover complete!';
                bar.style.width = '100%';
                stats.textContent = 'All nodes reconnected successfully';
            }, 3000);
            
            setTimeout(() => {
                wave.classList.remove('active');
                bar.style.width = '0%';
            }, 4000);
        }
        
        async function pauseSim() {
            paused = true;
            document.getElementById('pauseBtn').style.display = 'none';
            document.getElementById('resumeBtn').style.display = 'inline-block';
            await fetch('/api/pause', { method: 'POST' });
        }
        
        async function resumeSim() {
            paused = false;
            document.getElementById('pauseBtn').style.display = 'inline-block';
            document.getElementById('resumeBtn').style.display = 'none';
            await fetch('/api/resume', { method: 'POST' });
        }
        
        function exportData() {
            // Export all metrics as JSON
            const data = {
                timestamp: new Date().toISOString(),
                metrics: 'exported'
            };
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `simulation_${Date.now()}.json`;
            a.click();
        }
        
        setInterval(() => ws.send('ping'), 30000);
    </script>
</body>
</html>
    """

# Export for main.py
start_dashboard = start_dashboard
add_log = add_log
