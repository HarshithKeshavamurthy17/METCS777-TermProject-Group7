.PHONY: all etl detect dashboard clean test

# Default target
all: etl detect dashboard

# Run ETL pipeline
etl:
	@echo "Running ETL..."
	python scripts/run_etl.py

# Run Anomaly Detection
detect:
	@echo "Running Anomaly Detection..."
	python scripts/run_detection.py

# Start Dashboard
dashboard:
	@echo "Starting Dashboard..."
	python scripts/start_dashboard.py

# Run full pipeline
run_all:
	@echo "Running Full Pipeline..."
	bash scripts/run_all.sh

# Run tests
test:
	@echo "Running Tests..."
	pytest tests/

# Clean up generated data and logs
clean:
	@echo "Cleaning up..."
	rm -rf data/processed/*
	rm -rf data/anomalies/*
	rm -rf data/logs/*
	rm -rf data/pageviews/*
	rm -rf data/ground_truth/*
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@echo "Clean complete."

# Install dependencies
install:
	pip install -r requirements.txt
