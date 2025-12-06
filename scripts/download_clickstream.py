#!/usr/bin/env python3
"""Download Wikipedia clickstream data."""
import argparse
import requests
import os
from pathlib import Path
from tqdm import tqdm


CLICKSTREAM_BASE_URL = "https://dumps.wikimedia.org/other/clickstream/"


def download_file(url: str, output_path: str):
    """Download a file with progress bar."""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'wb') as f, tqdm(
        desc=os.path.basename(output_path),
        total=total_size,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                bar.update(len(chunk))


def download_month(month: str, output_dir: str):
    """
    Download clickstream data for a specific month.
    
    Args:
        month: Month in format YYYY-MM (e.g., "2023-09")
        output_dir: Directory to save files
    """
    # Wikipedia clickstream files are typically named:
    # clickstream-YYYY-MM-pageviews.tsv.gz
    filename = f"clickstream-{month}-pageviews.tsv.gz"
    url = f"{CLICKSTREAM_BASE_URL}{filename}"
    
    output_path = os.path.join(output_dir, filename.replace('.gz', ''))
    
    print(f"Downloading {month}...")
    try:
        download_file(url, output_path)
        print(f"Downloaded {month} to {output_path}")
    except requests.exceptions.HTTPError as e:
        print(f"Error downloading {month}: {e}")
        print(f"URL: {url}")
        print("Note: File naming may vary. Please check the actual URL structure.")


def main():
    parser = argparse.ArgumentParser(description="Download Wikipedia clickstream data")
    parser.add_argument(
        '--months',
        nargs='+',
        required=True,
        help='Months to download (e.g., 2023-09 2023-10)'
    )
    parser.add_argument(
        '--output-dir',
        default='data/raw',
        help='Output directory (default: data/raw)'
    )
    
    args = parser.parse_args()
    
    for month in args.months:
        download_month(month, args.output_dir)


if __name__ == '__main__':
    main()

