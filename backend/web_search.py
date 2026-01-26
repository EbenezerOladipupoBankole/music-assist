"""
Real-time Web Search Module for Music-Assist
Searches Church music websites when local data is insufficient
"""

import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urljoin
import re


class ChurchMusicWebSearch:
    """
    Real-time web searcher for Church of Jesus Christ of Latter-day Saints music content
    """
    
    def __init__(self):
        self.base_urls = [
            "https://www.churchofjesuschrist.org/music",
            "https://www.churchofjesuschrist.org/study/manual/sacred-music",
            "https://www.churchofjesuschrist.org/callings/church-music",
        ]
        self.max_results = 3  # Reduced for faster response
        self.timeout = 8  # Tighter timeout for snappier fallback
        
    async def search(self, query: str) -> List[Dict]:
        """
        Search Church music websites for relevant content
        
        Args:
            query: User's search query
            
        Returns:
            List of dicts with 'content', 'url', 'title', 'relevance_score'
        """
        try:
            # Use Google site search for Church music content
            # Format: "query site:churchofjesuschrist.org/music OR site:churchofjesuschrist.org/callings/church-music"
            search_query = f"{query} site:churchofjesuschrist.org/music OR site:churchofjesuschrist.org/callings/church-music"
            
            results = await self._google_search(search_query)
            
            # Extract content from each result URL
            extracted_results = []
            for result in results[:self.max_results]:
                content = await self._extract_content(result['url'])
                if content:
                    extracted_results.append({
                        'content': content,
                        'url': result['url'],
                        'title': result['title'],
                        'relevance_score': result.get('relevance_score', 0.5)
                    })
            
            return extracted_results
            
        except Exception as e:
            print(f"[WARNING] Web search error: {e}")
            return []
    
    async def _google_search(self, query: str) -> List[Dict]:
        """
        Perform Google search (simplified version)
        In production, you'd use Google Custom Search API
        
        For now, we'll do direct Church website search
        """
        try:
            # Fallback: Search directly on Church websites
            results = await self._direct_church_search(query)
            return results
            
        except Exception as e:
            print(f"[WARNING] Google search error: {e}")
            return []
    
    async def _direct_church_search(self, query: str) -> List[Dict]:
        """
        Search directly on Church music pages
        This is a simplified approach - extracts pages that might match the query
        """
        results = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Search common Church music pages
                search_urls = [
                    f"https://www.churchofjesuschrist.org/music/library/hymns",
                    f"https://www.churchofjesuschrist.org/callings/church-music",
                    f"https://www.churchofjesuschrist.org/music/frequently-asked-questions",
                    f"https://www.churchofjesuschrist.org/study/manual/sacred-music",
                ]
                
                tasks = [self._fetch_page(session, url) for url in search_urls]
                pages = await asyncio.gather(*tasks, return_exceptions=True)
                
                for url, page_data in zip(search_urls, pages):
                    if isinstance(page_data, Exception):
                        continue
                    
                    if page_data and self._is_relevant(page_data['content'], query):
                        results.append({
                            'url': url,
                            'title': page_data['title'],
                            'relevance_score': self._calculate_relevance(page_data['content'], query)
                        })
        
        except Exception as e:
            print(f"[WARNING] Direct search error: {e}")
        
        # Sort by relevance
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results
    
    async def _fetch_page(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        """Fetch a single page"""
        try:
            async with session.get(url, timeout=self.timeout) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract title
                    title = soup.find('title')
                    title = title.get_text() if title else url
                    
                    # Extract main content
                    content = self._extract_text_from_soup(soup)
                    
                    return {
                        'title': title.strip(),
                        'content': content
                    }
        except Exception as e:
            print(f"[WARNING] Error fetching {url}: {e}")
        
        return None
    
    async def _extract_content(self, url: str) -> Optional[str]:
        """Extract text content from a URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        content = self._extract_text_from_soup(soup)
                        return content
        except Exception as e:
            print(f"[WARNING] Error extracting content from {url}: {e}")
        
        return None
    
    def _extract_text_from_soup(self, soup: BeautifulSoup) -> str:
        """Extract clean text from BeautifulSoup object"""
        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Limit length to avoid overwhelming the context
        if len(text) > 3000:
            text = text[:3000] + "..."
        
        return text
    
    def _is_relevant(self, content: str, query: str) -> bool:
        """Check if content is relevant to query"""
        query_terms = query.lower().split()
        content_lower = content.lower()
        
        # Check if at least 2 query terms appear in content
        matches = sum(1 for term in query_terms if term in content_lower)
        return matches >= min(2, len(query_terms))
    
    def _calculate_relevance(self, content: str, query: str) -> float:
        """Calculate relevance score (0-1)"""
        query_terms = query.lower().split()
        content_lower = content.lower()
        
        # Count term frequency
        total_matches = sum(content_lower.count(term) for term in query_terms)
        
        # Normalize by content length (favor documents with higher term density)
        relevance = min(1.0, total_matches / (len(content_lower.split()) / 10))
        
        return relevance


def is_music_related_question(query: str, has_history: bool = False) -> bool:
    """
    Validate if question is about Church music.
    Supports conversational context: if has_history is True, brief follow-up questions
    are allowed even if they don't contain specific music keywords.
    """
    query_lower = query.lower().strip()
    
    # Relaxed limit for follow-ups (up to 20 words for complex phrasing like "layman understanding")
    if has_history and len(query_lower.split()) <= 20:
        follow_up_patterns = [
            r'\b(explain|elaborate|more|further|details|break down|why|how|what else|tell me)\b',
            r'\b(yes|no|ok|show me|layman|simple|understand|meaning|context)\b',
            r'\b(who|when|where|why)\b'
        ]
        if any(re.search(pattern, query_lower) for pattern in follow_up_patterns):
            return True

    # Music-related keywords
    music_keywords = [
        'music', 'hymn', 'hymns', 'song', 'songs', 'choir', 'sing', 'singing',
        'conductor', 'organist', 'pianist', 'accompanist', 'musical',
        'sacrament', 'worship', 'primary song', 'children song',
        'ward music', 'stake music', 'music leader', 'music coordinator',
        'mark wilberg', 'wilberg', 'mack wilberg', 'tabernacle choir',
        'sacred music', 'prelude', 'postlude', 'rest hymn',
        'tempo', 'melody', 'harmony', 'chord', 'key signature',
        'voice', 'soprano', 'alto', 'tenor', 'bass',
        'sheet music', 'lyrics', 'verse', 'chorus', 'intro', 'outro',
        'solo', 'solos', 'instrument', 'instrumental', 'brass', 'woodwind',
        'strings', 'orchestra', 'performance', 'practice', 'rehearsal',
        'rhythm', 'beat', 'measure', 'bar', 'notes', 'staff',
        # Common hymn names and phrases
        'stand all amazed', 'i stand all amazed', 'come follow me', 'how great thou art',
        'amazing grace', 'come thou fount', 'nearer my god', 'abide with me',
        'spirit of god', 'called to serve', 'i am a child of god', 'families can be together',
        'high on the mountain top', 'praise to the man', 'we thank thee o god',
        'the lord is my shepherd', 'lead kindly light', 'be still my soul',
        'i know that my redeemer', 'how firm a foundation', 'count your blessings',
        'love at home', 'i believe in christ', 'o my father', 'true to the faith',
        'come come ye saints', 'come, come, ye saints', 'all is well',
        # Hymn number references
        'hymn number', 'hymn #', 'hymn no', 'what number', 'which hymn',
        # Hymn history and authorship terms
        'composed', 'composer', 'wrote', 'written', 'author', 'lyricist',
        'history of', 'origin', 'tune', 'arrangement', 'arranged',
        'requirement', 'policy', 'guideline', 'instruction'
    ]
    
    # Check if any music keyword is in the query
    has_music_keyword = any(keyword in query_lower for keyword in music_keywords)
    
    # Check for hymn number pattern
    has_hymn_number = bool(re.search(r'(hymn|hynm|#)\s*\d+|\d+\s*(hymn|hynm)', query_lower))
    
    # Check for hymn history questions
    has_hymn_history_question = bool(re.search(
        r'who\s+(composed|wrote|created|arranged|is the (composer|author|lyricist))',
        query_lower
    ))
    
    # Allow common greetings
    greetings = ['hello', 'hi ', 'hi!', 'hey', 'greetings', 'morning', 'afternoon', 'evening', 'howdy']
    is_greeting = any(greet in query_lower for greet in greetings) and len(query_lower) < 20

    # Church context check
    church_keywords = ['church', 'lds', 'latter-day saint', 'ward', 'stake', 'sacrament', 'meeting', 'handbook']
    has_church_context = any(keyword in query_lower for keyword in church_keywords)

    return (
        is_greeting or
        has_music_keyword or 
        has_hymn_number or 
        has_hymn_history_question or 
        (has_church_context and any(word in query_lower for word in ['policy', 'guideline', 'requirement', 'music', 'sing', 'hymn']))
    )


async def test_web_search():
    """Test the web search functionality"""
    searcher = ChurchMusicWebSearch()
    
    # Test queries
    test_queries = [
        "Who is Mark Wilberg?",
        "What are the qualifications for ward music coordinator?",
        "How to choose sacrament hymns?"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"Is music-related: {is_music_related_question(query)}")
        print(f"{'='*60}")
        
        results = await searcher.search(query)
        
        if results:
            print(f"\nFound {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result['title']}")
                print(f"   URL: {result['url']}")
                print(f"   Relevance: {result['relevance_score']:.2f}")
                print(f"   Preview: {result['content'][:200]}...")
        else:
            print("No results found")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_web_search())
