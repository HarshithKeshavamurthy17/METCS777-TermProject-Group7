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
    return render_template('index.html')


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
        
        pdf = anomaly_df.toPandas().iloc[0].to_dict()
        
        # Get time series data for this edge
        # This would require loading the processed clickstream data
        # For now, return basic info
        
        return jsonify(pdf)
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
        port=dashboard_config.get('port', 7000),
        debug=dashboard_config.get('debug', False)
    )

