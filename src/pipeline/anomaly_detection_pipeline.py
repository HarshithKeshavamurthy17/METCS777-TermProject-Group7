"""Main anomaly detection pipeline."""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, lit, when, concat_ws, array
from typing import List, Dict
import os

from ..etl.clickstream_loader import ClickstreamLoader
from ..features.baseline import BaselineCalculator
from ..features.forecasting import generate_forecasts_for_all_edges
from ..detectors.statistical_detector import StatisticalDetector
from ..detectors.clustering_detector import ClusteringDetector
from ..detectors.mix_shift_detector import MixShiftDetector
from ..storage.anomalies_schema import AnomaliesStorage


class AnomalyDetectionPipeline:
    """End-to-end anomaly detection pipeline."""
    
    def __init__(self, spark: SparkSession, config: Dict):
        """
        Initialize pipeline.
        
        Args:
            spark: SparkSession
            config: Configuration dictionary
        """
        self.spark = spark
        self.config = config
        
        # Initialize components
        data_config = config.get('data', {})
        self.min_transitions = data_config.get('min_transitions', 10)
        
        self.loader = ClickstreamLoader(spark, self.min_transitions)
        self.baseline_calc = BaselineCalculator(spark)
        
        # Forecasting config (used later if enabled)
        self.forecasting_config = config.get('forecasting', {})
        self.forecasting_enabled = self.forecasting_config.get('enable', False)
        
        # Initialize detectors
        det_config = config.get('anomaly_detection', {})
        
        traffic_spike_config = det_config.get('traffic_spike', {})
        # Remove unsupported parameters
        traffic_spike_config = {k: v for k, v in traffic_spike_config.items() 
                                if k in ['z_score_threshold', 'ratio_threshold', 'mad_epsilon']}
        self.statistical_detector = StatisticalDetector(
            spark,
            **traffic_spike_config
        )
        
        self.clustering_detector = ClusteringDetector(
            spark,
            **det_config.get('clustering', {})
        )
        
        self.mix_shift_detector = MixShiftDetector(
            spark,
            **det_config.get('mix_shift', {})
        )
        
        
        # Initialize storage
        storage_config = config.get('storage', {})
        self.anomalies_storage = AnomaliesStorage(
            spark,
            data_config.get('anomalies_dir', 'data/anomalies'),
            storage_config.get('format', 'parquet')
        )
    
    def run_etl(self) -> DataFrame:
        """
        Run ETL pipeline to load and clean data.
        
        Returns:
            Cleaned DataFrame
        """
        print("=" * 80)
        print("STEP 1: ETL - Loading and cleaning clickstream data")
        print("=" * 80)
        
        data_config = self.config.get('data', {})
        months = data_config.get('months', [])
        raw_dir = data_config.get('raw_data_dir', 'data/raw')
        processed_dir = data_config.get('processed_data_dir', 'data/processed')
        
        # Check if processed data exists
        if os.path.exists(processed_dir) and os.listdir(processed_dir):
            print(f"Loading processed data from {processed_dir}...")
            df = self.spark.read.parquet(processed_dir)
        else:
            # Load raw files
            file_paths = []
            for month in months:
                # Expected filename format: clickstream-{month}-pageviews.tsv.gz or similar
                # User needs to download these files
                file_path = os.path.join(raw_dir, f"clickstream-{month}.tsv")
                if os.path.exists(file_path):
                    file_paths.append((file_path, month))
                else:
                    print(f"Warning: File not found for {month}: {file_path}")
            
            if not file_paths:
                raise FileNotFoundError(
                    f"No clickstream files found in {raw_dir}. "
                    "Please download data first using scripts/download_clickstream.py"
                )
            
            # Load and clean
            df = self.loader.load_multiple_months(file_paths)
            df = self.loader.clean(df)
            
            # Save processed data
            storage_format = self.config.get('storage', {}).get('format', 'parquet')
            self.loader.save_cleaned(df, processed_dir, storage_format)
        
        print(f"ETL complete. Total rows: {df.count()}")
        return df
    
    def run_feature_engineering(self, df: DataFrame) -> tuple:
        """
        Run feature engineering to compute baselines and features.
        
        Args:
            df: Cleaned clickstream DataFrame
            
        Returns:
            Tuple of (baselines_df, features_df, referrer_dist_df)
        """
        print("=" * 80)
        print("STEP 2: Feature Engineering - Computing baselines and features")
        print("=" * 80)
        
        months = self.config.get('data', {}).get('months', [])
        
        # Calculate baselines
        baselines = self.baseline_calc.calculate_edge_baselines(df, months)
        
        # Build features for clustering
        features = self.baseline_calc.build_edge_features(df, baselines, months)
        
        # Calculate referrer distributions
        referrer_dist = self.baseline_calc.calculate_referrer_distributions(df)
        
        # Apply forecasting if enabled
        self.forecast_df = None  # Store for later use
        if self.forecasting_enabled:
            print("\n--- Running Forecasting Module ---")
            forecast_df = generate_forecasts_for_all_edges(
                self.spark,
                df,
                months,
                min_history_months=self.forecasting_config.get('min_history_months', 3),
                forecast_ratio_threshold=self.forecasting_config.get('forecast_ratio_threshold', 2.0),
                model_type=self.forecasting_config.get('model_type', 'auto')
            )
            
            self.forecast_df = forecast_df  # Store for later
            
            # Join forecast columns to features DataFrame
            if forecast_df.count() > 0:
                print(f"Joining {forecast_df.count()} forecast records to features...")
                # Cast month to string to match
                forecast_df = forecast_df.withColumn('month', col('month').cast('string'))
                features = features.withColumn('month', col('month').cast('string'))
                
                features = features.join(
                    forecast_df,
                    ['prev', 'curr', 'type', 'month'],
                    'left'
                )
                # Fill nulls with defaults
                features = features.fillna({
                    'forecast_n': 0.0,
                    'forecast_lower': 0.0,
                    'forecast_upper': 0.0,
                    'forecast_error': 0.0,
                    'forecast_ratio': 1.0,
                    'forecast_flag': False
                })
                print(f"Features now have forecast columns: {[c for c in features.columns if 'forecast' in c]}")
            else:
                print("Warning: No forecasts generated")
        
        print("Feature engineering complete.")
        return baselines, features, referrer_dist
    
    def run_detection(self, df: DataFrame, baselines: DataFrame, 
                     features: DataFrame, referrer_dist: DataFrame) -> DataFrame:
        """
        Run all anomaly detectors.
        
        Args:
            df: Cleaned clickstream DataFrame
            baselines: Baseline statistics DataFrame
            features: Feature vectors DataFrame
            referrer_dist: Referrer distributions DataFrame
            
        Returns:
            Combined anomalies DataFrame
        """
        print("=" * 80)
        print("STEP 3: Anomaly Detection - Running all detectors")
        print("=" * 80)
        
        months = self.config.get('data', {}).get('months', [])
        
        # Process ALL months, not just the last one
        # For each month, use previous months as baseline (need at least 3 months for baseline)
        min_baseline_months = self.config.get('anomaly_detection', {}).get('traffic_spike', {}).get('min_baseline_months', 3)
        
        all_anomalies = []
        
        # Fit clustering detector once on all data
        print("\n--- Fitting Clustering Detector (once for all months) ---")
        clustering_fitted = False
        try:
            self.clustering_detector.fit(features, months)
            clustering_fitted = True
            print("✓ Clustering detector fitted successfully")
        except Exception as e:
            print(f"Warning: Clustering detector fit failed: {e}")
            print("Will skip clustering detection for all months...")
        
        # Process each month as a target month
        for i, target_month in enumerate(months):
            # Need at least min_baseline_months before this month to use as baseline
            if i < min_baseline_months:
                print(f"\n⚠ Skipping {target_month}: Need at least {min_baseline_months} baseline months (only {i} available)")
                continue
            
            baseline_months = months[:i]  # All months before current month
            print(f"\n{'='*80}")
            print(f"Processing month: {target_month} (baseline: {len(baseline_months)} months)")
            print(f"{'='*80}")
        
        # 1. Statistical detector (traffic spikes)
            print(f"\n--- Running Statistical Detector for {target_month} ---")
        statistical_anomalies = self.statistical_detector.detect(
            df, baselines, target_month
        )
        
        # Join forecast data to statistical anomalies if available
        if self.forecasting_enabled and self.forecast_df is not None and self.forecast_df.count() > 0:
            forecast_subset = self.forecast_df.filter(col('month') == target_month)
            
            if forecast_subset.count() > 0:
                # Ensure types match
                forecast_subset = forecast_subset.withColumn('month', col('month').cast('string'))
                statistical_anomalies = statistical_anomalies.withColumn('month', col('month').cast('string'))
                
                statistical_anomalies = statistical_anomalies.join(
                    forecast_subset,
                    ['prev', 'curr', 'type', 'month'],
                    'left'
                )
        
        all_anomalies.append(statistical_anomalies)
        
            # 2. Clustering detector (navigation edges) - only if fitted successfully
            if clustering_fitted:
                print(f"\n--- Running Clustering Detector for {target_month} ---")
        try:
            clustering_anomalies = self.clustering_detector.detect(
                features, months, target_month
            )
            all_anomalies.append(clustering_anomalies)
        except Exception as e:
                    print(f"Warning: Clustering detector failed for {target_month}: {e}")
        
        # 3. Mix-shift detector
            print(f"\n--- Running Mix-Shift Detector for {target_month} ---")
        mix_shift_anomalies = self.mix_shift_detector.detect(
            referrer_dist, target_month, baseline_months
        )
        all_anomalies.append(mix_shift_anomalies)
        
        # Combine all anomalies
        if all_anomalies:
            combined = all_anomalies[0]
            for anomalies_df in all_anomalies[1:]:
                combined = combined.unionByName(anomalies_df, allowMissingColumns=True)
        else:
            # Create empty DataFrame with correct schema
            from ..storage.anomalies_schema import ANOMALIES_SCHEMA
            combined = self.spark.createDataFrame([], ANOMALIES_SCHEMA)
        
        # Add forecast signals - if forecast_flag is True, append "forecast_spike" to anomaly_type
        if combined.count() > 0:
            # Ensure forecast columns exist (add if missing)
            forecast_cols = {
                'forecast_n': 0.0,
                'forecast_lower': 0.0,
                'forecast_upper': 0.0,
                'forecast_error': 0.0,
                'forecast_ratio': 1.0,
                'forecast_flag': False
            }
            
            for col_name, default_val in forecast_cols.items():
                if col_name not in combined.columns:
                    if isinstance(default_val, bool):
                        combined = combined.withColumn(col_name, lit(default_val))
                    else:
                        combined = combined.withColumn(col_name, lit(default_val))
            
            # Update anomaly_type to include forecast_spike when flag is True
            if 'forecast_flag' in combined.columns:
                combined = combined.withColumn(
                    'anomaly_type',
                    when(col('forecast_flag'), 
                         concat_ws('_', col('anomaly_type'), lit('forecast_spike')))
                    .otherwise(col('anomaly_type'))
                )
            
            # Fill null values for forecast columns
            combined = combined.fillna(forecast_cols)
        
        print(f"\nTotal anomalies detected: {combined.count()}")
        
        return combined
    
    def run(self):
        """Run the complete pipeline."""
        print("\n" + "=" * 80)
        print("WIKIPEDIA CLICKSTREAM ANOMALY DETECTION PIPELINE")
        print("=" * 80 + "\n")
        
        # Step 1: ETL
        df = self.run_etl()
        
        # Step 2: Feature Engineering
        baselines, features, referrer_dist = self.run_feature_engineering(df)
        
        # Step 3: Anomaly Detection
        anomalies = self.run_detection(df, baselines, features, referrer_dist)
        
        # Step 4: Save anomalies
        print("=" * 80)
        print("STEP 4: Saving Anomalies")
        print("=" * 80)
        self.anomalies_storage.save_anomalies(anomalies, mode="overwrite")
        
        print("\n" + "=" * 80)
        print("PIPELINE COMPLETE!")
        print("=" * 80)
        
        return anomalies

