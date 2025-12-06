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
    
    def __init__(self, spark, output_path: str, processed_path: str = None, format: str = "parquet"):
        """
        Initialize storage.
        
        Args:
            spark: SparkSession
            output_path: Path to store anomalies
            processed_path: Path to processed clickstream data (optional, for history)
            format: Storage format (parquet or delta)
        """
        self.spark = spark
        self.output_path = output_path
        self.processed_path = processed_path
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

    def get_historical_data(self, prev: str, curr: str):
        """
        Get historical traffic data for an edge.
        
        Args:
            prev: Source page
            curr: Destination page
            
        Returns:
            List of dictionaries containing month and traffic count
        """
        if not self.processed_path:
            return []
            
        try:
            from pyspark.sql.functions import col, sum as spark_sum
            
            # Read processed data
            df = self.spark.read.parquet(self.processed_path)
            
            # Filter for the specific edge
            edge_df = df.filter((col("prev") == prev) & (col("curr") == curr))
            
            # Group by month and sum traffic
            history = edge_df.groupBy("month") \
                .agg(spark_sum("n").alias("n")) \
                .orderBy("month") \
                .collect()
                
            return [{"month": row.month, "n": row.n} for row in history]
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return []

    def get_referrer_data(self, curr: str):
        """
        Get referrer distribution history for a page.
        
        Args:
            curr: Destination page
            
        Returns:
            List of dictionaries containing month and referrer breakdown
        """
        if not self.processed_path:
            return []
            
        try:
            from pyspark.sql.functions import col, sum as spark_sum, collect_list, struct
            
            # Read processed data
            df = self.spark.read.parquet(self.processed_path)
            
            # Filter for the destination page
            page_df = df.filter(col("curr") == curr)
            
            # Calculate total traffic per month for normalization
            monthly_totals = page_df.groupBy("month") \
                .agg(spark_sum("n").alias("total_n"))
            
            # Get top referrers per month (or all if small)
            # We'll aggregate by month and prev
            referrer_counts = page_df.groupBy("month", "prev") \
                .agg(spark_sum("n").alias("n"))
            
            # Join to get proportions
            referrer_props = referrer_counts.join(monthly_totals, "month") \
                .withColumn("proportion", col("n") / col("total_n"))
            
            # Collect results
            # We want: [{month: '...', referrers: [{prev: '...', proportion: ...}, ...]}]
            results = referrer_props.groupBy("month") \
                .agg(collect_list(struct("prev", "proportion")).alias("referrers")) \
                .orderBy("month") \
                .collect()
                
            return [
                {
                    "month": row.month,
                    "referrers": [
                        {"prev": r.prev, "proportion": r.proportion} 
                        for r in row.referrers
                    ]
                }
                for row in results
            ]
        except Exception as e:
            print(f"Error fetching referrer data: {e}")
            return []

