# Project Summary: Wikipedia Clickstream Anomaly Detection System

## Overview

This is a complete end-to-end system for detecting anomalies in Wikipedia clickstream data. The system processes tens of GB of monthly clickstream logs using Apache Spark and identifies three types of anomalies:

1. **Traffic Spikes**: Sudden increases in page transitions
2. **Navigation-Edge Anomalies**: Unusual navigation patterns detected via clustering
3. **Mix-Shift Anomalies**: Changes in referrer distribution for pages

## Project Structure

```
TermProject/
├── src/                          # Main source code
│   ├── etl/                     # Data ingestion and cleaning
│   │   └── clickstream_loader.py
│   ├── features/                 # Feature engineering
│   │   └── baseline.py
│   ├── detectors/                # Anomaly detection methods
│   │   ├── statistical_detector.py
│   │   ├── clustering_detector.py
│   │   └── mix_shift_detector.py
│   ├── storage/                  # Data models and storage
│   │   └── anomalies_schema.py
│   ├── pipeline/                 # Main pipeline orchestration
│   │   └── anomaly_detection_pipeline.py
│   ├── dashboard/                # Web dashboard
│   │   ├── app.py
│   │   └── templates/index.html
│   ├── streaming/                # Streaming demo
│   │   └── streaming_demo.py
│   ├── evaluation/               # Evaluation utilities
│   │   └── metrics.py
│   └── utils/                    # Utilities
│       ├── config.py
│       └── spark_session.py
├── scripts/                       # Executable scripts
│   ├── download_clickstream.py
│   ├── run_etl.py
│   ├── run_detection.py
│   ├── start_dashboard.py
│   ├── evaluate.py
│   └── setup.py
├── config/                        # Configuration files
│   ├── config.example.yaml
│   └── config.yaml
├── data/                          # Data directories
│   ├── raw/                      # Raw TSV files
│   ├── processed/                # Processed Parquet files
│   └── anomalies/                # Anomaly results
├── notebooks/                     # Jupyter notebooks
├── tests/                         # Unit tests
├── requirements.txt              # Python dependencies
├── README.md                     # Main documentation
├── USAGE.md                      # Usage guide
└── Makefile                      # Convenience commands
```

## Key Components

### 1. ETL Pipeline (`src/etl/`)

- Loads Wikipedia clickstream TSV files
- Cleans and normalizes page identifiers
- Filters low-volume edges
- Saves to Parquet format for efficient processing

### 2. Feature Engineering (`src/features/`)

- Calculates baseline statistics (median, mean, MAD) for each edge
- Builds feature vectors for clustering
- Computes referrer distributions for mix-shift detection

### 3. Anomaly Detectors (`src/detectors/`)

**Statistical Detector:**
- Uses robust Z-scores with MAD (Median Absolute Deviation)
- Flags edges with Z-score > 3.5 or ratio > 10x baseline
- Calculates confidence scores using sigmoid function

**Clustering Detector:**
- Uses K-means clustering on edge feature vectors
- Identifies edges far from cluster centers
- Detects unusual navigation patterns

**Mix-Shift Detector:**
- Compares referrer distributions across months
- Uses top referrer changes and proportion shifts
- Flags significant distribution changes

### 4. Dashboard (`src/dashboard/`)

- Flask-based web application
- Interactive anomaly table with filtering
- Statistics overview
- Network graph visualization
- RESTful API for data access

### 5. Pipeline Orchestration (`src/pipeline/`)

- Coordinates all components
- Runs ETL → Features → Detection → Storage
- Handles errors and logging

## Data Flow

```
Raw TSV Files
    ↓
ETL (Cleaning & Normalization)
    ↓
Parquet Storage
    ↓
Feature Engineering (Baselines, Features, Distributions)
    ↓
Anomaly Detection (3 detectors in parallel)
    ↓
Anomalies Table (Parquet)
    ↓
Dashboard (Visualization & Exploration)
```

## Usage

See `USAGE.md` for detailed instructions. Quick start:

```bash
# Setup
python scripts/setup.py
pip install -r requirements.txt

# Download data
python scripts/download_clickstream.py --months 2023-09 2023-10 2023-11

# Run pipeline
python scripts/run_etl.py
python scripts/run_detection.py

# Start dashboard
python scripts/start_dashboard.py
```

## Configuration

All settings are in `config/config.yaml`:

- **Spark**: Memory, cores, master URL
- **Data**: Paths, months, filters
- **Detection**: Thresholds for each detector
- **Dashboard**: Host, port, debug mode

## Success Criteria

✅ **Processing Scale**: Handles ≥ 50 GB of data via Spark  
✅ **Detection Quality**: Three distinct anomaly types implemented  
✅ **End-to-End**: Complete pipeline from raw data to dashboard  
✅ **Documentation**: Comprehensive README and usage guides  

## Team Responsibilities

- **Dirgha Jivani**: Spark config, ETL, clustering detector, backend
- **Harshith Keshavamurthy**: Statistical detector, performance tuning, evaluation
- **Aryaman Jalali**: Storage schema, baseline calculations, dashboard UI

## Technologies Used

- **Apache Spark**: Distributed data processing
- **PySpark**: Python API for Spark
- **Flask**: Web framework for dashboard
- **Plotly/D3.js**: Visualization libraries
- **Pandas/NumPy**: Data manipulation
- **Scipy**: Statistical functions (Jensen-Shannon divergence)

## Future Enhancements

- Real-time streaming with Kafka
- Machine learning models (isolation forest, autoencoders)
- More sophisticated graph visualizations
- Integration with Wikipedia Pageviews API
- Automated alerting system
- Performance optimizations (caching, indexing)

## Notes

- The system is designed to be scalable and can run on a Spark cluster
- For local testing, use smaller datasets or fewer months
- Memory requirements depend on data size; adjust Spark config accordingly
- The dashboard requires anomalies to be generated first

