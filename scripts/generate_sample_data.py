#!/usr/bin/env python3
"""Generate sample clickstream data for testing."""
import pandas as pd
import numpy as np
import os
from pathlib import Path


def generate_sample_data(output_dir: str, months: list, num_edges: int = 10000):
    """
    Generate sample clickstream data.
    
    Args:
        output_dir: Directory to save TSV files
        months: List of month strings
        num_edges: Number of edges to generate per month
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate some common pages
    pages = [
        "Main_Page", "United_States", "Wikipedia", "Earth", "World_War_II",
        "English_language", "Science", "History", "Technology", "Art",
        "Music", "Sports", "Geography", "Biology", "Chemistry", "Physics",
        "Mathematics", "Literature", "Philosophy", "Religion"
    ]
    
    referrers = pages + ["other-search", "other-external", "other-internal", "other-empty"]
    types_list = ["link", "external", "other"]
    
    for month in months:
        print(f"Generating sample data for {month}...")
        
        # Generate edges
        data = []
        for i in range(num_edges):
            prev = np.random.choice(referrers)
            curr = np.random.choice(pages)
            edge_type = np.random.choice(types_list)
            
            # Create some baseline traffic with occasional spikes
            base_traffic = np.random.poisson(50)
            
            # Add some anomalies (spikes) for certain edges
            if i < num_edges * 0.05:  # 5% of edges have spikes
                traffic = base_traffic * np.random.uniform(10, 50)
            else:
                traffic = base_traffic
            
            # Add some variation by month
            if month in ["2024-01", "2024-02"]:
                traffic = int(traffic * np.random.uniform(0.8, 1.2))
            
            data.append({
                "prev": prev,
                "curr": curr,
                "type": edge_type,
                "n": max(1, int(traffic))
            })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Save as TSV
        output_path = os.path.join(output_dir, f"clickstream-{month}.tsv")
        df.to_csv(output_path, sep="\t", index=False, header=True)
        
        print(f"  Saved {len(df)} edges to {output_path}")
    
    print(f"\nSample data generation complete! Generated files in {output_dir}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate sample clickstream data")
    parser.add_argument(
        "--output-dir",
        default="data/raw",
        help="Output directory"
    )
    parser.add_argument(
        "--months",
        nargs="+",
        default=["2023-06", "2023-07", "2023-08", "2023-09", "2023-10", "2023-11", "2023-12", "2024-01", "2024-02", "2024-03"],
        help="Months to generate"
    )
    parser.add_argument(
        "--num-edges",
        type=int,
        default=10000,
        help="Number of edges per month"
    )
    
    args = parser.parse_args()
    generate_sample_data(args.output_dir, args.months, args.num_edges)

