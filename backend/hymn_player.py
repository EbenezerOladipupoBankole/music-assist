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
        # Hymn database - Audio URLs are currently unavailable due to Church platform migration
        # Users should access hymns through: Gospel Library app, Sacred Music app, or ChurchofJesusChrist.org
        self.hymns_db = [
            {
                "title": "The Morning Breaks",
                "number": 1,
                "url": None,  # Temporarily unavailable - use Gospel Library app
                "tags": ["morning", "opening"],
                "access_note": "Listen via Gospel Library app or ChurchofJesusChrist.org/music"
            },
            {
                "title": "The Spirit of God",
                "number": 2,
                "url": None,
                "tags": ["opening", "restoration"],
                "access_note": "Listen via Gospel Library app or ChurchofJesusChrist.org/music"
            },
            {
                "title": "High on the Mountain Top",
                "number": 5,
                "url": None,
                "tags": ["opening", "restoration"],
                "access_note": "Listen via Gospel Library app or ChurchofJesusChrist.org/music"
            },
            {
                "title": "Redeemer of Israel",
                "number": 6,
                "url": None,
                "tags": ["opening", "savior"],
                "access_note": "Listen via Gospel Library app or ChurchofJesusChrist.org/music"
            },
            {
                "title": "We Thank Thee, O God, for a Prophet",
                "number": 19,
                "url": None,
                "tags": ["prophet", "opening"],
                "access_note": "Listen via Gospel Library app or ChurchofJesusChrist.org/music"
            },
            {
                "title": "Joseph Smith's First Prayer",
                "number": 26,
                "url": None,
                "tags": ["restoration", "joseph smith"],
                "access_note": "Listen via Gospel Library app or ChurchofJesusChrist.org/music"
            },
            {
                "title": "Abide with Me!",
                "number": 166,
                "url": None,
                "tags": ["closing", "evening", "comfort"],
                "access_note": "Listen via Gospel Library app or ChurchofJesusChrist.org/music"
            },
            {
                "title": "As Now We Take the Sacrament",
                "number": 169,
                "url": None,
                "tags": ["sacrament", "worship"],
                "access_note": "Listen via Gospel Library app or ChurchofJesusChrist.org/music"
            },
            {
                "title": "In Humility, Our Savior",
                "number": 172,
                "url": None,
                "tags": ["sacrament", "savior", "worship"],
                "access_note": "Listen via Gospel Library app or ChurchofJesusChrist.org/music"
            },
            {
                "title": "Jesus of Nazareth, Savior and King",
                "number": 181,
                "url": None,
                "tags": ["sacrament", "savior"],
                "access_note": "Listen via Gospel Library app or ChurchofJesusChrist.org/music"
            },
            {
                "title": "Upon the Cross of Calvary",
                "number": 184,
                "url": None,
                "tags": ["sacrament", "savior", "atonement"],
                "access_note": "Listen via Gospel Library app or ChurchofJesusChrist.org/music"
            },
            {
                "title": "I Stand All Amazed",
                "number": 193,
                "url": None,
                "tags": ["sacrament", "savior", "atonement"],
                "access_note": "Listen via Gospel Library app or ChurchofJesusChrist.org/music"
            },
            {
                "title": "There Is a Green Hill Far Away",
                "number": 194,
                "url": None,
                "tags": ["sacrament", "savior", "atonement"],
                "access_note": "Listen via Gospel Library app or ChurchofJesusChrist.org/music"
            },
            {
                "title": "I Am a Child of God",
                "number": 301,
                "url": None,
                "tags": ["children", "family"],
                "access_note": "Listen via Gospel Library app or ChurchofJesusChrist.org/music"
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
