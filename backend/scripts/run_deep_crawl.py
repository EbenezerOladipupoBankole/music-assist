import asyncio

from crawler import ChurchMusicCrawler


async def run_deep_crawl():
    # Deeper crawl settings for better knowledge coverage
    crawler = ChurchMusicCrawler(
        output_dir="./data/crawled",
        rate_limit_delay=1.0, # Slightly faster but still safe
        max_depth=3,          # Go deeper
        max_pages=200         # Collect more pages
    )
    
    # Target specific high-value URL sets
    urls = [
        # Main music portals
        "https://www.churchofjesuschrist.org/media/music?lang=eng",
        # Music Guidelines/Handbook sections
        "https://www.churchofjesuschrist.org/study/manual/general-handbook/19-music?lang=eng",
        "https://www.churchofjesuschrist.org/callings/music/common-questions-about-music-in-church-meetings?lang=eng",
        # Hymn history/info sections
        "https://www.churchofjesuschrist.org/music/library/hymns?lang=eng",
        # Conducting resources
        "https://www.churchofjesuschrist.org/study/manual/hymns/conducting-course?lang=eng",
        # Tabernacle Choir context
        "https://www.thetabernaclechoir.org/about.html"
    ]
    
    print("\n🚀 Starting DEEP CRAWL to populate expanded knowledge base...")
    await crawler.crawl_sites(urls)
    print("\n✅ Deep crawl complete.")

if __name__ == "__main__":
    asyncio.run(run_deep_crawl())
