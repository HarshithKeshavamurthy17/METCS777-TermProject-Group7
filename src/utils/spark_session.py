"""Spark session management."""
from pyspark.sql import SparkSession
from typing import Dict, Optional
from .config import load_config, get_spark_config


def create_spark_session(config: Optional[Dict] = None, app_name: Optional[str] = None) -> SparkSession:
    """
    Create and configure Spark session.
    
    Args:
        config: Configuration dictionary. If None, loads from config file.
        app_name: Override app name from config
        
    Returns:
        Configured SparkSession
    """
    if config is None:
        config = load_config()
    
    spark_config = get_spark_config(config)
    
    builder = SparkSession.builder.appName(app_name or spark_config['appName'])
    
    # Set Spark configuration
    for key, value in spark_config.items():
        if key != 'appName' and key != 'master':
            builder = builder.config(key, value)
    
    # Set master
    builder = builder.master(spark_config['master'])
    
    # Additional optimizations for Parquet
    builder = builder.config("spark.sql.parquet.compression.codec", "snappy")
    builder = builder.config("spark.sql.adaptive.enabled", "true")
    builder = builder.config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    
    # Disable Hadoop security for compatibility with newer Java versions
    builder = builder.config("spark.hadoop.fs.defaultFS", "file:///")
    builder = builder.config("spark.hadoop.mapreduce.framework.name", "local")
    
    spark = builder.getOrCreate()
    
    # Set log level to WARN to reduce noise
    spark.sparkContext.setLogLevel("WARN")
    
    return spark

