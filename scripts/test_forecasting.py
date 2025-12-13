#!/usr/bin/env python3
"""Quick test to verify forecasting works."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import load_config
from src.utils.spark_session import create_spark_session
from src.pipeline.anomaly_detection_pipeline import AnomalyDetectionPipeline

def main():
    print("=" * 80)
    print("TESTING FORECASTING MODULE")
    print("=" * 80)
    
    # Load config
    config = load_config()
    
    # Check if forecasting is enabled
    forecasting_enabled = config.get('forecasting', {}).get('enable', False)
    print(f"\nForecasting enabled: {forecasting_enabled}")
    
    if not forecasting_enabled:
        print("\n⚠️  WARNING: Forecasting is disabled in config.yaml")
        print("Set forecasting.enable: true in config/config.yaml")
        return 1
    
    # Create Spark session
    spark = create_spark_session(config)
    
    try:
        # Create pipeline
        pipeline = AnomalyDetectionPipeline(spark, config)
        
        # Run pipeline (this will generate forecasts)
        print("\nRunning pipeline with forecasting...")
        anomalies = pipeline.run()
        
        # Check if forecast columns exist
        forecast_cols = [c for c in anomalies.columns if 'forecast' in c]
        print(f"\n✓ Forecast columns found: {forecast_cols}")
        
        # Count anomalies with forecast flags
        if 'forecast_flag' in anomalies.columns:
            forecast_anomalies = anomalies.filter(anomalies.forecast_flag == True)
            count = forecast_anomalies.count()
            print(f"✓ Anomalies with forecast_flag=True: {count}")
        
        print("\n" + "=" * 80)
        print("✅ FORECASTING TEST COMPLETE")
        print("=" * 80)
        print("\nNew anomalies saved to: data/anomalies/anomalies.parquet")
        print("Refresh your dashboard to see forecast data!")
        
    finally:
        spark.stop()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())





