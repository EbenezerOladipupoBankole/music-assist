"""
Web Crawler for Church Music Resources
Responsibly crawls official LDS music websites for text content
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Set
from urllib.parse import urljoin, urlparse
import json
import os
from datetime import datetime
import time


class ChurchMusicCrawler:
    """
    Responsible web crawler for Church music resources
    """
    
    def __init__(
        self,
        output_dir: str = "./data/crawled",
        rate_limit_delay: float = 2.0,
        max_depth: int = 2,
        max_pages: int = 100
    ):
        self.output_dir = output_dir
        self.rate_limit_delay = rate_limit_delay
        self.max_depth = max_depth
        self.max_pages = max_pages
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Track visited URLs to avoid duplicates
        self.visited_urls: Set[str] = set()
        self.crawled_data: List[Dict] = []
        
        # Allowed domains (restrict to churchofjesuschrist.org)
        self.allowed_domains = ["www.churchofjesuschrist.org"]
        
        # User agent for responsible crawling
        self.headers = {
            "User-Agent": "Music-Assist Educational Crawler (contact: your-email@example.com)"
        }
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and within allowed domains"""
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme in ["http", "https"] and
                parsed.netloc in self.allowed_domains and
                not any(excluded in url.lower() for excluded in [
                    "login", "signin", "signup", "download",
                    ".pdf", ".mp3", ".wav", ".midi"
                ])
            )
        except:
            return False
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract main text content from HTML"""
        
        # Remove script, style, and navigation elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()
        
        # Try to find main content area
        main_content = (
            soup.find("main") or
            soup.find("article") or
            soup.find("div", class_=lambda x: x and "content" in x.lower()) or
            soup.find("body")
        )
        
        if main_content:
            # Extract text and clean up whitespace
            text = main_content.get_text(separator="\n", strip=True)
            # Remove excessive newlines
            text = "\n".join(line.strip() for line in text.split("\n") if line.strip())
            return text
        
        return ""
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract metadata from page"""
        
        title = ""
        if soup.title:
            title = soup.title.string.strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text(strip=True)
        
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = meta_desc["content"]
        
        return {
            "url": url,
            "title": title,
            "description": description,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract and normalize internal links"""
        links = []
        
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            
            # Only include valid URLs
            if self._is_valid_url(absolute_url):
                links.append(absolute_url)
        
        return list(set(links))  # Remove duplicates
    
    async def _crawl_page(
        self,
        session: aiohttp.ClientSession,
        url: str,
        depth: int
    ) -> Dict:
        """Crawl a single page"""
        
        if url in self.visited_urls or depth > self.max_depth:
            return None
        
        if len(self.visited_urls) >= self.max_pages:
            print(f"Reached max pages limit ({self.max_pages})")
            return None
        
        self.visited_urls.add(url)
        
        try:
            print(f"Crawling [{depth}]: {url}")
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
            
            # Fetch page
            async with session.get(url, headers=self.headers, timeout=30) as response:
                if response.status != 200:
                    print(f"  ✗ Status {response.status}")
                    return None
                
                html = await response.text()
            
            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract content
            content = self._extract_text_content(soup)
            
            if not content or len(content) < 100:
                print(f"  ✗ Insufficient content")
                return None
            
            # Extract metadata
            metadata = self._extract_metadata(soup, url)
            
            # Prepare document
            document = {
                **metadata,
                "content": content,
                "depth": depth
            }
            
            print(f"  ✓ Extracted {len(content)} chars")
            
            # Save document
            filename = f"doc_{len(self.crawled_data):04d}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(document, f, indent=2, ensure_ascii=False)
            
            self.crawled_data.append(document)
            
            # Extract links for further crawling
            if depth < self.max_depth:
                links = self._extract_links(soup, url)
                return {"document": document, "links": links}
            
            return {"document": document, "links": []}
            
        except asyncio.TimeoutError:
            print(f"  ✗ Timeout")
            return None
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return None
    
    async def crawl_sites(self, start_urls: List[str]) -> Dict:
        """
        Crawl multiple sites starting from given URLs
        """
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"Starting crawl of {len(start_urls)} URLs")
        print(f"Max depth: {self.max_depth}, Max pages: {self.max_pages}")
        print(f"{'='*60}\n")
        
        async with aiohttp.ClientSession() as session:
            # Queue of URLs to crawl (url, depth)
            queue = [(url, 0) for url in start_urls]
            processed = 0
            
            while queue and len(self.visited_urls) < self.max_pages:
                # Get next URL from queue
                url, depth = queue.pop(0)
                
                # Crawl page
                result = await self._crawl_page(session, url, depth)
                processed += 1
                
                # Add new links to queue
                if result and result.get("links") and depth < self.max_depth:
                    for link in result["links"]:
                        if link not in self.visited_urls:
                            queue.append((link, depth + 1))
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"Crawl complete!")
        print(f"  Documents: {len(self.crawled_data)}")
        print(f"  Pages visited: {len(self.visited_urls)}")
        print(f"  Time: {elapsed:.1f}s")
        print(f"{'='*60}\n")
        
        # Save summary
        summary = {
            "total_documents": len(self.crawled_data),
            "pages_visited": len(self.visited_urls),
            "elapsed_seconds": elapsed,
            "timestamp": datetime.utcnow().isoformat(),
            "start_urls": start_urls
        }
        
        with open(os.path.join(self.output_dir, "crawl_summary.json"), 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary


async def main():
    """Example usage"""
    
    crawler = ChurchMusicCrawler(
        output_dir="./data/crawled",
        rate_limit_delay=2.0,
        max_depth=2,
        max_pages=50
    )
    
    urls = [
        "https://www.churchofjesuschrist.org/media/music?lang=eng",
        "https://www.churchofjesuschrist.org/initiative/new-hymns?lang=eng",
        "https://www.churchofjesuschrist.org/callings/music/common-questions-about-music-in-church-meetings?lang=eng",
        "https://www.churchofjesuschrist.org/study/handbooks-and-callings/ward-or-branch-callings/music?lang=eng"
    ]
    
    await crawler.crawl_sites(urls)


if __name__ == "__main__":
    asyncio.run(main())