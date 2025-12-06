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

# Load anomalies
anomalies_df = None
anomalies_path = "data/anomalies/anomalies.parquet"

if os.path.exists(anomalies_path):
    anomalies_df = pd.read_parquet(anomalies_path)
    print(f"Loaded {len(anomalies_df)} anomalies")
else:
    print(f"Warning: Anomalies file not found at {anomalies_path}")
    anomalies_df = pd.DataFrame()


@app.route('/')
def index():
    """Main dashboard page."""
    try:
        return render_template('index.html')
    except Exception as e:
        # If template not found, return a simple HTML page
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
        limit = request.args.get('limit', type=int, default=1000)
        
        if month:
            df = df[df['month'] == month]
        if anomaly_type:
            df = df[df['anomaly_type'] == anomaly_type]
        if min_confidence:
            df = df[df['confidence'] >= min_confidence]
        
        # Sort and limit
        df = df.sort_values('confidence', ascending=False)
        if limit:
            df = df.head(limit)
        
        return jsonify({
            'anomalies': df.to_dict('records'),
            'count': len(df)
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
    print("Starting dashboard on http://localhost:5000")
    print(f"Loaded {len(anomalies_df)} anomalies")
    app.run(host='0.0.0.0', port=5000, debug=False)

