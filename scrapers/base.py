from abc import ABC, abstractmethod

class BaseScraper(ABC):
    @abstractmethod
    def scrape(self, keyword, count=100, **kwargs):
        """
        Scrape data for a given keyword.
        :param keyword: Search query
        :param count: Target number of items
        :return: List of dictionaries (scraped data)
        """
        pass
        
    @abstractmethod
    def health_check(self):
        """
        Check if the scraper is healthy (e.g. login status, connectivity).
        :return: Boolean or Dict
        """
        pass
