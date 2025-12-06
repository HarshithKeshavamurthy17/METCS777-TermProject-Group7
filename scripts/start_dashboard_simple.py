#!/usr/bin/env python3
"""Simple standalone dashboard that embeds HTML."""
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from pathlib import Path

app = Flask(__name__)
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

# Load raw clickstream data for time-series
raw_data_df = None
raw_data_dir = "data/raw"
months = ["2023-06", "2023-07", "2023-08", "2023-09", "2023-10", "2023-11", "2023-12", "2024-01", "2024-02", "2024-03"]

if os.path.exists(raw_data_dir):
    all_data = []
    for month in months:
        file_path = os.path.join(raw_data_dir, f"clickstream-{month}.tsv")
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, sep="\t")
            df['month'] = month
            all_data.append(df)
    if all_data:
        raw_data_df = pd.concat(all_data, ignore_index=True)
        print(f"Loaded {len(raw_data_df)} rows of raw clickstream data")
    else:
        raw_data_df = pd.DataFrame()
else:
    raw_data_df = pd.DataFrame()


@app.route('/')
def index():
    """Main dashboard page - Enhanced Material UI version."""
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
    
    # Fallback to embedded HTML (old version)
    print("⚠ Using fallback embedded HTML")
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wikipedia Clickstream Anomaly Detection Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; color: #333; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; }
        .header h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .stat-card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-card h3 { color: #667eea; font-size: 0.9rem; margin-bottom: 0.5rem; text-transform: uppercase; }
        .stat-card .value { font-size: 2rem; font-weight: bold; color: #333; }
        .filters { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 2rem; }
        .filter-group { display: flex; gap: 1rem; flex-wrap: wrap; align-items: center; }
        .filter-group select, .filter-group input { padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; }
        .filter-group button { padding: 0.5rem 1.5rem; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .table-container { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        thead { background: #667eea; color: white; }
        th, td { padding: 1rem; text-align: left; border-bottom: 1px solid #eee; }
        tbody tr:hover { background: #f9f9f9; }
        .anomaly-type { padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem; }
        .traffic_spike { background: #fee; color: #c33; }
        .navigation_edge { background: #eef; color: #33c; }
        .mix_shift { background: #efe; color: #3c3; }
        .loading { text-align: center; padding: 2rem; color: #666; }
        .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; border-bottom: 2px solid #ddd; }
        .tab { padding: 1rem 2rem; background: #f5f5f5; border: none; cursor: pointer; border-radius: 8px 8px 0 0; font-weight: 500; }
        .tab.active { background: #667eea; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .chart-container { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 2rem; }
        .chart-container h3 { margin-bottom: 1rem; color: #333; }
        #timeseries-chart { width: 100%; height: 400px; }
        .selected-anomaly { background: #e3f2fd !important; }
        .selected-anomaly:hover { background: #bbdefb !important; }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>Wikipedia Clickstream Anomaly Detection</h1>
            <p>Interactive dashboard for exploring detected anomalies</p>
        </div>
    </div>
    
    <div class="container">
        <div class="stats-grid" id="stats-grid">
            <div class="stat-card"><h3>Total Anomalies</h3><div class="value" id="total-anomalies">-</div></div>
            <div class="stat-card"><h3>Traffic Spikes</h3><div class="value" id="traffic-spikes">-</div></div>
            <div class="stat-card"><h3>Mix Shifts</h3><div class="value" id="mix-shifts">-</div></div>
            <div class="stat-card"><h3>Avg Confidence</h3><div class="value" id="avg-confidence">-</div></div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('anomalies')">Anomalies Table</button>
            <button class="tab" onclick="switchTab('graph')">Navigation Graph</button>
        </div>
        
        <div id="tab-anomalies" class="tab-content active">
        <div class="filters">
            <h2>Filters</h2>
            <div class="filter-group">
                <label>Anomaly Type:</label>
                <select id="filter-type" onchange="loadAnomalies()"><option value="">All</option><option value="traffic_spike">Traffic Spike</option><option value="mix_shift">Mix Shift</option></select>
                <label>Min Confidence:</label>
                <input type="number" id="filter-confidence" min="0" max="1" step="0.1" value="0.5" onchange="loadAnomalies()">
                <label>Month:</label>
                <select id="filter-month" onchange="loadAnomalies()"><option value="">All Months</option></select>
                <button onclick="loadAnomalies()">Apply Filters</button>
            </div>
        </div>
            
            <div class="chart-container" id="chart-container" style="display: none;">
                <h3 id="chart-title">Traffic Over Time</h3>
                <div id="timeseries-chart"></div>
            </div>
            
            <div class="table-container">
                <table>
                    <thead>
                        <tr><th>From (prev)</th><th>To (curr)</th><th>Type</th><th>Count</th><th>Deviation</th><th>Confidence</th><th>Description</th></tr>
                    </thead>
                    <tbody id="anomalies-table"><tr><td colspan="7" class="loading">Loading...</td></tr></tbody>
                </table>
            </div>
        </div>
        
        <div id="tab-graph" class="tab-content">
            <div class="filters">
                <h2>Graph Filters</h2>
                <div class="filter-group">
                    <label>Anomaly Type:</label>
                    <select id="graph-filter-type"><option value="">All</option><option value="traffic_spike">Traffic Spike</option><option value="mix_shift">Mix Shift</option></select>
                    <label>Top N:</label>
                    <input type="number" id="graph-top-n" min="10" max="200" value="50" step="10">
                    <label>Month:</label>
                    <select id="graph-month"><option value="">All Months</option></select>
                    <button onclick="loadGraph()">Update Graph</button>
                </div>
            </div>
            <div class="chart-container">
                <h3>Navigation Graph Visualization</h3>
                <div id="network-graph" style="width: 100%; height: 600px; border: 1px solid #eee; border-radius: 4px;"></div>
            </div>
        </div>
    </div>
    
    <script>
        async function loadStats() {
            try {
                const response = await fetch('/api/anomalies/stats');
                const stats = await response.json();
                document.getElementById('total-anomalies').textContent = stats.total || 0;
                document.getElementById('traffic-spikes').textContent = stats.by_type?.traffic_spike || 0;
                document.getElementById('mix-shifts').textContent = stats.by_type?.mix_shift || 0;
                document.getElementById('avg-confidence').textContent = (stats.avg_confidence || 0).toFixed(2);
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }
        
        async function loadAnomalies() {
            const type = document.getElementById('filter-type').value;
            const confidenceInput = document.getElementById('filter-confidence');
            const confidence = confidenceInput ? parseFloat(confidenceInput.value) : 0;
            const month = document.getElementById('filter-month').value;
            
            // Show loading state
            const tbody = document.getElementById('anomalies-table');
            tbody.innerHTML = '<tr><td colspan="7" class="loading">Loading anomalies...</td></tr>';
            
            const params = new URLSearchParams();
            if (type) params.append('anomaly_type', type);
            if (confidence && !isNaN(confidence) && confidence > 0) {
                params.append('min_confidence', confidence.toString());
            }
            if (month) params.append('month', month);
            params.append('limit', '1000');
            
            console.log('Loading anomalies with filters:', { type, confidence, month, params: params.toString() });
            
            try {
                const response = await fetch(`/api/anomalies?${params}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                
                console.log('Loaded anomalies:', { 
                    count: data.count, 
                    returned: data.anomalies?.length,
                    filters: { type, confidence, month },
                    sampleConfidences: data.anomalies?.slice(0, 5).map(a => a.confidence)
                });
                
                if (!data.anomalies || data.anomalies.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="7" class="loading">No anomalies found matching the filters (Type: ${type || 'All'}, Confidence: ${confidence || 'Any'}, Month: ${month || 'All'})</td></tr>`;
                    window.currentAnomalies = [];
                    return;
                }
                
                // Escape single quotes in strings to prevent JavaScript errors
                const escapeQuotes = (str) => String(str || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                
                tbody.innerHTML = data.anomalies.map((a, idx) => {
                    const prev = escapeQuotes(a.prev);
                    const curr = escapeQuotes(a.curr);
                    const type = escapeQuotes(a.type);
                    return `
                    <tr class="anomaly-row" data-idx="${idx}" onclick="selectAnomaly(${idx}, '${prev}', '${curr}', '${type}')" style="cursor: pointer;">
                        <td>${(a.prev || '').substring(0, 30)}${(a.prev || '').length > 30 ? '...' : ''}</td>
                        <td>${(a.curr || '').substring(0, 30)}${(a.curr || '').length > 30 ? '...' : ''}</td>
                        <td><span class="anomaly-type ${a.anomaly_type}">${a.anomaly_type}</span></td>
                        <td>${a.n || 0}</td>
                        <td>${(a.deviation_ratio || 0).toFixed(2)}x</td>
                        <td>${(a.confidence || 0).toFixed(2)}</td>
                        <td>${(a.description || '').substring(0, 50)}${(a.description || '').length > 50 ? '...' : ''}</td>
                    </tr>
                `;
                }).join('');
                window.currentAnomalies = data.anomalies;
                
                // Update stats display
                updateFilteredStats(data.anomalies);
            } catch (error) {
                console.error('Error loading anomalies:', error);
                tbody.innerHTML = `<tr><td colspan="7" class="loading" style="color: #c33;">Error loading anomalies: ${error.message}</td></tr>`;
            }
        }
        
        function updateFilteredStats(anomalies) {
            if (!anomalies || anomalies.length === 0) return;
            
            const byType = {};
            anomalies.forEach(a => {
                byType[a.anomaly_type] = (byType[a.anomaly_type] || 0) + 1;
            });
            
            const avgConfidence = anomalies.reduce((sum, a) => sum + (a.confidence || 0), 0) / anomalies.length;
            
            // Update display if needed (optional - can show filtered counts)
            console.log('Filtered stats:', { total: anomalies.length, byType, avgConfidence });
        }
        
        let currentAnomalies = [];
        let selectedAnomalyIdx = null;
        
        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(`tab-${tabName}`).classList.add('active');
        }
        
        async function selectAnomaly(idx, prev, curr, type) {
            // Remove previous selection
            document.querySelectorAll('.anomaly-row').forEach(r => r.classList.remove('selected-anomaly'));
            // Add selection to clicked row
            event.currentTarget.classList.add('selected-anomaly');
            selectedAnomalyIdx = idx;
            
            // Show chart container
            document.getElementById('chart-container').style.display = 'block';
            document.getElementById('chart-title').textContent = `Traffic Over Time: ${prev} → ${curr}`;
            document.getElementById('timeseries-chart').innerHTML = '<p style="text-align: center; padding: 2rem; color: #666;">Loading...</p>';
            
            // Load time-series data
            try {
                const typeParam = type ? `&type=${encodeURIComponent(type)}` : '';
                const response = await fetch(`/api/timeseries?prev=${encodeURIComponent(prev)}&curr=${encodeURIComponent(curr)}${typeParam}`);
                const data = await response.json();
                
                if (data.error) {
                    throw new Error(data.error);
                }
                
                if (data.months && data.traffic && data.months.length > 0) {
                    // Get anomaly month safely
                    let anomalyMonth = null;
                    if (currentAnomalies && currentAnomalies[idx]) {
                        anomalyMonth = currentAnomalies[idx].month;
                    }
                    
                    // Create bar chart using Plotly
                    const trace = {
                        x: data.months,
                        y: data.traffic,
                        type: 'bar',
                        marker: {
                            color: data.months.map((m) => {
                                // Highlight the anomaly month if available
                                return anomalyMonth && m === anomalyMonth ? '#f44336' : '#667eea';
                            })
                        },
                        name: 'Traffic',
                        text: data.traffic.map((t, i) => `Month: ${data.months[i]}<br>Traffic: ${t}`),
                        hoverinfo: 'text+y'
                    };
                    
                    const traces = [trace];
                    
                    // Add baseline if available
                    if (data.baseline && data.baseline[0] > 0) {
                        const baselineTrace = {
                            x: data.months,
                            y: data.baseline,
                            type: 'scatter',
                            mode: 'lines',
                            line: { color: '#999', dash: 'dash', width: 2 },
                            name: 'Baseline Median',
                            hoverinfo: 'y+name'
                        };
                        traces.push(baselineTrace);
                    }
                    
                    const layout = {
                        title: `Traffic: ${prev} → ${curr}`,
                        xaxis: { title: 'Month' },
                        yaxis: { title: 'Number of Transitions' },
                        hovermode: 'closest',
                        margin: { l: 60, r: 20, t: 40, b: 60 },
                        showlegend: true
                    };
                    
                    Plotly.newPlot('timeseries-chart', traces, layout, {responsive: true});
                } else {
                    document.getElementById('timeseries-chart').innerHTML = '<p style="text-align: center; padding: 2rem; color: #666;">No time-series data available for this edge</p>';
                }
            } catch (error) {
                console.error('Error loading time-series:', error);
                document.getElementById('timeseries-chart').innerHTML = `<p style="text-align: center; padding: 2rem; color: #c33;">Error loading time-series data: ${error.message}</p>`;
            }
        }
        
        async function loadGraph() {
            const type = document.getElementById('graph-filter-type').value;
            const topN = parseInt(document.getElementById('graph-top-n').value) || 50;
            const month = document.getElementById('graph-month').value;
            
            // Show loading state
            document.getElementById('network-graph').innerHTML = '<p style="text-align: center; padding: 2rem; color: #666;">Loading graph...</p>';
            
            const params = new URLSearchParams();
            if (type) params.append('anomaly_type', type);
            if (month) params.append('month', month);
            params.append('limit', topN);
            
            try {
                const response = await fetch(`/api/anomalies?${params}`);
                const data = await response.json();
                
                console.log('Graph data received:', { count: data.count, anomalies: data.anomalies?.length });
                
                if (!data.anomalies || data.anomalies.length === 0) {
                    const monthText = month ? ` for ${month}` : '';
                    document.getElementById('network-graph').innerHTML = `<p style="text-align: center; padding: 2rem; color: #666;">No anomalies found${monthText}. Try selecting a different month or removing filters.</p>`;
                    return;
                }
                
                // Build graph structure
                const nodes = new Set();
                const edges = [];
                
                data.anomalies.forEach(anomaly => {
                    const prev = String(anomaly.prev || '');
                    const curr = String(anomaly.curr || '');
                    nodes.add(prev);
                    nodes.add(curr);
                    
                    edges.push({
                        source: prev,
                        target: curr,
                        weight: parseFloat(anomaly.confidence || 0),
                        anomaly_type: anomaly.anomaly_type,
                        anomaly_id: String(anomaly.anomaly_id || '')
                    });
                });
                
                // Create node positions (simple circular layout)
                const nodeArray = Array.from(nodes);
                const angleStep = (2 * Math.PI) / nodeArray.length;
                const radius = 15;
                
                const nodeData = nodeArray.map((node, i) => {
                    const angle = i * angleStep;
                    return {
                        x: Math.cos(angle) * radius,
                        y: Math.sin(angle) * radius,
                        label: node.substring(0, 30),
                        id: node
                    };
                });
                
                // Create edge traces
                const edgeX = [];
                const edgeY = [];
                const edgeText = [];
                
                edges.forEach(edge => {
                    const sourceIdx = nodeArray.indexOf(edge.source);
                    const targetIdx = nodeArray.indexOf(edge.target);
                    
                    if (sourceIdx >= 0 && targetIdx >= 0) {
                        edgeX.push(nodeData[sourceIdx].x, nodeData[targetIdx].x, null);
                        edgeY.push(nodeData[sourceIdx].y, nodeData[targetIdx].y, null);
                        edgeText.push(`${edge.source} → ${edge.target}<br>Confidence: ${edge.weight.toFixed(2)}`);
                    }
                });
                
                // Edge trace
                const edgeTrace = {
                    x: edgeX,
                    y: edgeY,
                    mode: 'lines',
                    line: { width: 2, color: '#888' },
                    hoverinfo: 'skip',
                    showlegend: false
                };
                
                // Node trace
                const nodeTrace = {
                    x: nodeData.map(n => n.x),
                    y: nodeData.map(n => n.y),
                    mode: 'markers+text',
                    type: 'scatter',
                    text: nodeData.map(n => n.label),
                    textposition: 'middle center',
                    marker: {
                        size: 15,
                        color: '#667eea',
                        line: { width: 2, color: '#fff' }
                    },
                    hovertext: nodeArray,
                    hoverinfo: 'text',
                    showlegend: false
                };
                
                const layout = {
                    title: `Anomaly Network Graph (${data.anomalies.length} anomalies)`,
                    showlegend: false,
                    hovermode: 'closest',
                    margin: { b: 20, l: 20, r: 20, t: 60 },
                    xaxis: { showgrid: false, zeroline: false, showticklabels: false },
                    yaxis: { showgrid: false, zeroline: false, showticklabels: false },
                    plot_bgcolor: 'white',
                    paper_bgcolor: 'white'
                };
                
                Plotly.newPlot('network-graph', [edgeTrace, nodeTrace], layout, {responsive: true});
            } catch (error) {
                console.error('Error loading graph:', error);
                document.getElementById('network-graph').innerHTML = `<p style="text-align: center; padding: 2rem; color: #c33;">Error loading graph: ${error.message}</p>`;
            }
        }
        
        // Populate month filter for graph
        async function initGraphFilters() {
            try {
                const response = await fetch('/api/anomalies/stats');
                const stats = await response.json();
                const monthSelect = document.getElementById('graph-month');
                
                // Only add months that actually have anomalies
                const monthsWithAnomalies = Object.keys(stats.by_month || {});
                if (monthsWithAnomalies.length > 0) {
                    monthsWithAnomalies.sort().forEach(month => {
                        const option = document.createElement('option');
                        option.value = month;
                        option.textContent = month;
                        monthSelect.appendChild(option);
                    });
                    // Set default to first month with anomalies
                    monthSelect.value = monthsWithAnomalies[0];
                } else {
                    // Fallback: add all months from data
                    const allMonths = ["2023-09", "2023-10", "2023-11", "2023-12", "2024-01", "2024-02", "2024-03"];
                    allMonths.forEach(month => {
                        const option = document.createElement('option');
                        option.value = month;
                        option.textContent = month;
                        monthSelect.appendChild(option);
                    });
                }
            } catch (error) {
                console.error('Error loading graph filters:', error);
            }
        }
        
        // Populate month filter for anomalies table
        async function initAnomalyFilters() {
            try {
                const response = await fetch('/api/anomalies/stats');
                const stats = await response.json();
                const monthSelect = document.getElementById('filter-month');
                
                // Add months that have anomalies
                const monthsWithAnomalies = Object.keys(stats.by_month || {});
                monthsWithAnomalies.sort().forEach(month => {
                    const option = document.createElement('option');
                    option.value = month;
                    option.textContent = month;
                    monthSelect.appendChild(option);
                });
            } catch (error) {
                console.error('Error loading anomaly filters:', error);
            }
        }
        
        loadStats();
        initAnomalyFilters().then(() => {
            loadAnomalies();
        });
        initGraphFilters().then(() => {
            // Load graph automatically after filters are initialized
            setTimeout(() => {
                if (document.getElementById('tab-graph').classList.contains('active')) {
                    loadGraph();
                }
            }, 500);
        });
        
        // Load graph when graph tab is opened
        let graphLoaded = false;
        const originalSwitchTab = switchTab;
        switchTab = function(tabName) {
            originalSwitchTab(tabName);
            if (tabName === 'graph') {
                if (!graphLoaded) {
                    loadGraph();
                    graphLoaded = true;
                } else {
                    // Reload graph when switching back to tab
                    loadGraph();
                }
            }
        };
    </script>
</body>
</html>
    """
    return html


@app.route('/api/anomalies/stats')
def get_anomalies_stats():
    """Get statistics about anomalies."""
    try:
        if anomalies_df.empty:
            return jsonify({
                'total': 0,
                'by_type': {},
                'by_month': {},
                'avg_confidence': 0.0
            })
        
        stats = {
            'total': len(anomalies_df),
            'by_type': anomalies_df['anomaly_type'].value_counts().to_dict() if 'anomaly_type' in anomalies_df.columns else {},
            'by_month': anomalies_df['month'].value_counts().to_dict() if 'month' in anomalies_df.columns else {},
            'avg_confidence': float(anomalies_df['confidence'].mean()) if 'confidence' in anomalies_df.columns else 0.0
        }
        
        return jsonify(stats)
    except Exception as e:
        print(f"Error in get_anomalies_stats: {e}")
        return jsonify({
            'total': 0,
            'by_type': {},
            'by_month': {},
            'avg_confidence': 0.0
        }), 500


@app.route('/api/anomalies/overview')
def anomalies_overview():
    """Returns monthly counts of each anomaly type."""
    try:
        if anomalies_df.empty:
            return jsonify({
                'months': [],
                'traffic_spike': [],
                'mix_shift': [],
                'forecast_spike': []
            })
        
        # Group by month and anomaly_type
        if 'month' not in anomalies_df.columns or 'anomaly_type' not in anomalies_df.columns:
            return jsonify({
                'months': [],
                'traffic_spike': [],
                'mix_shift': [],
                'forecast_spike': []
            })
        
        # Get all months sorted
        all_months = sorted(anomalies_df['month'].unique())
        
        # Count by type per month
        traffic_spike = []
        mix_shift = []
        forecast_spike = []
        
        for month in all_months:
            month_data = anomalies_df[anomalies_df['month'] == month]
            traffic_spike.append(int(len(month_data[month_data['anomaly_type'] == 'traffic_spike'])))
            mix_shift.append(int(len(month_data[month_data['anomaly_type'] == 'mix_shift'])))
            # Check for forecast spikes (either in anomaly_type or forecast_flag)
            forecast_count = len(month_data[
                (month_data['anomaly_type'].str.contains('forecast', case=False, na=False)) |
                (month_data.get('forecast_flag', pd.Series([False] * len(month_data))) == True)
            ])
            forecast_spike.append(int(forecast_count))
        
        return jsonify({
            'months': all_months,
            'traffic_spike': traffic_spike,
            'mix_shift': mix_shift,
            'forecast_spike': forecast_spike
        })
    except Exception as e:
        import traceback
        print(f"Error in anomalies_overview: {e}")
        print(traceback.format_exc())
        return jsonify({
            'months': [],
            'traffic_spike': [],
            'mix_shift': [],
            'forecast_spike': []
        }), 500


@app.route('/api/anomalies/top')
def top_anomalies():
    """Returns top 5 most interesting anomalies."""
    try:
        if anomalies_df.empty:
            return jsonify([])
        
        df = anomalies_df.copy()
        
        # Calculate interest score: combine confidence and deviation_ratio
        if 'deviation_ratio' in df.columns and 'confidence' in df.columns:
            df['interest_score'] = df['confidence'] * df['deviation_ratio']
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
        print(f"Error in top_anomalies: {e}")
        print(traceback.format_exc())
        return jsonify([]), 500


@app.route('/api/anomalies/insights')
def anomalies_insights():
    """Returns key insights about the anomalies."""
    try:
        if anomalies_df.empty:
            return jsonify({'insights': []})
        
        insights = []
        
        # Highest deviation anomaly
        if 'deviation_ratio' in anomalies_df.columns:
            max_dev = anomalies_df.loc[anomalies_df['deviation_ratio'].idxmax()]
            insights.append(
                f"In {max_dev.get('month', 'N/A')}, {max_dev.get('prev', 'N/A')} → {max_dev.get('curr', 'N/A')} "
                f"had the largest spike ({max_dev.get('deviation_ratio', 0):.1f}x baseline)."
            )
        
        # Page with most anomalies
        if 'curr' in anomalies_df.columns:
            top_page = anomalies_df['curr'].value_counts().index[0]
            count = int(anomalies_df['curr'].value_counts().iloc[0])
            insights.append(
                f"'{top_page}' appears in {count} anomaly records, the most of any page."
            )
        
        # Month with highest anomaly count
        if 'month' in anomalies_df.columns:
            top_month = anomalies_df['month'].value_counts().index[0]
            count = int(anomalies_df['month'].value_counts().iloc[0])
            insights.append(
                f"{top_month} had {count} anomalies, the highest count of any month."
            )
        
        # Most common referrer category (if available)
        if 'prev' in anomalies_df.columns:
            top_referrer = anomalies_df['prev'].value_counts().index[0]
            count = int(anomalies_df['prev'].value_counts().iloc[0])
            insights.append(
                f"'{top_referrer}' was the most common referrer source ({count} occurrences)."
            )
        
        return jsonify({'insights': insights[:4]})  # Limit to 4 insights
    except Exception as e:
        import traceback
        print(f"Error in anomalies_insights: {e}")
        print(traceback.format_exc())
        return jsonify({'insights': []}), 500


@app.route('/api/anomalies')
def get_anomalies():
    """Get anomalies with filtering."""
    try:
        if anomalies_df.empty:
            return jsonify({'anomalies': [], 'count': 0})
        
        df = anomalies_df.copy()
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
        
        # Apply confidence filter BEFORE sorting and limiting
        if min_confidence:
            df = df[df['confidence'] >= min_confidence]
            print(f"After confidence filter (>= {min_confidence}): {len(df)} rows")
        
        df = df.sort_values('confidence', ascending=False)
        if limit:
            df = df.head(limit)
        
        print(f"Returning {len(df)} anomalies (filters: type={anomaly_type}, confidence>={min_confidence}, month={month})")
        
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
                'total': 0, 'by_type': {}, 'by_month': {},
                'avg_confidence': 0.0, 'top_anomalies': []
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


@app.route('/api/timeseries')
def get_timeseries():
    """Get time-series data for a specific edge."""
    try:
        prev = request.args.get('prev')
        curr = request.args.get('curr')
        edge_type = request.args.get('type', '')
        
        if not prev or not curr:
            return jsonify({'months': [], 'traffic': [], 'baseline': [], 'forecast': []})
        
        if raw_data_df.empty:
            return jsonify({'months': [], 'traffic': [], 'baseline': [], 'forecast': []})
        
        # Filter raw data for this edge
        edge_filter = (raw_data_df['prev'] == prev) & (raw_data_df['curr'] == curr)
        if edge_type:
            edge_filter = edge_filter & (raw_data_df['type'] == edge_type)
        
        edge_data = raw_data_df[edge_filter].copy()
        
        if len(edge_data) == 0:
            return jsonify({'months': [], 'traffic': [], 'baseline': [], 'forecast': []})
        
        # Aggregate by month
        monthly_traffic = edge_data.groupby('month')['n'].sum().reset_index()
        monthly_traffic = monthly_traffic.sort_values('month')
        
        # Get baseline and forecast from anomalies if available
        baseline_median = 0
        forecast_n = None
        forecast_lower = None
        forecast_upper = None
        
        if not anomalies_df.empty:
            baseline_filter = (anomalies_df['prev'] == prev) & (anomalies_df['curr'] == curr)
            if edge_type:
                baseline_filter = baseline_filter & (anomalies_df['type'] == edge_type)
            
            baseline_row = anomalies_df[baseline_filter]
            if len(baseline_row) > 0:
                row = baseline_row.iloc[0]
                baseline_median = float(row.get('baseline_median', 0))
                if 'forecast_n' in row and pd.notna(row['forecast_n']):
                    forecast_n = float(row['forecast_n'])
                if 'forecast_lower' in row and pd.notna(row['forecast_lower']):
                    forecast_lower = float(row['forecast_lower'])
                if 'forecast_upper' in row and pd.notna(row['forecast_upper']):
                    forecast_upper = float(row['forecast_upper'])
        
        # Ensure all months are represented
        all_months = sorted(months)
        traffic_by_month = {}
        for _, row in monthly_traffic.iterrows():
            traffic_by_month[row['month']] = int(row['n'])
        
        traffic_list = [traffic_by_month.get(m, 0) for m in all_months]
        baseline_list = [baseline_median] * len(all_months)
        forecast_list = [forecast_n] * len(all_months) if forecast_n is not None else [None] * len(all_months)
        forecast_lower_list = [forecast_lower] * len(all_months) if forecast_lower is not None else [None] * len(all_months)
        forecast_upper_list = [forecast_upper] * len(all_months) if forecast_upper is not None else [None] * len(all_months)
        
        return jsonify({
            'months': all_months,
            'traffic': traffic_list,
            'baseline': baseline_list,
            'forecast': forecast_list,
            'forecast_lower': forecast_lower_list,
            'forecast_upper': forecast_upper_list
        })
    except Exception as e:
        import traceback
        print(f"Error in timeseries: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e), 'months': [], 'traffic': [], 'baseline': [], 'forecast': []}), 500


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
            anomaly_id_int = anomaly_id
        
        # Try multiple ways to find the anomaly
        if 'anomaly_id' in anomalies_df.columns:
            anomaly_row = anomalies_df[anomalies_df['anomaly_id'] == anomaly_id_int]
        else:
            # Fallback: use index
            try:
                if isinstance(anomaly_id_int, int) and 0 <= anomaly_id_int < len(anomalies_df):
                    anomaly_row = anomalies_df.iloc[[anomaly_id_int]]
                else:
                    anomaly_row = pd.DataFrame()
            except:
                anomaly_row = pd.DataFrame()
        
        if len(anomaly_row) == 0:
            return jsonify({'error': f'Anomaly not found: {anomaly_id}'}), 404
        
        anomaly = anomaly_row.iloc[0].to_dict()
        prev = anomaly.get('prev', '')
        curr = anomaly.get('curr', '')
        month = anomaly.get('month', '')
        edge_type = anomaly.get('type', 'link')
        
        # 1. Get 6-month time series
        timeseries_6m = []
        if not raw_data_df.empty:
            edge_data = raw_data_df[
                (raw_data_df['prev'] == prev) &
                (raw_data_df['curr'] == curr) &
                (raw_data_df['type'] == edge_type)
            ]
            monthly = edge_data.groupby('month')['n'].sum().reset_index().sort_values('month')
            timeseries_6m = monthly.tail(6).to_dict('records')
        
        # 2. Get forecast values
        forecast_values = {
            'forecast_n': anomaly.get('forecast_n', 0),
            'forecast_lower': anomaly.get('forecast_lower', 0),
            'forecast_upper': anomaly.get('forecast_upper', 0),
            'forecast_error': anomaly.get('forecast_error', 0),
            'forecast_ratio': anomaly.get('forecast_ratio', 1.0),
            'forecast_flag': bool(anomaly.get('forecast_flag', False))
        }
        
        # 3. Get referrer shares for last 6 months
        referrer_shares = []
        if not raw_data_df.empty:
            # Get last 6 months
            all_months = sorted(raw_data_df['month'].unique())
            last_6_months = all_months[-6:] if len(all_months) >= 6 else all_months
            
            for m in last_6_months:
                month_data = raw_data_df[
                    (raw_data_df['curr'] == curr) &
                    (raw_data_df['month'] == m)
                ]
                if len(month_data) > 0:
                    total = month_data['n'].sum()
                    if total > 0:
                        shares = month_data.groupby('prev')['n'].sum().reset_index()
                        shares['proportion'] = shares['n'] / total
                        shares = shares.sort_values('proportion', ascending=False)
                        
                        referrer_shares.append({
                            'month': m,
                            'total': int(total),
                            'referrers': shares.head(10).to_dict('records')
                        })
        
        # 4. Detection signals breakdown
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
        
        # 5. Get daily pageviews
        try:
            from src.external.pageviews_api import get_pageviews_for_anomaly
            daily_pageviews = get_pageviews_for_anomaly(curr, month, days_before=30, days_after=30)
        except:
            daily_pageviews = []
        
        # Check if daily spike matches monthly anomaly
        daily_spike_match = False
        if daily_pageviews and len(daily_pageviews) > 0:
            # Check if there's a spike in daily data around anomaly month
            anomaly_date = pd.to_datetime(month + '-15')
            views_around_anomaly = [
                pv for pv in daily_pageviews 
                if abs((pd.to_datetime(pv['date'], format='%Y%m%d') - anomaly_date).days) <= 7
            ]
            if views_around_anomaly:
                avg_views = np.mean([pv['views'] for pv in daily_pageviews])
                spike_views = [pv['views'] for pv in views_around_anomaly]
                if max(spike_views) > avg_views * 1.5:
                    daily_spike_match = True
        
        # 6. Get signals list
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
            signals.append('MAD-Z Score')
        if deviation_ratio >= 10:
            signals.append('High Deviation')
        
        # 7. Check referrer mix changes
        top_referrer_flip = False
        major_mix_shift = False
        if len(referrer_shares) >= 2:
            # Compare last month vs previous months
            last_month = referrer_shares[-1]
            prev_months = referrer_shares[:-1]
            
            if prev_months:
                # Get top referrer from previous months
                prev_top_refs = {}
                for m_data in prev_months:
                    if m_data['referrers']:
                        top_ref = m_data['referrers'][0]['prev']
                        prev_top_refs[top_ref] = prev_top_refs.get(top_ref, 0) + 1
                
                prev_top = max(prev_top_refs.items(), key=lambda x: x[1])[0] if prev_top_refs else None
                curr_top = last_month['referrers'][0]['prev'] if last_month['referrers'] else None
                
                if prev_top and curr_top and prev_top != curr_top:
                    top_referrer_flip = True
                
                # Check for major share change
                if prev_months and last_month['referrers']:
                    prev_share = 0
                    for m_data in prev_months:
                        for ref in m_data['referrers']:
                            if ref['prev'] == curr_top:
                                prev_share = max(prev_share, ref['proportion'])
                    
                    curr_share = last_month['referrers'][0]['proportion']
                    if abs(curr_share - prev_share) > 0.2:
                        major_mix_shift = True
        
        return jsonify({
            'anomaly': anomaly,
            'timeseries_6m': timeseries_6m,
            'forecast_values': forecast_values,
            'referrer_shares': referrer_shares,
            'detection_signals': detection_signals,
            'daily_pageviews': daily_pageviews,
            'daily_spike_match': daily_spike_match,
            'top_referrer_flip': top_referrer_flip,
            'major_mix_shift': major_mix_shift,
            'signals': signals
        })
    except Exception as e:
        import traceback
        print(f"Error in get_anomaly_detail: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/pageviews/<path:page_title>')
def get_pageviews(page_title):
    """Get daily pageviews for a Wikipedia page."""
    try:
        # Decode URL-encoded title
        from urllib.parse import unquote
        page_title = unquote(page_title).replace('_', ' ')
        
        # Get date range from query params or default to last 60 days
        from datetime import datetime, timedelta
        end_date = request.args.get('end', datetime.now().strftime('%Y%m%d'))
        days = int(request.args.get('days', 60))
        start_date = request.args.get('start', (datetime.now() - timedelta(days=days)).strftime('%Y%m%d'))
        
        # Use external pageviews API
        try:
            from src.external.pageviews_api import fetch_daily_pageviews
            data = fetch_daily_pageviews(page_title, start_date, end_date)
            
            return jsonify({
                'title': page_title,
                'data': data
            })
        except ImportError:
            # Fallback: generate mock data
            from src.external.pageviews_api import generate_daily_mock_data
            data = generate_daily_mock_data(page_title, start_date, end_date)
            return jsonify({
                'title': page_title,
                'data': data
            })
    except Exception as e:
        import traceback
        print(f"Error in get_pageviews: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e), 'title': page_title, 'data': []}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("Starting Dashboard")
    print("=" * 60)
    print(f"Loaded {len(anomalies_df)} anomalies")
    print("Access the dashboard at: http://localhost:2222")
    print("=" * 60)
    app.run(host='0.0.0.0', port=2222, debug=False)

