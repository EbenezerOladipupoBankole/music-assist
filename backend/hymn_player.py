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
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/001-the-morning-breaks-vocal-64k-eng.mp3",
                "tags": ["morning", "opening"]
            },
            {
                "title": "The Spirit of God",
                "number": 2,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/002-the-spirit-of-god-vocal-64k-eng.mp3",
                "tags": ["opening", "restoration"]
            },
            {
                "title": "High on the Mountain Top",
                "number": 5,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/005-high-on-the-mountain-top-vocal-64k-eng.mp3",
                "tags": ["opening", "restoration"]
            },
            {
                "title": "Redeemer of Israel",
                "number": 6,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/006-redeemer-of-israel-words-and-music-128k-eng.mp3",
                "tags": ["opening", "savior"]
            },
            {
                "title": "We Thank Thee, O God, for a Prophet",
                "number": 19,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/019-we-thank-thee-o-god-for-a-prophet-words-and-music-128k-eng.mp3",
                "tags": ["prophet", "opening"]
            },
            {
                "title": "Joseph Smith's First Prayer",
                "number": 26,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/026-joseph-smiths-first-prayer-words-and-music-128k-eng.mp3",
                "tags": ["restoration", "joseph smith"]
            },
            {
                "title": "Abide with Me!",
                "number": 166,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/166-abide-with-me-words-and-music-128k-eng.mp3",
                "tags": ["closing", "evening", "comfort"]
            },
            {
                "title": "As Now We Take the Sacrament",
                "number": 169,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/169-as-now-we-take-the-sacrament-words-and-music-128k-eng.mp3",
                "tags": ["sacrament", "worship"]
            },
            {
                "title": "In Humility, Our Savior",
                "number": 172,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/172-in-humility-our-savior-words-and-music-128k-eng.mp3",
                "tags": ["sacrament", "savior", "worship"]
            },
            {
                "title": "Jesus of Nazareth, Savior and King",
                "number": 181,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/181-jesus-of-nazareth-savior-and-king-words-and-music-128k-eng.mp3",
                "tags": ["sacrament", "savior"]
            },
            {
                "title": "Upon the Cross of Calvary",
                "number": 184,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/184-upon-the-cross-of-calvary-words-and-music-128k-eng.mp3",
                "tags": ["sacrament", "savior", "atonement"]
            },
            {
                "title": "I Stand All Amazed",
                "number": 193,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/193-i-stand-all-amazed-vocal-64k-eng.mp3",
                "tags": ["sacrament", "savior", "atonement"]
            },
            {
                "title": "There Is a Green Hill Far Away",
                "number": 194,
                "url": "https://media2.ldscdn.org/audio/music/hymns/hymns-eng/194-there-is-a-green-hill-far-away-vocal-64k-eng.mp3",
                "tags": ["sacrament", "savior", "atonement"]
            },
            {
                "title": "I Am a Child of God",
                "number": 301,
                "url": "https://media2.ldscdn.org/audio/music/childrens-songbook/childrens-songbook-eng/301-i-am-a-child-of-god-vocal-64k-eng.mp3",
                "tags": ["children", "family"]
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
        
        # 2. Check for tag match
        for h in self.hymns_db:
            if any(clean_query in tag.lower() for tag in h.get("tags", [])):
                if h not in results:
                    results.append(h)

        # 3. Check for title match (substring)
        for h in self.hymns_db:
            if clean_query in h["title"].lower():
                if h not in results:
                    results.append(h)
                    
        return results
