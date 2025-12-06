"""Clickstream data loading and cleaning."""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, trim, lower, when, regexp_replace
from pyspark.sql.types import StringType, IntegerType, StructType, StructField
from typing import List, Optional
import os


class ClickstreamLoader:
    """Load and clean Wikipedia clickstream data."""
    
    SCHEMA = StructType([
        StructField("prev", StringType(), True),
        StructField("curr", StringType(), True),
        StructField("type", StringType(), True),
        StructField("n", IntegerType(), True),
    ])
    
    def __init__(self, spark: SparkSession, min_transitions: int = 10):
        """
        Initialize loader.
        
        Args:
            spark: SparkSession
            min_transitions: Minimum number of transitions to keep an edge
        """
        self.spark = spark
        self.min_transitions = min_transitions
    
    def load_month(self, file_path: str, month: str) -> DataFrame:
        """
        Load a single month's clickstream data.
        
        Args:
            file_path: Path to TSV file
            month: Month identifier (e.g., "2023-09")
            
        Returns:
            DataFrame with added 'month' column
        """
        print(f"Loading clickstream data for {month} from {file_path}")
        
        df = self.spark.read \
            .option("sep", "\t") \
            .option("header", "true") \
            .schema(self.SCHEMA) \
            .csv(file_path)
        
        # Add month column
        from pyspark.sql.functions import lit
        if "month" not in [f.name for f in df.schema.fields]:
            df = df.withColumn("month", lit(month))
        else:
            df = df.withColumn("month", lit(month))
        
        return df
    
    def load_multiple_months(self, file_paths: List[tuple]) -> DataFrame:
        """
        Load multiple months of data.
        
        Args:
            file_paths: List of (file_path, month) tuples
            
        Returns:
            Combined DataFrame
        """
        dfs = []
        for file_path, month in file_paths:
            if os.path.exists(file_path):
                df = self.load_month(file_path, month)
                dfs.append(df)
            else:
                print(f"Warning: File not found: {file_path}")
        
        if not dfs:
            raise ValueError("No valid files found to load")
        
        # Union all dataframes
        combined_df = dfs[0]
        for df in dfs[1:]:
            combined_df = combined_df.unionByName(df, allowMissingColumns=True)
        
        return combined_df
    
    def clean(self, df: DataFrame) -> DataFrame:
        """
        Clean and normalize clickstream data.
        
        Args:
            df: Raw clickstream DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        print("Cleaning clickstream data...")
        
        # Remove nulls in critical columns
        df = df.filter(
            col("prev").isNotNull() &
            col("curr").isNotNull() &
            col("n").isNotNull() &
            (col("n") > 0)
        )
        
        # Trim whitespace
        df = df.withColumn("prev", trim(col("prev")))
        df = df.withColumn("curr", trim(col("curr")))
        df = df.withColumn("type", trim(col("type")))
        
        # Filter out very low-volume edges
        df = df.filter(col("n") >= self.min_transitions)
        
        # Normalize page titles (lowercase for consistency, but preserve original)
        df = df.withColumn("prev_normalized", lower(col("prev")))
        df = df.withColumn("curr_normalized", lower(col("curr")))
        
        # Clean special characters in page titles (keep as-is for now, but can normalize)
        # Handle special buckets like "other-search", "other-external", etc.
        df = df.withColumn(
            "prev_category",
            when(col("prev").startswith("other-"), col("prev"))
            .when(col("prev") == "null", "direct")
            .otherwise("page")
        )
        
        df = df.withColumn(
            "curr_category",
            when(col("curr").startswith("other-"), col("curr"))
            .when(col("curr") == "null", "direct")
            .otherwise("page")
        )
        
        print(f"Cleaned data: {df.count()} rows")
        
        return df
    
    def save_cleaned(self, df: DataFrame, output_path: str, format: str = "parquet"):
        """
        Save cleaned data to storage.
        
        Args:
            df: Cleaned DataFrame
            output_path: Output directory path
            format: Output format (parquet or delta)
        """
        print(f"Saving cleaned data to {output_path} in {format} format...")
        
        if format == "parquet":
            df.write \
                .mode("overwrite") \
                .partitionBy("month") \
                .option("compression", "snappy") \
                .parquet(output_path)
        elif format == "delta":
            df.write \
                .format("delta") \
                .mode("overwrite") \
                .partitionBy("month") \
                .save(output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        print(f"Saved cleaned data to {output_path}")

