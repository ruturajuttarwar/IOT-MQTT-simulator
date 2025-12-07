# IoT/MQTT Network Simulation

A comprehensive IoT network simulator with real-time visualization, featuring BLE and WiFi protocols, MQTT messaging, energy tracking, and mobility models.

## 🚀 Quick Start

```bash
# Terminal 1 - Start Backend
python3 main.py

# Terminal 2 - Start Frontend
cd frontend
npm install  # First time only
npm run dev

# Open Browser
http://localhost:3000
```

## 📚 Documentation

**See [USER_GUIDE.md](USER_GUIDE.md) for complete documentation including:**
- Installation instructions
- Feature descriptions
- Testing procedures
- Troubleshooting guide
- Configuration options

## ✨ Key Features

- **Dynamic Node Management**: Add/delete nodes on-the-fly
- **Real-time Visualization**: Network canvas with animated message flow
- **Energy Tracking**: Battery levels and consumption monitoring
- **Mobility Models**: Static and mobile node simulation
- **Protocol Support**: BLE 5.x and WiFi 802.11n
- **MQTT Protocol**: Full QoS 0/1 implementation
- **Broker Failover**: Automatic failover simulation
- **Advanced Metrics**: Delivery ratio, latency, topic heatmap

## 🎯 Tech Stack

**Backend:**
- Python 3.8+
- Flask + Socket.IO
- Simulated MQTT, BLE, WiFi protocols

**Frontend:**
- React 18
- Tailwind CSS
- Socket.IO Client
- Vite

## 📖 Full Documentation

For detailed setup, features, and testing instructions, please refer to:

**[USER_GUIDE.md](USER_GUIDE.md)**

## 🎓 Project Structure

```
├── main.py                 # Entry point
├── config/                 # Configuration files
├── sim/                    # Simulation components
├── gui/                    # Flask backend
├── frontend/               # React frontend
└── USER_GUIDE.md          # Complete documentation
```

## 📝 License

Educational project for IoT/MQTT network simulation.
