"""Fetch daily pageviews from Wikimedia API."""
import requests
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timedelta

def fetch_daily_pageviews(page: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Fetch daily pageviews for a page.
    
    Args:
        page: Page title
        start_date: Start date (YYYYMMDD)
        end_date: End date (YYYYMMDD)
        
    Returns:
        List of {date: 'YYYY-MM-DD', views: int}
    """
    # API endpoint
    # https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Earth/daily/20231001/20231031
    base_url = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user"
    url = f"{base_url}/{page}/daily/{start_date}/{end_date}"
    
    headers = {
        'User-Agent': 'WikipediaClickstreamAnomalyDetector/1.0 (https://github.com/yourusername/project; your@email.com)'
    }
    
    try:
        print(f"Fetching daily pageviews for {page}: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 404:
            print(f"Page not found or no data: {page}")
            return []
            
        response.raise_for_status()
        
        data = response.json()
        items = data.get('items', [])
        
        result = []
        for item in items:
            timestamp = item.get('timestamp', '')
            # Convert YYYYMMDD00 to YYYY-MM-DD
            if len(timestamp) >= 8:
                date_str = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
                result.append({
                    'date': date_str,
                    'views': item.get('views', 0)
                })
                
        return result
        
    except Exception as e:
        print(f"Error fetching daily pageviews: {e}")
        return []

def get_pageview_series(page: str, month: str, cache_dir: str = 'data/pageviews') -> List[Dict[str, Any]]:
    """
    Get pageview time series for a page around a specific month.
    Fetches 30 days before the end of the month.
    
    Args:
        page: Page title
        month: Target month (YYYY-MM)
        cache_dir: Directory to store cached files
        
    Returns:
        List of {date: 'YYYY-MM-DD', views: int}
    """
    try:
        dt = datetime.strptime(month, '%Y-%m')
        # Calculate start and end dates
        # End date: last day of the month
        # Start date: 30 days before
        
        # Get next month first day, then subtract 1 day to get this month last day
        if dt.month == 12:
            next_month = dt.replace(year=dt.year + 1, month=1)
        else:
            next_month = dt.replace(month=dt.month + 1)
            
        end_dt = next_month - timedelta(days=1)
        start_dt = end_dt - timedelta(days=30)
        
        start_str = start_dt.strftime('%Y%m%d')
        end_str = end_dt.strftime('%Y%m%d')
        
    except ValueError:
        print(f"Invalid month format: {month}")
        return []
        
    # Ensure cache directory exists
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    
    # Sanitize page name for filename
    safe_page = "".join([c if c.isalnum() or c in ('-', '_') else '_' for c in page])
    cache_file = Path(cache_dir) / f"{safe_page}_{start_str}_{end_str}.json"
    
    # Check cache
    if cache_file.exists():
        # Check if file is not empty
        if cache_file.stat().st_size > 0:
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass # Re-fetch if corrupted
            
    # Fetch from API
    series = fetch_daily_pageviews(page, start_str, end_str)
    
    if series:
        # Save to cache
        with open(cache_file, 'w') as f:
            json.dump(series, f)
            
    return series
