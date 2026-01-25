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
        # Sample database of hymns with official LDS media library URLs (Modern Pattern)
        self.hymns_db = [
            {
                "title": "The Morning Breaks",
                "number": 1,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/001-the-morning-breaks-words-and-music-128k-eng.mp3"
            },
            {
                "title": "The Spirit of God",
                "number": 2,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/002-the-spirit-of-god-words-and-music-128k-eng.mp3"
            },
            {
                "title": "High on the Mountain Top",
                "number": 5,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/005-high-on-the-mountain-top-words-and-music-128k-eng.mp3"
            },
            {
                "title": "Redeemer of Israel",
                "number": 6,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/006-redeemer-of-israel-words-and-music-128k-eng.mp3"
            },
            {
                "title": "We Thank Thee, O God, for a Prophet",
                "number": 19,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/019-we-thank-thee-o-god-for-a-prophet-words-and-music-128k-eng.mp3"
            },
            {
                "title": "Joseph Smith's First Prayer",
                "number": 26,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/026-joseph-smiths-first-prayer-words-and-music-128k-eng.mp3"
            },
            {
                "title": "Come, Come, Ye Saints",
                "number": 30,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/030-come-come-ye-saints-words-and-music-128k-eng.mp3"
            },
            {
                "title": "For the Strength of the Hills",
                "number": 35,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/035-for-the-strength-of-the-hills-words-and-music-128k-eng.mp3"
            },
            {
                "title": "Lead, Kindly Light",
                "number": 97,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/097-lead-kindly-light-words-and-music-128k-eng.mp3"
            },
            {
                "title": "I Know That My Redeemer Lives",
                "number": 136,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/136-i-know-that-my-redeemer-lives-words-and-music-128k-eng.mp3"
            },
            {
                "title": "How Firm a Foundation",
                "number": 85,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/085-how-firm-a-foundation-words-and-music-128k-eng.mp3"
            },
            {
                "title": "I Am a Child of God",
                "number": 301,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/301-i-am-a-child-of-god-words-and-music-128k-eng.mp3"
            },
            {
                "title": "God Be with You Till We Meet Again",
                "number": 152,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/152-god-be-with-you-till-we-meet-again-words-and-music-128k-eng.mp3"
            },
            {
                "title": "Abide with Me!",
                "number": 166,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/166-abide-with-me-words-and-music-128k-eng.mp3"
            }
        ]
        
        # List of known titles for random selection or validation
        self.known_hymns = [h["title"] for h in self.hymns_db]

    def get_hymns(self, query: str) -> List[Dict]:
        """Search for hymns matching the query (by title or number)."""
        if not query:
            return []
            
        clean_query = query.lower().strip()
        results = []
        
        # 1. Check for exact number match
        number_match = re.search(r'\b(\d{1,3})\b', clean_query)
        if number_match:
            num = int(number_match.group(1))
            for h in self.hymns_db:
                if h.get("number") == num:
                    results.append(h)
        
        # 2. Check for title match (substring)
        for h in self.hymns_db:
            if clean_query in h["title"].lower():
                if h not in results:
                    results.append(h)
                    
        return results
