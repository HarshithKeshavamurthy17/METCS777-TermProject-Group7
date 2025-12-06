#!/usr/bin/env python3
"""Run ETL pipeline."""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import load_config
from src.utils.spark_session import create_spark_session
from src.etl.clickstream_loader import ClickstreamLoader


def main():
    parser = argparse.ArgumentParser(description="Run ETL pipeline")
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
        # Initialize loader
        data_config = config.get('data', {})
        min_transitions = data_config.get('min_transitions', 10)
        loader = ClickstreamLoader(spark, min_transitions)
        
        # Load data
        months = data_config.get('months', [])
        raw_dir = data_config.get('raw_data_dir', 'data/raw')
        
        file_paths = []
        for month in months:
            file_path = Path(raw_dir) / f"clickstream-{month}.tsv"
            if file_path.exists():
                file_paths.append((str(file_path), month))
            else:
                print(f"Warning: File not found for {month}: {file_path}")
        
        if not file_paths:
            print("Error: No clickstream files found.")
            print(f"Please download data to {raw_dir} first using:")
            print("  python scripts/download_clickstream.py --months <month1> <month2> ...")
            return 1
        
        # Load and clean
        df = loader.load_multiple_months(file_paths)
        df = loader.clean(df)
        
        # Save
        processed_dir = data_config.get('processed_data_dir', 'data/processed')
        storage_format = config.get('storage', {}).get('format', 'parquet')
        loader.save_cleaned(df, processed_dir, storage_format)
        
        print(f"\nETL complete! Processed {df.count()} rows.")
        print(f"Saved to {processed_dir}")
        
    finally:
        spark.stop()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

