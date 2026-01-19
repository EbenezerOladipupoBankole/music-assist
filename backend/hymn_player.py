"""
Hymn Player Module
Manages hymn audio links and searching for the Music-Assist API
"""

import re
from typing import List, Dict

class HymnPlayer:
    """
    Manages hymn audio links and searching.
    """
    def __init__(self):
        # Sample database of hymns with official LDS media library URLs
        self.hymns_db = [
            {
                "title": "The Morning Breaks",
                "number": 1,
                "url": "https://media2.ldscdn.org/assets/music/hymns/2019-01-0010-the-morning-breaks-vocal-mp3-eng.mp3"
            },
            {
                "title": "The Spirit of God",
                "number": 2,
                "url": "https://media2.ldscdn.org/assets/music/hymns/2019-01-0020-the-spirit-of-god-vocal-mp3-eng.mp3"
            },
            {
                "title": "High on the Mountain Top",
                "number": 5,
                "url": "https://media2.ldscdn.org/assets/music/hymns/2019-01-0050-high-on-the-mountain-top-vocal-mp3-eng.mp3"
            },
            {
                "title": "Redeemer of Israel",
                "number": 6,
                "url": "https://media2.ldscdn.org/assets/music/hymns/2019-01-0060-redeemer-of-israel-vocal-mp3-eng.mp3"
            },
            {
                "title": "We Thank Thee, O God, for a Prophet",
                "number": 19,
                "url": "https://media2.ldscdn.org/assets/music/hymns/2019-01-0190-we-thank-thee-o-god-for-a-prophet-vocal-mp3-eng.mp3"
            },
            {
                "title": "Joseph Smith's First Prayer",
                "number": 26,
                "url": "https://media2.ldscdn.org/assets/music/hymns/2019-01-0260-joseph-smiths-first-prayer-vocal-mp3-eng.mp3"
            },
            {
                "title": "Come, Come, Ye Saints",
                "number": 30,
                "url": "https://media2.ldscdn.org/assets/music/hymns/2019-01-0300-come-come-ye-saints-vocal-mp3-eng.mp3"
            },
            {
                "title": "For the Strength of the Hills",
                "number": 35,
                "url": "https://media2.ldscdn.org/assets/music/hymns/2019-01-0350-for-the-strength-of-the-hills-vocal-mp3-eng.mp3"
            },
            {
                "title": "I Know That My Redeemer Lives",
                "number": 136,
                "url": "https://media2.ldscdn.org/assets/music/hymns/2019-01-1360-i-know-that-my-redeemer-lives-vocal-mp3-eng.mp3"
            },
            {
                "title": "I Am a Child of God",
                "number": 301,
                "url": "https://media2.ldscdn.org/assets/music/childrens-songbook/2002-01-0010-i-am-a-child-of-god-words-and-music-192k-eng.mp3"
            },
            {
                "title": "God Be with You Till We Meet Again",
                "number": 152,
                "url": "https://media2.ldscdn.org/assets/music/hymns/2019-01-1520-god-be-with-you-till-we-meet-again-vocal-mp3-eng.mp3"
            },
            {
                "title": "Abide with Me!",
                "number": 166,
                "url": "https://media2.ldscdn.org/assets/music/hymns/2019-01-1660-abide-with-me-vocal-mp3-eng.mp3"
            }
        ]
        
        # List of known titles for random selection or validation
        self.known_hymns = [h["title"] for h in self.hymns_db]

    def get_hymns(self, query: str) -> List[Dict]:
        """Search for hymns matching the query (by title or number)."""
        if not query:
            return []
            
        query = query.lower().strip()
        results = []
        
        # 1. Check for exact number match
        number_match = re.search(r'\b(\d{1,3})\b', query)
        if number_match:
            num = int(number_match.group(1))
            for h in self.hymns_db:
                if h.get("number") == num:
                    results.append(h)
        
        # 2. Check for title match (substring)
        for h in self.hymns_db:
            if query in h["title"].lower():
                if h not in results:
                    results.append(h)
                    
        return results
