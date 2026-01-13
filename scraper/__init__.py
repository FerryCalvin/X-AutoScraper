"""
Twitter/X Stealth Scraper
Built by Friday for sentiment analysis project
"""

from .scraper import TwitterScraper
from .models import Tweet, SearchResult

__version__ = "1.0.0"
__all__ = ["TwitterScraper", "Tweet", "SearchResult"]
