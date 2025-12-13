"""Wikimedia Pageviews API integration for daily pageview data."""
import requests
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import urllib.parse
from functools import lru_cache


def fetch_daily_pageviews(page_title: str, start: str, end: str, project: str = "en.wikipedia") -> List[Dict[str, any]]:
    """
    Fetch daily pageviews from Wikimedia API.
    
    Args:
        page_title: Wikipedia page title (e.g., "Earth" or "Main_Page")
        start: Start date in YYYYMMDD format
        end: End date in YYYYMMDD format
        project: Project name (default: "en.wikipedia")
        
    Returns:
        List of dictionaries with 'date' and 'views' keys
    """
    # Create cache directory
    cache_dir = Path("data/pageviews")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Check cache first
    cache_file = cache_dir / f"{page_title.replace(' ', '_')}_{start}_{end}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except:
            pass
    
    # Encode page title for URL
    encoded_title = urllib.parse.quote(page_title.replace(' ', '_'), safe='')
    
    # Build API URL
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/all-access/all-agents/{encoded_title}/daily/{start}/{end}"
    
    headers = {
        'User-Agent': 'WikipediaClickstreamAnomalyDetector/1.0 (https://github.com/HarshithKeshavamurthy17/METCS777-TermProject-Group7; contact@example.com)'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        items = data.get('items', [])
        
        # Format results
        results = []
        for item in items:
            results.append({
                'date': item.get('timestamp', '')[:8],  # YYYYMMDD
                'views': item.get('views', 0)
            })
        
        # Cache results
        with open(cache_file, 'w') as f:
            json.dump(results, f)
        
        return results
        
    except requests.exceptions.RequestException as e:
        print(f"Warning: Failed to fetch pageviews for {page_title}: {e}")
        # Return empty or generate mock data for local testing
        return generate_daily_mock_data(page_title, start, end)
    except Exception as e:
        print(f"Warning: Error processing pageviews for {page_title}: {e}")
        return generate_daily_mock_data(page_title, start, end)


def generate_daily_mock_data(page_title: str, start: str, end: str) -> List[Dict[str, any]]:
    """
    Generate synthetic daily pageview data for local testing.
    
    Args:
        page_title: Page title
        start: Start date YYYYMMDD
        end: End date YYYYMMDD
        
    Returns:
        List of daily pageview records
    """
    import random
    import numpy as np
    
    # Parse dates
    start_date = datetime.strptime(start, '%Y%m%d')
    end_date = datetime.strptime(end, '%Y%m%d')
    
    # Generate daily data
    results = []
    current_date = start_date
    base_views = random.randint(100, 1000)  # Base daily views
    
    while current_date <= end_date:
        # Add some randomness and weekly pattern
        day_of_week = current_date.weekday()
        weekend_factor = 0.7 if day_of_week >= 5 else 1.0
        
        views = int(base_views * weekend_factor * random.uniform(0.8, 1.2))
        results.append({
            'date': current_date.strftime('%Y%m%d'),
            'views': max(0, views)
        })
        current_date += timedelta(days=1)
    
    return results


def get_pageviews_for_anomaly(page_title: str, anomaly_month: str, days_before: int = 30, days_after: int = 30) -> List[Dict[str, any]]:
    """
    Get daily pageviews around an anomaly month.
    
    Args:
        page_title: Page title
        anomaly_month: Month in YYYY-MM format
        days_before: Days before anomaly to fetch
        days_after: Days after anomaly to fetch
        
    Returns:
        List of daily pageview records
    """
    try:
        anomaly_date = datetime.strptime(anomaly_month + '-15', '%Y-%m-%d')
    except:
        anomaly_date = datetime.now()
    
    start_date = (anomaly_date - timedelta(days=days_before)).strftime('%Y%m%d')
    end_date = (anomaly_date + timedelta(days=days_after)).strftime('%Y%m%d')
    
    return fetch_daily_pageviews(page_title, start_date, end_date)





