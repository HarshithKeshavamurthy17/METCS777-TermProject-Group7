"""Flask dashboard application."""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import pandas as pd
import json
import os
from pathlib import Path
from pyspark.sql import SparkSession
from ..utils.config import load_config
from ..storage.anomalies_schema import AnomaliesStorage
from ..features.daily_pageviews import get_pageview_series
from flask import Response
import io
import csv


app = Flask(__name__)
CORS(app)

# Global variables
spark = None
anomalies_storage = None
config = None


def init_app():
    """Initialize the dashboard application."""
    global spark, anomalies_storage, config
    
    config = load_config()
    data_config = config.get('data', {})
    
    # Initialize Spark
    from ..utils.spark_session import create_spark_session
    spark = create_spark_session(config)
    
    # Initialize storage
    storage_config = config.get('storage', {})
    anomalies_storage = AnomaliesStorage(
        spark,
        data_config.get('anomalies_dir', 'data/anomalies'),
        storage_config.get('format', 'parquet')
    )


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('material_dashboard_enhanced.html')


@app.route('/api/anomalies')
def get_anomalies():
    """Get anomalies with filtering."""
    try:
        # Get filters from query parameters
        month = request.args.get('month')
        anomaly_type = request.args.get('anomaly_type')
        min_confidence = request.args.get('min_confidence', type=float)
        limit = request.args.get('limit', type=int, default=1000)
        
        # Build filters
        filters = {}
        if month:
            filters['month'] = month
        if anomaly_type:
            filters['anomaly_type'] = anomaly_type
        
        # Load anomalies
        df = anomalies_storage.load_anomalies(filters)
        
        # Apply confidence filter
        if min_confidence:
            from pyspark.sql.functions import col
            df = df.filter(col('confidence') >= min_confidence)
        
        # Limit results
        if limit:
            df = df.limit(limit)
        
        # Convert to Pandas
        pdf = df.toPandas()
        
        # Sort by confidence descending
        pdf = pdf.sort_values('confidence', ascending=False)
        
        return jsonify({
            'anomalies': pdf.to_dict('records'),
            'count': len(pdf)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/anomalies/stats')
def get_anomaly_stats():
    """Get anomaly statistics."""
    try:
        df = anomalies_storage.load_anomalies()
        pdf = df.toPandas()
        
        stats = {
            'total': len(pdf),
            'by_type': pdf.groupby('anomaly_type').size().to_dict(),
            'by_month': pdf.groupby('month').size().to_dict(),
            'avg_confidence': float(pdf['confidence'].mean()),
            'top_anomalies': pdf.nlargest(10, 'confidence')[['prev', 'curr', 'anomaly_type', 'confidence']].to_dict('records')
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/anomalies/<anomaly_id>')
def get_anomaly_detail(anomaly_id):
    """Get detailed information about a specific anomaly."""
    try:
        df = anomalies_storage.load_anomalies()
        from pyspark.sql.functions import col
        anomaly_df = df.filter(col('anomaly_id') == anomaly_id)
        
        if anomaly_df.count() == 0:
            return jsonify({'error': 'Anomaly not found'}), 404
        
        # Get raw anomaly data
        anomaly_data = anomaly_df.toPandas().iloc[0].to_dict()
        
        # Construct response with expected structure
        response = {
            'anomaly': anomaly_data,
            'detection_signals': {
                'statistical': {
                    'label': 'Statistical Deviation',
                    'value': float(anomaly_data.get('deviation_ratio', 0)),
                    'status': 'anomaly' if float(anomaly_data.get('deviation_ratio', 0)) > 2.0 else 'elevated'
                },
                'forecast': {
                    'label': 'Forecast Error',
                    'value': float(anomaly_data.get('n', 0)) - float(anomaly_data.get('forecast_n', 0)) if anomaly_data.get('forecast_n') else 0.0,
                    'status': 'anomaly' if anomaly_data.get('forecast_flag') else 'normal'
                }
            },
            'timeseries_6m': [], # Placeholder - would need to fetch from features
            'referrer_shares': [], # Placeholder - would need to fetch from features
            'forecast_values': {
                'forecast_n': float(anomaly_data.get('forecast_n', 0)) if anomaly_data.get('forecast_n') else None,
                'forecast_error': 0.0,
                'forecast_flag': bool(anomaly_data.get('forecast_flag', False))
            },
            'top_referrer_flip': False,
            'major_mix_shift': anomaly_data.get('anomaly_type') == 'mix_shift'
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/anomalies/top')
def get_top_anomalies():
    """Get top 5 anomalies by confidence."""
    try:
        df = anomalies_storage.load_anomalies()
        pdf = df.toPandas()
        
        if pdf.empty:
            return jsonify([])
            
        top_5 = pdf.nlargest(5, 'confidence').to_dict('records')
        return jsonify(top_5)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/anomalies/insights')
def get_insights():
    """Generate insights from anomalies."""
    try:
        df = anomalies_storage.load_anomalies()
        pdf = df.toPandas()
        
        if pdf.empty:
            return jsonify({'insights': []})
            
        insights = []
        
        # Insight 1: Dominant type
        type_counts = pdf['anomaly_type'].value_counts()
        if not type_counts.empty:
            dominant_type = type_counts.index[0]
            insights.append(f"Most anomalies are of type '{dominant_type}' ({type_counts.iloc[0]} detected).")
            
        # Insight 2: High confidence count
        high_conf = len(pdf[pdf['confidence'] > 0.8])
        if high_conf > 0:
            insights.append(f"{high_conf} anomalies have very high confidence (> 0.8).")
            
        # Insight 3: Top affected page
        if 'curr' in pdf.columns:
            top_page = pdf['curr'].mode()
            if not top_page.empty:
                insights.append(f"'{top_page.iloc[0]}' is the most affected destination page.")
                
        return jsonify({'insights': insights})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/anomalies/overview')
def get_overview_chart():
    """Get monthly anomaly counts by type."""
    try:
        df = anomalies_storage.load_anomalies()
        pdf = df.toPandas()
        
        if pdf.empty:
            return jsonify({'months': []})
            
        # Group by month and type
        counts = pdf.groupby(['month', 'anomaly_type']).size().unstack(fill_value=0)
        
        months = sorted(counts.index.tolist())
        response = {
            'months': months,
            'traffic_spike': counts.get('traffic_spike', pd.Series(0, index=months)).tolist(),
            'mix_shift': counts.get('mix_shift', pd.Series(0, index=months)).tolist(),
            'forecast_spike': counts.get('forecast_spike', pd.Series(0, index=months)).tolist() # Assuming this type exists or maps to something
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/graph')
def get_anomaly_graph():
    """Get network graph data for anomalies."""
    try:
        month = request.args.get('month')
        limit = request.args.get('limit', type=int, default=100)
        
        filters = {}
        if month:
            filters['month'] = month
        
        df = anomalies_storage.load_anomalies(filters)
        
        # Limit and sort
        from pyspark.sql.functions import col
        df = df.orderBy(col('confidence').desc()).limit(limit)
        
        pdf = df.toPandas()
        
        # Build graph structure
        nodes = set()
        edges = []
        
        for _, row in pdf.iterrows():
            prev = str(row['prev'])
            curr = str(row['curr'])
            nodes.add(prev)
            nodes.add(curr)
            
            edges.append({
                'source': prev,
                'target': curr,
                'weight': float(row['confidence']),
                'anomaly_type': row['anomaly_type'],
                'anomaly_id': row['anomaly_id']
            })
        
        nodes_list = [{'id': node, 'label': node[:50]} for node in nodes]
        
        return jsonify({
            'nodes': nodes_list,
            'edges': edges
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    init_app()
    dashboard_config = config.get('dashboard', {}) if config else {}
    app.run(
        host=dashboard_config.get('host', '0.0.0.0'),
        port=dashboard_config.get('port', 5000),
        debug=dashboard_config.get('debug', False)
    )

