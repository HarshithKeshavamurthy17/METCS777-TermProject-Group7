#!/usr/bin/env python3
"""Re-run detection pipeline with forecasting enabled."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import load_config
from src.utils.spark_session import create_spark_session
from src.pipeline.anomaly_detection_pipeline import AnomalyDetectionPipeline

def main():
    print("=" * 80)
    print("RE-RUNNING DETECTION WITH FORECASTING")
    print("=" * 80)
    
    # Load config
    config = load_config()
    
    # Ensure forecasting is enabled
    if not config.get('forecasting', {}).get('enable', False):
        print("\n⚠️  WARNING: Forecasting is disabled!")
        print("Setting forecasting.enable = true in config...")
        config['forecasting']['enable'] = True
    
    print(f"\n✓ Forecasting enabled: {config.get('forecasting', {}).get('enable', False)}")
    print(f"✓ Min history months: {config.get('forecasting', {}).get('min_history_months', 3)}")
    
    # Create Spark session
    spark = create_spark_session(config)
    
    try:
        # Create pipeline
        pipeline = AnomalyDetectionPipeline(spark, config)
        
        # Run full pipeline
        print("\n" + "=" * 80)
        print("RUNNING FULL PIPELINE")
        print("=" * 80)
        anomalies = pipeline.run()
        
        # Verify forecast columns
        print("\n" + "=" * 80)
        print("VERIFYING FORECAST DATA")
        print("=" * 80)
        
        forecast_cols = [c for c in anomalies.columns if 'forecast' in c]
        print(f"Forecast columns: {forecast_cols}")
        
        if forecast_cols:
            # Count anomalies with forecast data
            anomalies_with_forecast = anomalies.filter(
                anomalies.forecast_flag.isNotNull() | (anomalies.forecast_n > 0)
            )
            count = anomalies_with_forecast.count()
            print(f"Anomalies with forecast data: {count}")
            
            # Count forecast spikes
            if 'forecast_flag' in anomalies.columns:
                forecast_spikes = anomalies.filter(anomalies.forecast_flag == True)
                spike_count = forecast_spikes.count()
                print(f"Anomalies flagged as forecast spikes: {spike_count}")
                
                if spike_count > 0:
                    print("\nSample forecast spike:")
                    sample = forecast_spikes.limit(1).toPandas()
                    print(sample[['prev', 'curr', 'n', 'forecast_n', 'forecast_upper', 'forecast_flag']].to_dict('records')[0])
        else:
            print("⚠️  WARNING: No forecast columns found in anomalies!")
        
        print("\n" + "=" * 80)
        print("✅ PIPELINE COMPLETE")
        print("=" * 80)
        print(f"\nTotal anomalies: {anomalies.count()}")
        print("Anomalies saved to: data/anomalies/anomalies.parquet")
        print("\n🔄 Restart dashboard to see forecast data:")
        print("   1. Stop current dashboard (Ctrl+C)")
        print("   2. Run: python scripts/start_dashboard_simple.py")
        print("   3. Refresh browser at http://localhost:2222")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        spark.stop()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())





