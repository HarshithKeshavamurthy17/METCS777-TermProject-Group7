#!/usr/bin/env python3
"""
Start the Anomaly Detection Dashboard.
This script launches the Flask application to visualize the detected anomalies.
"""
import sys
import os
import socket
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

# Import the demo dashboard script which is robust and handles full datasets
from scripts.start_dashboard_demo import app


def find_available_port(start_port=7000, max_attempts=10):
    """Find an available port in the 7000 series."""
    for i in range(max_attempts):
        port = start_port + i
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    # If all ports in 7000 series are taken, fall back to system-assigned port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


if __name__ == '__main__':
    print("Starting Dashboard...")
    # Use port 7000 by default, or find available port in 7000 series
    port = int(os.environ.get('PORT', find_available_port(7000)))
    print(f"Dashboard will run on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
