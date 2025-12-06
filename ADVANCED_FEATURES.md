# Advanced Features Documentation

## Overview

This document describes the advanced "Next Level" features added to the Wikipedia Clickstream Anomaly Detection System.

## 🎯 Features Added

### 1. Time-Series Forecasting (`src/features/forecasting.py`)

**Purpose**: Predict future traffic for each edge and flag anomalies when actual traffic deviates significantly from forecasts.

**Implementation**:
- **Primary**: Prophet (Facebook's time-series forecasting library)
- **Fallback 1**: ARIMA (statsmodels)
- **Fallback 2**: Exponential Smoothing (statsmodels)
- **Fallback 3**: Simple Moving Average (built-in)

**Features**:
- Forecasts next-month traffic for each edge
- Computes confidence intervals (forecast_lower, forecast_upper)
- Flags anomalies when:
  - Actual traffic > forecast_upper, OR
  - Actual traffic > forecast_n * ratio_threshold (default 2.0x)

**Configuration**:
```yaml
forecasting:
  enable: false  # Set to true to enable
  min_history_months: 6
  model_type: "prophet"  # prophet, arima, exponential, moving_avg
  forecast_ratio_threshold: 2.0
  forecast_upper_threshold: true
```

**Usage**: Automatically integrated into pipeline when enabled. Results appear in anomalies table with `forecast_flag`, `forecast_n`, `forecast_error`, etc.

---

### 2. GNN-Based Anomaly Detection (`src/detectors/gnn_detector.py`)

**Purpose**: Use graph structure and embeddings to detect anomalous navigation patterns.

**Implementation**:
- **Primary**: GraphSAGE/GAT using PyTorch Geometric
- **Fallback 1**: Node2Vec embeddings
- **Fallback 2**: DeepWalk-style embeddings (simple random walks)
- **Fallback 3**: Disabled gracefully if no graph libraries available

**Features**:
- Builds directed graph from clickstream edges
- Computes node embeddings
- Calculates anomaly scores based on embedding distances
- Flags edges above percentile threshold (default P95)

**Configuration**:
```yaml
gnn_detector:
  enable: false  # Set to true to enable
  method: "auto"  # auto, gnn, node2vec, deepwalk
  score_percentile: 95.0
  max_edges_for_graph: 10000
  embedding_dim: 64
```

**Usage**: Runs as additional detector in pipeline. Adds `gnn_score` and `gnn_flag` to anomalies.

---

### 3. Pageviews API Integration (`src/integrations/pageviews_api.py`)

**Purpose**: Fetch daily pageview data from Wikimedia API for pages flagged as anomalies.

**Features**:
- Fetches daily pageviews for Wikipedia articles
- Configurable date windows (before/after anomaly)
- Rate limiting and error handling
- Caching via LRU cache

**Configuration**:
```yaml
pageviews:
  enable: true
  project: "en.wikipedia.org"
  access: "all-access"
  agent: "user"
  granularity: "daily"
  window_days_before: 30
  window_days_after: 30
  rate_limit_delay: 0.1
```

**API Endpoint**: `GET /api/pageviews/<page_title>`

**Usage**: Used in explainability panel to show daily pageview trends around anomaly dates.

---

### 4. Explainability Module (`src/features/explainability.py`)

**Purpose**: Generate rich explanations for detected anomalies.

**Features**:
- Time-series analysis for edges
- Referrer distribution analysis
- Signal extraction (which detectors fired)
- Human-readable explanations

**Functions**:
- `get_anomaly_timeseries()`: Get historical traffic data
- `get_referrer_distribution()`: Get referrer mix over time
- `generate_explanation()`: Create narrative explanation
- `get_signals()`: Extract all detection signals

**Usage**: Used by dashboard explainability panel.

---

### 5. Material UI Dashboard (`src/dashboard/templates/material_dashboard.html`)

**Purpose**: Modern, beautiful dashboard with explainability panel.

**Features**:
- **Material Design** components and styling
- **Statistics Cards**: Total anomalies, spikes, mix shifts, confidence
- **Filterable Table**: Search and filter anomalies
- **Explainability Panel**: Slide-out panel with:
  - Anomaly overview
  - Detection signals (badges/chips)
  - Human-readable explanation
  - Time-series chart (actual, baseline, forecast)
  - Referrer distribution (future enhancement)

**UI Highlights**:
- Clean, modern Material Design
- Responsive layout
- Smooth animations
- Clear visual hierarchy
- Good storytelling through explanations

**Access**: Click "View Details" on any anomaly row to open explainability panel.

---

## 🔧 Integration Points

### Pipeline Integration (`src/pipeline/anomaly_detection_pipeline.py`)

All new features are integrated into the main pipeline:

1. **Forecasting**: Runs during feature engineering phase
2. **GNN Detector**: Runs as additional detector in detection phase
3. **Signals**: Automatically compiled from all detectors
4. **Schema**: Extended to include new fields

### Storage Schema (`src/storage/anomalies_schema.py`)

New fields added:
- `forecast_n`, `forecast_lower`, `forecast_upper`
- `forecast_error`, `forecast_ratio`, `forecast_flag`
- `gnn_score`, `gnn_flag`
- `signals` (comma-separated string)

### Dashboard Backend (`scripts/start_dashboard_simple.py`)

New endpoints:
- `GET /api/anomalies/<id>`: Detailed anomaly info with explainability
- `GET /api/pageviews/<title>`: Daily pageview data
- `GET /api/timeseries`: Enhanced with forecast data

---

## 📦 Dependencies

### Required
- All existing dependencies (pyspark, pandas, flask, etc.)

### Optional (for advanced features)
```bash
# Forecasting
pip install prophet  # or fbprophet
# OR
pip install statsmodels  # For ARIMA fallback

# GNN Detection
pip install torch torch-geometric networkx node2vec

# All are optional - system degrades gracefully if missing
```

---

## 🚀 Usage

### Enable Features

Edit `config/config.yaml`:

```yaml
forecasting:
  enable: true

gnn_detector:
  enable: true

pageviews:
  enable: true

explainability_panel:
  enable: true
```

### Run Pipeline

```bash
# Standard pipeline (features auto-enabled if config says so)
python scripts/run_detection.py

# Start dashboard
python scripts/start_dashboard_simple.py
# Access at http://localhost:2222
```

### View Explainability

1. Open dashboard
2. Browse anomalies table
3. Click "View Details" on any anomaly
4. Explore:
   - Detection signals
   - Explanation narrative
   - Time-series chart
   - Forecast vs actual

---

## 🎨 UI/UX Highlights

### Material Design
- Clean, modern interface
- Consistent color scheme
- Smooth animations
- Responsive layout

### Storytelling
- Clear anomaly explanations
- Visual time-series charts
- Signal badges showing which detectors fired
- Confidence indicators

### Readability
- Large, clear typography
- Good contrast ratios
- Logical information hierarchy
- Intuitive navigation

---

## 🔄 Backward Compatibility

**All features are backward compatible**:
- Default config has all advanced features **disabled**
- Existing scripts work without changes
- Missing optional libraries cause graceful degradation (warnings, not errors)
- Old anomaly data still loads correctly (new fields are nullable)

---

## 📝 Notes

1. **Forecasting** requires at least 6 months of history (configurable)
2. **GNN detector** may be slow for very large graphs (use `max_edges_for_graph` to limit)
3. **Pageviews API** has rate limits - caching helps but be mindful
4. **Explainability panel** loads data on-demand (may take a moment for first load)

---

## 🐛 Troubleshooting

### Forecasting not working?
- Check if Prophet/statsmodels installed: `pip install prophet` or `pip install statsmodels`
- Verify `min_history_months` - need enough data
- Check logs for warnings

### GNN detector disabled?
- Install: `pip install torch torch-geometric networkx`
- Or use fallback: set `method: "deepwalk"` (only needs networkx)

### Pageviews API errors?
- Check internet connection
- Verify page title encoding (spaces → underscores)
- Check rate limiting settings

### Dashboard not loading?
- Check Flask is running: `python scripts/start_dashboard_simple.py`
- Verify anomalies file exists: `data/anomalies/anomalies.parquet`
- Check browser console for errors

---

## 🎯 Future Enhancements

Potential improvements:
- Real-time streaming with Kafka
- More sophisticated GNN models
- Interactive referrer distribution charts
- Export explanations to PDF
- Alert system for high-confidence anomalies
- Machine learning model integration (isolation forest, autoencoders)

---

## 📚 References

- [Prophet Documentation](https://facebook.github.io/prophet/)
- [PyTorch Geometric](https://pytorch-geometric.readthedocs.io/)
- [Material Design Guidelines](https://material.io/design)
- [Wikimedia Pageviews API](https://wikimedia.org/api/rest_v1/metrics/pageviews/)



