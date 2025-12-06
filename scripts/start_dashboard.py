#!/usr/bin/env python3
"""Start the dashboard server."""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dashboard.app import app, init_app
from src.utils.config import load_config


def main():
    parser = argparse.ArgumentParser(description="Start anomaly detection dashboard")
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to config file'
    )
    parser.add_argument(
        '--host',
        default=None,
        help='Host to bind to (default: from config or 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='Port to bind to (default: from config or 5000)'
    )
    
    args = parser.parse_args()
    
    # Load config to get defaults
    config = load_config(args.config)
    dashboard_config = config.get('dashboard', {})
    
    # Determine host and port
    host = args.host or dashboard_config.get('host', '0.0.0.0')
    port = args.port or dashboard_config.get('port', 5000)
    
    # Initialize app
    init_app()
    
    # Run app
    print(f"Starting dashboard on http://{host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    main()

