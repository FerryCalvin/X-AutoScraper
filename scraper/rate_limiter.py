"""
Smart Rate Limiter with exponential backoff
"""

import time
from typing import Optional
from dataclasses import dataclass, field
from collections import deque
from .config import ScraperConfig


@dataclass
class RateLimitState:
    """Tracks rate limit state"""
    requests: deque = field(default_factory=deque)
    backoff_until: float = 0
    consecutive_errors: int = 0
    

class RateLimiter:
    """
    Smart rate limiter with:
    - Sliding window rate limiting
    - Exponential backoff on errors
    - Adaptive throttling
    """
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self.state = RateLimitState()
        
    def _cleanup_old_requests(self):
        """Remove requests outside the current window"""
        cutoff = time.time() - self.config.window_seconds
        while self.state.requests and self.state.requests[0] < cutoff:
            self.state.requests.popleft()
    
    def can_make_request(self) -> bool:
        """Check if we can make a request right now"""
        # Check backoff
        if time.time() < self.state.backoff_until:
            return False
            
        # Check rate limit
        self._cleanup_old_requests()
        return len(self.state.requests) < self.config.requests_per_window
    
    def wait_time(self) -> float:
        """Calculate how long to wait before next request"""
        now = time.time()
        
        # If in backoff, wait until backoff ends
        if now < self.state.backoff_until:
            return self.state.backoff_until - now
        
        self._cleanup_old_requests()
        
        # If under limit, no wait needed
        if len(self.state.requests) < self.config.requests_per_window:
            return 0
        
        # Otherwise wait for oldest request to expire
        oldest = self.state.requests[0]
        wait = (oldest + self.config.window_seconds) - now
        return max(0, wait)
    
    def wait_if_needed(self) -> float:
        """Block until we can make a request, return actual wait time"""
        wait = self.wait_time()
        if wait > 0:
            time.sleep(wait)
        return wait
    
    def record_request(self):
        """Record that a request was made"""
        self.state.requests.append(time.time())
        self.state.consecutive_errors = 0
        
    def record_success(self):
        """Record successful request"""
        self.state.consecutive_errors = 0
        
    def record_error(self, is_rate_limit: bool = False):
        """Record an error, apply backoff if needed"""
        self.state.consecutive_errors += 1
        
        if is_rate_limit or self.state.consecutive_errors >= 3:
            # Apply exponential backoff
            backoff = min(
                self.config.backoff_factor ** self.state.consecutive_errors,
                300  # Max 5 minutes
            )
            self.state.backoff_until = time.time() + backoff
            return backoff
        return 0
    
    def reset(self):
        """Reset rate limiter state"""
        self.state = RateLimitState()
        
    @property
    def current_usage(self) -> dict:
        """Get current rate limit usage info"""
        self._cleanup_old_requests()
        return {
            "requests_in_window": len(self.state.requests),
            "max_requests": self.config.requests_per_window,
            "window_seconds": self.config.window_seconds,
            "in_backoff": time.time() < self.state.backoff_until,
            "backoff_remaining": max(0, self.state.backoff_until - time.time()),
        }
