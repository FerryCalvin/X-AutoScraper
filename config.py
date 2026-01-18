"""
Configuration Loader for AutoScraper
Loads settings from config.yaml with sensible defaults
"""
import os
import yaml

# Default configuration values
DEFAULT_CONFIG = {
    'scraper': {
        'default_count': 100,
        'scroll_delay_min': 1.5,
        'scroll_delay_max': 4.0,
        'max_scroll_attempts': 100,
        'coffee_break_interval': 50,
        'coffee_break_duration': 15
    },
    'workers': {
        'default_mode': 3,
        'parallel_threshold': 500,
        'stagger_delay': 10
    },
    'chunking': {
        'enabled': True,
        'chunk_days': 7,
        'min_range_for_chunking': 7
    },
    'rate_limit': {
        'max_requests_per_minute': 30,
        'warning_threshold': 20,
        'danger_threshold': 25
    },
    'logging': {
        'enabled': True,
        'file': 'logs/autoscraper.log',
        'level': 'INFO',
        'max_size_mb': 10,
        'backup_count': 5
    },
    'output': {
        'directory': 'outputs',
        'format': 'csv',
        'include_clean_text': True
    },
    'sentiment': {
        'enabled': False,
        'model': 'indobert',
        'batch_size': 32
    },
    'topics': {
        'enabled': False,
        'num_topics': 5,
        'words_per_topic': 10
    }
}


def load_config(config_path='config.yaml'):
    """
    Load configuration from YAML file with fallback to defaults.
    
    Args:
        config_path: Path to config.yaml file
        
    Returns:
        dict: Merged configuration (file values override defaults)
    """
    config = DEFAULT_CONFIG.copy()
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f) or {}
                
            # Deep merge file config into defaults
            for key, value in file_config.items():
                if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                    config[key].update(value)
                else:
                    config[key] = value
                    
        except Exception as e:
            print(f"⚠️ Error loading config: {e}. Using defaults.")
    
    return config


def get(key_path, default=None):
    """
    Get a config value using dot notation.
    
    Example:
        get('scraper.max_scroll_attempts')  # Returns 100
        get('workers.stagger_delay', 5)     # Returns 10 or default 5
    
    Args:
        key_path: Dot-separated path to config value
        default: Default value if key not found
        
    Returns:
        Config value or default
    """
    keys = key_path.split('.')
    value = CONFIG
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value


# Load config at module import
CONFIG = load_config()

# Convenience accessors
SCRAPER = CONFIG.get('scraper', {})
WORKERS = CONFIG.get('workers', {})
LOGGING = CONFIG.get('logging', {})
OUTPUT = CONFIG.get('output', {})
RATE_LIMIT = CONFIG.get('rate_limit', {})
