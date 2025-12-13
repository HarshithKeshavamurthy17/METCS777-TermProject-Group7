"""Wikimedia Pageviews API integration."""
import requests
import pandas as pd
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import time
import urllib.parse
from functools import lru_cache


class PageviewsAPI:
    """Fetch daily pageviews from Wikimedia API."""
    
    def __init__(self, config: Dict):
        """
        Initialize Pageviews API client.
        
        Args:
            config: Configuration dictionary with pageviews settings
        """
        self.config = config.get('pageviews', {})
        self.enabled = self.config.get('enable', False)
        self.project = self.config.get('project', 'en.wikipedia.org')
        self.access = self.config.get('access', 'all-access')
        self.agent = self.config.get('agent', 'user')
        self.granularity = self.config.get('granularity', 'daily')
        self.window_days_before = self.config.get('window_days_before', 30)
        self.window_days_after = self.config.get('window_days_after', 30)
        self.rate_limit_delay = self.config.get('rate_limit_delay', 0.1)  # seconds between requests
        
        self.base_url = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Simple rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    def _encode_title(self, title: str) -> str:
        """URL encode page title."""
        # Replace spaces with underscores and URL encode
        title = title.replace(' ', '_')
        return urllib.parse.quote(title, safe='')
    
    @lru_cache(maxsize=1000)
    def get_daily_pageviews(
        self, 
        article_title: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get daily pageviews for an article.
        
        Args:
            article_title: Wikipedia article title (e.g., "Earth" or "Main_Page")
            start_date: Start date in YYYYMMDD format (optional)
            end_date: End date in YYYYMMDD format (optional)
            
        Returns:
            DataFrame with columns: date, views
        """
        if not self.enabled:
            return pd.DataFrame(columns=['date', 'views'])
        
        # Default date range: ±window_days around today
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start_dt = datetime.now() - timedelta(days=self.window_days_before)
            start_date = start_dt.strftime('%Y%m%d')
        
        # Encode title
        encoded_title = self._encode_title(article_title)
        
        # Build URL
        url = f"{self.base_url}/{self.project}/{self.access}/{self.agent}/{encoded_title}/{self.granularity}/{start_date}/{end_date}"
        
        try:
            self._rate_limit()
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response
            items = data.get('items', [])
            
            if not items:
                return pd.DataFrame(columns=['date', 'views'])
            
            # Convert to DataFrame
            views_data = []
            for item in items:
                views_data.append({
                    'date': item.get('timestamp', '')[:8],  # YYYYMMDD
                    'views': item.get('views', 0)
                })
            
            df = pd.DataFrame(views_data)
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            df = df.sort_values('date')
            
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"Warning: Failed to fetch pageviews for {article_title}: {e}")
            return pd.DataFrame(columns=['date', 'views'])
        except Exception as e:
            print(f"Warning: Error processing pageviews for {article_title}: {e}")
            return pd.DataFrame(columns=['date', 'views'])
    
    def get_pageviews_for_anomaly(
        self,
        article_title: str,
        anomaly_month: str,
        window_days_before: Optional[int] = None,
        window_days_after: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get pageviews around an anomaly month.
        
        Args:
            article_title: Wikipedia article title
            anomaly_month: Month string in YYYY-MM format
            window_days_before: Days before anomaly month (optional)
            window_days_after: Days after anomaly month (optional)
            
        Returns:
            DataFrame with daily pageviews
        """
        # Parse anomaly month
        try:
            anomaly_date = datetime.strptime(anomaly_month + '-01', '%Y-%m-%d')
        except:
            anomaly_date = datetime.now()
        
        # Calculate date range
        before_days = window_days_before or self.window_days_before
        after_days = window_days_after or self.window_days_after
        
        start_date = (anomaly_date - timedelta(days=before_days)).strftime('%Y%m%d')
        end_date = (anomaly_date + timedelta(days=after_days)).strftime('%Y%m%d')
        
        return self.get_daily_pageviews(article_title, start_date, end_date)
    
    def get_multiple_pageviews(
        self,
        article_titles: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Get pageviews for multiple articles.
        
        Args:
            article_titles: List of article titles
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            
        Returns:
            Dictionary mapping article title to DataFrame
        """
        results = {}
        for title in article_titles:
            results[title] = self.get_daily_pageviews(title, start_date, end_date)
        return results





