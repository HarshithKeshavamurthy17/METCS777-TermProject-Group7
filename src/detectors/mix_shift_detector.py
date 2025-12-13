"""Mix-shift anomaly detector using distribution divergence."""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, lit, monotonically_increasing_id, collect_list, struct,
    when, abs, sum as spark_sum, max as spark_max, least
)
from pyspark.sql.types import StringType, DoubleType
from pyspark.sql.window import Window
import numpy as np
from scipy.spatial.distance import jensenshannon


class MixShiftDetector:
    """Detect mix-shift anomalies using referrer distribution changes."""
    
    def __init__(
        self,
        spark: SparkSession,
        js_divergence_threshold: float = 0.3,
        min_referrers: int = 3,
        top_referrer_change_threshold: float = 0.2
    ):
        """
        Initialize mix-shift detector.
        
        Args:
            spark: SparkSession
            js_divergence_threshold: Jensen-Shannon divergence threshold
            min_referrers: Minimum number of referrers to consider
            top_referrer_change_threshold: Threshold for top referrer change
        """
        self.spark = spark
        self.js_divergence_threshold = js_divergence_threshold
        self.min_referrers = min_referrers
        self.top_referrer_change_threshold = top_referrer_change_threshold
    
    def calculate_js_divergence(self, p: np.ndarray, q: np.ndarray) -> float:
        """
        Calculate Jensen-Shannon divergence.
        
        Args:
            p: Probability distribution 1
            q: Probability distribution 2
            
        Returns:
            JS divergence (0 to 1)
        """
        # Normalize
        p = p / (p.sum() + 1e-10)
        q = q / (q.sum() + 1e-10)
        
        # Calculate JS divergence
        m = (p + q) / 2.0
        js = 0.5 * jensenshannon(p, q)
        
        return float(js)
    
    def detect(self, referrer_dist: DataFrame, target_month: str, baseline_months: list) -> DataFrame:
        """
        Detect mix-shift anomalies by comparing referrer distributions.
        
        Args:
            referrer_dist: DataFrame with referrer distributions (curr, prev, month, proportion)
            target_month: Month to analyze
            baseline_months: List of months to use as baseline
            
        Returns:
            DataFrame with anomaly records
        """
        print(f"Detecting mix-shift anomalies for {target_month}...")
        
        # Filter to relevant months
        relevant_months = baseline_months + [target_month]
        dist_filtered = referrer_dist.filter(col("month").isin(relevant_months))
        
        # Calculate baseline distribution (average over baseline months)
        baseline_dist = dist_filtered.filter(col("month").isin(baseline_months)) \
            .groupBy("curr", "prev") \
            .agg(spark_sum("n").alias("baseline_n"))
        
        baseline_total = baseline_dist.groupBy("curr") \
            .agg(spark_sum("baseline_n").alias("baseline_total"))
        
        baseline_props = baseline_dist.join(baseline_total, "curr") \
            .withColumn("baseline_proportion", col("baseline_n") / col("baseline_total")) \
            .select("curr", "prev", "baseline_proportion")
        
        # Get target month distribution
        target_dist = dist_filtered.filter(col("month") == target_month) \
            .select("curr", "prev", "proportion", "n", "total_n")
        
        # Join and calculate divergence
        comparison = target_dist.join(baseline_props, ["curr", "prev"], "outer") \
            .fillna(0.0, subset=["proportion", "baseline_proportion"])
        
        # Group by curr to calculate JS divergence
        # We need to collect referrers per curr page
        curr_referrers = comparison.groupBy("curr") \
            .agg(
                collect_list(struct("prev", "proportion")).alias("target_dist"),
                collect_list(struct("prev", "baseline_proportion")).alias("baseline_dist"),
                spark_sum("n").alias("total_n")
            )
        
        # Calculate JS divergence using UDF
        from pyspark.sql.functions import udf
        
        def compute_js_div(target_list, baseline_list):
            """Compute JS divergence from lists."""
            # Convert to dictionaries
            target_dict = {r.prev: r.proportion for r in target_list if hasattr(r, 'prev')}
            baseline_dict = {r.prev: r.baseline_proportion for r in baseline_list if hasattr(r, 'prev')}
            
            # Get all referrers
            all_refs = set(target_dict.keys()) | set(baseline_dict.keys())
            if len(all_refs) < self.min_referrers:
                return 0.0
            
            # Create aligned arrays
            p = np.array([target_dict.get(ref, 0.0) for ref in sorted(all_refs)])
            q = np.array([baseline_dict.get(ref, 0.0) for ref in sorted(all_refs)])
            
            return self.calculate_js_divergence(p, q)
        
        js_udf = udf(compute_js_div, DoubleType())
        
        # Alternative: simpler approach using top referrer change
        # Get top referrer for baseline
        baseline_top = baseline_props.groupBy("curr") \
            .agg(spark_max("baseline_proportion").alias("baseline_top_prop"))
        
        # Use DataFrame aliases to avoid ambiguous column references
        baseline_props_alias = baseline_props.alias("bp")
        baseline_top_alias = baseline_top.alias("bt")
        
        baseline_top_ref = baseline_props_alias.join(
            baseline_top_alias,
            (col("bp.curr") == col("bt.curr")) &
            (col("bp.baseline_proportion") == col("bt.baseline_top_prop"))
        ).select(col("bp.curr").alias("curr"), col("bp.prev").alias("baseline_top_ref"), col("bt.baseline_top_prop"))
        
        # Get top referrer for target
        target_top = target_dist.groupBy("curr") \
            .agg(spark_max("proportion").alias("target_top_prop"))
        
        # Use DataFrame aliases to avoid ambiguous column references
        target_dist_alias = target_dist.alias("td")
        target_top_alias = target_top.alias("tt")
        
        target_top_ref = target_dist_alias.join(
            target_top_alias,
            (col("td.curr") == col("tt.curr")) &
            (col("td.proportion") == col("tt.target_top_prop"))
        ).select(col("td.curr").alias("curr"), col("td.prev").alias("target_top_ref"), col("tt.target_top_prop"), col("td.total_n"))
        
        # Compare top referrers
        top_comparison = baseline_top_ref.join(target_top_ref, "curr", "inner") \
            .withColumn(
                "top_ref_changed",
                col("baseline_top_ref") != col("target_top_ref")
            ).withColumn(
                "top_prop_change",
                abs(col("target_top_prop") - col("baseline_top_prop"))
            )
        
        # Filter anomalies
        anomalies = top_comparison.filter(
            (col("top_ref_changed") == True) |
            (col("top_prop_change") >= self.top_referrer_change_threshold)
        )
        
        # Add anomaly metadata
        anomalies = anomalies.withColumn(
            "anomaly_id",
            monotonically_increasing_id().cast(StringType())
        ).withColumn(
            "anomaly_type",
            lit("mix_shift")
        ).withColumn(
            "month",
            lit(target_month)
        ).withColumn(
            "prev",
            col("target_top_ref")
        ).withColumn(
            "curr",
            col("curr")
        ).withColumn(
            "type",
            lit("link")  # Default
        ).withColumn(
            "n",
            col("total_n")
        ).withColumn(
            "baseline_median",
            lit(0.0)  # Not applicable for mix-shift
        ).withColumn(
            "deviation_ratio",
            col("top_prop_change")
        ).withColumn(
            "z_score",
            lit(0.0)  # Not applicable
        ).withColumn(
            "confidence",
            when(col("top_ref_changed"), 0.9)
            .otherwise(
                # Linear interpolation: map [0.2, 1.0] to [0.5, 1.0]
                # Formula: 0.5 + 0.5 * (change - 0.2) / 0.8
                least(lit(0.5) + lit(0.5) * (col("top_prop_change") - lit(0.2)) / lit(0.8), lit(1.0))
            )
        ).withColumn(
            "description",
            when(
                col("top_ref_changed"),
                lit(f"Top referrer changed from {col('baseline_top_ref')} to {col('target_top_ref')}")
            ).otherwise(
                lit(f"Top referrer proportion changed by {col('top_prop_change')}")
            )
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
        print(f"Detected {count} mix-shift anomalies for {target_month}")
        
        return result

