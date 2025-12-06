#!/usr/bin/env python3
"""Evaluate anomaly detection results."""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.metrics import evaluate_anomalies


def main():
    parser = argparse.ArgumentParser(description="Evaluate anomaly detection results")
    parser.add_argument(
        '--anomalies',
        default='data/anomalies',
        help='Path to anomalies data'
    )
    parser.add_argument(
        '--ground-truth',
        help='Path to ground truth data (optional)'
    )
    
    args = parser.parse_args()
    
    evaluate_anomalies(args.anomalies, args.ground_truth)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

