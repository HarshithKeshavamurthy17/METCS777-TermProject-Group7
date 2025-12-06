"""Streaming demo for real-time anomaly detection."""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, window, current_timestamp, lit
from pyspark.sql.types import TimestampType
from typing import Dict
import time


class StreamingDemo:
    """Demo of streaming anomaly detection."""
    
    def __init__(self, spark: SparkSession, config: Dict):
        """
        Initialize streaming demo.
        
        Args:
            spark: SparkSession
            config: Configuration dictionary
        """
        self.spark = spark
        self.config = config
    
    def simulate_streaming(self, source_df: DataFrame, output_path: str):
        """
        Simulate streaming by replaying historical data in micro-batches.
        
        Args:
            source_df: Historical clickstream DataFrame
            output_path: Path to write streaming results
        """
        print("Setting up streaming demo...")
        
        # Add timestamp column (simulate real-time)
        df_with_time = source_df.withColumn(
            "timestamp",
            current_timestamp()
        )
        
        # Write to a temporary location for streaming source
        temp_path = output_path + "_temp"
        df_with_time.write.mode("overwrite").parquet(temp_path)
        
        # Create streaming DataFrame
        streaming_df = self.spark.readStream \
            .schema(df_with_time.schema) \
            .option("maxFilesPerTrigger", 1) \
            .parquet(temp_path)
        
        # Simple aggregation (in production, would run anomaly detection)
        windowed_counts = streaming_df \
            .withWatermark("timestamp", "1 hour") \
            .groupBy(
                window(col("timestamp"), "1 hour"),
                col("prev"),
                col("curr")
            ) \
            .agg({"n": "sum"})
        
        # Write to console (for demo)
        query = windowed_counts.writeStream \
            .outputMode("update") \
            .format("console") \
            .option("truncate", False) \
            .start()
        
        print("Streaming started. Check console output.")
        print("Press Ctrl+C to stop...")
        
        try:
            query.awaitTermination()
        except KeyboardInterrupt:
            print("\nStopping streaming...")
            query.stop()
        
        print("Streaming demo complete.")


def run_streaming_demo(config_path: str = None):
    """Run the streaming demo."""
    from ..utils.config import load_config
    from ..utils.spark_session import create_spark_session
    
    config = load_config(config_path)
    spark = create_spark_session(config)
    
    try:
        # Load processed data
        data_config = config.get('data', {})
        processed_dir = data_config.get('processed_data_dir', 'data/processed')
        
        df = spark.read.parquet(processed_dir)
        
        # Limit to small subset for demo
        df_sample = df.limit(10000)
        
        # Run streaming demo
        demo = StreamingDemo(spark, config)
        output_path = data_config.get('anomalies_dir', 'data/anomalies') + "_streaming"
        demo.simulate_streaming(df_sample, output_path)
        
    finally:
        spark.stop()

