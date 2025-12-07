"""
Data export utilities for metrics and results
"""

import csv
import json
from datetime import datetime
from typing import Dict, List


def export_metrics_csv(metrics: Dict, filename: str = None):
    """Export metrics to CSV file"""
    if filename is None:
        filename = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write headers
        writer.writerow(['Metric', 'Value'])
        
        # Write data
        for key, value in metrics.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    writer.writerow([f"{key}.{subkey}", subvalue])
            else:
                writer.writerow([key, value])
                
    return filename


def export_metrics_json(metrics: Dict, filename: str = None):
    """Export metrics to JSON file"""
    if filename is None:
        filename = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
    with open(filename, 'w') as f:
        json.dump(metrics, f, indent=2)
        
    return filename


def export_node_data(nodes: List, filename: str = None):
    """Export per-node data to CSV"""
    if filename is None:
        filename = f"nodes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Headers
        writer.writerow([
            'Node ID', 'Protocol', 'Mobile', 'Position X', 'Position Y',
            'Battery %', 'Messages Sent', 'Messages Received', 'Energy (mJ)'
        ])
        
        # Data
        for node in nodes:
            writer.writerow([
                node.node_id,
                node.protocol,
                node.is_mobile,
                node.position[0],
                node.position[1],
                node.energy_tracker.battery_level,
                node.stats.get('messages_sent', 0),
                node.stats.get('messages_received', 0),
                node.energy_tracker.total_energy_mj
            ])
            
    return filename
