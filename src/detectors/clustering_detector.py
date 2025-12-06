"""Clustering-based anomaly detector using K-means."""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, lit, monotonically_increasing_id, udf, array
from pyspark.sql.types import DoubleType, StringType, ArrayType
from pyspark.ml.clustering import KMeans
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml import Pipeline
from typing import List
import numpy as np


class ClusteringDetector:
    """Detect navigation-edge anomalies using K-means clustering."""
    
    def __init__(
        self,
        spark: SparkSession,
        n_clusters: int = 50,
        distance_threshold_percentile: float = 95.0,
        max_iterations: int = 100,
        seed: int = 42
    ):
        """
        Initialize clustering detector.
        
        Args:
            spark: SparkSession
            n_clusters: Number of clusters for K-means
            distance_threshold_percentile: Percentile for distance threshold
            max_iterations: Max iterations for K-means
            seed: Random seed
        """
        self.spark = spark
        self.n_clusters = n_clusters
        self.distance_threshold_percentile = distance_threshold_percentile
        self.max_iterations = max_iterations
        self.seed = seed
        self.model = None
        self.distance_threshold = None
    
    def prepare_features(self, features_df: DataFrame, months: List[str]) -> DataFrame:
        """
        Prepare feature vectors for clustering.
        
        Args:
            features_df: DataFrame with edge features
            months: List of month columns to use as features
            
        Returns:
            DataFrame with assembled feature vectors
        """
        print("Preparing feature vectors for clustering...")
        
        # Select feature columns
        feature_cols = [col(month) for month in months] + \
                      [col("baseline_median"), col("baseline_mean")] + \
                      [col(f"ratio_{month}") for month in months] + \
                      [col("type_link"), col("type_external"), col("type_other")]
        
        # Filter out rows with null features
        features_clean = features_df.filter(
            col("baseline_median").isNotNull()
        )
        
        # Only use columns that exist
        available_cols = []
        for month in months:
            if month in features_clean.columns:
                available_cols.append(month)
            if f"ratio_{month}" in features_clean.columns:
                available_cols.append(f"ratio_{month}")
        
        # Add baseline columns if they exist
        for col_name in ["baseline_median", "baseline_mean"]:
            if col_name in features_clean.columns:
                available_cols.append(col_name)
        
        # Add type columns if they exist
        for type_col in ["type_link", "type_external", "type_other"]:
            if type_col in features_clean.columns:
                available_cols.append(type_col)
        
        if not available_cols:
            raise ValueError("No feature columns available for clustering")
        
        # Assemble features into vector
        assembler = VectorAssembler(
            inputCols=available_cols,
            outputCol="features_raw",
            handleInvalid="skip"
        )
        
        features_vector = assembler.transform(features_clean)
        
        # Scale features
        scaler = StandardScaler(
            inputCol="features_raw",
            outputCol="features",
            withStd=True,
            withMean=True
        )
        
        scaler_model = scaler.fit(features_vector)
        features_scaled = scaler_model.transform(features_vector)
        
        print(f"Prepared {features_scaled.count()} feature vectors")
        
        return features_scaled
    
    def fit(self, features_df: DataFrame, months: List[str]) -> None:
        """
        Fit K-means model on feature vectors.
        
        Args:
            features_df: DataFrame with edge features
            months: List of months
        """
        print(f"Fitting K-means model with {self.n_clusters} clusters...")
        
        # Prepare features
        features_prepared = self.prepare_features(features_df, months)
        
        # Fit K-means
        kmeans = KMeans(
            k=self.n_clusters,
            maxIter=self.max_iterations,
            seed=self.seed,
            featuresCol="features"
        )
        
        self.model = kmeans.fit(features_prepared)
        
        # Calculate distances to cluster centers
        predictions = self.model.transform(features_prepared)
        
        # Calculate distance threshold
        # Distance is stored in the prediction, but we need to compute it manually
        from pyspark.ml.linalg import Vectors
        
        def compute_distance(features, center):
            """Compute Euclidean distance."""
            if features is None or center is None:
                return float('inf')
            return float(np.linalg.norm(features - center))
        
        # Get cluster centers
        centers = self.model.clusterCenters()
        
        # For each point, compute distance to its assigned center
        def get_distance(features, cluster_id):
            center = centers[int(cluster_id)]
            return compute_distance(features, center)
        
        distance_udf = udf(get_distance, DoubleType())
        predictions_with_distance = predictions.withColumn(
            "distance_to_center",
            distance_udf(col("features"), col("prediction"))
        )
        
        # Calculate percentile threshold
        distances = [row.distance_to_center for row in predictions_with_distance.select("distance_to_center").collect()]
        self.distance_threshold = np.percentile(distances, self.distance_threshold_percentile)
        
        print(f"Fitted model. Distance threshold (p{self.distance_threshold_percentile}): {self.distance_threshold:.4f}")
    
    def detect(self, features_df: DataFrame, months: List[str], target_month: str) -> DataFrame:
        """
        Detect navigation-edge anomalies.
        
        Args:
            features_df: DataFrame with edge features
            months: List of months
            target_month: Month to analyze
            
        Returns:
            DataFrame with anomaly records
        """
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        print(f"Detecting navigation-edge anomalies for {target_month}...")
        
        # Prepare features
        features_prepared = self.prepare_features(features_df, months)
        
        # Get predictions
        predictions = self.model.transform(features_prepared)
        
        # Calculate distances (simplified - using cluster assignment)
        # In production, compute actual Euclidean distance
        from pyspark.ml.linalg import Vectors
        
        centers = self.model.clusterCenters()
        
        def compute_distance(features, cluster_id):
            if features is None:
                return float('inf')
            center = centers[int(cluster_id)]
            return float(np.linalg.norm(features - center))
        
        distance_udf = udf(compute_distance, DoubleType())
        predictions_with_distance = predictions.withColumn(
            "distance_to_center",
            distance_udf(col("features"), col("prediction"))
        )
        
        # Filter anomalies (high distance to center)
        anomalies = predictions_with_distance.filter(
            col("distance_to_center") >= self.distance_threshold
        )
        
        # Join back to get original edge info
        # features_df already has these columns, and they are preserved in predictions
        # But just in case, we select them. 
        # We drop baseline_median from edge_info to avoid ambiguity if it exists in anomalies
        edge_info = features_df.select("prev", "curr", "type")
        anomalies = anomalies.join(edge_info, ["prev", "curr", "type"], "left")
        
        # Get current month traffic
        # This would need to be joined from the original data
        # For now, use baseline_median as proxy
        anomalies = anomalies.withColumn("n", col("baseline_median"))
        
        # Add anomaly metadata
        anomalies = anomalies.withColumn(
            "anomaly_id",
            monotonically_increasing_id().cast(StringType())
        ).withColumn(
            "anomaly_type",
            lit("navigation_edge")
        ).withColumn(
            "month",
            lit(target_month)
        ).withColumn(
            "deviation_ratio",
            lit(1.0)  # Placeholder
        ).withColumn(
            "z_score",
            lit(0.0)  # Placeholder
        ).withColumn(
            "confidence",
            (col("distance_to_center") / lit(self.distance_threshold)).cast(DoubleType())
        ).withColumn(
            "description",
            lit(f"Navigation edge anomaly: distance to cluster center = {col('distance_to_center')}")
        )
        
        # Select final columns
        result = anomalies.select(
            "anomaly_id",
            "month",
            "prev",
            "curr",
            "type",
            "n",
            "baseline_median",
            "deviation_ratio",
            "z_score",
            "anomaly_type",
            "confidence",
            "description"
        )
        
        count = result.count()
        print(f"Detected {count} navigation-edge anomalies for {target_month}")
        
        return result

