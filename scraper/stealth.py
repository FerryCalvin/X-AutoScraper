"""
Stealth utilities for anti-detection
"""

import random
import time
from typing import Dict, Optional
from .config import DEFAULT_HEADERS, ScraperConfig


class StealthManager:
    """Manages anti-detection techniques"""
    
    # Realistic User-Agent strings (updated Dec 2024)
    USER_AGENTS = [
        # Chrome Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        # Chrome Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        # Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]
    
    # Sec-Ch-Ua values matching Chrome versions
    SEC_CH_UA_OPTIONS = [
        '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        '"Not_A Brand";v="8", "Chromium";v="119", "Google Chrome";v="119"',
        '"Not_A Brand";v="8", "Chromium";v="121", "Google Chrome";v="121"',
        '"Microsoft Edge";v="120", "Not_A Brand";v="8", "Chromium";v="120"',
    ]
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self._current_ua_index = 0
        
    def get_random_user_agent(self) -> str:
        """Get a random user agent"""
        return random.choice(self.USER_AGENTS)
    
    def get_rotating_user_agent(self) -> str:
        """Get user agent with rotation"""
        ua = self.USER_AGENTS[self._current_ua_index % len(self.USER_AGENTS)]
        self._current_ua_index += 1
        return ua
    
    def get_browser_version(self) -> str:
        """Get random browser version for curl_cffi impersonation"""
        return random.choice(self.config.browser_versions)
    
    def build_headers(
        self, 
        guest_token: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Build realistic browser headers"""
        headers = DEFAULT_HEADERS.copy()
        
        # Add User-Agent
        headers["User-Agent"] = self.get_random_user_agent()
        
        # Add Sec-Ch-Ua
        sec_ch_ua = random.choice(self.SEC_CH_UA_OPTIONS)
        headers["Sec-Ch-Ua"] = sec_ch_ua
        
        # Add guest token if available
        if guest_token:
            headers["X-Guest-Token"] = guest_token
            
        # Add any extra headers
        if extra_headers:
            headers.update(extra_headers)
            
        return headers
    
    def random_delay(self) -> float:
        """Generate random human-like delay"""
        delay = random.uniform(self.config.min_delay, self.config.max_delay)
        # Add occasional longer pauses (5% chance)
        if random.random() < 0.05:
            delay += random.uniform(2.0, 5.0)
        return delay
    
    def wait(self):
        """Wait with random delay"""
        delay = self.random_delay()
        time.sleep(delay)
        return delay
    
    def jitter(self, base_delay: float, factor: float = 0.3) -> float:
        """Add jitter to a delay"""
        jitter_amount = base_delay * factor
        return base_delay + random.uniform(-jitter_amount, jitter_amount)
