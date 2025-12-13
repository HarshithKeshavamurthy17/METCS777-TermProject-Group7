#!/usr/bin/env python3
"""Start the dashboard server."""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dashboard.app import app, init_app


def main():
    parser = argparse.ArgumentParser(description="Start anomaly detection dashboard")
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to config file'
    )
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=7000,
        help='Port to bind to (default: 7000)'
    )
    
    args = parser.parse_args()
    
    # Initialize app
    init_app()
    
    # Run app
    print(f"Starting dashboard on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()

