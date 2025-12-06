#!/usr/bin/env python3
"""
Start the Anomaly Detection Dashboard.
This script launches the Flask application to visualize the detected anomalies.
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

# Import the demo dashboard script which is robust and handles full datasets
from scripts.start_dashboard_demo import app

if __name__ == '__main__':
    print("Starting Dashboard...")
    # Run on port 5000 by default, or use PORT env var
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
