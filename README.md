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

---

## What You Need Before Starting

### Required Software

**1. Python 3.8 or higher**

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

## COMPLETE SETUP & RUN GUIDE 

**This section walks through EVERY SINGLE STEP from scratch. Follow this if you want to run the entire project without missing anything.**

### Prerequisites Check

Before starting, let's verify everything:

**1. Check Python:**
```bash
python3 --version
```
Should show: `Python 3.8.x` or higher

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
remote: Enumerating objects: 166, done.
remote: Counting objects: 100% (166/166), done.
...
Resolving deltas: 100% (54/54), done.
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

**If you see these files, you're good to go!**

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

**If you see (venv), it worked!**

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
Collecting pyspark>=3.5.0
  Downloading pyspark-3.5.0-py2.py3-none-any.whl (317 MB)
     ━━━━━━━━━━━━━━━━━━━━━━ 317.0/317.0 MB 5.2 MB/s
Collecting flask>=3.0.0
  Downloading Flask-3.0.0-py3-none-any.whl (99 kB)
...
Successfully installed flask-3.0.0 numpy-1.24.0 pandas-2.0.0 pyspark-3.5.0 ...
```

**This takes 2-3 minutes. Be patient!**

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

**If both print checkmarks, your environment is ready!**

---

### Part 3: Check the Data 

We've included pre-generated anomaly results so you don't need to download 60GB of data or run the full pipeline!

**Verify the data exists:**
```bash
ls data/anomalies/
```

**You should see:**
```
_SUCCESS
anomalies.parquet
```

**Verify the file size (should be ~110KB):**
```bash
ls -lh data/anomalies/anomalies.parquet
```

**You should see something like:**
```
-rw-r--r--  1 user  staff   110K Dec  5 23:37 anomalies.parquet
```

**If you see the `anomalies.parquet` file, all 2,346 pre-detected anomalies are ready to go!**

---

### Part 4: Start the Dashboard 

> ** CRITICAL: DO NOT SKIP TO THIS STEP!**  
> You MUST complete Part 2 (virtual environment setup) first!  
> If you skip it, you'll get "No module named 'pyspark'" errors.

**Step 4.1: Make sure you completed Part 2**

Check if you see `(venv)` at the start of your terminal prompt:
```
(venv) user@computer:~/test-clone$
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

**Step 4.2: Make sure venv is activated**
Check for `(venv)` in your prompt. If not there:
```bash
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate      # Windows
```

**Step 4.3: Run the dashboard**

> **Note:** If you're on Mac, port 5000 is often used by AirPlay Receiver.  
> We recommend using port 5002 instead to avoid conflicts.

```bash
# Recommended - use port 5002
PORT=5002 python run_dashboard.py

# OR if port 5000 is free on your system
python run_dashboard.py
```

**Expected output:**
```
Setting default log level to "WARN".
...
✓ Loaded 2,346 anomalies from single file
✓ By type: {'mix_shift': 130, 'traffic_spike': 2216}

Starting Dashboard...
 * Serving Flask app 'scripts.start_dashboard_demo'
 * Debug mode: off
WARNING: This is a development server...
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5002
Press CTRL+C to quit
```

**If you see "Running on http://127.0.0.1:5002", it's working!**

> **Note:** You may see some SSL/TLS errors in the terminal after this - ignore them.  
> They're just random connection attempts and don't affect the dashboard.

**Step 4.4: Open in browser**

**IMPORTANT:** Open your web browser and type this EXACTLY in the address bar:
```
http://127.0.0.1:5002
```

**Common mistakes to avoid:**
- Don't use `https://` (it's `http://`)
- Don't use `localhost` (Chrome may redirect to HTTPS)
- Use exactly: `http://127.0.0.1:5002`

**You should see:**
- A dark-themed dashboard
- Stats showing "2,346 Total Anomalies"
- Charts and a filterable table
- Top anomalies section

**If you see the dashboard, CONGRATULATIONS! You're done!**

**To stop the dashboard:**
Press `Ctrl+C` in the terminal

---

### Part 5 (Optional): Download Fresh Data & Run Full Pipeline

** WARNING: This downloads ~10GB and takes 20-40 minutes. Only do this if you want to process your own data!**

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
```bash
python run_pipeline.py
```

**This will:**
1. Load the TSV files (takes 2-3 min per month)
2. Clean and filter the data
3. Save to Parquet format (faster)
4. Calculate baselines (median traffic for each edge)
5. Run 3 anomaly detectors
6. Save results to `data/anomalies/`

**Expected runtime:** 10-15 minutes for 2 months

**Expected output:**
```
Starting Anomaly Detection Pipeline...

=== ETL Phase ===
Loading month 2023-09...
✓ Loaded 10,234,567 raw edges
✓ After filtering: 8,456,123 valid edges
Saving to Parquet...
✓ Saved to data/processed/month=2023-09/

Loading month 2023-10...
...

=== Baseline Calculation ===
Calculating baselines for 1,567,890 unique edges...
✓ Baselines calculated

=== Anomaly Detection ===
Running Statistical Detector (traffic spikes)...
  Processing month 2023-09...
  ✓ Found 623 traffic spikes
  Processing month 2023-10...
  ✓ Found 712 traffic spikes

Running Mix-Shift Detector...
  ✓ Found 34 mix shifts

Running Clustering Detector...
  ✓ Found 0 navigation edges

=== Saving Results ===
Total anomalies: 1,369
Saving to data/anomalies/...
✓ Pipeline complete!
```

**Step 5.3: Re-start the dashboard to see new results**
```bash
python run_dashboard.py
```

Now the dashboard will show YOUR freshly detected anomalies!

---

### Troubleshooting EVERY Possible Error

**Error: "Port 5000 already in use"**
```bash
# Solution 1: Use different port
PORT=5002 python run_dashboard.py
# Then open http://localhost:5002

# Solution 2 (Mac only): Disable AirPlay Receiver
# System Preferences → Sharing → Uncheck "AirPlay Receiver"
```

**Error: "No module named 'pyspark'"**
```bash
# Make sure venv is activated - look for (venv) in prompt
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
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

# If empty, either:
# 1. Download from GitHub releases (if we uploaded data)
# 2. Run the pipeline: python run_pipeline.py
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

# 5. Run dashboard
PORT=5002 python run_dashboard.py

# 6. Open browser
# Go to http://127.0.0.1:5002 (use HTTP not HTTPS!)
```

**Run full pipeline (optional):**
```bash
# Download data
python scripts/download_clickstream.py --months 2023-09 2023-10

# Process and detect
python run_pipeline.py

# View results
python run_dashboard.py
```

---


## Getting Started (Step-by-Step)

### Step 1: Clone Our Repository

Open your terminal and run:

```bash
git clone https://github.com/HarshithKeshavamurthy17/METCS777-TermProject-Group7.git
cd METCS777-TermProject-Group7
```

You should now be inside the project folder. Verify by running:
```bash
ls
```

You should see folders like `src/`, `scripts/`, `config/`, etc.

---

### Step 2: Set Up the Environment

**Create a virtual environment** (this keeps our project dependencies separate):

```bash
# Create it
python3 -m venv venv

# Activate it
# On Mac/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

You'll know it worked when you see `(venv)` at the start of your terminal prompt.

**Install all dependencies:**

```bash
pip install -r requirements.txt
```

This will install:
- PySpark (for distributed data processing)
- Flask (for the web dashboard)
- Pandas, NumPy, SciPy (for data manipulation)
- And a few other libraries

**Verify everything installed correctly:**

```bash
python -c "from pyspark.sql import SparkSession; print('✓ Spark is ready!')"
python -c "import flask, pandas, numpy; print('✓ All dependencies loaded!')"
```

If both print checkmarks, you're all set!

---

### Step 3: Launch the Dashboard

**Here's the good news:** We've already run the full pipeline and included the results in the repository! You can start the dashboard immediately without processing any data.

**Start the dashboard:**

```bash
python run_dashboard.py
```

You should see output like:
```
✓ Loaded 2,346 anomalies from partitioned parquet files
✓ Months with anomalies: ['2023-09', '2023-10', ...]
 * Running on http://127.0.0.1:5000
```

**Open your browser** and go to: **http://localhost:5000**

You should see our interactive dashboard with all the anomalies we detected!

** Troubleshooting:**

If you get **"Port 5000 already in use"**:
```bash
# Try a different port
PORT=5002 python run_dashboard.py
# Then open http://localhost:5002
```

If you get **"No module named 'pyspark'"**:
- Make sure your virtual environment is activated (you should see `(venv)` in your terminal)
- Run `pip install -r requirements.txt` again

---

### Step 4 (Optional): Download Fresh Data

Want to download your own Wikipedia data and run the full pipeline from scratch? Here's how:

**Download clickstream data:**

```bash
python scripts/download_clickstream.py --months 2023-09 2023-10
```

This downloads 2 months of data (~3GB). It'll be saved in `data/raw/`.

**Note:** Each month is about 1.5GB compressed, so downloading 6 months takes a while (10-30 minutes depending on your internet). We recommend starting with just 1-2 months for testing.

** Troubleshooting:**

If the download fails:
- Check your internet connection
- The Wikimedia servers might be temporarily down
- You can manually download files from https://dumps.wikimedia.org/other/clickstream/
- Place them in `data/raw/` with names like `clickstream-2023-09.tsv.gz`

---

### Step 5 (Optional): Run the Full Pipeline

**Process the data and detect anomalies:**

```bash
python run_pipeline.py
```

This will:
1. **Load the data** from `data/raw/`
2. **Clean it** (remove malformed entries, normalize page names)
3. **Save to Parquet** format (much faster to read later)
4. **Calculate baselines** (what's "normal" traffic for each page transition)
5. **Run anomaly detection** using all three methods
6. **Save results** to `data/anomalies/`

**Expected runtime:** 10-20 minutes for 6 months of data (faster with fewer months).

**You'll see output like:**
```
Processing month 2023-09...
✓ Loaded 10,234,567 edges
✓ Cleaned to 8,456,123 valid edges
✓ Baseline calculated for 1,567,890 unique edges
Running Statistical Detector...
  ✓ Found 1,234 traffic spikes
Running Mix-Shift Detector...
  ✓ Found 56 mix shifts
Running Clustering Detector...
  ✓ Found 0 navigation edges
Total anomalies: 1,290
Saved to data/anomalies/month=2023-09/
```

** Troubleshooting:**

If you get **"OutOfMemoryError: Java heap space"**:
1. Open `config/config.yaml`
2. Reduce these values:
   ```yaml
   spark:
     executor_memory: "4g"  # was 8g
     driver_memory: "4g"    # was 8g
   ```
3. Process fewer months at a time

If the pipeline crashes:
- Make sure Java is installed and `JAVA_HOME` is set
- Try running with just 1 month first to test
- Check that you have enough disk space

---

## Understanding Our Results

After running the pipeline (or using our pre-generated results), here's what we found:

### Overall Statistics

- **Total Anomalies Detected:** 2,346
- **Time Period:** September 2023 - March 2024 (7 months)
- **Data Processed:** ~70 million page transitions
- **Detection Methods:** 3 (statistical, clustering, mix-shift)

### Breakdown by Type

| Type | Count | % | What It Means |
|------|-------|---|---------------|
| **Traffic Spikes** | 2,216 | 94.5% | Page transitions that jumped 10x+ above normal |
| **Mix-Shifts** | 130 | 5.5% | Pages where traffic sources changed 20%+ |
| **Navigation Edges** | 0 | 0% | Unusual paths (none detected with current params) |

### Top Anomaly Examples

**1. Israel-Hamas War Coverage (Oct 2023)**
```
Main_Page → 2023_Israel–Hamas_war
Traffic: 45,230 clicks
Baseline: 295 clicks
Spike: 153.32x normal
```
This was the biggest spike we detected. When the war broke out in October, traffic to this article exploded from Wikipedia's main page.

**2. Taylor Swift (Multiple Months)**
```
Spotify → Taylor_Swift
Spike: 45.23x normal
```
Album releases and tour coverage drove massive spikes throughout fall 2023.

**3. ChatGPT Interest (Nov 2023)**
```
Google → ChatGPT
Spike: 87.12x normal
```
Peak of the AI hype cycle, everyone was searching and clicking.

---

## Project Structure Explained

Here's how we organized everything:

```
├── src/                    # All our source code
│   ├── etl/                # Loads and cleans the raw data
│   ├── features/           # Calculates baselines and statistics
│   ├── detectors/          # The 3 anomaly detection algorithms
│   ├── pipeline/           # Ties everything together
│   ├── dashboard/          # Web interface (Flask app)
│   └── utils/              # Helper functions
│
├── scripts/                # Things you can run
│   ├── download_clickstream.py
│   ├── run_detection.py
│   └── start_dashboard_demo.py
│
├── config/
│   └── config.yaml         # All the settings (thresholds, paths, etc.)
│
├── data/                   # Where data lives (not in git)
│   ├── raw/                # Downloaded TSV files
│   ├── processed/          # Cleaned Parquet files
│   └── anomalies/          # Our detection results
│
├── run_pipeline.py         #  Run this to process data
├── run_dashboard.py        #  Run this to see results
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
Result:  ANOMALY (way above threshold)
```

### 2. Mix-Shift Detector (Traffic Source Changes)

**The Problem:** What if a page's traffic doesn't spike, but the *sources* change?

**Our Solution:**
1. For each page, track where visitors come from (Google, other Wikipedia pages, etc.)
2. Calculate the proportion of traffic from each source
3. Compare current month to the baseline
4. If the top referrer changed OR any source shifted by 20%+, flag it

**Example:**
```
Page: United_States
Previous month referrers:
  - Google: 40%
  - other-search: 30%
  - Main_Page: 20%
  - other: 10%

Current month:
  - Main_Page: 55%   +35 points!
  - Google: 25%
  - other-search: 15%
  - other: 5%

Result:  MIX-SHIFT (Main_Page became dominant)
Reason: Probably featured on Wikipedia's front page
```

### 3. Clustering Detector (Navigation Edges)

**The Problem:** Some paths between pages are just weird, even if traffic isn't high.

**Our Solution:**
1. Create features for each edge (traffic volume, link type, etc.)
2. Use K-means clustering to group "normal" navigation patterns
3. Calculate distance from each edge to its cluster center
4. Edges far from any cluster = unusual navigation

**Note:** We didn't find any with our current parameters, but the detector is ready if we tune it.

---

## The Dashboard Features

When you open http://localhost:5000, here's what you can do:

### 1. Overview Cards
- See total anomaly counts
- Breakdown by type
- Quick stats

### 2. Time Series Chart
- Monthly anomaly trends
- Toggle different anomaly types
- Interactive hover for details

### 3. Top 5 Most Interesting
- The craziest anomalies we found
- Click to see full details

### 4. Filterable Table
**Filters:**
- Month (dropdown)
- Anomaly type (traffic spike / mix-shift)
- Minimum confidence

**Columns:**
- Referrer page
- Target page
- What happened (badges + description)
- Traffic count
- How many times above baseline
- 6-month trend sparkline
- View Details button

### 5. Explainability Panel
Click "View Details" on any anomaly to see:
- **Detection Signals:** Why we flagged it (Z-score, deviation ratio)
- **Time Series Chart:** 6-month traffic pattern
- **Daily Pageviews:** Granular daily data from Wikipedia API
- **Referrer Distribution:** How traffic sources changed
- **Raw Details:** All the numbers

---

## Configuration & Tuning

Want to adjust how sensitive the detection is? Edit `config/config.yaml`:

```yaml
detection:
  statistical:
    z_score_threshold: 3.5      # Higher = fewer, stronger anomalies
    ratio_threshold: 10.0       # Minimum X times above baseline
  
  mix_shift:
    top_prop_threshold: 0.2     # 20% change in top referrer
  
  clustering:
    n_clusters: 10              # Number of behavior groups
    distance_threshold_percentile: 95  # Top 5% = anomalies
```

**If you want MORE anomalies:** Lower the thresholds  
**If you want FEWER, higher-quality anomalies:** Raise the thresholds

---

## Common Issues & Solutions

### "I don't see any data in the dashboard"

**Check:**
1. Is `data/anomalies/` folder populated? Should have files like `month=2023-09/part-00000.parquet`
2. Did you run `python run_pipeline.py` first? (Or use our pre-generated results)
3. Check the terminal where the dashboard is running for error messages

### "Pipeline is really slow"

**Solutions:**
- Process fewer months: Edit `config/config.yaml` and reduce the `months` list
- Reduce Spark memory if you're on a low-RAM machine
- Expected: 2-3 minutes per month on a modern laptop

### "Port 5000 is already in use"

**On Mac:**
- This is usually AirPlay Receiver
- Either disable it in System Preferences → Sharing
- Or run on different port: `PORT=5002 python run_dashboard.py`

### "Java heap space" error

**Fix:**
```yaml
# In config/config.yaml
spark:
  executor_memory: "4g"  # Reduce from 8g
  driver_memory: "4g"
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

---

## Technologies We Used

| Technology | Why We Chose It |
|-----------|-----------------|
| **Apache Spark** | Handle 60GB+ of data, distributed processing |
| **PySpark** | Python API for Spark, easier than Scala for our team |
| **Parquet** | Columnar storage = 10x compression, fast queries |
| **Flask** | Lightweight Python web framework |
| **Plotly.js** | Interactive charts in the dashboard |
| **Pandas** | Data manipulation for the dashboard |

---

## Development Notes

### How We Split the Work

- **Harshith**: Led anomaly detection research, implemented the statistical detector, and handled performance + configuration across the system.
- **Aryaman**: Led user-facing components, developing the dashboard UI/UX, backend API, and all visualization modules.
- **Dirgha**: Led data engineering components, creating the ETL workflow, Spark infrastructure, and the clustering anomaly detection model.
- 
### Design Decisions We Made

1. **Why Parquet instead of keeping TSV?**
   - 10x smaller files
   - Only read columns we need (faster)
   - Built-in schema validation

2. **Why partition by month?**
   - Most queries filter by month
   - Can add new months without reprocessing old ones
   - Parallel writes are faster

3. **Why three detectors?**
   - Each catches different anomaly types
   - Statistical = spikes
   - Mix-shift = behavior changes
   - Clustering = outlier patterns

4. **Why pre-generate results?**
   - Easier for demos and grading
   - Not everyone has time to download 60GB
   - Shows what the pipeline produces

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
1. Check the [Common Issues](#common-issues--solutions) section above
2. Make sure you followed every step in [Getting Started](#getting-started-step-by-step)
3. Verify all prerequisites in [What You Need](#what-you-need-before-starting)

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
open http://localhost:5000
```



---

**Built by Team 7**
