#!/usr/bin/env python3
"""Run anomaly detection pipeline."""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import load_config
from src.utils.spark_session import create_spark_session
from src.pipeline.anomaly_detection_pipeline import AnomalyDetectionPipeline


def main():
    parser = argparse.ArgumentParser(description="Run anomaly detection pipeline")
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to config file'
    )
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    
    # Create Spark session
    spark = create_spark_session(config)
    
    try:
        # Run pipeline
        pipeline = AnomalyDetectionPipeline(spark, config)
        anomalies = pipeline.run()
        
        print(f"\nPipeline completed successfully!")
        print(f"Total anomalies detected: {anomalies.count()}")
        
    finally:
        spark.stop()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

