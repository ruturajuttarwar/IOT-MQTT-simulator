# IoT/MQTT Network Simulation - User Guide

## 📖 Table of Contents
1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Dashboard Features](#dashboard-features)
6. [Testing Features](#testing-features)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Configuration](#advanced-configuration)

---

## Overview

This is a comprehensive IoT/MQTT network simulation with a modern React frontend. It simulates IoT devices using BLE and WiFi protocols, MQTT messaging, energy consumption, mobility models, and broker failover mechanisms.

**Key Features:**
- Real-time network visualization
- Dynamic node management (add/delete nodes on-the-fly)
- Energy consumption tracking
- Mobility models (static and mobile nodes)
- MAC layer statistics (BLE and WiFi)
- MQTT message logging
- Broker failover simulation
- Advanced metrics and analytics

---

## System Requirements

### Required Software
- **Python 3.8+**
- **Node.js 16+** and npm
- **Modern web browser** (Chrome, Firefox, Safari, Edge)

### Python Dependencies
```bash
flask
flask-socketio
python-socketio
```

### Node.js Dependencies
```bash
react
tailwindcss
socket.io-client
lucide-react
```

---

## Installation

### Step 1: Clone/Download the Project
```bash
cd /path/to/project
```

### Step 2: Install Python Dependencies
```bash
pip install flask flask-socketio python-socketio
```

### Step 3: Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

---

## Quick Start

### 1. Start the Backend Server

Open a terminal and run:
```bash
python3 main.py
```

You should see:
```
============================================================
IoT/MQTT Simulation
============================================================
Nodes: 1 (initial node)
Dashboard: http://localhost:8000
============================================================
✓ Created 1 initial node
ℹ Use the dashboard to add more nodes dynamically
Starting Flask dashboard on http://localhost:8000
```

**Backend runs on:** `http://localhost:8000`

### 2. Start the Frontend

Open a **new terminal** and run:
```bash
cd frontend
npm run dev
```

You should see:
```
  VITE v5.0.8  ready in 500 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

**Frontend runs on:** `http://localhost:3000`

### 3. Open the Dashboard

Open your web browser and navigate to:
```
http://localhost:3000
```

You should see the IoT/MQTT Network Simulation dashboard with:
- Network visualization canvas (left side)
- Control panels and statistics (right side)
- Tab navigation at the top

---

## Dashboard Features

### Navigation Tabs

The dashboard has **6 main tabs**:

#### 1. **Overview Tab**
- **Configuration Panel**: Shows current node count and distribution
- **Statistics**: Total messages, active nodes, uptime, subscribers
- **Nodes List**: All nodes with connection status
- **Message Log**: Real-time MQTT messages

#### 2. **Manage Nodes Tab** ⭐ NEW
- **Simulation Controls**:
  - **Start**: Resume simulation
  - **Stop**: Pause simulation
  - **Restart**: Delete ALL nodes and reload page (fresh start)
- **Add Node**: Create new nodes dynamically
  - **Node ID**: Unique identifier (e.g., `sensor_1`, `gateway_1`) *Required*
  - **Protocol**: WiFi or BLE (stays as selected - BLE won't auto-switch) *Required*
  - **Role**: Publisher Only, Subscriber Only, or Both *Required*
  - **Position X**: Canvas X coordinate (0-1000) *Required*
  - **Position Y**: Canvas Y coordinate (0-1000) *Required*
  - **Mobile**: Check if node should move
  - **Subscribe To**: Select specific publishers to subscribe to (optional)
  - Click "Add Node"
- **Delete Node**: Remove any node by clicking trash icon
- **Node List**: View all current nodes with status

**Visual Feedback**:
- **Bright Yellow Dots**: Packets being sent from node to broker
- **Green Dots**: ACK packets returning from broker to node
- **Orange/Green Pulses**: MQTT messages (PUBLISH/SUBSCRIBE)

#### 3. **Energy Tab**
- **Battery Levels**: Visual battery bars for each node
  - Green: > 70%
  - Yellow: 30-70%
  - Red: < 30%
- **Energy Stats**: Current state (TX/RX/Sleep/Idle)
- **Duty Cycle**: Percentage of active time

#### 4. **Mobility Tab**
- **Mobile vs Static**: Visual distinction
- **Position Tracking**: Real-time coordinates
- **Movement Updates**: Counter for position changes
- **Failover Status**: Broker health and failover stats

#### 5. **MAC Layer Tab**
- **BLE Statistics**:
  - Packets sent/dropped/retried
  - Connection events
  - Advertisements
  - Sleep cycles
- **WiFi Statistics**:
  - Packets sent/dropped/retried
  - Collisions
  - ACKs received
  - Beacons sent

#### 6. **Metrics Tab**
- **Delivery Ratio**: Percentage of successful deliveries
- **Average Latency**: Message latency in milliseconds
- **Topic Heatmap**: Most active topics
- **Duplicate Detection**: Duplicate message count

### Network Canvas

The main visualization shows:
- **MQTT Broker**: Red circle in the center
- **Nodes**: Arranged in a circle around the broker
  - Blue circles = BLE nodes
  - Green circles = WiFi nodes
- **Connection Lines**: Gray lines from nodes to broker
- **Animated Pulses**: Orange dots showing message flow

### Real-Time Updates

All data updates automatically:
- **Node states**: Every 0.5 seconds
- **MQTT messages**: Instant
- **Metrics**: Every 5 seconds
- **Canvas animation**: 60 FPS

---

## Testing Features

### Test 1: Dynamic Node Management with Custom Positioning

**Objective**: Add and remove nodes with custom positions and control simulation

**Steps:**
1. Go to **"Manage Nodes"** tab
2. **Observe**: Start, Stop, Restart buttons at the top
3. Click **"Add Node"** button
4. Fill in the form (all fields with * are required):
   - **Node ID**: `sensor_temp_1`
   - **Protocol**: **BLE** (it will stay BLE - no auto-switching)
   - **Role**: **Publisher Only**
   - **Position X**: `200` (required)
   - **Position Y**: `300` (required)
   - Check **Mobile Node** checkbox
5. Click **"Add Node"**
6. **Observe**: 
   - New BLE node appears at exact position (200, 300) on canvas
   - Node stays as BLE protocol
   - **Bright yellow dots** travel from node to broker (packets)
   - **Green dots** return from broker to node (ACKs)
7. Add another node:
   - **Node ID**: `gateway_1`
   - **Protocol**: **WiFi**
   - **Role**: **Subscriber Only**
   - **Position X**: `800`
   - **Position Y**: `400`
   - Leave Mobile unchecked
8. **Observe**: WiFi node appears at position (800, 400)
9. Click **"Stop"** button
10. **Observe**: 
    - Uptime stops counting
    - Packets stop being sent
    - Nodes stop activity
11. Click **"Start"** button
12. **Observe**: Simulation resumes
13. Click **trash icon** next to `sensor_temp_1`
14. Confirm deletion
15. **Observe**: Node disappears from canvas
16. Click **"Restart"** button
17. Confirm restart
18. **Observe**: Page reloads, ALL nodes are deleted, fresh start

**Expected Result**: 
- Nodes positioned exactly at specified X/Y coordinates
- BLE nodes stay as BLE (no auto-switching to WiFi)
- All nodes can be deleted individually
- Stop button pauses simulation (uptime stops, packets stop)
- Start button resumes simulation
- Restart button reloads page and clears everything
- Bright yellow dots show packet transmission
- Green dots show ACK responses

---

### Test 2: Energy Consumption Monitoring

**Objective**: Monitor battery levels and energy consumption

**Steps:**
1. Add 3-4 nodes (mix of BLE and WiFi)
2. Go to **"Energy"** tab
3. **Observe**: Battery bars for each node
4. Wait 30 seconds
5. **Observe**: Battery levels decrease
6. **Compare**: BLE nodes consume less power than WiFi nodes
7. Check **Duty Cycle** percentages
8. Check **Current State** (TX/RX/Sleep/Idle)

**Expected Result**: 
- Battery levels decrease over time
- BLE nodes have lower power consumption
- Duty cycle shows activity percentage
- Current state changes based on node activity

---

### Test 3: Mobility Tracking

**Objective**: Track mobile node movement

**Steps:**
1. Go to **"Manage Nodes"** tab
2. Add a node with **Mobile** checked
3. Go to **"Mobility"** tab
4. **Observe**: Node marked as "Mobile" with purple background
5. Watch **Position** coordinates change
6. Check **Updates** counter increasing
7. Go back to **Overview** tab
8. **Observe**: Mobile node moving on canvas

**Expected Result**:
- Mobile nodes show position updates
- Coordinates change over time
- Movement visible on canvas

---

### Test 4: MQTT Message Flow

**Objective**: Monitor MQTT messages

**Steps:**
1. Add 2-3 nodes
2. Go to **"Overview"** tab
3. Watch **Message Log** panel
4. **Observe** different message types:
   - **PUBLISH** (blue): Sensor data being sent
   - **SUBSCRIBE** (green): Nodes subscribing to topics
   - **CONNECT** (yellow): Node connections
5. Click on a message to see details:
   - Topic path
   - Payload data
   - QoS level
   - Retain flag

**Expected Result**:
- Messages appear in real-time
- Different message types are color-coded
- Full message details are visible

---

### Test 5: Protocol Comparison (BLE vs WiFi)

**Objective**: Compare BLE and WiFi performance

**Steps:**
1. Add 3 BLE nodes
2. Add 3 WiFi nodes
3. Go to **"MAC Layer"** tab
4. Wait 1 minute
5. **Compare** statistics:
   - Packets sent
   - Collisions (WiFi only)
   - Connection events (BLE only)
   - Retries
6. Go to **"Energy"** tab
7. **Compare** battery consumption

**Expected Result**:
- WiFi sends more packets (higher data rate)
- WiFi has collisions, BLE doesn't
- BLE has connection events
- BLE consumes less energy

---

### Test 6: Broker Failover

**Objective**: Test broker failover mechanism

**Steps:**
1. Add 4-5 nodes
2. Go to **"Mobility"** or **"Metrics"** tab
3. Check **Failover Panel**
4. **Observe**:
   - Primary broker status (green checkmark)
   - Failover broker status
   - Failover count (should be 0)
5. Note **Reconnection Time**
6. Check **Registered Nodes** count

**Expected Result**:
- Both brokers show as alive
- Failover statistics are tracked
- Nodes are registered with failover manager

---

### Test 7: Advanced Metrics

**Objective**: Analyze network performance metrics

**Steps:**
1. Add 5+ nodes
2. Let simulation run for 2-3 minutes
3. Go to **"Metrics"** tab
4. Check **Delivery Ratio** (should be > 95%)
5. Check **Average Latency** (should be < 50ms)
6. View **Topic Heatmap** (top 3 active topics)
7. Check **Duplicate Detection** count

**Expected Result**:
- High delivery ratio (> 95%)
- Low latency (< 50ms)
- Topic heatmap shows sensor data topics
- Few or no duplicates

---

### Test 8: Publisher/Subscriber Selective Subscription

**Objective**: Test selective subscription between nodes

**Steps:**
1. Go to **"Manage Nodes"** tab
2. Add a publisher node:
   - **Node ID**: `publisher_1`
   - **Protocol**: WiFi
   - **Role**: **Publisher Only**
   - Position X: `300`, Y: `300`
3. Add another publisher:
   - **Node ID**: `publisher_2`
   - **Protocol**: BLE
   - **Role**: **Publisher Only**
   - Position X: `700`, Y: `300`
4. Add a selective subscriber:
   - **Node ID**: `subscriber_1`
   - **Protocol**: WiFi
   - **Role**: **Subscriber Only**
   - Position X: `500`, Y: `600`
   - **Subscribe To**: Check only `publisher_1`
5. Click **"Add Node"**
6. Go to **"Overview"** tab
7. Watch **Message Log**
8. **Observe**: 
   - `publisher_1` and `publisher_2` send PUBLISH messages
   - `subscriber_1` only subscribes to `publisher_1` topics
9. Add another subscriber that subscribes to all:
   - **Node ID**: `subscriber_all`
   - **Role**: **Subscriber Only**
   - **Subscribe To**: Leave empty (subscribes to all)
10. **Observe**: `subscriber_all` receives from both publishers

**Expected Result**:
- Publishers only send data (no subscriptions)
- Subscribers only receive data (no publishing)
- Selective subscribers only get data from chosen publishers
- Empty subscription list means subscribe to all

---

### Test 9: Scalability

**Objective**: Test system with many nodes

**Steps:**
1. Start with 1 node
2. Add nodes one by one up to 10
3. **Observe**:
   - Canvas performance (should stay smooth)
   - Message log updates
   - Statistics accuracy
4. Try adding 5 more nodes (total 15)
5. Check if system remains responsive

**Expected Result**:
- System handles 10-15 nodes smoothly
- Canvas maintains 60 FPS
- All features continue working
- No significant lag

---

## Troubleshooting

### Problem: Backend won't start

**Error**: `ModuleNotFoundError: No module named 'flask'`

**Solution**:
```bash
pip install flask flask-socketio python-socketio
```

---

### Problem: Frontend won't start

**Error**: `Cannot find module 'react'`

**Solution**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

### Problem: Port already in use

**Error**: `Address already in use: 8000` or `3000`

**Solution**:
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

---

### Problem: No nodes appearing

**Symptoms**: Canvas shows "Waiting for nodes..."

**Solution**:
1. Check backend terminal for errors
2. Check browser console (F12) for errors
3. Verify Socket.IO connection
4. Refresh browser (Ctrl+R or Cmd+R)
5. Add a node manually via "Manage Nodes" tab

---

### Problem: Messages not showing

**Symptoms**: Message log is empty

**Solution**:
1. Wait 5-15 seconds (nodes publish periodically)
2. Check nodes are connected (green status)
3. Add more nodes to increase activity
4. Check browser console for errors

---

### Problem: Canvas not animating

**Symptoms**: Nodes appear but don't move/update

**Solution**:
1. Check browser performance
2. Close other tabs to free resources
3. Reduce number of nodes
4. Refresh browser

---

## Advanced Configuration

### Change Initial Node Count

Edit `main.py`:
```python
# Line ~50
# Change from 1 to desired number
node = Node(
    node_id=f"node_0",
    protocol='wifi',
    is_mobile=False,
    broker_address=BROKER_PRIMARY
)
```

### Change Simulation Parameters

Edit `config/simulation_config.py`:
```python
# Area size
AREA_WIDTH = 1000.0  # meters
AREA_HEIGHT = 1000.0  # meters

# Mobility
MOBILITY_MODEL = "random_waypoint"  # or "grid"

# MQTT
MQTT_KEEP_ALIVE = 60  # seconds
MQTT_QOS_DEFAULT = 1  # QoS level

# Energy
ENABLE_ENERGY_TRACKING = True
INITIAL_BATTERY_LEVEL = 100.0  # percentage
```

### Change Protocol Parameters

Edit `config/phy_profiles.py`:
```python
# BLE settings
BLE_PROFILE = {
    'data_rate_bps': 1_000_000,  # 1 Mbps
    'tx_power_mw': 45.0,
    'rx_power_mw': 36.0,
    # ... more settings
}

# WiFi settings
WIFI_PROFILE = {
    'data_rate_bps': 150_000_000,  # 150 Mbps
    'tx_power_mw': 100.0,
    'rx_power_mw': 50.0,
    # ... more settings
}
```

### Change Dashboard Port

Edit `config/simulation_config.py`:
```python
GUI_PORT = 8000  # Change to desired port
```

Then update frontend proxy in `frontend/vite.config.js`:
```javascript
proxy: {
  '/api': 'http://localhost:8000',  // Match GUI_PORT
  // ...
}
```

---

## Project Structure

```
project/
├── main.py                      # Entry point
├── config/
│   ├── simulation_config.py     # Global configuration
│   └── phy_profiles.py          # Protocol parameters
├── sim/
│   ├── node.py                  # Node implementation
│   ├── energy.py                # Energy tracking
│   ├── mobility.py              # Mobility models
│   ├── ble_mac.py               # BLE MAC layer
│   ├── wifi_mac.py              # WiFi MAC layer
│   ├── mqtt_client_sim.py       # MQTT client
│   ├── broker_failover.py       # Failover manager
│   └── metrics.py               # Metrics collector
├── gui/
│   └── flask_dashboard.py       # Flask backend
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── services/            # Socket.IO service
│   │   └── App.jsx              # Main app
│   ├── package.json
│   └── vite.config.js
└── USER_GUIDE.md                # This file
```

---

## Support

For issues or questions:
1. Check the **Troubleshooting** section
2. Review browser console (F12) for errors
3. Check backend terminal for error messages
4. Verify all dependencies are installed

---

## Summary

This IoT/MQTT simulation provides a comprehensive platform for:
- ✅ Testing IoT protocols (BLE and WiFi)
- ✅ Monitoring energy consumption
- ✅ Tracking node mobility
- ✅ Analyzing MQTT message flow
- ✅ Evaluating network performance
- ✅ Experimenting with broker failover
- ✅ Dynamic node management

**Quick Start Reminder:**
```bash
# Terminal 1
python3 main.py

# Terminal 2
cd frontend && npm run dev

# Browser
http://localhost:3000
```

Enjoy exploring the simulation! 🚀
