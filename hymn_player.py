import json
import re
import os
import urllib.request
import random
from bs4 import BeautifulSoup

class HymnPlayer:
    """
    A module to handle searching for and 'singing' (playing) LDS hymns
    by linking to the official music library.
    """
    def __init__(self, data_path):
        self.data_path = data_path
        self.known_hymns = self._load_hymns_from_docs()

    def _load_hymns_from_docs(self):
        """Parses the crawled documentation to find mentioned hymn titles."""
        hymns = []
        if not os.path.exists(self.data_path):
            print(f"Warning: Data file not found at {self.data_path}")
            return hymns
            
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                content = data.get('content', '')
                # Extract text inside curly quotes which denotes hymn titles in the docs
                # e.g. “The Spirit of God”
                matches = re.findall(r'“([^”]+)”', content)
                hymns = list(set(matches))  # Remove duplicates
        except Exception as e:
            print(f"Error loading hymns: {e}")
        return hymns

    def get_hymn_url(self, query):
        """Searches for the hymn and returns the audio player URL."""
        
        # 1. Clean up the query (remove conversational fillers)
        clean_query = re.sub(r'\s+(for me|please|now|today)[.!?]*$', '', query, flags=re.IGNORECASE).strip()
        
        # 2. Handle empty or generic requests -> Random Hymn
        if not clean_query or clean_query.lower() in ['something', 'anything', 'a hymn', 'a song']:
            if self.known_hymns:
                target_hymn = random.choice(self.known_hymns)
            else:
                target_hymn = "The Spirit of God"
            
            page_url = self._construct_url(target_hymn)
            return self._scrape_audio_url(page_url)

        # 3. Search for specific hymn
        match = None
        query_lower = clean_query.lower()
        
        for hymn in sorted(self.known_hymns, key=len, reverse=True):
            h_lower = hymn.lower()
            if query_lower in h_lower or h_lower in query_lower:
                match = hymn
                break
        
        target_hymn = match if match else clean_query
        
        page_url = self._construct_url(target_hymn)
        return self._scrape_audio_url(page_url)

    def _scrape_audio_url(self, page_url):
        """Fetches the page to find the actual MP3 link."""
        try:
            # Simple scraping to find the first MP3
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(page_url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=5) as response:
                soup = BeautifulSoup(response.read(), 'html.parser')
                
                # 1. Check for <audio> tags (HTML5 player)
                audio = soup.find('audio')
                if audio:
                    if audio.get('src'): return audio['src']
                    source = audio.find('source', src=True)
                    if source: return source['src']

                # 2. Check for explicit download links (<a> tags)
                for a in soup.find_all('a', href=True):
                    # Check if .mp3 is in the link (handles query params or full paths)
                    if '.mp3' in a['href']:
                        return a['href']
                        
        except Exception as e:
            print(f"Could not scrape audio URL: {e}")
            
        return page_url

    def _construct_url(self, hymn_title):
        """Constructs the official URL."""
        # Convert title to URL slug: "The Spirit of God" -> "the-spirit-of-god"
        slug = hymn_title.lower().replace(" ", "-").replace(",", "").replace("!", "").replace("'", "")
        
        # Official Church Music Library URL pattern
        return f"https://www.churchofjesuschrist.org/music/library/hymns/{slug}?lang=eng"

if __name__ == "__main__":
    # Pointing to the file that contains a list of standard hymns
    DATA_FILE = r"c:\Users\LENOVO\music-assist\data\crawled\doc_0044.json"
    
    bot_singer = HymnPlayer(DATA_FILE)
    
    # Example interaction
    print(f"Bot loaded {len(bot_singer.known_hymns)} hymns from documentation.")
    
    # Try to sing a hymn
    url = bot_singer.get_hymn_url("The Spirit of God")
    print(f"Audio URL: {url}")