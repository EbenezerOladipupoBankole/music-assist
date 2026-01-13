import re
from typing import Dict, Optional, List

class HymnPlayer:
    """
    A simple class to find hymn URLs based on titles.
    It holds a small, hardcoded list of hymns for demonstration.
    """
    def __init__(self):
        """
        Initializes the HymnPlayer.
        
        In a real application, this list could be populated by enhancing the crawler
        to find and store links to audio files from the church's music library.
        """
        self.hymn_data: Dict[str, Dict[str, str]] = {
            "come, come, ye saints": {
                "title": "Come, Come, Ye Saints",
                "url": "https://media2.ldscdn.org/assets/music/hymns/2001-01-0300-come-come-ye-saints-vocal-and-instrumental-192k-eng.mp3"
            },
            "i am a child of god": {
                "title": "I Am a Child of God",
                "url": "https://media2.ldscdn.org/assets/music/childrens-songbook/2001-01-0020-i-am-a-child-of-god-vocal-and-instrumental-192k-eng.mp3"
            },
            "the spirit of god": {
                "title": "The Spirit of God",
                "url": "https://media2.ldscdn.org/assets/music/hymns/2001-01-0020-the-spirit-of-god-vocal-and-instrumental-192k-eng.mp3"
            },
        }
        self.known_hymns = [v['title'] for k, v in self.hymn_data.items()]

    def get_hymn(self, query: str) -> Optional[Dict[str, str]]:
        """
        Finds a hymn based on a user query.
        Returns a dict with title and url if found, otherwise None.
        """
        query = query.lower().strip().replace("’", "'")
        if not query:
            return None

        for hymn_key, hymn_info in self.hymn_data.items():
            if query in hymn_key or hymn_key in query:
                return hymn_info

        return None

    def get_hymns(self, query: str) -> List[Dict[str, str]]:
        """
        Finds all hymns matching the query.
        Returns a list of dicts with title and url.
        """
        query = query.lower().strip().replace("’", "'")
        if not query:
            return []

        # Find all hymns where the key is in the query OR the query is in the key
        # This supports "play hymn A and hymn B" as well as "play [part of title]"
        return [info for key, info in self.hymn_data.items() if key in query or query in key]