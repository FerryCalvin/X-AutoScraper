"""
High-level Twitter Scraper Interface
Easy to use for friends!
"""

import json
import csv
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Callable
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .config import ScraperConfig
from .models import Tweet, SearchResult
from .twitter_client import TwitterClient, TwitterAPIError


console = Console()


class TwitterScraper:
    """
    High-level Twitter scraper interface.
    
    Usage:
        scraper = TwitterScraper()
        tweets = scraper.scrape("python programming", count=100)
        scraper.export_json(tweets, "hasil_scraping.json")
    """
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self.client = TwitterClient(self.config)
        
    def scrape(
        self,
        keyword: str,
        count: int = 100,
        show_progress: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Tweet]:
        """
        Scrape tweets by keyword.
        
        Args:
            keyword: Search keyword/query
            count: Number of tweets to fetch (default 100)
            show_progress: Show progress bar (default True)
            progress_callback: Optional callback(current, total)
            
        Returns:
            List of Tweet objects
        """
        tweets: List[Tweet] = []
        
        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task(
                    f"Scraping '{keyword}'...",
                    total=count
                )
                
                def update_progress(current: int, total: int):
                    progress.update(task, completed=current)
                    if progress_callback:
                        progress_callback(current, total)
                
                tweets = self.client.search_tweets(
                    keyword=keyword,
                    max_tweets=count,
                    progress_callback=update_progress
                )
                    
                progress.update(task, completed=len(tweets))
        else:
            tweets = self.client.search_tweets(
                keyword=keyword,
                max_tweets=count,
                progress_callback=progress_callback
            )
        
        return tweets
    
    async def scrape_async(
        self,
        keyword: str,
        count: int = 100,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Tweet]:
        """Async version of scrape"""
        return await self.client.search_tweets_async(
            keyword=keyword,
            max_tweets=count,
            progress_callback=progress_callback
        )
    
    def scrape_to_result(
        self,
        keyword: str,
        count: int = 100,
        show_progress: bool = True
    ) -> SearchResult:
        """
        Scrape tweets and return SearchResult with metadata.
        """
        result = SearchResult(keyword=keyword)
        tweets = self.scrape(keyword, count, show_progress)
        for tweet in tweets:
            result.add_tweet(tweet)
        result.completed_at = datetime.now()
        return result
    
    @staticmethod
    def export_json(tweets: List[Tweet], filepath: str, indent: int = 2):
        """Export tweets to JSON file"""
        path = Path(filepath)
        data = [tweet.model_dump(mode="json") for tweet in tweets]
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent, default=str)
            
        console.print(f"[green]✓[/green] Exported {len(tweets)} tweets to {path}")
        return path
    
    @staticmethod
    def export_csv(tweets: List[Tweet], filepath: str):
        """Export tweets to CSV file"""
        path = Path(filepath)
        
        if not tweets:
            console.print("[yellow]Warning:[/yellow] No tweets to export")
            return path
        
        # Flatten tweet data for CSV
        fieldnames = [
            "id", "text", "created_at", "language",
            "like_count", "retweet_count", "reply_count", "view_count",
            "user_id", "username", "user_display_name", "user_followers",
            "hashtags", "mentions", "urls", "has_media"
        ]
        
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for tweet in tweets:
                writer.writerow({
                    "id": tweet.id,
                    "text": tweet.text.replace("\n", " "),
                    "created_at": tweet.created_at.isoformat(),
                    "language": tweet.language,
                    "like_count": tweet.like_count,
                    "retweet_count": tweet.retweet_count,
                    "reply_count": tweet.reply_count,
                    "view_count": tweet.view_count,
                    "user_id": tweet.user.id,
                    "username": tweet.user.username,
                    "user_display_name": tweet.user.display_name,
                    "user_followers": tweet.user.followers_count,
                    "hashtags": ",".join(tweet.hashtags),
                    "mentions": ",".join(tweet.mentions),
                    "urls": ",".join(tweet.urls),
                    "has_media": tweet.has_media,
                })
        
        console.print(f"[green]✓[/green] Exported {len(tweets)} tweets to {path}")
        return path
    
    @staticmethod
    def print_summary(tweets: List[Tweet]):
        """Print summary of scraped tweets"""
        if not tweets:
            console.print("[yellow]No tweets found[/yellow]")
            return
            
        console.print("\n[bold]📊 Scraping Summary[/bold]")
        console.print(f"  Total tweets: {len(tweets)}")
        
        # Language distribution
        lang_counts = {}
        for tweet in tweets:
            lang = tweet.language or "unknown"
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        
        console.print("  Languages:")
        for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1])[:5]:
            console.print(f"    - {lang}: {count}")
        
        # Engagement stats
        total_likes = sum(t.like_count for t in tweets)
        total_retweets = sum(t.retweet_count for t in tweets)
        total_views = sum(t.view_count for t in tweets)
        
        console.print(f"  Total engagement:")
        console.print(f"    - Likes: {total_likes:,}")
        console.print(f"    - Retweets: {total_retweets:,}")
        console.print(f"    - Views: {total_views:,}")
        
        # Top tweet
        top_tweet = max(tweets, key=lambda t: t.like_count + t.retweet_count)
        console.print(f"\n  [bold]🔥 Top Tweet:[/bold]")
        console.print(f"    @{top_tweet.user.username}: {top_tweet.text[:100]}...")
        console.print(f"    ❤️ {top_tweet.like_count} | 🔄 {top_tweet.retweet_count} | 👁️ {top_tweet.view_count}")
