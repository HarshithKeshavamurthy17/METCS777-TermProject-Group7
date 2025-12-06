"""Evaluation metrics for anomaly detection."""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, sum as spark_sum, count
from typing import List, Dict
import pandas as pd


class AnomalyEvaluator:
    """Evaluate anomaly detection performance."""
    
    def __init__(self, spark: SparkSession):
        """Initialize evaluator."""
        self.spark = spark
    
    def precision_at_k(self, anomalies_df: DataFrame, ground_truth: List[str], k: int = 50) -> float:
        """
        Calculate Precision@K.
        
        Args:
            anomalies_df: DataFrame with detected anomalies
            ground_truth: List of known anomaly identifiers (e.g., page names)
            k: Top K anomalies to consider
            
        Returns:
            Precision@K score
        """
        # Get top K anomalies by confidence
        top_k = anomalies_df.orderBy(col("confidence").desc()).limit(k)
        
        # Convert to Pandas for easier processing
        top_k_pd = top_k.toPandas()
        
        # Check how many are in ground truth
        # This is a simplified check - in practice, ground truth would be more structured
        hits = 0
        for _, row in top_k_pd.iterrows():
            # Check if prev or curr is in ground truth
            if row['prev'] in ground_truth or row['curr'] in ground_truth:
                hits += 1
        
        precision = hits / k if k > 0 else 0.0
        return precision
    
    def calculate_statistics(self, anomalies_df: DataFrame) -> Dict:
        """
        Calculate basic statistics about detected anomalies.
        
        Args:
            anomalies_df: DataFrame with anomalies
            
        Returns:
            Dictionary with statistics
        """
        total = anomalies_df.count()
        
        # Count by type
        by_type = anomalies_df.groupBy("anomaly_type") \
            .agg(count("*").alias("count")) \
            .toPandas() \
            .set_index("anomaly_type")["count"] \
            .to_dict()
        
        # Average confidence
        avg_confidence = anomalies_df.agg({"confidence": "avg"}).collect()[0][0]
        
        # Top anomalies
        top_anomalies = anomalies_df.orderBy(col("confidence").desc()) \
            .limit(10) \
            .toPandas() \
            .to_dict('records')
        
        return {
            "total_anomalies": total,
            "by_type": by_type,
            "avg_confidence": float(avg_confidence) if avg_confidence else 0.0,
            "top_10": top_anomalies
        }
    
    def compare_with_pageviews(self, anomalies_df: DataFrame, pageviews_df: DataFrame) -> DataFrame:
        """
        Compare detected anomalies with pageview trends.
        
        Args:
            anomalies_df: Detected anomalies
            pageviews_df: Pageview time series data
            
        Returns:
            DataFrame with comparison results
        """
        # Join anomalies with pageviews
        comparison = anomalies_df.join(
            pageviews_df,
            anomalies_df.curr == pageviews_df.page,
            "left"
        )
        
        return comparison


def evaluate_anomalies(anomalies_path: str, ground_truth_path: str = None):
    """
    Evaluate detected anomalies.
    
    Args:
        anomalies_path: Path to anomalies data
        ground_truth_path: Optional path to ground truth data
    """
    from ..utils.spark_session import create_spark_session
    from ..utils.config import load_config
    
    config = load_config()
    spark = create_spark_session(config)
    
    try:
        evaluator = AnomalyEvaluator(spark)
        
        # Load anomalies
        anomalies_df = spark.read.parquet(anomalies_path)
        
        # Calculate statistics
        stats = evaluator.calculate_statistics(anomalies_df)
        
        print("=" * 80)
        print("ANOMALY DETECTION EVALUATION")
        print("=" * 80)
        print(f"Total anomalies: {stats['total_anomalies']}")
        print(f"By type: {stats['by_type']}")
        print(f"Average confidence: {stats['avg_confidence']:.3f}")
        print("\nTop 10 anomalies:")
        for i, anomaly in enumerate(stats['top_10'], 1):
            print(f"{i}. {anomaly.get('prev', 'N/A')} -> {anomaly.get('curr', 'N/A')} "
                  f"(confidence: {anomaly.get('confidence', 0):.3f})")
        
        # If ground truth provided, calculate precision
        if ground_truth_path:
            # Load ground truth (simplified - would be more structured in practice)
            ground_truth_df = spark.read.parquet(ground_truth_path)
            ground_truth_pages = ground_truth_df.select("page").distinct().rdd.map(lambda r: r[0]).collect()
            
            precision_50 = evaluator.precision_at_k(anomalies_df, ground_truth_pages, k=50)
            print(f"\nPrecision@50: {precision_50:.3f}")
        
    finally:
        spark.stop()

