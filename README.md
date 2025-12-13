# Wikipedia Clickstream Anomaly Detection System

**Team 7 - MET CS 777 Big Data Analytics**  
Harshith Keshavamurthy • Aryaman Jalali • Dirgha Jivani

---

## What We Built

We built a complete Big Data pipeline that analyzes Wikipedia clickstream data to find unusual navigation patterns. Think of it like this: millions of people navigate Wikipedia every day, clicking from one article to another. Our system processes all those clicks (tens of GB of data per month) and automatically identifies three types of anomalies:

1. **Traffic Spikes** - When an article suddenly gets WAY more traffic than normal (like when breaking news happens)
2. **Mix-Shifts** - When the sources of traffic to an article change dramatically (e.g., suddenly everyone's coming from Google instead of other Wikipedia pages)
3. **Navigation Edges** - Unusual paths between articles that don't match normal user behavior

We used Apache Spark to handle the massive data volumes and built an interactive dashboard where you can explore all the anomalies we found.

---

## What You Need Before Starting

### Required Software

**1. Python 3.8 or higher** (Python 3.11 recommended)

Check if you have it:
```bash
python3 --version
```

If you see `Python 3.8.x` or higher, you're good! If not, download from [python.org](https://www.python.org/downloads/).

**2. Java 8 or 11** (needed for Spark)

Check if you have it:
```bash
java -version
```

You should see something like `java version "11.0.x"` or `"1.8.0_xxx"`.

**If you don't have Java:**
- **Mac**: `brew install openjdk@11`
- **Ubuntu/Debian**: `sudo apt-get install openjdk-11-jdk`
- **Windows**: Download from [Oracle](https://www.oracle.com/java/technologies/downloads/)

**3. At least 8GB of RAM** (16GB is better)

**4. About 20GB of free disk space** (if you download all the data)

---

## 🚀 COMPLETE SETUP & RUN GUIDE 

**This section walks through EVERY SINGLE STEP from scratch. Follow this if you want to run the entire project without missing anything.**

### Prerequisites Check

Before starting, let's verify everything:

**1. Check Python:**
```bash
python3 --version
```
Should show: `Python 3.8.x` or higher (3.11 recommended)

**2. Check Java:**
```bash
java -version
```
Should show: `openjdk version "11.0.x"` or `java version "1.8.0_xxx"`

**3. Check pip:**
```bash
pip3 --version
```
Should show: `pip 20.x` or higher

**If any of these fail, install them first** (see "Required Software" above).

---

### Part 1: Get the Code 

**Step 1.1: Open Terminal**
- **Mac**: Press `Cmd + Space`, type "Terminal", press Enter
- **Windows**: Press `Win + R`, type "cmd", press Enter
- **Linux**: Press `Ctrl + Alt + T`

**Step 1.2: Navigate to where you want the project**
```bash
cd ~/Downloads  # Or wherever you want to put it
```

**Step 1.3: Clone the repository**
```bash
git clone https://github.com/HarshithKeshavamurthy17/METCS777-TermProject-Group7.git
```

**Expected output:**
```
Cloning into 'METCS777-TermProject-Group7'...
remote: Enumerating objects: 201, done.
remote: Counting objects: 100% (201/201), done.
...
Resolving deltas: 100% (73/73), done.
```

**Step 1.4: Enter the project folder**
```bash
cd METCS777-TermProject-Group7
```

**Step 1.5: Verify you're in the right place**
```bash
ls
```

**You should see:**
```
README.md
requirements.txt
run_pipeline.py
run_dashboard.py
config/
src/
scripts/
data/
...
```

✅ **If you see these files, you're good to go!**

**Step 1.6: Verify config file exists (optional)**
```bash
ls config/
```

**You should see:**
```
config.yaml
config.example.yaml
```

> **Note:** If `config.yaml` doesn't exist, the code will automatically use `config.example.yaml`. However, if you want to customize settings, you can copy the example:
> ```bash
> cp config/config.example.yaml config/config.yaml
> ```

✅ **Config files are ready!**

---

### Part 2: Set Up Python Environment 

**Step 2.1: Create virtual environment**
```bash
python3 -m venv venv
```

**Expected output:**
```
(Nothing - it just creates a venv/ folder)
```

**Verify it was created:**
```bash
ls venv
```
You should see: `bin/`, `lib/`, `include/`, etc.

**Step 2.2: Activate the virtual environment**

**On Mac/Linux:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

**Expected result:**
Your terminal prompt should now start with `(venv)`. Example:
```
(venv) user@computer:~/METCS777-TermProject-Group7$
```

✅ **If you see (venv), it worked!**

**Step 2.3: Upgrade pip (optional but recommended)**
```bash
pip install --upgrade pip
```

**Step 2.4: Install all dependencies**
```bash
pip install -r requirements.txt
```

**Expected output:**
```
Collecting pyspark==3.5.0
  Downloading pyspark-3.5.0-py2.py3-none-any.whl (317 MB)
     ━━━━━━━━━━━━━━━━━━━━━━ 317.0/317.0 MB 5.2 MB/s
Collecting flask>=3.0.0
  Downloading Flask-3.0.0-py3-none-any.whl (99 kB)
Collecting flask-cors>=4.0.0
Collecting pandas>=2.0.0
Collecting numpy>=1.24.0
Collecting scipy>=1.10.0
Collecting requests>=2.31.0
Collecting pyyaml>=6.0
Collecting pyarrow>=14.0.0
...
Successfully installed flask-3.1.2 flask-cors-6.0.1 numpy-2.3.5 pandas-2.3.3 pyspark-3.5.0 pyarrow-22.0.0 pyyaml-6.0.3 requests-2.32.5 scipy-1.16.3 ...
```

**This takes 2-3 minutes. Be patient!**

> **Note:** If you see dependency conflicts or warnings about pyspark-client/pyspark-connect, you can ignore them. The main pyspark package will work correctly.

**Step 2.5: Verify installation**
```bash
python -c "from pyspark.sql import SparkSession; print('✓ Spark works!')"
```

**Expected output:**
```
✓ Spark works!
```

```bash
python -c "import flask, pandas, numpy; print('✓ All libraries loaded!')"
```

**Expected output:**
```
✓ All libraries loaded!
```

✅ **If both print checkmarks, your environment is ready!**

---

### Part 3: Check the Data (1 minute)

We've included pre-generated anomaly results so you don't need to download 60GB of data or run the full pipeline!

**Verify the data exists:**
```bash
ls data/anomalies/
```

**You should see:**
```
_SUCCESS
month=2023-09/
month=2023-10/
month=2023-11/
month=2023-12/
month=2024-01/
month=2024-02/
month=2024-03/
```

**This is partitioned Parquet format** - data is organized by month for efficient querying.

**Verify one of the month directories:**
```bash
ls data/anomalies/month=2023-09/
```

**You should see:**
```
anomaly_type=mix_shift/
anomaly_type=navigation_edge/
anomaly_type=traffic_spike/
```

**This shows anomalies are partitioned by both month AND type** - this is normal and expected!

**If you see this structure, all 1,813 pre-detected anomalies are ready to go!**

> **Note:** If you don't see the `data/anomalies/` directory or it's empty, that's okay! The dashboard will still start, but you'll need to run the pipeline first (see Part 5) to generate anomalies.

---

### Part 4: Start the Dashboard (2 minutes)

> **⚠️ CRITICAL: DO NOT SKIP TO THIS STEP!**  
> You MUST complete Part 2 (virtual environment setup) first!  
> If you skip it, you'll get "No module named 'pyspark'" errors.

**Step 4.1: Make sure you completed Part 2**

Check if you see `(venv)` at the start of your terminal prompt:
```
(venv) user@computer:~/METCS777-TermProject-Group7$
```

**If you DON'T see (venv):**
```bash
# Go back and do Part 2!
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

**Step 4.2: Make sure you're in the project root**
```bash
pwd
```

**Should show:**
```
/Users/yourname/Downloads/METCS777-TermProject-Group7
```
(or wherever you cloned it)

**Step 4.3: Run the dashboard**

The dashboard automatically finds an available port in the 7000 series (7000, 7001, 7002, etc.) to avoid conflicts.

> **Important:** Make sure you're still in the project root directory and your virtual environment is activated (you should see `(venv)` in your prompt).

```bash
python run_dashboard.py
```

**Expected output:**
```
================================================================================
LOADING FULL DATASET FOR DASHBOARD
================================================================================
✓ Loaded 1813 anomalies from partitioned parquet files
✓ Months with anomalies: ['2023-09', '2023-10', '2023-11', '2023-12', '2024-01', '2024-02', '2024-03']
✓ Anomaly types: ['mix_shift', 'navigation_edge', 'traffic_spike']
✓ By month: {'2023-09': 204, '2023-10': 375, '2023-11': 401, ...}
✓ By type: {'mix_shift': 130, 'navigation_edge': 504, 'traffic_spike': 1179}

Starting Dashboard...
Dashboard will run on http://localhost:7000
 * Serving Flask app 'scripts.start_dashboard_demo'
 * Debug mode: off
WARNING: This is a development server...
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:7000
Press CTRL+C to quit
```

✅ **If you see "Running on http://127.0.0.1:7000" (or 7001, 7002, etc.), it's working!**

> **Note:** The dashboard automatically finds an available port. If 7000 is busy, it will try 7001, then 7002, etc. The exact port will be shown in the terminal output.

**Step 4.4: Open in browser**

**IMPORTANT:** Open your web browser and type the EXACT URL shown in the terminal (e.g., `http://127.0.0.1:7000`):

```
http://127.0.0.1:7000
```
(Or whatever port number was shown in the terminal)

**⚠️ Common mistakes to avoid:**
- ❌ Don't use `https://` (it's `http://`)
- ❌ Don't use `localhost` (Chrome may redirect to HTTPS)
- ✅ Use exactly: `http://127.0.0.1:7000` (or the port shown in terminal)

**You should see:**
- A dark-themed dashboard
- Stats showing "1,813 Total Anomalies"
- Charts and a filterable table
- Top anomalies section
- Navigation Edges card showing 504 anomalies

✅ **If you see the dashboard, CONGRATULATIONS! You're done!**

**To stop the dashboard:**
Press `Ctrl+C` in the terminal

---

### Part 5 (Optional): Download Fresh Data & Run Full Pipeline

**⚠️ WARNING: This downloads ~10GB and takes 20-40 minutes. Only do this if you want to process your own data!**

**Step 5.1: Download Wikipedia clickstream data**

From the project root (with venv activated):
```bash
python scripts/download_clickstream.py --months 2023-09 2023-10
```

**This will:**
- Download 2 months of compressed data (~3GB)
- Save to `data/raw/clickstream-2023-09.tsv.gz` and `clickstream-2023-10.tsv.gz`
- Take 5-15 minutes depending on your internet

**Expected output:**
```
Downloading 2023-09 clickstream...
  URL: https://dumps.wikimedia.org/other/clickstream/2023-09/clickstream-2023-09.tsv.gz
  Saving to: data/raw/clickstream-2023-09.tsv.gz
  Downloaded: 1.5 GB
✓ Download complete

Downloading 2023-10 clickstream...
  ...
✓ All downloads complete
```

**Step 5.2: Run the full pipeline**

> **Note:** The pipeline automatically handles Python version consistency between Spark driver and workers. You don't need to set any environment variables manually.

```bash
python run_pipeline.py
```

**This will:**
1. Load the TSV files (takes 2-3 min per month)
2. Clean and filter the data
3. Save to Parquet format (faster)
4. Calculate baselines (median traffic for each edge)
5. Run 3 anomaly detectors (Statistical, Clustering, Mix-Shift)
6. Save results to `data/anomalies/` (partitioned by month)

**Expected runtime:** 1-2 minutes for all 10 months (if data is already processed)

**Expected output:**
```
Starting Anomaly Detection Pipeline...
Using Python: /path/to/venv/bin/python

===============================================================================
STEP 1: ETL - Loading and cleaning clickstream data
===============================================================================
Loading processed data from data/processed...
ETL complete. Total rows: 60000

===============================================================================
STEP 3: Anomaly Detection - Running all detectors
===============================================================================
--- Fitting Clustering Detector (once for all months) ---
Fitting K-means model with 50 clusters...
✓ Clustering detector fitted successfully

===============================================================================
Processing month: 2023-09 (baseline: 3 months)
===============================================================================
--- Running Statistical Detector for 2023-09 ---
Detected 114 traffic spike anomalies for 2023-09
--- Running Clustering Detector for 2023-09 ---
Detected 72 navigation-edge anomalies for 2023-09
--- Running Mix-Shift Detector for 2023-09 ---
Detected 18 mix-shift anomalies for 2023-09

... (continues for all months)

Total anomalies detected: 1813
===============================================================================
STEP 4: Saving Anomalies
===============================================================================
Saved anomalies to data/anomalies
===============================================================================
PIPELINE COMPLETE!
===============================================================================
Pipeline completed successfully!
Total anomalies detected: 1813
```

**Step 5.3: Re-start the dashboard to see new results**
```bash
python run_dashboard.py
```

Now the dashboard will show YOUR freshly detected anomalies!

---

### Troubleshooting EVERY Possible Error

**Error: "Port already in use"**
```bash
# The dashboard automatically finds available ports (7000, 7001, 7002, etc.)
# Just use the port shown in the terminal output
# If you want to force a specific port:
PORT=7005 python run_dashboard.py
```

**Error: "No module named 'pyspark'"**
```bash
# Make sure venv is activated - look for (venv) in prompt
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

**Error: "Python in worker has different version than driver"**
```bash
# This is automatically handled by run_pipeline.py
# It sets PYSPARK_PYTHON and PYSPARK_DRIVER_PYTHON to the venv Python
# If you still see this error, make sure you're using the venv:
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
python run_pipeline.py
```

**Error: "java.lang.OutOfMemoryError: Java heap space"**
```bash
# Edit config/config.yaml
# Change these lines:
# executor_memory: "4g"  # was 8g
# driver_memory: "4g"    # was 8g

# Then re-run pipeline
python run_pipeline.py
```

**Error: "command not found: python3"**
```bash
# Try just "python" instead
python --version

# If that works, replace python3 with python in all commands
```

**Error: Downloads fail**
```bash
# Manually download from:
# https://dumps.wikimedia.org/other/clickstream/

# Save files to data/raw/ with exact names:
# clickstream-2023-09.tsv.gz
# clickstream-2023-10.tsv.gz
```

**Error: "The system cannot find the path specified" (Windows)**
```bash
# Use forward slashes or escape backslashes
cd C:/Users/YourName/Downloads/METCS777-TermProject-Group7

# OR
cd C:\\Users\\YourName\\Downloads\\METCS777-TermProject-Group7
```

**Dashboard loads but shows "No anomalies"**
```bash
# Check data exists
ls data/anomalies/

# You should see month= directories like:
# month=2023-09/
# month=2023-10/
# etc.

# If the directory doesn't exist or is empty, run the pipeline:
python run_pipeline.py

# Note: The pipeline needs processed data first. If you don't have processed data,
# you'll need to download raw data first (see Part 5).
```

**Error: "config.yaml not found" or config errors**
```bash
# The code automatically falls back to config.example.yaml
# But if you want to customize, copy the example:
cp config/config.example.yaml config/config.yaml

# Then edit config/config.yaml with your settings
```

**Error: "No such file or directory: data/anomalies"**
```bash
# Create the directory (though it should exist in the repo):
mkdir -p data/anomalies

# Or run the pipeline which will create it:
python run_pipeline.py
```

**Error: "[AMBIGUOUS_REFERENCE]" or Spark SQL errors**
```bash
# These are fixed in the current codebase
# Make sure you have the latest version from GitHub
git pull origin main

# If still seeing errors, check that you're using the correct Python version
python --version  # Should be 3.8+
```

---

## Quick Reference Commands

**Full setup from scratch:**
```bash
# 1. Clone
git clone https://github.com/HarshithKeshavamurthy17/METCS777-TermProject-Group7.git
cd METCS777-TermProject-Group7

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 3. Install
pip install -r requirements.txt

# 4. Verify
python -c "from pyspark.sql import SparkSession; print('Ready!')"

# 5. Run dashboard (uses pre-generated anomalies)
python run_dashboard.py

# 6. Open browser
# Go to http://127.0.0.1:7000 (or port shown in terminal - use HTTP not HTTPS!)
```

**Run full pipeline (optional):**
```bash
# Download data (optional - we include pre-generated results)
python scripts/download_clickstream.py --months 2023-09 2023-10

# Process and detect
python run_pipeline.py

# View results
python run_dashboard.py
```

---

## Understanding Our Results

After running the pipeline (or using our pre-generated results), here's what we found:

### Overall Statistics

- **Total Anomalies Detected:** 1,813
- **Time Period:** September 2023 - March 2024 (7 months)
- **Baseline Period:** June 2023 - August 2023 (first 3 months used as baseline)
- **Data Processed:** ~60,000 page transitions across 10 months
- **Detection Methods:** 3 (statistical, clustering, mix-shift)

### Breakdown by Type

| Type | Count | % | What It Means |
|------|-------|---|---------------|
| **Traffic Spikes** | 1,179 | 65.0% | Page transitions that jumped 10x+ above normal |
| **Navigation Edges** | 504 | 27.8% | Unusual paths detected via K-means clustering |
| **Mix-Shifts** | 130 | 7.2% | Pages where traffic sources changed 20%+ |

### Breakdown by Month

| Month | Anomalies | Notes |
|-------|-----------|-------|
| 2023-09 | 204 | First month with anomalies (3-month baseline required) |
| 2023-10 | 375 | Highest count - includes Israel-Hamas war coverage |
| 2023-11 | 401 | Peak anomaly month |
| 2023-12 | 207 | Holiday season patterns |
| 2024-01 | 204 | New year events |
| 2024-02 | 213 | Continued patterns |
| 2024-03 | 209 | Latest month |

### Top Anomaly Examples

**1. Traffic Spikes (Statistical Detector)**
- Detects when traffic is 10x+ above baseline median
- Uses Z-score (MAD-based) > 3.5 threshold
- Example: Breaking news events cause massive traffic spikes

**2. Navigation Edges (Clustering Detector)**
- Uses K-means clustering (50 clusters) on feature vectors
- Flags edges far from cluster centers (95th percentile distance)
- Example: Unusual navigation paths that don't match normal user behavior

**3. Mix-Shifts (Mix-Shift Detector)**
- Detects when referrer distribution changes significantly
- Uses Jensen-Shannon divergence > 0.3
- Example: Page suddenly gets traffic from different sources

---

## Project Structure Explained

Here's how we organized everything:

```
├── src/                    # All our source code
│   ├── etl/                # Loads and cleans the raw data
│   ├── features/           # Calculates baselines and statistics
│   ├── detectors/          # The 3 anomaly detection algorithms
│   │   ├── statistical_detector.py
│   │   ├── clustering_detector.py
│   │   └── mix_shift_detector.py
│   ├── pipeline/           # Ties everything together
│   ├── dashboard/          # Web interface (Flask app)
│   │   └── templates/      # HTML templates
│   ├── storage/            # Parquet storage utilities
│   └── utils/              # Helper functions (Spark session, config)
│
├── scripts/                # Things you can run
│   ├── download_clickstream.py
│   ├── run_detection.py
│   └── start_dashboard_demo.py
│
├── config/
│   ├── config.yaml         # All the settings (thresholds, paths, etc.)
│   └── config.example.yaml # Example config file
│
├── data/                   # Where data lives (not in git except .gitkeep)
│   ├── raw/                # Downloaded TSV files
│   ├── processed/          # Cleaned Parquet files (partitioned by month)
│   └── anomalies/          # Our detection results (partitioned by month)
│       ├── month=2023-09/
│       ├── month=2023-10/
│       └── ...
│
├── run_pipeline.py         # ⭐ Run this to process data
├── run_dashboard.py        # ⭐ Run this to see results
└── requirements.txt        # All Python dependencies
```

---

## How Our Algorithms Work

### 1. Statistical Detector (Traffic Spikes)

**The Problem:** How do we know when traffic is *unusually* high?

**Our Solution:**
1. For each page transition (e.g., `Main_Page → Python`), we look at the last 6 months of data
2. Calculate the **median** (middle value) - this is our "normal" traffic
3. Calculate **MAD** (Median Absolute Deviation) - how spread out the data is
4. For the current month, calculate a **Z-score**: how many standard deviations away from normal
5. If Z-score > 3.5 OR traffic is 10x+ baseline, it's an anomaly

**Why this works:** We use MAD instead of standard deviation because it's robust to outliers. News events create huge spikes that would throw off a simple average.

**Example:**
```
Edge: Main_Page → Python
Historical traffic: [100, 95, 110, 98, 105, 102]
Baseline median: 101
Current month: 1,250
Deviation: 1,250 / 101 = 12.4x
Z-score: 87.3
Result: ⚠️ ANOMALY (way above threshold)
```

### 2. Mix-Shift Detector (Traffic Source Changes)

**The Problem:** What if a page's traffic doesn't spike, but the *sources* change?

**Our Solution:**
1. For each page, track where visitors come from (Google, other Wikipedia pages, etc.)
2. Calculate the proportion of traffic from each source
3. Compare current month to the baseline using Jensen-Shannon divergence
4. If JS divergence > 0.3 OR top referrer changed by 20%+, flag it

**Example:**
```
Page: United_States
Previous month referrers:
  - Google: 40%
  - other-search: 30%
  - Main_Page: 20%
  - other: 10%

Current month:
  - Main_Page: 55%   ⬆️ +35 points!
  - Google: 25%
  - other-search: 15%
  - other: 5%

Result: ⚠️ MIX-SHIFT (Main_Page became dominant)
Reason: Probably featured on Wikipedia's front page
```

### 3. Clustering Detector (Navigation Edges)

**The Problem:** Some paths between pages are just weird, even if traffic isn't high.

**Our Solution:**
1. Create feature vectors for each edge (traffic volume, link type, etc.)
2. Use K-means clustering (50 clusters) to group "normal" navigation patterns
3. Calculate distance from each edge to its cluster center
4. Edges far from any cluster (95th percentile distance) = unusual navigation

**Example:**
```
Edge: Obscure_Page → Another_Obscure_Page
Features: [low_traffic, unusual_link_type, ...]
Distance to nearest cluster: 4.69 (above 95th percentile threshold)
Result: ⚠️ NAVIGATION EDGE ANOMALY
```

---

## The Dashboard Features

When you open the dashboard (e.g., `http://127.0.0.1:7000`), here's what you can do:

### 1. Overview Cards
- See total anomaly counts (1,813)
- Breakdown by type (Traffic Spikes, Navigation Edges, Mix-Shifts)
- Quick stats

### 2. Time Series Chart
- Monthly anomaly trends across all 7 months
- Toggle different anomaly types
- Interactive hover for details

### 3. Top 5 Most Interesting
- The craziest anomalies we found
- Click to see full details

### 4. Filterable Table
**Filters:**
- Month (dropdown - includes "All Months")
- Anomaly type (traffic spike / navigation edge / mix-shift)
- Minimum confidence

**Columns:**
- Referrer page
- Target page
- What happened (badges + description)
- Traffic count
- Deviation ratio (how many times above baseline)
- 6-month trend sparkline
- Forecast column (actual vs predicted)
- View Details button

### 5. Explainability Panel
Click "View Details" on any anomaly to see:
- **Detection Signals:** Why we flagged it (Z-score, deviation ratio, distance)
- **Time Series Chart:** 6-month traffic pattern
- **Daily Pageviews:** Granular daily data from Wikipedia API
- **Referrer Distribution:** How traffic sources changed
- **Raw Details:** All the numbers

---

## Configuration & Tuning

Want to adjust how sensitive the detection is? Edit `config/config.yaml`:

```yaml
anomaly_detection:
  traffic_spike:
    z_score_threshold: 3.5      # Higher = fewer, stronger anomalies
    ratio_threshold: 10.0        # Minimum X times above baseline
  
  mix_shift:
    js_divergence_threshold: 0.3 # Higher = fewer mix-shifts
    top_referrer_change_threshold: 0.2  # 20% change in top referrer
  
  clustering:
    n_clusters: 50               # Number of behavior groups
    distance_threshold_percentile: 95  # Top 5% = anomalies

dashboard:
  port: 7000                     # Dashboard port (auto-finds if busy)
```

**If you want MORE anomalies:** Lower the thresholds  
**If you want FEWER, higher-quality anomalies:** Raise the thresholds

---

## Common Issues & Solutions

### "I don't see any data in the dashboard"

**Check:**
1. Is `data/anomalies/` folder populated? Should have directories like `month=2023-09/`
2. Did you run `python run_pipeline.py` first? (Or use our pre-generated results)
3. Check the terminal where the dashboard is running for error messages
4. Make sure you're using the URL shown in terminal (e.g., `http://127.0.0.1:7000`)

### "Pipeline is really slow"

**Solutions:**
- Process fewer months: Edit `config/config.yaml` and reduce the `months` list
- Reduce Spark memory if you're on a low-RAM machine
- Expected: 1-2 minutes for all months on a modern laptop (if data is already processed)

### "Port already in use"

**Solution:**
- The dashboard automatically finds available ports (7000, 7001, 7002, etc.)
- Just use the port shown in the terminal output
- No manual configuration needed!

### "Java heap space" error

**Fix:**
```yaml
# In config/config.yaml
spark:
  executor_memory: "4g"  # Reduce from 8g
  driver_memory: "4g"     # Reduce from 4g
```

### "No module named 'pyspark'"

**Fix:**
```bash
# Make sure venv is activated
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate      # Windows

# Reinstall
pip install -r requirements.txt
```

### "Python version mismatch" error

**Fix:**
- This is automatically handled by `run_pipeline.py`
- It sets `PYSPARK_PYTHON` and `PYSPARK_DRIVER_PYTHON` to the venv Python
- Make sure you're using the virtual environment:
```bash
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
python run_pipeline.py
```

---

## Technologies We Used

| Technology | Why We Chose It |
|-----------|-----------------|
| **Apache Spark** | Handle 60GB+ of data, distributed processing |
| **PySpark** | Python API for Spark, easier than Scala for our team |
| **Parquet** | Columnar storage = 10x compression, fast queries, partitioned by month |
| **Flask** | Lightweight Python web framework |
| **Plotly.js** | Interactive charts in the dashboard |
| **Pandas** | Data manipulation for the dashboard |

---

## Development Notes

### How We Split the Work

- **Harshith**: Led anomaly detection research, implemented the statistical detector, and handled performance + configuration across the system.
- **Aryaman**: Led user-facing components, developing the dashboard UI/UX, backend API, and all visualization modules.
- **Dirgha**: Led data engineering components, creating the ETL workflow, Spark infrastructure, and the clustering anomaly detection model.

### Design Decisions We Made

1. **Why Parquet instead of keeping TSV?**
   - 10x smaller files
   - Only read columns we need (faster)
   - Built-in schema validation
   - Partitioned by month for efficient queries

2. **Why partition by month?**
   - Most queries filter by month
   - Can add new months without reprocessing old ones
   - Parallel writes are faster
   - Efficient for dashboard filtering

3. **Why three detectors?**
   - Each catches different anomaly types
   - Statistical = spikes
   - Mix-shift = behavior changes
   - Clustering = outlier patterns

4. **Why pre-generate results?**
   - Easier for demos and grading
   - Not everyone has time to download 60GB
   - Shows what the pipeline produces
   - All 1,813 anomalies included in repository

5. **Why auto-find ports?**
   - Avoids conflicts with AirPlay Receiver (Mac port 5000)
   - No manual configuration needed
   - Works out of the box

6. **Why handle Python version automatically?**
   - Prevents "Python version mismatch" errors
   - Ensures driver and workers use same Python
   - No manual environment variable setup needed

---

## Testing & Validation

### How We Validated Our Results

1. **Manual Review**: We looked at the top 50 anomalies
   - 46/50 matched real-world events (92% accuracy)
   - False positives were mostly bot traffic or data quality issues

2. **Cross-Reference**: Checked against:
   - Google Trends (confirmed search interest)
   - Wikipedia's trend pages
   - News archives for Oct 2023 events

3. **Edge Cases**: Tested with:
   - Months with missing data
   - Pages with zero baseline traffic
   - Edges with extremely high variance

---

## What's Next (Future Enhancements)

If we continued this project, we'd add:

1. **Real-Time Streaming**: Process data as it comes in (using Kafka + Spark Streaming)
2. **Machine Learning**: Train isolation forest or autoencoder models
3. **Graph Analysis**: Use PageRank to find influential pages
4. **Alerting**: Send notifications when major anomalies are detected
5. **More Data Sources**: Combine with page view API, edit history, etc.

---

## Academic Context

**Course**: MET CS 777 - Big Data Analytics  
**Semester**: Fall 2024  
**Boston University Metropolitan College**

---

## Questions?

If you run into issues:
1. Check the [Common Issues & Solutions](#common-issues--solutions) section above
2. Make sure you followed every step in [Complete Setup & Run Guide](#-complete-setup--run-guide)
3. Verify all prerequisites in [What You Need Before Starting](#what-you-need-before-starting)

---

## License & Usage

This project was created for academic purposes as part of MET CS 777.

---

**Quick Start Recap:**
```bash
# 1. Clone
git clone https://github.com/HarshithKeshavamurthy17/METCS777-TermProject-Group7.git
cd METCS777-TermProject-Group7

# 2. Setup
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# 3. Run Dashboard (using our pre-generated results)
python run_dashboard.py

# 4. Open browser
# Go to http://127.0.0.1:7000 (or port shown in terminal - use HTTP not HTTPS!)
```

That's it! You should now see 1,813 Wikipedia anomalies ready to explore. 🚀

---

**Built with ☕ and 📊 by Team 7**
