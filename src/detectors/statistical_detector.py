"""Statistical anomaly detector using MAD and Z-scores."""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, when, abs as spark_abs, lit, exp, pow, struct, monotonically_increasing_id,
    udf, array
)
from pyspark.sql.types import DoubleType, StructType, StructField, StringType
from typing import Dict
import uuid
import math


class StatisticalDetector:
    """Detect traffic spike anomalies using robust statistics."""
    
    def __init__(
        self, 
        spark: SparkSession,
        z_score_threshold: float = 3.5,
        ratio_threshold: float = 10.0,
        mad_epsilon: float = 0.01
    ):
        """
        Initialize statistical detector.
        
        Args:
            spark: SparkSession
            z_score_threshold: Z-score threshold for anomalies
            ratio_threshold: Ratio threshold (n / baseline_median)
            mad_epsilon: Small value to avoid division by zero in MAD
        """
        self.spark = spark
        self.z_score_threshold = z_score_threshold
        self.ratio_threshold = ratio_threshold
        self.mad_epsilon = mad_epsilon
    
    def calculate_robust_z_score(self, n: float, median: float, mad: float) -> float:
        """
        Calculate robust Z-score using MAD.
        
        z = (n - median) / (MAD + epsilon)
        """
        if mad + self.mad_epsilon == 0:
            return 0.0
        return (n - median) / (mad + self.mad_epsilon)
    
    def calculate_confidence(self, z_score: float, ratio: float) -> float:
        """
        Calculate confidence score using sigmoid function.
        
        Args:
            z_score: Robust Z-score
            ratio: Deviation ratio (n / baseline_median)
            
        Returns:
            Confidence score between 0 and 1
        """
        # Normalize inputs
        z_norm = min(abs(z_score) / max(self.z_score_threshold, 1.0), 10.0)
        ratio_norm = min(ratio / max(self.ratio_threshold, 1.0), 10.0)
        
        # Sigmoid to map to [0, 1]
        # Center at 1.0 (barely anomaly) -> 0.5 confidence
        # Slope 1.0 -> gentler curve
        confidence = 1.0 / (1.0 + math.exp(-1.0 * (combined - 1.0)))
        
        return min(max(confidence, 0.0), 1.0)
    
    def detect(self, df: DataFrame, baselines: DataFrame, target_month: str) -> DataFrame:
        """
        Detect traffic spike anomalies for a target month.
        
        Args:
            df: Clickstream DataFrame with current month data
            baselines: Baseline statistics DataFrame
            target_month: Month to analyze (e.g., "2023-12")
            
        Returns:
            DataFrame with anomaly records
        """
        print(f"Detecting traffic spike anomalies for {target_month}...")
        
        # Filter to target month
        month_data = df.filter(col("month") == target_month)
        
        # Aggregate by edge
        from pyspark.sql.functions import sum as spark_sum
        edge_traffic = month_data.groupBy("prev", "curr", "type") \
            .agg(spark_sum("n").alias("n"))
        
        # Join with baselines
        edge_with_baseline = edge_traffic.join(
            baselines, 
            ["prev", "curr", "type"], 
            "inner"
        )
        
        # Calculate statistics
        anomalies = edge_with_baseline.withColumn(
            "deviation_ratio",
            when(col("baseline_median") > 0, col("n") / col("baseline_median"))
            .otherwise(0.0)
        ).withColumn(
            "z_score",
            (col("n") - col("baseline_median")) / (col("baseline_mad") + lit(self.mad_epsilon))
        )
        
        # Filter anomalies
        anomalies = anomalies.filter(
            (col("deviation_ratio") >= self.ratio_threshold) |
            (spark_abs(col("z_score")) >= self.z_score_threshold)
        )
        
        # Calculate confidence using UDF - make it standalone to avoid serialization issues
        z_thresh = self.z_score_threshold
        r_thresh = self.ratio_threshold
        
        def calc_conf(z, r):
            try:
                z_val = float(z) if z else 0.0
                r_val = float(r) if r else 0.0
                
                # Normalize inputs
                z_norm = min(abs(z_val) / max(z_thresh, 1.0), 10.0)
                ratio_norm = min(r_val / max(r_thresh, 1.0), 10.0)
                
                # Combined signal
                combined = (z_norm + ratio_norm) / 2.0
                
                # Sigmoid to map to [0, 1]
                # Center at 1.0 (barely anomaly) -> 0.5 confidence
                # Slope 1.0 -> gentler curve
                import math
                confidence = 1.0 / (1.0 + math.exp(-1.0 * (combined - 1.0)))
                
                return float(min(max(confidence, 0.0), 1.0))
            except:
                return 0.0
        
        confidence_udf = udf(calc_conf, DoubleType())
        
        anomalies = anomalies.withColumn(
            "confidence",
            confidence_udf(col("z_score"), col("deviation_ratio"))
        )
        
        # Add anomaly metadata
        anomalies = anomalies.withColumn(
            "anomaly_id",
            monotonically_increasing_id().cast(StringType())
        ).withColumn(
            "anomaly_type",
            lit("traffic_spike")
        ).withColumn(
            "month",
            lit(target_month)
        ).withColumn(
            "description",
            when(
                col("deviation_ratio") >= self.ratio_threshold,
                lit(f"Traffic spike: {target_month} traffic is {col('deviation_ratio')}x baseline")
            ).otherwise(
                lit(f"Statistical anomaly: Z-score = {col('z_score')}")
            )
        )
        
        # Select final columns (include forecast columns if they exist)
        base_cols = [
            "anomaly_id", "month", "prev", "curr", "type", "n",
            "baseline_median", "deviation_ratio", "z_score",
            "anomaly_type", "confidence", "description"
        ]
        
        # Add forecast columns if they exist
        forecast_cols = ["forecast_n", "forecast_lower", "forecast_upper", 
                        "forecast_error", "forecast_ratio", "forecast_flag"]
        available_cols = base_cols + [c for c in forecast_cols if c in anomalies.columns]
        
        result = anomalies.select(*available_cols)
        
        # Fill null forecast columns if they don't exist
        for col_name in forecast_cols:
            if col_name not in result.columns:
                if col_name == 'forecast_flag':
                    result = result.withColumn(col_name, lit(False))
                else:
                    result = result.withColumn(col_name, lit(0.0))
        
        count = result.count()
        print(f"Detected {count} traffic spike anomalies for {target_month}")
        
        return result

