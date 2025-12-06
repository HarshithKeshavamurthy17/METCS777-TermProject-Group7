"""Explainability features for anomaly analysis."""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, collect_list, struct, when, lit
from typing import Dict, List, Optional
import pandas as pd


class ExplainabilityCalculator:
    """Calculate explainability features for anomalies."""
    
    def __init__(self, spark: SparkSession):
        """Initialize explainability calculator."""
        self.spark = spark
    
    def get_anomaly_timeseries(
        self,
        df: DataFrame,
        prev: str,
        curr: str,
        edge_type: str,
        months: List[str]
    ) -> pd.DataFrame:
        """
        Get time-series data for a specific edge.
        
        Args:
            df: Clickstream DataFrame
            prev: Previous page
            curr: Current page
            edge_type: Edge type
            months: List of months
            
        Returns:
            DataFrame with month, n, baseline_median, baseline_mad, z_score, etc.
        """
        # Filter to this edge
        edge_data = df.filter(
            (col("prev") == prev) &
            (col("curr") == curr) &
            (col("type") == edge_type)
        )
        
        # Select relevant columns
        cols = ['month', 'n', 'baseline_median', 'baseline_mad', 
                'deviation_ratio', 'z_score', 'forecast_n', 
                'forecast_lower', 'forecast_upper']
        
        # Only select columns that exist
        available_cols = [c for c in cols if c in edge_data.columns]
        edge_data = edge_data.select(['month'] + available_cols)
        
        # Convert to pandas
        pdf = edge_data.toPandas()
        pdf = pdf.sort_values('month')
        
        return pdf
    
    def get_referrer_distribution(
        self,
        referrer_dist: DataFrame,
        curr: str,
        months: List[str]
    ) -> pd.DataFrame:
        """
        Get referrer distribution for a page over months.
        
        Args:
            referrer_dist: Referrer distribution DataFrame
            curr: Current page
            months: List of months
            
        Returns:
            DataFrame with month, prev, proportion, n
        """
        # Filter to this page
        page_dist = referrer_dist.filter(col("curr") == curr)
        
        # Filter to relevant months
        page_dist = page_dist.filter(col("month").isin(months))
        
        # Convert to pandas
        pdf = page_dist.toPandas()
        pdf = pdf.sort_values(['month', 'proportion'], ascending=[True, False])
        
        return pdf
    
    def generate_explanation(
        self,
        anomaly: Dict,
        timeseries: pd.DataFrame,
        referrer_dist: Optional[pd.DataFrame] = None
    ) -> str:
        """
        Generate human-readable explanation for an anomaly.
        
        Args:
            anomaly: Anomaly record dictionary
            timeseries: Time-series data for the edge
            referrer_dist: Referrer distribution data (optional)
            
        Returns:
            Explanation string
        """
        parts = []
        
        # Get anomaly type
        anomaly_type = anomaly.get('anomaly_type', 'unknown')
        prev = anomaly.get('prev', 'Unknown')
        curr = anomaly.get('curr', 'Unknown')
        month = anomaly.get('month', 'Unknown')
        n = anomaly.get('n', 0)
        baseline_median = anomaly.get('baseline_median', 0)
        deviation_ratio = anomaly.get('deviation_ratio', 0)
        confidence = anomaly.get('confidence', 0)
        
        # Main explanation
        parts.append(f"This anomaly detected in {month} shows unusual traffic from '{prev}' to '{curr}'.")
        
        # Traffic spike explanation
        if anomaly_type == 'traffic_spike' or deviation_ratio > 10:
            parts.append(
                f"Traffic spiked to {n:,} transitions ({deviation_ratio:.1f}x the baseline median of {baseline_median:.0f})."
            )
        
        # Statistical explanation
        z_score = anomaly.get('z_score', 0)
        if abs(z_score) > 3.5:
            parts.append(
                f"Statistical analysis shows a robust Z-score of {z_score:.2f}, indicating a significant deviation from normal patterns."
            )
        
        # Forecast explanation
        if 'forecast_n' in anomaly and anomaly.get('forecast_flag', False):
            forecast_n = anomaly.get('forecast_n', 0)
            forecast_upper = anomaly.get('forecast_upper', 0)
            parts.append(
                f"Time-series forecasting predicted {forecast_n:.0f} transitions (upper bound: {forecast_upper:.0f}), "
                f"but actual traffic was {n:,}, exceeding the forecast."
            )
        
        # Mix shift explanation
        if anomaly_type == 'mix_shift':
            parts.append(
                "The referrer distribution for this page changed significantly, indicating a shift in how users "
                "are discovering or navigating to this content."
            )
        
        # GNN explanation
        if anomaly.get('gnn_flag', False):
            gnn_score = anomaly.get('gnn_score', 0)
            parts.append(
                f"Graph-based analysis flagged this edge as anomalous (score: {gnn_score:.3f}), suggesting "
                "unusual navigation patterns in the Wikipedia link graph."
            )
        
        # Confidence
        parts.append(f"Overall confidence: {confidence:.1%}")
        
        return " ".join(parts)
    
    def get_signals(self, anomaly: Dict) -> List[str]:
        """
        Extract all signals that fired for an anomaly.
        
        Args:
            anomaly: Anomaly record dictionary
            
        Returns:
            List of signal names
        """
        signals = []
        
        # Check each detector
        anomaly_type = anomaly.get('anomaly_type', '')
        if anomaly_type == 'traffic_spike':
            signals.append('Traffic Spike')
        elif anomaly_type == 'mix_shift':
            signals.append('Mix Shift')
        elif anomaly_type == 'navigation_edge':
            signals.append('Navigation Edge')
        
        # Check forecast flag
        if anomaly.get('forecast_flag', False):
            signals.append('Forecast Deviation')
        
        # Check GNN flag
        if anomaly.get('gnn_flag', False):
            signals.append('GNN Outlier')
        
        # Check statistical thresholds
        deviation_ratio = anomaly.get('deviation_ratio', 0)
        if deviation_ratio >= 10:
            signals.append('High Deviation Ratio')
        
        z_score = abs(anomaly.get('z_score', 0))
        if z_score >= 3.5:
            signals.append('MAD-Z Score')
        
        return signals if signals else ['Anomaly Detected']



