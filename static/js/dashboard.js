// Dashboard JavaScript
const socket = io();
const canvas = document.getElementById('network-canvas');
const ctx = canvas.getContext('2d');

let nodes = [];
let messages = [];
let stats = {};
let startTime = Date.now();

// Canvas setup
function resizeCanvas() {
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

// Socket.IO event handlers
socket.on('connect', () => {
    console.log('Connected to server');
    loadConfig();
});

socket.on('init', (data) => {
    nodes = data.nodes;
    console.log('Initialized with', nodes.length, 'nodes');
});

socket.on('update', (data) => {
    nodes = data.nodes;
    stats = data.stats;
    updateStats();
    updateNodeList();
});

socket.on('message', (data) => {
    addMessageLog(data);
    // Add visual pulse
    messages.push({
        from: data.from,
        progress: 0,
        type: data.msg_type
    });
});

// Load configuration
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        document.getElementById('config-text').textContent = 
            `${config.total_nodes} nodes (${config.ble_nodes} BLE, ${config.wifi_nodes} WiFi)`;
        document.getElementById('node-count').textContent = config.total_nodes;
    } catch (error) {
        console.error('Error loading config:', error);
    }
}

// Update statistics
function updateStats() {
    document.getElementById('msg-count').textContent = stats.total_messages || 0;
    document.getElementById('active-nodes').textContent = stats.active_nodes || 0;
    document.getElementById('sub-count').textContent = stats.total_subscriptions || 0;
    document.getElementById('uptime').textContent = (stats.uptime || 0) + 's';
}

// Update node list
function updateNodeList() {
    const list = document.getElementById('node-list');
    list.innerHTML = '';
    
    nodes.forEach(node => {
        const item = document.createElement('div');
        item.className = `node-item node-${node.protocol.toLowerCase()}`;
        
        const statusClass = node.connected ? 'bg-success' : 'bg-danger';
        const statusText = node.connected ? 'Connected' : 'Disconnected';
        
        item.innerHTML = `
            <span><strong>${node.id}</strong> <small class="text-muted">(${node.protocol})</small></span>
            <span class="badge ${statusClass} node-badge">${statusText}</span>
        `;
        list.appendChild(item);
    });
}

// Add message to log
function addMessageLog(data) {
    const log = document.getElementById('message-log');
    const entry = document.createElement('div');
    
    const time = new Date(data.timestamp * 1000).toLocaleTimeString();
    
    if (data.msg_type === 'PUBLISH') {
        entry.className = 'log-entry log-publish';
        entry.innerHTML = `
            <span class="log-time"><i class="bi bi-clock"></i> ${time}</span>
            <div class="log-header"><i class="bi bi-arrow-up-circle"></i> PUBLISH from ${data.from}</div>
            <div class="log-detail">
                <strong>Topic:</strong> ${data.topic}<br>
                <strong>Payload:</strong> ${data.payload}<br>
                <strong>QoS:</strong> ${data.qos} | <strong>Retain:</strong> ${data.retain}
            </div>
        `;
    } else if (data.msg_type === 'SUBSCRIBE') {
        entry.className = 'log-entry log-subscribe';
        entry.innerHTML = `
            <span class="log-time"><i class="bi bi-clock"></i> ${time}</span>
            <div class="log-header"><i class="bi bi-arrow-down-circle"></i> SUBSCRIBE from ${data.from}</div>
            <div class="log-detail">
                <strong>Topic:</strong> ${data.topic}<br>
                <strong>QoS:</strong> ${data.qos}
            </div>
        `;
    } else if (data.msg_type === 'CONNECT') {
        entry.className = 'log-entry log-connect';
        entry.innerHTML = `
            <span class="log-time"><i class="bi bi-clock"></i> ${time}</span>
            <div class="log-header"><i class="bi bi-plug"></i> CONNECTED: ${data.from}</div>
        `;
    }
    
    log.insertBefore(entry, log.firstChild);
    
    // Keep only last 100 entries
    while (log.children.length > 100) {
        log.removeChild(log.lastChild);
    }
}

// Canvas drawing
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    if (nodes.length === 0) {
        // Show loading message
        ctx.fillStyle = '#6c757d';
        ctx.font = '20px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('Waiting for nodes...', canvas.width / 2, canvas.height / 2);
        requestAnimationFrame(draw);
        return;
    }
    
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(canvas.width, canvas.height) * 0.35;
    
    // Draw connection lines
    nodes.forEach((node, i) => {
        const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
        const x = centerX + Math.cos(angle) * radius;
        const y = centerY + Math.sin(angle) * radius;
        
        ctx.strokeStyle = node.connected ? '#6c757d' : '#dee2e6';
        ctx.lineWidth = node.connected ? 2 : 1;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(x, y);
        ctx.stroke();
    });
    
    // Draw broker
    ctx.fillStyle = '#dc3545';
    ctx.beginPath();
    ctx.arc(centerX, centerY, 40, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#b02a37';
    ctx.lineWidth = 3;
    ctx.stroke();
    
    ctx.fillStyle = 'white';
    ctx.font = 'bold 18px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('MQTT', centerX, centerY - 8);
    ctx.font = '14px Arial';
    ctx.fillText('Broker', centerX, centerY + 12);
    
    // Draw nodes
    nodes.forEach((node, i) => {
        const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
        const x = centerX + Math.cos(angle) * radius;
        const y = centerY + Math.sin(angle) * radius;
        
        // Node circle
        ctx.fillStyle = node.protocol === 'BLE' ? '#0d6efd' : '#198754';
        ctx.beginPath();
        ctx.arc(x, y, 25, 0, Math.PI * 2);
        ctx.fill();
        
        // Border
        ctx.strokeStyle = node.connected ? '#212529' : '#adb5bd';
        ctx.lineWidth = 3;
        ctx.stroke();
        
        // Label
        ctx.fillStyle = '#212529';
        ctx.font = 'bold 12px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const shortId = node.id.split('_').pop();
        ctx.fillText(shortId, x, y + 40);
        
        // Protocol
        ctx.font = '10px Arial';
        ctx.fillStyle = '#6c757d';
        ctx.fillText(node.protocol, x, y + 54);
    });
    
    // Draw message pulses
    messages = messages.filter(msg => {
        msg.progress += 0.02;
        if (msg.progress > 1) return false;
        
        const fromNode = nodes.find(n => n.id === msg.from);
        if (!fromNode) return false;
        
        const fromIdx = nodes.indexOf(fromNode);
        const angle = (fromIdx / nodes.length) * Math.PI * 2 - Math.PI / 2;
        const fromX = centerX + Math.cos(angle) * radius;
        const fromY = centerY + Math.sin(angle) * radius;
        
        const x = fromX + (centerX - fromX) * msg.progress;
        const y = fromY + (centerY - fromY) * msg.progress;
        
        // Pulse
        const color = msg.type === 'PUBLISH' ? '#ffc107' : '#198754';
        ctx.fillStyle = color;
        ctx.globalAlpha = 1 - msg.progress * 0.7;
        ctx.beginPath();
        ctx.arc(x, y, 8, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
        
        return true;
    });
    
    requestAnimationFrame(draw);
}

// Start animation
draw();
