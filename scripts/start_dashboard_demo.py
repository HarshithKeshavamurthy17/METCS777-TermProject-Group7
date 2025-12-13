#!/usr/bin/env python3
"""Start dashboard with demo data (pandas-based)."""
import pandas as pd
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
from pathlib import Path

# Set template folder to the correct location
template_dir = Path(__file__).parent.parent / 'src' / 'dashboard' / 'templates'
app = Flask(__name__, template_folder=str(template_dir))
CORS(app)

# Load anomalies using Spark (supports partitioned parquet) - LOAD ALL DATA
anomalies_df = None
raw_data_df = None
anomalies_path = "data/anomalies"
processed_path = "data/processed"

print("=" * 80)
print("LOADING FULL DATASET FOR DASHBOARD")
print("=" * 80)

try:
    from pyspark.sql import SparkSession
    from src.utils.config import load_config
    from src.utils.spark_session import create_spark_session
    from src.storage.anomalies_schema import AnomaliesStorage
    
    # Initialize Spark and load ALL anomalies
    config = load_config()
    spark = create_spark_session(config)
    
    # Check if anomalies directory exists before trying to load
    anomalies_dir_exists = os.path.exists(anomalies_path)
    has_partitions = False
    if anomalies_dir_exists:
        # Check if it has partition subdirectories (month=, anomaly_type=, etc.)
        try:
            subdirs = [d for d in os.listdir(anomalies_path) if os.path.isdir(os.path.join(anomalies_path, d))]
            has_partitions = any('=' in d for d in subdirs)  # Partitioned format has "month=2023-11" style dirs
        except:
            pass
    
    if anomalies_dir_exists and (has_partitions or any(f.endswith('.parquet') for f in os.listdir(anomalies_path) if os.path.isfile(os.path.join(anomalies_path, f)))):
        try:
            storage = AnomaliesStorage(spark, anomalies_path, format='parquet')
            # Load ALL anomalies from all partitions
            df = storage.load_anomalies()
            anomalies_df = df.toPandas()
        except Exception as load_error:
            print(f"⚠ Warning: Could not load anomalies from {anomalies_path}: {load_error}")
            print("   The directory exists but may be empty or corrupted.")
            print("   Run 'python run_pipeline.py' to generate anomalies.")
            anomalies_df = pd.DataFrame()
else:
        print(f"⚠ Warning: Anomalies directory not found at {anomalies_path}")
        print("   Run 'python run_pipeline.py' first to generate anomalies.")
        print("   The dashboard will start but show no anomalies.")
    anomalies_df = pd.DataFrame()
    
    print(f"✓ Loaded {len(anomalies_df)} anomalies from partitioned parquet files")
    if not anomalies_df.empty:
        months = sorted(anomalies_df['month'].unique())
        print(f"✓ Months with anomalies: {months}")
        print(f"✓ Anomaly types: {sorted(anomalies_df['anomaly_type'].unique())}")
        print(f"✓ By month: {anomalies_df.groupby('month').size().to_dict()}")
        print(f"✓ By type: {anomalies_df.groupby('anomaly_type').size().to_dict()}")
        
        # Check deviation_ratio distribution
        if 'deviation_ratio' in anomalies_df.columns:
            high_dev = anomalies_df[anomalies_df['deviation_ratio'] > 5.0]
            print(f"\n📊 DEVIATION RATIO STATISTICS:")
            print(f"  Anomalies with deviation_ratio > 5.0: {len(high_dev)}")
            print(f"  Max deviation_ratio: {anomalies_df['deviation_ratio'].max():.2f}")
            print(f"  Min deviation_ratio: {anomalies_df['deviation_ratio'].min():.2f}")
            print(f"  Avg deviation_ratio: {anomalies_df['deviation_ratio'].mean():.2f}")
    
    # Load ALL processed data for timeseries
    if os.path.exists(processed_path):
        try:
            processed_df = spark.read.parquet(processed_path)
            raw_data_df = processed_df.toPandas()
            print(f"✓ Loaded {len(raw_data_df)} rows of processed data for timeseries")
            if not raw_data_df.empty:
                processed_months = sorted(raw_data_df['month'].unique())
                print(f"✓ Processed data months: {processed_months}")
        except Exception as e:
            print(f"⚠ Warning: Could not load processed data: {e}")
            raw_data_df = pd.DataFrame()
    else:
        print(f"⚠ Warning: Processed data directory not found at {processed_path}")
        raw_data_df = pd.DataFrame()
    
    # ALSO try to load raw TSV files if processed data is limited
    if raw_data_df is None or raw_data_df.empty or len(raw_data_df['month'].unique()) < 3:
        print("\n⚠ Limited processed data - loading raw TSV files for full timeseries...")
        raw_data_dir = config.get('data', {}).get('raw_data_dir', 'data/raw')
        if os.path.exists(raw_data_dir):
            all_raw_data = []
            months = ["2023-06", "2023-07", "2023-08", "2023-09", "2023-10", "2023-11", "2023-12", "2024-01", "2024-02", "2024-03"]
            for month in months:
                file_path = os.path.join(raw_data_dir, f"clickstream-{month}.tsv")
                if os.path.exists(file_path):
                    try:
                        df_month = pd.read_csv(file_path, sep="\t", nrows=10000)  # Limit for performance
                        df_month['month'] = month
                        all_raw_data.append(df_month)
                        print(f"  ✓ Loaded {month}: {len(df_month)} rows")
                    except Exception as e:
                        print(f"  ⚠ Could not load {month}: {e}")
            
            if all_raw_data:
                raw_data_df = pd.concat(all_raw_data, ignore_index=True)
                print(f"✓ Loaded {len(raw_data_df)} total rows from raw TSV files")
                print(f"✓ Raw data months: {sorted(raw_data_df['month'].unique())}")
    
    spark.stop()
    print("=" * 80)
    
except Exception as e:
    print(f"⚠ Warning: Could not load anomalies using Spark: {e}")
    print("Falling back to single file check...")
    
    # Fallback to single file
    single_file = "data/anomalies/anomalies.parquet"
    if os.path.exists(single_file):
        anomalies_df = pd.read_parquet(single_file)
        print(f"✓ Loaded {len(anomalies_df)} anomalies from single file")
    else:
        print(f"⚠ Warning: Anomalies file not found at {single_file}")
        anomalies_df = pd.DataFrame()
    
    raw_data_df = pd.DataFrame()


@app.route('/')
def index():
    """Main dashboard page."""
    # Try to load enhanced Material UI template first
    enhanced_template = Path(__file__).parent.parent / 'src' / 'dashboard' / 'templates' / 'material_dashboard_enhanced.html'
    if enhanced_template.exists():
        try:
            with open(enhanced_template, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"✓ Loaded Enhanced Material UI template from {enhanced_template}")
                return content
        except Exception as e:
            print(f"✗ Error loading enhanced template: {e}")
    
    # Fallback to regular Material UI template
    template_path = Path(__file__).parent.parent / 'src' / 'dashboard' / 'templates' / 'material_dashboard.html'
    if template_path.exists():
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"✓ Loaded Material UI template from {template_path}")
                return content
        except Exception as e:
            print(f"✗ Error loading Material UI template: {e}")
    
    # Fallback to index.html
    try:
        return render_template('index.html')
    except Exception as e:
        # Final fallback: simple HTML page
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Anomaly Detection Dashboard</title></head>
        <body>
            <h1>Wikipedia Clickstream Anomaly Detection Dashboard</h1>
            <p>Template error: {str(e)}</p>
            <p>API is working: <a href="/api/anomalies/stats">/api/anomalies/stats</a></p>
        </body>
        </html>
        """


@app.route('/api/anomalies')
def get_anomalies():
    """Get anomalies with filtering."""
    try:
        if anomalies_df.empty:
            return jsonify({'anomalies': [], 'count': 0})
        
        df = anomalies_df.copy()
        
        # Apply filters
        month = request.args.get('month')
        anomaly_type = request.args.get('anomaly_type')
        min_confidence = request.args.get('min_confidence', type=float)
        # If no month filter, allow more results (for "All Months" view)
        limit = request.args.get('limit', type=int, default=5000 if not month else 1000)
        
        if month:
            df = df[df['month'] == month]
        if anomaly_type:
            df = df[df['anomaly_type'] == anomaly_type]
        if min_confidence:
            df = df[df['confidence'] >= min_confidence]
        
        # Sort by deviation_ratio first (for traffic spikes), then confidence
        # Prioritize anomalies with deviation_ratio > 1.0 (real spikes)
        # Put placeholder values (deviation_ratio = 1.0) at the bottom
        if 'deviation_ratio' in df.columns:
            # Split into high deviation (real anomalies) and low/placeholder
            high_dev = df[df['deviation_ratio'] > 1.0]
            low_dev = df[df['deviation_ratio'] <= 1.0]
            
            # Sort each group separately
            high_dev = high_dev.sort_values(['deviation_ratio', 'confidence'], ascending=[False, False])
            low_dev = low_dev.sort_values('confidence', ascending=False)
            
            # Concatenate: high deviation first, then low deviation
            df = pd.concat([high_dev, low_dev], ignore_index=True)
        else:
        df = df.sort_values('confidence', ascending=False)
        
        if limit:
            df = df.head(limit)
        
        # Ensure all required fields are present and properly formatted
        # Convert to dict with proper types
        anomalies_list = []
        for _, row in df.iterrows():
            anomaly_dict = {
                'anomaly_id': str(row.get('anomaly_id', '')),
                'month': str(row.get('month', '')),
                'prev': str(row.get('prev', '')),
                'curr': str(row.get('curr', '')),
                'type': str(row.get('type', 'link')),
                'n': int(row.get('n', 0)),
                'baseline_median': float(row.get('baseline_median', 0)),
                'deviation_ratio': float(row.get('deviation_ratio', 0)),  # Ensure this is a float
                'z_score': float(row.get('z_score', 0)),
                'anomaly_type': str(row.get('anomaly_type', '')),
                'confidence': float(row.get('confidence', 0)),
                'description': str(row.get('description', '')),
                'forecast_n': float(row.get('forecast_n', 0)) if pd.notna(row.get('forecast_n')) and float(row.get('forecast_n', 0)) > 0 else None,
                'forecast_lower': float(row.get('forecast_lower', 0)) if pd.notna(row.get('forecast_lower', 0)) else None,
                'forecast_upper': float(row.get('forecast_upper', 0)) if pd.notna(row.get('forecast_upper', 0)) else None,
                'forecast_error': float(row.get('forecast_error', 0)),
                'forecast_ratio': float(row.get('forecast_ratio', 1.0)),
                'forecast_flag': bool(row.get('forecast_flag', False))
            }
            anomalies_list.append(anomaly_dict)
        
        return jsonify({
            'anomalies': anomalies_list,
            'count': len(anomalies_list)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/anomalies/stats')
def get_anomaly_stats():
    """Get anomaly statistics."""
    try:
        if anomalies_df.empty:
            return jsonify({
                'total': 0,
                'by_type': {},
                'by_month': {},
                'avg_confidence': 0.0,
                'top_anomalies': []
            })
        
        stats = {
            'total': len(anomalies_df),
            'by_type': anomalies_df['anomaly_type'].value_counts().to_dict(),
            'by_month': anomalies_df['month'].value_counts().to_dict(),
            'avg_confidence': float(anomalies_df['confidence'].mean()),
            'top_anomalies': anomalies_df.nlargest(10, 'confidence')[
                ['prev', 'curr', 'anomaly_type', 'confidence']
            ].to_dict('records')
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/anomalies/top')
def get_top_anomalies():
    """Get top 5 most interesting anomalies - detailed version."""
    try:
        if anomalies_df.empty:
            return jsonify([])
        
        df = anomalies_df.copy()
        
        # Calculate interest score: prioritize high deviation ratios (more interesting spikes)
        # Weight deviation_ratio more heavily as it shows actual traffic spikes
        if 'deviation_ratio' in df.columns and 'confidence' in df.columns:
            # For traffic spikes, deviation_ratio is the key metric
            # Scale confidence to 0-1 range if needed, then combine
            df['interest_score'] = (df['deviation_ratio'] * 0.7) + (df['confidence'].clip(0, 1) * df['deviation_ratio'] * 0.3)
        elif 'deviation_ratio' in df.columns:
            df['interest_score'] = df['deviation_ratio']
        elif 'confidence' in df.columns:
            df['interest_score'] = df['confidence']
        else:
            df['interest_score'] = 1.0
        
        # Sort by interest score descending
        top = df.nlargest(5, 'interest_score')
        
        results = []
        for _, row in top.iterrows():
            results.append({
                'prev': str(row.get('prev', '')),
                'curr': str(row.get('curr', '')),
                'month': str(row.get('month', '')),
                'anomaly_type': str(row.get('anomaly_type', '')),
                'confidence': float(row.get('confidence', 0)),
                'deviation_ratio': float(row.get('deviation_ratio', 0)),
                'forecast_error': float(row.get('forecast_error', 0)) if 'forecast_error' in row else 0.0,
                'description': str(row.get('description', ''))
            })
        
        return jsonify(results)
    except Exception as e:
        import traceback
        print(f"Error in get_top_anomalies: {e}")
        print(traceback.format_exc())
        return jsonify([]), 500


@app.route('/api/anomalies/insights')
def get_insights():
    """Generate insights from anomalies - detailed version like the working dashboard."""
    try:
        if anomalies_df.empty:
            return jsonify({'insights': []})
        
        df = anomalies_df.copy()
        insights = []
        
        # Insight 1: Highest deviation anomaly (most interesting)
        if 'deviation_ratio' in df.columns and not df.empty:
            max_dev_idx = df['deviation_ratio'].idxmax()
            max_dev = df.loc[max_dev_idx]
            insights.append(
                f"In {max_dev.get('month', 'N/A')}, {max_dev.get('prev', 'N/A')} → {max_dev.get('curr', 'N/A')} "
                f"had the largest spike ({max_dev.get('deviation_ratio', 0):.1f}x baseline)."
            )
        
        # Insight 2: Page with most anomalies
        if 'curr' in df.columns and not df.empty:
            top_page = df['curr'].value_counts().index[0]
            count = int(df['curr'].value_counts().iloc[0])
            insights.append(
                f"'{top_page}' appears in {count} anomaly records, the most of any page."
            )
        
        # Insight 3: Month with highest anomaly count
        if 'month' in df.columns and not df.empty:
            top_month = df['month'].value_counts().index[0]
            count = int(df['month'].value_counts().iloc[0])
            insights.append(
                f"{top_month} had {count} anomalies, the highest count of any month."
            )
        
        # Insight 4: Most common referrer source
        if 'prev' in df.columns and not df.empty:
            top_referrer = df['prev'].value_counts().index[0]
            count = int(df['prev'].value_counts().iloc[0])
            insights.append(
                f"'{top_referrer}' was the most common referrer source ({count} occurrences)."
            )
        
        return jsonify({'insights': insights[:4]})  # Limit to 4 insights
    except Exception as e:
        import traceback
        print(f"Error in get_insights: {e}")
        print(traceback.format_exc())
        return jsonify({'insights': []}), 500


@app.route('/api/anomalies/overview')
def get_overview_chart():
    """Get monthly anomaly counts by type - for overview chart."""
    try:
        if anomalies_df.empty:
            return jsonify({
                'months': [],
                'traffic_spike': [],
                'mix_shift': [],
                'navigation_edge': [],
                'forecast_spike': []
            })
        
        df = anomalies_df.copy()
        
        # Group by month and type
        if 'month' in df.columns and 'anomaly_type' in df.columns:
            counts = df.groupby(['month', 'anomaly_type']).size().unstack(fill_value=0)
            months = sorted(counts.index.tolist())
            
            # Get counts for each type
            traffic_spike = counts.get('traffic_spike', pd.Series(0, index=months)).tolist() if len(months) > 0 else []
            mix_shift = counts.get('mix_shift', pd.Series(0, index=months)).tolist() if len(months) > 0 else []
            navigation_edge = counts.get('navigation_edge', pd.Series(0, index=months)).tolist() if len(months) > 0 else []
            
            # Check for forecast_spike in anomaly_type or forecast_flag
            forecast_spike = []
            if 'forecast_flag' in df.columns:
                forecast_df = df[df['forecast_flag'] == True]
                if not forecast_df.empty:
                    forecast_counts = forecast_df.groupby('month').size()
                    forecast_spike = [int(forecast_counts.get(m, 0)) for m in months]
                else:
                    forecast_spike = [0] * len(months)
            else:
                forecast_spike = [0] * len(months)
            
            response = {
                'months': months,
                'traffic_spike': traffic_spike,
                'mix_shift': mix_shift,
                'navigation_edge': navigation_edge,
                'forecast_spike': forecast_spike
            }
            
            print(f"📊 Overview chart data:")
            print(f"  Months: {months}")
            print(f"  Traffic spikes: {traffic_spike}")
            print(f"  Mix shifts: {mix_shift}")
            print(f"  Navigation edges: {navigation_edge}")
        else:
            response = {
                'months': [],
                'traffic_spike': [],
                'mix_shift': [],
                'navigation_edge': [],
                'forecast_spike': []
            }
        
        return jsonify(response)
    except Exception as e:
        import traceback
        print(f"Error in get_overview_chart: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/anomalies/<anomaly_id>')
def get_anomaly_detail(anomaly_id):
    """Get detailed information about a specific anomaly with full explainability."""
    try:
        if anomalies_df.empty:
            return jsonify({'error': 'No anomalies available'}), 404
        
        # Try to convert anomaly_id to int, fallback to string
        try:
            anomaly_id_int = int(anomaly_id)
        except:
            anomaly_id_int = None
        
        anomaly_row = pd.DataFrame()
        
        # Strategy 1: Lookup by anomaly_id column
        if 'anomaly_id' in anomalies_df.columns:
            # Try exact string match
            matches = anomalies_df[anomalies_df['anomaly_id'] == str(anomaly_id)]
            if not matches.empty:
                anomaly_row = matches
            # Try int match if applicable
            elif anomaly_id_int is not None:
                matches = anomalies_df[anomalies_df['anomaly_id'] == str(anomaly_id_int)]
                if not matches.empty:
                    anomaly_row = matches
        
        # Strategy 2: Lookup by index (fallback)
        if anomaly_row.empty and anomaly_id_int is not None:
            if 0 <= anomaly_id_int < len(anomalies_df):
                print(f"Lookup by ID failed, falling back to index {anomaly_id_int}")
                anomaly_row = anomalies_df.iloc[[anomaly_id_int]]
        
        if len(anomaly_row) == 0:
            print(f"Anomaly not found: {anomaly_id}")
            return jsonify({'error': f'Anomaly not found: {anomaly_id}'}), 404
        
        anomaly = anomaly_row.iloc[0].to_dict()
        prev = anomaly.get('prev', '')
        curr = anomaly.get('curr', '')
        month = anomaly.get('month', '')
        edge_type = anomaly.get('type', 'link')
        
        # Get forecast values
        forecast_values = {
            'forecast_n': float(anomaly.get('forecast_n', 0)) if anomaly.get('forecast_n') else None,
            'forecast_lower': float(anomaly.get('forecast_lower', 0)) if anomaly.get('forecast_lower') else None,
            'forecast_upper': float(anomaly.get('forecast_upper', 0)) if anomaly.get('forecast_upper') else None,
            'forecast_error': float(anomaly.get('forecast_error', 0)),
            'forecast_ratio': float(anomaly.get('forecast_ratio', 1.0)),
            'forecast_flag': bool(anomaly.get('forecast_flag', False))
        }
        
        # Detection signals breakdown
        z_score = anomaly.get('z_score', 0)
        deviation_ratio = anomaly.get('deviation_ratio', 0)
        forecast_error = forecast_values['forecast_error']
        baseline_median = anomaly.get('baseline_median', 0)
        
        detection_signals = {
            'z_score': {
                'value': float(z_score),
                'status': 'anomaly' if abs(z_score) >= 3.5 else ('elevated' if abs(z_score) >= 2.0 else 'normal'),
                'label': 'Robust Z-score (σ-MAD)'
            },
            'deviation_ratio': {
                'value': float(deviation_ratio),
                'status': 'anomaly' if deviation_ratio >= 10 else ('elevated' if deviation_ratio >= 5 else 'normal'),
                'label': 'Deviation Ratio'
            },
            'forecast_error': {
                'value': float(forecast_error),
                'status': 'anomaly' if abs(forecast_error) > baseline_median * 2 else ('elevated' if abs(forecast_error) > baseline_median else 'normal'),
                'label': 'Forecast Error'
            }
        }
        
        # Get daily pageviews (try to load, fallback to empty)
        daily_pageviews = []
        # Get daily pageviews (try to load, fallback to empty)
        daily_pageviews = []
        try:
            from src.external.pageviews_api import get_pageviews_for_anomaly
            print(f"Fetching pageviews for {curr}...")
            daily_pageviews = get_pageviews_for_anomaly(curr, month, days_before=30, days_after=30)
            print(f"Successfully fetched {len(daily_pageviews)} daily records")
        except Exception as e:
            print(f"Warning: Could not fetch pageviews: {e}")
            # Do not fail the request, just continue with empty pageviews
            pass
        
        # Get signals list
        signals = []
        if anomaly.get('anomaly_type') == 'traffic_spike':
            signals.append('Traffic Spike')
        elif anomaly.get('anomaly_type') == 'mix_shift':
            signals.append('Mix Shift')
        elif anomaly.get('anomaly_type') == 'navigation_edge':
            signals.append('Navigation Edge')
        
        if anomaly.get('forecast_flag'):
            signals.append('Forecast Deviation')
        if abs(z_score) >= 3.5:
            signals.append('High Z-score')
        if deviation_ratio >= 10:
            signals.append('High Deviation')
        
        # Get timeseries data for this edge
        timeseries_6m = []
        try:
            # Use raw_data_df if available
            if raw_data_df is not None and not raw_data_df.empty:
                # Filter for this specific edge
                edge_filter = (raw_data_df['prev'] == prev) & (raw_data_df['curr'] == curr)
                if edge_type and 'type' in raw_data_df.columns:
                    edge_filter = edge_filter & (raw_data_df['type'] == edge_type)
                
                edge_data = raw_data_df[edge_filter]
                
                if not edge_data.empty:
                    # Aggregate by month
                    monthly = edge_data.groupby('month')['n'].sum().reset_index()
                    monthly = monthly.sort_values('month')
                    timeseries_6m = monthly.tail(6).to_dict('records')
                    print(f"✓ Loaded {len(timeseries_6m)} months of timeseries for {prev} -> {curr}")
                else:
                    print(f"⚠ No timeseries data found for {prev} -> {curr}")
            else:
                print(f"⚠ raw_data_df is not available for timeseries")
        except Exception as e:
            print(f"✗ Error loading timeseries for detail: {e}")
            import traceback
            traceback.print_exc()
        
        # Get referrer shares
        referrer_shares = []
        try:
            if raw_data_df is not None and not raw_data_df.empty:
                # Get all available months
                all_months = sorted(raw_data_df['month'].unique())
                
                # Get last 6 months of data for this page (curr)
                last_6_months = all_months[-6:] if len(all_months) >= 6 else all_months
                
                for m in last_6_months:
                    # Get all traffic to this page in this month
                    month_data = raw_data_df[
                        (raw_data_df['curr'] == curr) &
                        (raw_data_df['month'] == m)
                    ]
                    
                    if not month_data.empty:
                        total = month_data['n'].sum()
                        if total > 0:
                            # Group by referrer (prev) and calculate proportions
                            referrer_counts = month_data.groupby('prev')['n'].sum().reset_index()
                            referrer_counts['proportion'] = referrer_counts['n'] / total
                            referrer_counts = referrer_counts.sort_values('proportion', ascending=False)
                            
                            referrer_shares.append({
                                'month': m,
                                'total': int(total),
                                'referrers': referrer_counts.head(10).to_dict('records')
                            })
                
                print(f"✓ Loaded referrer shares for {len(referrer_shares)} months for {curr}")
            else:
                print(f"⚠ raw_data_df is not available for referrer shares")
        except Exception as e:
            print(f"✗ Error loading referrer shares for detail: {e}")
            import traceback
            traceback.print_exc()
        
        return jsonify({
            'anomaly': anomaly,
            'timeseries_6m': timeseries_6m,
            'forecast_values': forecast_values,
            'referrer_shares': referrer_shares,
            'detection_signals': detection_signals,
            'daily_pageviews': daily_pageviews,
            'daily_spike_match': False,
            'top_referrer_flip': False,
            'major_mix_shift': anomaly.get('anomaly_type') == 'mix_shift',
            'signals': signals
        })
    except Exception as e:
        import traceback
        print(f"Error in get_anomaly_detail: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/timeseries')
def get_timeseries():
    """Get time-series data for a specific edge - for trend sparklines."""
    global raw_data_df, anomalies_df
    try:
        prev = request.args.get('prev')
        curr = request.args.get('curr')
        edge_type = request.args.get('type', '')
        
        if not prev or not curr:
            return jsonify({'months': [], 'traffic': [], 'baseline': [], 'forecast': []})
        
        # Use raw_data_df if available (loaded at startup)
        if 'raw_data_df' in globals() and raw_data_df is not None and not raw_data_df.empty:
            edge_filter = (raw_data_df['prev'] == prev) & (raw_data_df['curr'] == curr)
            if edge_type:
                edge_filter = edge_filter & (raw_data_df['type'] == edge_type)
            
            edge_data = raw_data_df[edge_filter].copy()
            
            if len(edge_data) > 0:
                # Aggregate by month
                monthly_traffic = edge_data.groupby('month')['n'].sum().reset_index()
                monthly_traffic = monthly_traffic.sort_values('month')
                
                # Get baseline and forecast from anomalies if available
                baseline_median = 0
                forecast_n = None
                
                if not anomalies_df.empty:
                    baseline_filter = (anomalies_df['prev'] == prev) & (anomalies_df['curr'] == curr)
                    if edge_type:
                        baseline_filter = baseline_filter & (anomalies_df['type'] == edge_type)
                    
                    baseline_row = anomalies_df[baseline_filter]
                    if len(baseline_row) > 0:
                        row = baseline_row.iloc[0]
                        baseline_median = float(row.get('baseline_median', 0))
                        if 'forecast_n' in row and pd.notna(row.get('forecast_n', 0)) and row.get('forecast_n', 0) != 0:
                            forecast_n = float(row['forecast_n'])
                
                months = monthly_traffic['month'].tolist()
                traffic = monthly_traffic['n'].tolist()
                baseline = [baseline_median] * len(months) if baseline_median > 0 else [0] * len(months)
                forecast = [forecast_n] * len(months) if forecast_n is not None else [None] * len(months)
                
                print(f"\u2713 Timeseries for {prev} -> {curr}: {len(months)} months")
                
                return jsonify({
                    'months': months,
                    'traffic': traffic,
                    'baseline': baseline,
                    'forecast': forecast
                })
            else:
                print(f"\u26a0 No timeseries data found for {prev} -> {curr}")
        
        # Fallback: Return data from anomalies_df (single month only)
        df = anomalies_df.copy()
        edge_data = df[(df['prev'] == prev) & (df['curr'] == curr)]
        
        if edge_data.empty:
            return jsonify({'months': [], 'traffic': [], 'baseline': [], 'forecast': []})
        
        # Return monthly data from anomalies
        months = []
        traffic = []
        baseline = []
        forecast = []
        
        for _, row in edge_data.iterrows():
            months.append(str(row.get('month', '')))
            traffic.append(int(row.get('n', 0)))
            baseline.append(float(row.get('baseline_median', 0)))
            forecast_n_val = row.get('forecast_n', 0)
            forecast.append(float(forecast_n_val) if pd.notna(forecast_n_val) and forecast_n_val != 0 else None)
        
        return jsonify({
            'months': months,
            'traffic': traffic,
            'baseline': baseline,
            'forecast': forecast
        })
    except Exception as e:
        import traceback
        print(f"Error in get_timeseries: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e), 'months': [], 'traffic': [], 'baseline': [], 'forecast': []}), 500


@app.route('/api/graph')
def get_anomaly_graph():
    """Get network graph data for anomalies."""
    try:
        if anomalies_df.empty:
            return jsonify({'nodes': [], 'edges': []})
        
        df = anomalies_df.copy()
        
        month = request.args.get('month')
        limit = request.args.get('limit', type=int, default=100)
        
        if month:
            df = df[df['month'] == month]
        
        df = df.nlargest(limit, 'confidence')
        
        # Build graph structure
        nodes = set()
        edges = []
        
        for _, row in df.iterrows():
            prev = str(row['prev'])
            curr = str(row['curr'])
            nodes.add(prev)
            nodes.add(curr)
            
            edges.append({
                'source': prev,
                'target': curr,
                'weight': float(row['confidence']),
                'anomaly_type': row['anomaly_type'],
                'anomaly_id': str(row['anomaly_id'])
            })
        
        nodes_list = [{'id': node, 'label': node[:50]} for node in nodes]
        
        return jsonify({
            'nodes': nodes_list,
            'edges': edges
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    import socket
    
    def find_available_port(start_port=7000, max_attempts=10):
        """Find an available port in the 7000 series."""
        for i in range(max_attempts):
            port = start_port + i
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                continue
        # If all ports in 7000 series are taken, fall back to system-assigned port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
    
    port = find_available_port(7000)
    print(f"Starting dashboard on http://localhost:{port}")
    print(f"Loaded {len(anomalies_df)} anomalies")
    app.run(host='0.0.0.0', port=port, debug=False)

