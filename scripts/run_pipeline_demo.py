#!/usr/bin/env python3
"""Demo pipeline using pandas (no Spark) for testing."""
import pandas as pd
import numpy as np
import os
from pathlib import Path
from typing import List, Dict
import json


def load_and_clean_data(data_dir: str, months: List[str]) -> pd.DataFrame:
    """Load and clean clickstream data."""
    print("Loading and cleaning data...")
    all_data = []
    
    for month in months:
        file_path = os.path.join(data_dir, f"clickstream-{month}.tsv")
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, sep="\t")
            df['month'] = month
            all_data.append(df)
    
    if not all_data:
        raise FileNotFoundError(f"No data files found in {data_dir}")
    
    df = pd.concat(all_data, ignore_index=True)
    
    # Clean data
    df = df.dropna(subset=['prev', 'curr', 'n'])
    df = df[df['n'] >= 10]  # Filter low-volume edges
    df['prev'] = df['prev'].str.strip()
    df['curr'] = df['curr'].str.strip()
    
    print(f"Loaded {len(df)} rows")
    return df


def calculate_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate baseline statistics."""
    print("Calculating baselines...")
    
    # Group by edge and calculate statistics
    baselines = df.groupby(['prev', 'curr', 'type']).agg({
        'n': ['median', 'mean', 'std']
    }).reset_index()
    
    baselines.columns = ['prev', 'curr', 'type', 'baseline_median', 'baseline_mean', 'baseline_std']
    
    # Calculate MAD (approximate)
    edge_data = df.groupby(['prev', 'curr', 'type', 'month'])['n'].sum().reset_index()
    edge_data = edge_data.merge(baselines[['prev', 'curr', 'type', 'baseline_median']], 
                                on=['prev', 'curr', 'type'])
    edge_data['abs_dev'] = abs(edge_data['n'] - edge_data['baseline_median'])
    mad = edge_data.groupby(['prev', 'curr', 'type'])['abs_dev'].mean().reset_index()
    mad.columns = ['prev', 'curr', 'type', 'baseline_mad']
    
    baselines = baselines.merge(mad, on=['prev', 'curr', 'type'])
    baselines = baselines.fillna({'baseline_median': 0, 'baseline_mean': 0, 
                                   'baseline_std': 0.01, 'baseline_mad': 0.01})
    
    print(f"Calculated baselines for {len(baselines)} edges")
    return baselines


def detect_traffic_spikes(df: pd.DataFrame, baselines: pd.DataFrame, 
                          target_month: str, z_threshold: float = 3.5, 
                          ratio_threshold: float = 10.0, anomaly_id_start: int = 0) -> pd.DataFrame:
    """Detect traffic spike anomalies."""
    print(f"Detecting traffic spikes for {target_month}...")
    
    # Filter to target month
    month_data = df[df['month'] == target_month].copy()
    edge_traffic = month_data.groupby(['prev', 'curr', 'type'])['n'].sum().reset_index()
    
    # Join with baselines
    edge_with_baseline = edge_traffic.merge(baselines, on=['prev', 'curr', 'type'], how='inner')
    
    # Calculate statistics
    edge_with_baseline['deviation_ratio'] = edge_with_baseline['n'] / (edge_with_baseline['baseline_median'] + 0.01)
    edge_with_baseline['z_score'] = (edge_with_baseline['n'] - edge_with_baseline['baseline_median']) / (edge_with_baseline['baseline_mad'] + 0.01)
    
    # Filter anomalies
    anomalies = edge_with_baseline[
        (edge_with_baseline['deviation_ratio'] >= ratio_threshold) |
        (abs(edge_with_baseline['z_score']) >= z_threshold)
    ].copy()
    
    # Calculate confidence
    z_norm = abs(anomalies['z_score']) / max(z_threshold, 1.0)
    ratio_norm = np.minimum(anomalies['deviation_ratio'] / max(ratio_threshold, 1.0), 10.0)
    combined = (z_norm + ratio_norm) / 2.0
    anomalies['confidence'] = 1.0 / (1.0 + np.exp(-5.0 * (combined - 0.5)))
    anomalies['confidence'] = np.clip(anomalies['confidence'], 0.0, 1.0)
    
    # Add metadata
    anomalies['anomaly_id'] = range(anomaly_id_start, anomaly_id_start + len(anomalies))
    anomalies['anomaly_type'] = 'traffic_spike'
    anomalies['month'] = target_month
    anomalies['description'] = anomalies.apply(
        lambda row: f"Traffic spike: {target_month} traffic is {row['deviation_ratio']:.1f}x baseline" 
        if row['deviation_ratio'] >= ratio_threshold 
        else f"Statistical anomaly: Z-score = {row['z_score']:.2f}", axis=1
    )
    
    # Select columns
    result = anomalies[['anomaly_id', 'month', 'prev', 'curr', 'type', 'n', 
                       'baseline_median', 'deviation_ratio', 'z_score', 
                       'anomaly_type', 'confidence', 'description']]
    
    print(f"Detected {len(result)} traffic spike anomalies")
    return result


def detect_mix_shifts(df: pd.DataFrame, target_month: str, 
                      baseline_months: List[str], anomaly_id_start: int = 0) -> pd.DataFrame:
    """Detect mix-shift anomalies."""
    print(f"Detecting mix-shifts for {target_month}...")
    
    # Calculate referrer distributions
    referrer_dist = df.groupby(['curr', 'prev', 'month'])['n'].sum().reset_index()
    total_traffic = referrer_dist.groupby(['curr', 'month'])['n'].sum().reset_index()
    total_traffic.columns = ['curr', 'month', 'total_n']
    referrer_dist = referrer_dist.merge(total_traffic, on=['curr', 'month'])
    referrer_dist['proportion'] = referrer_dist['n'] / referrer_dist['total_n']
    
    # Baseline distribution
    baseline_dist = referrer_dist[referrer_dist['month'].isin(baseline_months)]
    baseline_agg = baseline_dist.groupby(['curr', 'prev'])['n'].sum().reset_index()
    baseline_total = baseline_agg.groupby('curr')['n'].sum().reset_index()
    baseline_total.columns = ['curr', 'baseline_total']
    baseline_props = baseline_agg.merge(baseline_total, on='curr')
    baseline_props['baseline_proportion'] = baseline_props['n'] / baseline_props['baseline_total']
    
    # Get top referrer for baseline
    baseline_top = baseline_props.loc[baseline_props.groupby('curr')['baseline_proportion'].idxmax()]
    baseline_top = baseline_top[['curr', 'prev', 'baseline_proportion']]
    baseline_top.columns = ['curr', 'baseline_top_ref', 'baseline_top_prop']
    
    # Target distribution
    target_dist = referrer_dist[referrer_dist['month'] == target_month]
    if len(target_dist) == 0:
        return pd.DataFrame(columns=['anomaly_id', 'month', 'prev', 'curr', 'type', 'n',
                                     'baseline_median', 'deviation_ratio', 'z_score',
                                     'anomaly_type', 'confidence', 'description'])
    
    target_top = target_dist.loc[target_dist.groupby('curr')['proportion'].idxmax()]
    target_top = target_top[['curr', 'prev', 'proportion', 'total_n']]
    target_top.columns = ['curr', 'target_top_ref', 'target_top_prop', 'total_n']
    
    # Compare
    comparison = baseline_top.merge(target_top, on='curr', how='inner')
    comparison['top_ref_changed'] = comparison['baseline_top_ref'] != comparison['target_top_ref']
    comparison['top_prop_change'] = abs(comparison['target_top_prop'] - comparison['baseline_top_prop'])
    
    # Filter anomalies
    anomalies = comparison[
        (comparison['top_ref_changed'] == True) |
        (comparison['top_prop_change'] >= 0.2)
    ].copy()
    
    if len(anomalies) == 0:
        return pd.DataFrame(columns=['anomaly_id', 'month', 'prev', 'curr', 'type', 'n',
                                     'baseline_median', 'deviation_ratio', 'z_score',
                                     'anomaly_type', 'confidence', 'description'])
    
    # Add metadata
    anomalies['anomaly_id'] = range(anomaly_id_start, anomaly_id_start + len(anomalies))
    anomalies['anomaly_type'] = 'mix_shift'
    anomalies['month'] = target_month
    anomalies['prev'] = anomalies['target_top_ref']
    anomalies['type'] = 'link'
    anomalies['n'] = anomalies['total_n']
    anomalies['baseline_median'] = 0.0
    anomalies['deviation_ratio'] = anomalies['top_prop_change']
    anomalies['z_score'] = 0.0
    anomalies['confidence'] = np.where(
        anomalies['top_ref_changed'],
        0.9,
        np.minimum(anomalies['top_prop_change'] / 0.5, 1.0)
    )
    anomalies['description'] = anomalies.apply(
        lambda row: f"Top referrer changed from {row['baseline_top_ref']} to {row['target_top_ref']}"
        if row['top_ref_changed']
        else f"Top referrer proportion changed by {row['top_prop_change']:.2f}",
        axis=1
    )
    
    result = anomalies[['anomaly_id', 'month', 'prev', 'curr', 'type', 'n',
                        'baseline_median', 'deviation_ratio', 'z_score',
                        'anomaly_type', 'confidence', 'description']]
    
    print(f"Detected {len(result)} mix-shift anomalies")
    return result


def main():
    """Run the demo pipeline."""
    print("=" * 80)
    print("WIKIPEDIA CLICKSTREAM ANOMALY DETECTION - DEMO PIPELINE")
    print("=" * 80)
    print()
    
    # Configuration
    data_dir = "data/raw"
    output_dir = "data/anomalies"
    months = ["2023-06", "2023-07", "2023-08", "2023-09", "2023-10", "2023-11", "2023-12", "2024-01", "2024-02", "2024-03"]
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Step 1: Load and clean
    df = load_and_clean_data(data_dir, months)
    
    # Step 2: Calculate baselines
    baselines = calculate_baselines(df)
    
    # Step 3: Detect anomalies for each month (using previous months as baseline)
    all_anomalies = []
    anomaly_id_counter = 0
    
    # Need at least 3 months for baseline
    for i in range(3, len(months)):
        target_month = months[i]
        baseline_months = months[:i]  # Use all previous months as baseline
        
        print(f"\n--- Processing {target_month} (baseline: {baseline_months}) ---")
        
        # Detect traffic spikes
        traffic_spikes = detect_traffic_spikes(df, baselines, target_month, 
                                               anomaly_id_start=anomaly_id_counter)
        if len(traffic_spikes) > 0:
            all_anomalies.append(traffic_spikes)
            anomaly_id_counter += len(traffic_spikes)
        
        # Detect mix shifts
        mix_shifts = detect_mix_shifts(df, target_month, baseline_months,
                                      anomaly_id_start=anomaly_id_counter)
        if len(mix_shifts) > 0:
            all_anomalies.append(mix_shifts)
            anomaly_id_counter += len(mix_shifts)
    
    # Combine all anomalies
    if all_anomalies:
        all_anomalies = pd.concat(all_anomalies, ignore_index=True)
    else:
        all_anomalies = pd.DataFrame(columns=['anomaly_id', 'month', 'prev', 'curr', 'type', 'n',
                                                'baseline_median', 'deviation_ratio', 'z_score',
                                                'anomaly_type', 'confidence', 'description'])
    
    # Save
    output_path = os.path.join(output_dir, "anomalies.parquet")
    all_anomalies.to_parquet(output_path, index=False)
    
    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE!")
    print("=" * 80)
    print(f"\nTotal anomalies detected: {len(all_anomalies)}")
    print(f"  - Traffic spikes: {len(traffic_spikes)}")
    print(f"  - Mix shifts: {len(mix_shifts)}")
    print(f"\nResults saved to: {output_path}")
    print("\nTop 10 anomalies by confidence:")
    print(all_anomalies.nlargest(10, 'confidence')[['prev', 'curr', 'anomaly_type', 'confidence']].to_string())
    
    return all_anomalies


if __name__ == '__main__':
    main()

