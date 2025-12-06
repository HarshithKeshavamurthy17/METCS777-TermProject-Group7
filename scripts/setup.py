#!/usr/bin/env python3
"""Setup script for the project."""
import os
import shutil
from pathlib import Path


def setup_project():
    """Set up project directories and configuration."""
    project_root = Path(__file__).parent.parent
    
    # Create directories
    directories = [
        "data/raw",
        "data/processed",
        "data/anomalies",
        "notebooks",
        "tests",
        "logs"
    ]
    
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Copy config if it doesn't exist
    config_example = project_root / "config" / "config.example.yaml"
    config_actual = project_root / "config" / "config.yaml"
    
    if not config_actual.exists() and config_example.exists():
        shutil.copy(config_example, config_actual)
        print(f"Created config/config.yaml from example")
    elif config_actual.exists():
        print("Config file already exists, skipping...")
    
    print("\nSetup complete!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Download data: python scripts/download_clickstream.py --months <months>")
    print("3. Run ETL: python scripts/run_etl.py")
    print("4. Run detection: python scripts/run_detection.py")
    print("5. Start dashboard: python scripts/start_dashboard.py")


if __name__ == '__main__':
    setup_project()

