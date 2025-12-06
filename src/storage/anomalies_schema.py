"""Schema definitions for anomalies table."""
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType, BooleanType
)


ANOMALIES_SCHEMA = StructType([
    StructField("anomaly_id", StringType(), False),
    StructField("month", StringType(), False),
    StructField("prev", StringType(), True),
    StructField("curr", StringType(), True),
    StructField("type", StringType(), True),
    StructField("n", IntegerType(), True),
    StructField("baseline_median", DoubleType(), True),
    StructField("deviation_ratio", DoubleType(), True),
    StructField("z_score", DoubleType(), True),
    StructField("anomaly_type", StringType(), False),
    StructField("confidence", DoubleType(), True),
    StructField("description", StringType(), True),
    # Forecasting fields
    StructField("forecast_n", DoubleType(), True),
    StructField("forecast_lower", DoubleType(), True),
    StructField("forecast_upper", DoubleType(), True),
    StructField("forecast_error", DoubleType(), True),
    StructField("forecast_ratio", DoubleType(), True),
    StructField("forecast_flag", BooleanType(), True),
])


class AnomaliesStorage:
    """Handle storage of anomaly records."""
    
    def __init__(self, spark, output_path: str, format: str = "parquet"):
        """
        Initialize storage.
        
        Args:
            spark: SparkSession
            output_path: Path to store anomalies
            format: Storage format (parquet or delta)
        """
        self.spark = spark
        self.output_path = output_path
        self.format = format
    
    def save_anomalies(self, anomalies_df, mode: str = "append"):
        """
        Save anomalies to storage.
        
        Args:
            anomalies_df: DataFrame with anomalies
            mode: Write mode (append, overwrite, etc.)
        """
        print(f"Saving anomalies to {self.output_path}...")
        
        if self.format == "parquet":
            anomalies_df.write \
                .mode(mode) \
                .partitionBy("month", "anomaly_type") \
                .option("compression", "snappy") \
                .parquet(self.output_path)
        elif self.format == "delta":
            anomalies_df.write \
                .format("delta") \
                .mode(mode) \
                .partitionBy("month", "anomaly_type") \
                .save(self.output_path)
        else:
            raise ValueError(f"Unsupported format: {self.format}")
        
        print(f"Saved anomalies to {self.output_path}")
    
    def load_anomalies(self, filters: dict = None):
        """
        Load anomalies from storage.
        
        Args:
            filters: Dictionary of column: value filters
            
        Returns:
            DataFrame with anomalies
        """
        if self.format == "parquet":
            df = self.spark.read.parquet(self.output_path)
        elif self.format == "delta":
            df = self.spark.read.format("delta").load(self.output_path)
        else:
            raise ValueError(f"Unsupported format: {self.format}")
        
        if filters:
            from pyspark.sql.functions import col
            for col_name, value in filters.items():
                df = df.filter(col(col_name) == value)
        
        return df

