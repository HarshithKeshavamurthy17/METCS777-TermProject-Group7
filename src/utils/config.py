"""Configuration loading utilities."""
import yaml
import os
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file. If None, looks for config/config.yaml
        
    Returns:
        Dictionary containing configuration
    """
    if config_path is None:
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "config.yaml"
        
        # Fallback to example config if actual config doesn't exist
        if not config_path.exists():
            config_path = project_root / "config" / "config.example.yaml"
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Resolve relative paths
    project_root = Path(config_path).parent.parent
    if 'data' in config:
        for key in ['raw_data_dir', 'processed_data_dir', 'anomalies_dir']:
            if key in config['data']:
                path = config['data'][key]
                if not os.path.isabs(path):
                    config['data'][key] = str(project_root / path)
    
    return config


def get_spark_config(config: Dict[str, Any]) -> Dict[str, str]:
    """Extract Spark configuration from main config."""
    spark_config = config.get('spark', {})
    return {
        'appName': spark_config.get('app_name', 'Wikipedia Clickstream Anomaly Detection'),
        'master': spark_config.get('master', 'local[*]'),
        'spark.executor.memory': spark_config.get('executor_memory', '8g'),
        'spark.driver.memory': spark_config.get('driver_memory', '4g'),
        'spark.executor.cores': str(spark_config.get('executor_cores', 4)),
        'spark.driver.maxResultSize': spark_config.get('max_result_size', '2g'),
    }

