#!/bin/bash

# Exit on error
set -e

echo "============================================================"
echo "🚀 STARTING FULL PIPELINE EXECUTION"
echo "============================================================"
echo "Date: $(date)"
echo "============================================================"

# Ensure consistent Python version for Spark driver and workers
export PYSPARK_PYTHON=/opt/anaconda3/bin/python
export PYSPARK_DRIVER_PYTHON=/opt/anaconda3/bin/python

# 1. Run ETL
echo ""
echo "------------------------------------------------------------"
echo "STEP 1: ETL & Data Preparation"
echo "------------------------------------------------------------"
python scripts/run_etl.py

# 2. Run Detection
echo ""
echo "------------------------------------------------------------"
echo "STEP 2: Anomaly Detection & Forecasting"
echo "------------------------------------------------------------"
python scripts/run_detection.py

# 3. Start Dashboard
echo ""
echo "------------------------------------------------------------"
echo "STEP 3: Starting Dashboard"
echo "------------------------------------------------------------"
echo "Dashboard will be available at http://localhost:5000"
echo "Press Ctrl+C to stop."
python scripts/start_dashboard.py
