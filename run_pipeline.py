#!/usr/bin/env python3
"""
Run the Anomaly Detection Pipeline.
This script orchestrates the full pipeline using Spark:
1. ETL (Load and Clean Data)
2. Feature Engineering (Calculate Baselines)
3. Anomaly Detection (Traffic Spikes, Mix Shifts, Navigation Edges)
4. Forecasting (Optional)
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from scripts.run_detection import main

if __name__ == '__main__':
    print("Starting Anomaly Detection Pipeline...")
    sys.exit(main())
