# Wikipedia Clickstream Anomaly Detection System

**MET CS 777 Term Project - Group 7**

**Team Members:**
- Harshith Keshavamurthy
- Aryaman Jalali
- Dirgha Jivani

---

## 📋 Table of Contents
- [Overview](#overview)
- [Project Structure](#project-structure)
- [Environment Setup](#environment-setup)
- [How to Run the Code](#how-to-run-the-code)
- [Dataset Description](#dataset-description)
- [Results](#results)
- [Troubleshooting](#troubleshooting)
- [Code Quality](#code-quality)

---

## 🔍 Overview

This project implements an **end-to-end Big Data pipeline** for detecting anomalies in Wikipedia clickstream data. The system processes large-scale clickstream logs (tens of GB) using Apache Spark to identify unusual patterns in user navigation.

### Anomaly Types Detected

1. **Traffic Spikes** 📈
   - Sudden, statistically significant increases in page transitions
   - Detection method: Robust Z-scores with MAD (Median Absolute Deviation)
   - Threshold: Z-score > 3.5 or deviation ratio > 10x baseline

2. **Mix-Shift Anomalies** 🔄
   - Significant changes in the distribution of traffic sources for a page
   - Detection method: Referrer distribution analysis
   - Indicates changes in how users discover content

3. **Navigation-Edge Anomalies** 🗺️
   - Unusual navigation patterns that deviate from established clusters
   - Detection method: K-means clustering on edge feature vectors
   - Identifies rare or anomalous user paths

---

## 📁 Project Structure

```
METCS777-TermProject-Group7/
├── src/                          # Main source code
│   ├── etl/                      # Data ingestion and cleaning
│   │   └── clickstream_loader.py
│   ├── features/                 # Feature engineering (baselines)
│   │   └── baseline.py
│   ├── detectors/                # Anomaly detection algorithms
│   │   ├── statistical_detector.py    # Traffic spike detection
│   │   ├── clustering_detector.py     # Navigation edge detection
│   │   └── mix_shift_detector.py      # Mix-shift detection
│   ├── storage/                  # Data storage schemas
│   │   └── anomalies_schema.py
│   ├── pipeline/                 # Pipeline orchestration
│   │   └── anomaly_detection_pipeline.py
│   ├── dashboard/                # Flask web application
│   │   ├── app.py
│   │   └── templates/
│   ├── external/                 # External API integrations
│   │   └── pageviews_api.py
│   └── utils/                    # Shared utilities
│       ├── config.py
│       └── spark_session.py
├── scripts/                      # Executable scripts
│   ├── download_clickstream.py   # Data downloader
│   ├── run_detection.py          # Main Spark pipeline runner
│   └── start_dashboard_demo.py   # Dashboard server
├── config/                       # Configuration files
│   └── config.yaml               # All pipeline parameters
├── data/                         # Data directory (gitignored)
│   ├── raw/                      # Raw TSV files
│   ├── processed/                # Processed Parquet files
│   └── anomalies/                # Detected anomalies
├── tests/                        # Unit tests
├── run_pipeline.py               # ⭐ Easy-to-run pipeline script
├── run_dashboard.py              # ⭐ Easy-to-run dashboard script
├── requirements.txt              # Python dependencies
└── README.md                     # Project documentation
```

---

## 🛠️ Environment Setup

### Prerequisites

Before you begin, ensure you have the following installed:

1. **Python 3.8+**
   ```bash
   python --version  # Should be 3.8 or higher
   ```

2. **Java 8 or 11** (Required for Apache Spark)
   ```bash
   java -version  # Should be 1.8 or 11
   ```
   
   - **macOS**: 
     ```bash
     brew install openjdk@11
     ```
   - **Ubuntu/Debian**:
     ```bash
     sudo apt-get install openjdk-11-jdk
     ```
   - **Windows**: Download from [Oracle](https://www.oracle.com/java/technologies/downloads/)

3. **System Requirements**
   - **RAM**: Minimum 8GB (16GB recommended for full dataset)
   - **Disk Space**: ~10GB for data and dependencies

### Installation Steps

#### Step 1: Clone the Repository

```bash
git clone https://github.com/HarshithKeshavamurthy17/METCS777-TermProject-Group7.git
cd METCS777-TermProject-Group7
```

#### Step 2: Create a Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

#### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `pyspark>=3.5.0` - Apache Spark for distributed processing
- `flask>=3.0.0` - Web framework for dashboard
- `pandas>=2.0.0` - Data manipulation
- `numpy>=1.24.0` - Numerical computing
- `scipy>=1.10.0` - Scientific computing
- `requests>=2.31.0` - HTTP requests
- `pyyaml>=6.0` - Configuration file parsing

#### Step 4: Verify Installation

```bash
# Test Spark
python -c "from pyspark.sql import SparkSession; print('Spark OK')"

# Test other dependencies
python -c "import flask, pandas, numpy; print('All dependencies OK')"
```

---

## ▶️ How to Run the Code

### Quick Start (3 Simple Steps)

#### 1️⃣ Download Data

```bash
python scripts/download_clickstream.py --months 2023-09 2023-10 2023-11 2023-12 2024-01 2024-02
```

**What this does:**
- Downloads Wikipedia clickstream TSV files from Wikimedia dumps
- Saves files to `data/raw/`
- Each file is ~1-2GB compressed

**Note:** This can take 10-30 minutes depending on your internet speed.

#### 2️⃣ Run the Pipeline

```bash
python run_pipeline.py
```

**What this does:**
1. **ETL Phase**: Loads and cleans TSV files
2. **Feature Engineering**: Calculates baselines (median, MAD, etc.)
3. **Anomaly Detection**: Runs all three detectors in parallel
4. **Storage**: Saves results to `data/anomalies/` in Parquet format

**Expected output:**
```
Starting Anomaly Detection Pipeline...
✓ ETL completed: 10,234,567 edges processed
✓ Baseline calculated: 1,567,890 unique edges
✓ Statistical detector: 2,216 traffic spikes found
✓ Mix-shift detector: 130 mix shifts found
✓ Clustering detector: 0 navigation edges found
✓ Total anomalies: 2,346
✓ Saved to data/anomalies/
```

**Runtime:** ~10-20 minutes for 6 months of data (depends on your machine)

#### 3️⃣ Start the Dashboard

```bash
python run_dashboard.py
```

**What this does:**
- Launches a Flask web server on `http://localhost:5000`
- Loads all detected anomalies from `data/anomalies/`
- Provides interactive visualizations and filtering

**Expected output:**
```
Starting Dashboard...
✓ Loaded 2,346 anomalies from partitioned parquet files
✓ Months with anomalies: ['2023-09', '2023-10', '2023-11', '2023-12', '2024-01', '2024-02', '2024-03']
 * Running on http://127.0.0.1:5000
```

**Access the dashboard:**
Open your browser and navigate to: **http://localhost:5000**

---

## 📊 Dataset Description

### Wikipedia Clickstream Data

The Wikipedia Clickstream dataset contains counts of (referrer, resource) pairs extracted from the request logs of Wikipedia.

**Source:** [Wikimedia Dumps - Clickstream](https://dumps.wikimedia.org/other/clickstream/)

**Format:** TSV (Tab-Separated Values)

**Schema:**
| Column | Type   | Description |
|--------|--------|-------------|
| `prev` | string | Referrer page (where the user came from) |
| `curr` | string | Current page (where the user navigated to) |
| `type` | string | Link type (e.g., `link`, `external`, `other`) |
| `n`    | int    | Number of transitions (count) |

**Example Row:**
```
Google	Main_Page	external	12453
```
This means 12,453 users navigated from Google to Wikipedia's Main Page.

**Dataset Size:**
- **Months Processed**: 6 months (Sep 2023 - Feb 2024)
- **Total Records**: ~10 million edges per month
- **Compressed Size**: ~1-2GB per month
- **Uncompressed Size**: ~5-10GB per month

---

## 📈 Results

### Summary Statistics

Running the pipeline on 6 months of data (Sep 2023 - Feb 2024) produced:

| Metric | Value |
|--------|-------|
| **Total Anomalies Detected** | 2,346 |
| **Traffic Spikes** | 2,216 (94.5%) |
| **Mix-Shift Anomalies** | 130 (5.5%) |
| **Navigation Edges** | 0 (0%) |
| **Max Deviation Ratio** | 153.62x |
| **Avg Deviation Ratio** | 33.84x |

### Anomalies by Month

```
2023-09:  252 anomalies
2023-10:  543 anomalies
2023-11:  557 anomalies
2023-12:  251 anomalies
2024-01:  249 anomalies
2024-02:  249 anomalies
2024-03:  245 anomalies
```

### Example Anomalies

#### 1. Traffic Spike Example
```
Referrer: Main_Page
Target: 2023_Israel–Hamas_war
Month: 2023-10
Deviation Ratio: 153.62x
Z-Score: 45.2
```
**Interpretation:** This spike corresponds to the outbreak of the Israel-Hamas war in October 2023, causing massive traffic from Wikipedia's main page to the war article.

#### 2. Mix-Shift Example
```
Target Page: United_States
Month: 2023-11
Top Referrer Change: other-search → Main_Page (+35%)
```
**Interpretation:** The United States page saw a significant shift in traffic sources, with more users arriving from the main page instead of search engines.

### Dashboard Features

The interactive dashboard provides:

1. **Overview Charts** 📊
   - Monthly anomaly counts by type
   - Trend analysis across time

2. **Filterable Anomaly Table** 🔍
   - Filter by month, type, and deviation threshold
   - Sort by any column
   - Export capabilities

3. **Explainability Panel** 🧠
   - Detailed breakdown of detection signals
   - Time-series charts showing traffic patterns
   - Referrer distribution changes
   - Z-score and deviation ratio visualizations

4. **Top Anomalies** 🏆
   - Highlights the 5 most significant anomalies
   - Quick navigation to interesting cases

---

## 🔧 Troubleshooting

### Common Issues

#### Issue 1: "Out of Memory" Error

**Symptoms:**
```
java.lang.OutOfMemoryError: Java heap space
```

**Solution:**
Edit `config/config.yaml` and reduce memory allocation:
```yaml
spark:
  executor_memory: "4g"  # Reduce from 8g
  driver_memory: "4g"    # Reduce from 8g
```

Or process fewer months at a time.

---

#### Issue 2: "Port 5000 Already in Use"

**Symptoms:**
```
Address already in use
Port 5000 is in use by another program
```

**Solution:**
Run the dashboard on a different port:
```bash
PORT=5002 python run_dashboard.py
```

Then access via `http://localhost:5002`

---

#### Issue 3: "JAVA_HOME Not Set"

**Symptoms:**
```
Please set JAVA_HOME
```

**Solution:**
Set the JAVA_HOME environment variable:
```bash
# macOS/Linux (add to ~/.bashrc or ~/.zshrc)
export JAVA_HOME=$(/usr/libexec/java_home)

# Or manually:
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-11.jdk/Contents/Home
```

---

#### Issue 4: Download Script Fails

**Symptoms:**
```
Failed to download clickstream data
```

**Solution:**
Manually download files from:
https://dumps.wikimedia.org/other/clickstream/

Then place them in `data/raw/` with naming: `clickstream-YYYY-MM.tsv.gz`

---

## ✅ Code Quality

### Design Principles

1. **Modularity** 🧩
   - Clean separation between ETL, feature engineering, and detection
   - Each detector is independent and can be run separately
   - Easy to add new anomaly detection methods

2. **Configuration-Driven** ⚙️
   - All parameters in `config/config.yaml`
   - No hardcoded values
   - Easy to tune thresholds without code changes

3. **Scalability** 📈
   - Built on Apache Spark for distributed processing
   - Handles datasets exceeding local memory
   - Partitioned storage for efficient querying

4. **Documentation** 📝
   - Comprehensive docstrings in all modules
   - Inline comments explaining complex logic
   - Type hints for better code clarity

5. **Error Handling** 🛡️
   - Graceful degradation when external APIs fail
   - Fallback mechanisms for missing data
   - Clear error messages with debugging guidance

### Code Comments

All code files include:
- Module-level docstrings explaining purpose
- Function/class docstrings with parameters and return types
- Inline comments for complex algorithms
- Examples in critical sections

---

## 🎓 Academic Context

**Course:** MET CS 777 - Big Data Analytics  
**Institution:** Boston University Metropolitan College  
**Semester:** Fall 2024  
**Submission Date:** December 2024

---

## 📧 Contact

For questions or issues, please contact:
- Harshith Keshavamurthy
- Aryaman Jalali
- Dirgha Jivani

---

## 📄 License

This project is submitted as part of academic coursework for MET CS 777.

---

**Happy Anomaly Hunting! 🔍**
