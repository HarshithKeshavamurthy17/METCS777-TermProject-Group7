"""Fetch ground truth data from Wikimedia API."""
import requests
import json
import os
from pathlib import Path
from typing import List
from datetime import datetime

def fetch_top_pages(year: str, month: str, limit: int = 100) -> List[str]:
    """
    Fetch top pages for a given month from Wikimedia API.
    
    Args:
        year: Year string (YYYY)
        month: Month string (MM)
        limit: Number of top pages to return
        
    Returns:
        List of page titles
    """
    # API endpoint
    # https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/2023/10/all-days
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{year}/{month}/all-days"
    
    headers = {
        'User-Agent': 'WikipediaClickstreamAnomalyDetector/1.0 (https://github.com/yourusername/project; your@email.com)'
    }
    
    try:
        print(f"Fetching ground truth from: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract articles
        articles = data.get('items', [])[0].get('articles', [])
        
        # Filter out special pages (Main_Page, Special:*, etc.)
        valid_articles = []
        for article in articles:
            title = article.get('article', '')
            if title == 'Main_Page' or title.startswith('Special:') or title.startswith('User:'):
                continue
            valid_articles.append(title)
            if len(valid_articles) >= limit:
                break
                
        return valid_articles
        
    except Exception as e:
        print(f"Error fetching ground truth: {e}")
        return []

def get_ground_truth(month_str: str, cache_dir: str = 'data/ground_truth') -> List[str]:
    """
    Get ground truth for a month, using cache if available.
    
    Args:
        month_str: Month in format YYYY-MM
        cache_dir: Directory to store cached files
        
    Returns:
        List of page titles
    """
    try:
        year, month = month_str.split('-')
    except ValueError:
        print(f"Invalid month format: {month_str}. Expected YYYY-MM")
        return []
        
    # Ensure cache directory exists
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    
    cache_file = Path(cache_dir) / f"top_pages_{month_str}.json"
    
    # Check cache
    if cache_file.exists():
        print(f"Loading ground truth from cache: {cache_file}")
        with open(cache_file, 'r') as f:
            return json.load(f)
            
    # Fetch from API
    pages = fetch_top_pages(year, month)
    
    if pages:
        # Save to cache
        with open(cache_file, 'w') as f:
            json.dump(pages, f)
        print(f"Saved ground truth to cache: {cache_file}")
        
    return pages
