"""Baseline statistics and feature engineering."""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, window, median, mean, stddev, count, sum as spark_sum,
    collect_list, array, lit, when, lag, lead, percent_rank, percentile_approx
)
from pyspark.sql.window import Window
from typing import Dict, List
import numpy as np


class BaselineCalculator:
    """Calculate baseline statistics for anomaly detection."""
    
    def __init__(self, spark: SparkSession):
        """Initialize baseline calculator."""
        self.spark = spark
    
    def calculate_edge_baselines(self, df: DataFrame, months: List[str]) -> DataFrame:
        """
        Calculate baseline statistics for each prev->curr edge.
        
        Computes:
        - baseline_median: Median traffic over historical months
        - baseline_mean: Mean traffic
        - baseline_std: Standard deviation
        - baseline_mad: Median Absolute Deviation (approximated)
        
        Args:
            df: Clickstream DataFrame with columns (prev, curr, n, month)
            months: List of month strings in chronological order
            
        Returns:
            DataFrame with baseline statistics per edge
        """
        print("Calculating edge baselines...")
        
        # Group by prev, curr and aggregate over months
        edge_stats = df.groupBy("prev", "curr", "type") \
            .pivot("month", months) \
            .sum("n") \
            .fillna(0)
        
        # Calculate statistics across months (columns)
        month_cols = [col(month) for month in months]
        
        # For median, we'll use a window function approach
        # First, create a long format with all values
        edge_long = df.select("prev", "curr", "type", "month", "n") \
            .groupBy("prev", "curr", "type", "month") \
            .agg(spark_sum("n").alias("n"))
        
        # Calculate median using approximate percentile
        # For simplicity, use mean as approximation of median when we have few months
        # In production, would use percentile_approx
        from pyspark.sql.functions import percentile_approx
        
        # Use percentile_approx for median (50th percentile)
        median_df = edge_long.groupBy("prev", "curr", "type") \
            .agg(percentile_approx("n", 0.5).alias("baseline_median"))
        
        # Calculate mean and std
        mean_std = edge_long.groupBy("prev", "curr", "type") \
            .agg(
                mean("n").alias("baseline_mean"),
                stddev("n").alias("baseline_std")
            )
        
        # Approximate MAD: median of absolute deviations from median
        from pyspark.sql.functions import abs as spark_abs
        edge_with_median = edge_long.join(median_df, ["prev", "curr", "type"])
        edge_with_median = edge_with_median.withColumn(
            "abs_dev", 
            spark_abs(col("n") - col("baseline_median"))
        )
        
        mad_df = edge_with_median.groupBy("prev", "curr", "type") \
            .agg(mean("abs_dev").alias("baseline_mad"))  # Approximate MAD
        
        # Combine all statistics
        baselines = median_df.join(mean_std, ["prev", "curr", "type"]) \
            .join(mad_df, ["prev", "curr", "type"])
        
        # Fill nulls with small values
        baselines = baselines.fillna({
            "baseline_median": 0.0,
            "baseline_mean": 0.0,
            "baseline_std": 0.01,
            "baseline_mad": 0.01
        })
        
        print(f"Calculated baselines for {baselines.count()} edges")
        
        return baselines
    
    def build_edge_features(self, df: DataFrame, baselines: DataFrame, months: List[str]) -> DataFrame:
        """
        Build feature vectors for clustering-based anomaly detection.
        
        Features:
        - Normalized traffic over months (array)
        - Ratio vs baseline
        - Type encoding
        - Category encodings
        
        Args:
            df: Clickstream DataFrame
            baselines: Baseline statistics DataFrame
            months: List of months in order
            
        Returns:
            DataFrame with feature vectors
        """
        print("Building edge feature vectors...")
        
        # Aggregate traffic per edge per month
        edge_monthly = df.groupBy("prev", "curr", "type", "month") \
            .agg(spark_sum("n").alias("n"))
        
        # Pivot to get traffic per month as columns
        edge_pivot = edge_monthly.groupBy("prev", "curr", "type") \
            .pivot("month", months) \
            .sum("n") \
            .fillna(0)
        
        # Join with baselines
        edge_features = edge_pivot.join(baselines, ["prev", "curr", "type"], "left")
        
        # Create normalized traffic array
        month_cols = [col(month).alias(f"traffic_{month}") for month in months]
        edge_features = edge_features.select(
            ["prev", "curr", "type", "baseline_median", "baseline_mean", "baseline_mad"] + 
            [col(month) for month in months]
        )
        
        # Calculate ratios
        for month in months:
            edge_features = edge_features.withColumn(
                f"ratio_{month}",
                when(col("baseline_median") > 0, col(month) / col("baseline_median"))
                .otherwise(0.0)
            )
        
        # Type encoding (simple one-hot would be better, but this works)
        type_mapping = {"link": 1.0, "external": 2.0, "other": 3.0}
        for type_val, encoding in type_mapping.items():
            edge_features = edge_features.withColumn(
                f"type_{type_val}",
                when(col("type") == type_val, 1.0).otherwise(0.0)
            )
        
        print(f"Built features for {edge_features.count()} edges")
        
        return edge_features
    
    def calculate_referrer_distributions(self, df: DataFrame) -> DataFrame:
        """
        Calculate referrer (prev) distribution for each curr page per month.
        
        Used for mix-shift anomaly detection.
        
        Args:
            df: Clickstream DataFrame
            
        Returns:
            DataFrame with referrer distributions
        """
        print("Calculating referrer distributions...")
        
        # Aggregate by curr, prev, month
        referrer_agg = df.groupBy("curr", "prev", "month") \
            .agg(spark_sum("n").alias("n"))
        
        # Calculate total traffic per curr, month
        total_traffic = referrer_agg.groupBy("curr", "month") \
            .agg(spark_sum("n").alias("total_n"))
        
        # Calculate proportions
        referrer_dist = referrer_agg.join(total_traffic, ["curr", "month"]) \
            .withColumn("proportion", col("n") / col("total_n")) \
            .select("curr", "prev", "month", "n", "proportion", "total_n")
        
        print(f"Calculated distributions for {referrer_dist.count()} curr-prev-month combinations")
        
        return referrer_dist

