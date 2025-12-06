# Usage Guide

## Quick Start

1. **Setup the project:**
```bash
python scripts/setup.py
pip install -r requirements.txt
```

2. **Download data:**
```bash
python scripts/download_clickstream.py --months 2023-09 2023-10 2023-11 2023-12 2024-01 2024-02
```

3. **Run ETL:**
```bash
python scripts/run_etl.py
```

4. **Run anomaly detection:**
```bash
python scripts/run_detection.py
```

5. **Start dashboard:**
```bash
python scripts/start_dashboard.py
```

Then open `http://localhost:5000` in your browser.

## Detailed Workflow

### Step 1: Data Download

The clickstream data files are large (several GB each). Download them using:

```bash
python scripts/download_clickstream.py --months 2023-09 2023-10 2023-11
```

Files will be saved to `data/raw/` directory.

**Note:** The actual file naming on Wikipedia may vary. You may need to:
1. Check the actual URLs at https://dumps.wikimedia.org/other/clickstream/
2. Manually download and rename files if needed
3. Or modify the download script to match the actual naming convention

### Step 2: ETL Pipeline

The ETL pipeline:
- Loads TSV files
- Cleans and normalizes data
- Filters low-volume edges
- Saves to Parquet format for faster processing

```bash
python scripts/run_etl.py --config config/config.yaml
```

### Step 3: Anomaly Detection

Runs all three detectors:
- Statistical detector (traffic spikes)
- Clustering detector (navigation edges)
- Mix-shift detector (referrer distribution changes)

```bash
python scripts/run_detection.py --config config/config.yaml
```

Results are saved to `data/anomalies/` in Parquet format.

### Step 4: Dashboard

Interactive web dashboard to explore anomalies:

```bash
python scripts/start_dashboard.py --port 5000
```

Features:
- Filter anomalies by month, type, confidence
- View statistics
- Network graph visualization
- Detailed anomaly information

### Step 5: Evaluation

Evaluate detection results:

```bash
python scripts/evaluate.py --anomalies data/anomalies
```

## Configuration

Edit `config/config.yaml` to customize:

- **Spark settings**: Memory, cores, master URL
- **Data paths**: Input/output directories
- **Detection thresholds**: Z-score, ratio thresholds, etc.
- **Dashboard settings**: Host, port

## Troubleshooting

### Out of Memory

If you get memory errors:
1. Reduce `executor_memory` and `driver_memory` in config
2. Process fewer months at a time
3. Increase `min_transitions` to filter more edges

### No Data Files

If download fails:
1. Check internet connection
2. Verify file URLs at Wikipedia dumps site
3. Manually download and place in `data/raw/`

### Spark Not Found

If Spark errors occur:
1. Install Java 8 or 11
2. Set `JAVA_HOME` environment variable
3. Or use PySpark (included in requirements.txt)

## Performance Tips

1. **Use Parquet format**: Already configured, but ensure you're using it
2. **Partition data**: Data is partitioned by month for faster queries
3. **Filter early**: `min_transitions` filter reduces data size
4. **Cluster mode**: For large datasets, use `master: "yarn"` in config

## Next Steps

- Add more anomaly types
- Integrate with real-time data streams
- Add machine learning models
- Expand dashboard visualizations

