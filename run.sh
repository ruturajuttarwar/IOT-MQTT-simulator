#!/bin/bash
# Quick run script for IoT/MQTT Simulation

echo "======================================"
echo "IoT/MQTT Simulation"
echo "Project Groups 2&6"
echo "======================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found"
    exit 1
fi

# Menu
echo "Select option:"
echo "1) Run full simulation with GUI"
echo "2) Run Experiment 1 (Duty Cycle)"
echo "3) Run Experiment 2 (BLE vs WiFi)"
echo "4) Run Experiment 3 (Broker Failover)"
echo "5) Install dependencies"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo ""
        echo "Starting full simulation..."
        echo "Dashboard will be available at: http://localhost:8000"
        echo ""
        python3 main.py
        ;;
    2)
        echo ""
        echo "Running Experiment 1: Duty Cycle Impact"
        python3 -m experiments.experiment1_duty_cycle
        ;;
    3)
        echo ""
        echo "Running Experiment 2: BLE vs WiFi Comparison"
        python3 -m experiments.experiment2_ble_vs_wifi
        ;;
    4)
        echo ""
        echo "Running Experiment 3: Broker Failover"
        python3 -m experiments.experiment3_failover
        ;;
    5)
        echo ""
        echo "Installing dependencies..."
        pip3 install -r requirements.txt
        echo "Done!"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
