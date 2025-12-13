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
        # Get cluster centers and convert to serializable format (list of numpy arrays)
        centers_raw = self.model.clusterCenters()
        # Convert DenseVector to numpy array for serialization
        centers_list = []
        for c in centers_raw:
            # Handle both DenseVector and numpy array cases
            try:
                if hasattr(c, 'toArray') and not isinstance(c, np.ndarray):
                    # It's a DenseVector
                    centers_list.append(np.array(c.toArray()))
                else:
                    # Already a numpy array or can be converted directly
                    centers_list.append(np.array(c))
            except Exception:
                # Fallback: try direct conversion
                centers_list.append(np.array(c))
        
        # Broadcast centers for use in UDF
        from pyspark import SparkContext
        sc = self.spark.sparkContext
        centers_broadcast = sc.broadcast(centers_list)
        
        def get_distance(features, prediction):
            """Compute distance from features to assigned cluster center."""
            try:
                if features is None or prediction is None:
                return float('inf')
                
                # Get centers from broadcast variable
                centers = centers_broadcast.value
                cluster_id = int(prediction)
                
                if cluster_id < 0 or cluster_id >= len(centers):
                    return float('inf')
        
                # Convert features to numpy array - handle both DenseVector and numpy array
                if features is None:
                    return float('inf')
                elif isinstance(features, np.ndarray):
                    features_array = features
                elif hasattr(features, 'toArray'):
                    # It's a DenseVector
                    features_array = np.array(features.toArray())
                else:
                    # Try to convert to array
                    features_array = np.array(features)
                
            center = centers[cluster_id]
                
                # Ensure both are numpy arrays
                if not isinstance(features_array, np.ndarray):
                    features_array = np.array(features_array)
                if not isinstance(center, np.ndarray):
                    center = np.array(center)
                
                # Compute Euclidean distance
                return float(np.linalg.norm(features_array - center))
            except Exception as e:
                # Log error for debugging (but don't print in production)
                # Return inf on any error
                return float('inf')
        
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
        
        # Calculate distances to cluster centers
        # Get cluster centers and convert to serializable format
        centers_raw = self.model.clusterCenters()
        # Convert DenseVector to numpy array for serialization
        centers_list = []
        for c in centers_raw:
            # Handle both DenseVector and numpy array cases
            try:
                if hasattr(c, 'toArray') and not isinstance(c, np.ndarray):
                    # It's a DenseVector
                    centers_list.append(np.array(c.toArray()))
                else:
                    # Already a numpy array or can be converted directly
                    centers_list.append(np.array(c))
            except Exception:
                # Fallback: try direct conversion
                centers_list.append(np.array(c))
        
        # Broadcast centers for use in UDF
        from pyspark import SparkContext
        sc = self.spark.sparkContext
        centers_broadcast = sc.broadcast(centers_list)
        
        def compute_distance(features, cluster_id):
            """Compute distance from features to assigned cluster center."""
            try:
                if features is None or cluster_id is None:
                    return float('inf')
                
                # Get centers from broadcast variable
                centers = centers_broadcast.value
                cid = int(cluster_id)
                
                if cid < 0 or cid >= len(centers):
                    return float('inf')
                
                # Convert features to numpy array - handle both DenseVector and numpy array
            if features is None:
                    return float('inf')
                elif isinstance(features, np.ndarray):
                    features_array = features
                elif hasattr(features, 'toArray'):
                    # It's a DenseVector
                    features_array = np.array(features.toArray())
                else:
                    # Try to convert to array
                    features_array = np.array(features)
                
                center = centers[cid]
                
                # Ensure both are numpy arrays
                if not isinstance(features_array, np.ndarray):
                    features_array = np.array(features_array)
                if not isinstance(center, np.ndarray):
                    center = np.array(center)
                
                # Compute Euclidean distance
                return float(np.linalg.norm(features_array - center))
            except Exception as e:
                # Log error for debugging (but don't print in production)
                # Return inf on any error
                return float('inf')
        
        distance_udf = udf(compute_distance, DoubleType())
        predictions_with_distance = predictions.withColumn(
            "distance_to_center",
            distance_udf(col("features"), col("prediction"))
        )
        
        # Filter anomalies (high distance to center)
        anomalies = predictions_with_distance.filter(
            col("distance_to_center") >= self.distance_threshold
        )
        
        # features_prepared should already have prev, curr, type, baseline_median
        # But to be safe, ensure we have these columns
        # Check if we need to join (only if baseline_median is missing)
        if "baseline_median" not in anomalies.columns:
            # Need to join to get baseline_median - use alias to avoid ambiguity
            edge_info = features_df.select("prev", "curr", "type", col("baseline_median").alias("edge_baseline_median"))
            anomalies_alias = anomalies.alias("anom")
            edge_info_alias = edge_info.alias("edge")
            
            anomalies = anomalies_alias.join(
                edge_info_alias,
                (col("anom.prev") == col("edge.prev")) &
                (col("anom.curr") == col("edge.curr")) &
                (col("anom.type") == col("edge.type")),
                "left"
            ).withColumn("baseline_median", col("edge.edge_baseline_median"))
        
        # Get current month traffic - use baseline_median
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
            (lit(1.0) - (lit(0.5) * (lit(self.distance_threshold) / col("distance_to_center")))).cast(DoubleType())
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

