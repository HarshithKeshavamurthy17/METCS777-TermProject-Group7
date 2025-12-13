#!/usr/bin/env python3
"""Add forecast columns to existing anomalies using pandas (faster)."""
import pandas as pd
import numpy as np
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.features.forecasting import build_edge_timeseries, fit_and_forecast

def add_forecasts_to_anomalies():
    """Add forecast data to existing anomalies.parquet."""
    print("=" * 80)
    print("ADDING FORECAST DATA TO EXISTING ANOMALIES")
    print("=" * 80)
    
    # Load existing anomalies
    anomalies_path = "data/anomalies/anomalies.parquet"
    if not os.path.exists(anomalies_path):
        print(f"Error: {anomalies_path} not found")
        return 1
    
    print(f"\nLoading existing anomalies from {anomalies_path}...")
    anomalies_df = pd.read_parquet(anomalies_path)
    print(f"Loaded {len(anomalies_df)} anomalies")
    
    # Load raw data to build time series
    print("\nLoading raw clickstream data...")
    months = ['2023-06', '2023-07', '2023-08', '2023-09', '2023-10', '2023-11', '2023-12', '2024-01', '2024-02', '2024-03']
    all_data = []
    
    for month in months:
        file_path = f"data/raw/clickstream-{month}.tsv"
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, sep="\t")
            df['month'] = month
            all_data.append(df)
    
    if not all_data:
        print("Error: No raw data files found")
        return 1
    
    raw_df = pd.concat(all_data, ignore_index=True)
    print(f"Loaded {len(raw_df)} rows of raw data")
    
    # Build time series
    print("\nBuilding time series...")
    edge_monthly = raw_df.groupby(['prev', 'curr', 'type', 'month'])['n'].sum().reset_index()
    
    timeseries_dict = {}
    for (prev, curr, edge_type), group in edge_monthly.groupby(['prev', 'curr', 'type']):
        group = group.sort_values('month')
        group['date'] = pd.to_datetime(group['month'] + '-01')
        timeseries_dict[(prev, curr, edge_type)] = group[['month', 'date', 'n']].reset_index(drop=True)
    
    print(f"Built time series for {len(timeseries_dict)} edges")
    
    # Generate forecasts for each anomaly
    print("\nGenerating forecasts for anomalies...")
    forecast_data = []
    min_history = 3
    
    for idx, row in anomalies_df.iterrows():
        prev = row['prev']
        curr = row['curr']
        edge_type = row.get('type', 'link')
        month = row['month']
        
        key = (prev, curr, edge_type)
        if key not in timeseries_dict:
            continue
        
        ts_df = timeseries_dict[key]
        if len(ts_df) < min_history:
            continue
        
        # Get actual value
        actual_row = ts_df[ts_df['month'] == month]
        if len(actual_row) == 0:
            continue
        
        actual_n = float(actual_row['n'].iloc[0])
        
        # Forecast
        try:
            forecast_result = fit_and_forecast(ts_df, horizon=1, model_type='auto')
            forecast_n = forecast_result['forecast_n']
            forecast_lower = forecast_result['forecast_lower']
            forecast_upper = forecast_result['forecast_upper']
            
            forecast_error = actual_n - forecast_n
            forecast_ratio = actual_n / (forecast_n + 1e-6)
            forecast_flag = (actual_n > forecast_upper) or (forecast_ratio >= 2.0)
            
            forecast_data.append({
                'idx': idx,
                'forecast_n': forecast_n,
                'forecast_lower': forecast_lower,
                'forecast_upper': forecast_upper,
                'forecast_error': forecast_error,
                'forecast_ratio': forecast_ratio,
                'forecast_flag': forecast_flag
            })
        except Exception as e:
            continue
    
    print(f"Generated forecasts for {len(forecast_data)} anomalies")
    
    # Merge forecast data
    forecast_df = pd.DataFrame(forecast_data)
    forecast_df = forecast_df.set_index('idx')
    
    # Add forecast columns to anomalies
    for col in ['forecast_n', 'forecast_lower', 'forecast_upper', 'forecast_error', 'forecast_ratio', 'forecast_flag']:
        anomalies_df[col] = forecast_df[col]
    
    # Fill NaN with defaults
    anomalies_df['forecast_n'] = anomalies_df['forecast_n'].fillna(0.0)
    anomalies_df['forecast_lower'] = anomalies_df['forecast_lower'].fillna(0.0)
    anomalies_df['forecast_upper'] = anomalies_df['forecast_upper'].fillna(0.0)
    anomalies_df['forecast_error'] = anomalies_df['forecast_error'].fillna(0.0)
    anomalies_df['forecast_ratio'] = anomalies_df['forecast_ratio'].fillna(1.0)
    anomalies_df['forecast_flag'] = anomalies_df['forecast_flag'].fillna(False)
    
    # Update anomaly_type for forecast spikes
    anomalies_df.loc[anomalies_df['forecast_flag'] == True, 'anomaly_type'] = \
        anomalies_df.loc[anomalies_df['forecast_flag'] == True, 'anomaly_type'].astype(str) + '_forecast_spike'
    
    # Save
    print(f"\nSaving updated anomalies with forecast data...")
    anomalies_df.to_parquet(anomalies_path, index=False)
    
    print(f"\n✅ SUCCESS!")
    print(f"Updated {len(anomalies_df)} anomalies")
    print(f"Anomalies with forecast_flag=True: {anomalies_df['forecast_flag'].sum()}")
    print(f"\n🔄 Restart dashboard to see forecast data:")
    print(f"   python scripts/start_dashboard_simple.py")
    
    return 0

if __name__ == '__main__':
    sys.exit(add_forecasts_to_anomalies())





