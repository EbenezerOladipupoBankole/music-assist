import asyncio
import os
import sys

from dotenv import load_dotenv

from crawler import ChurchMusicCrawler
from rag_pipeline import RAGPipeline

# Load environment variables
load_dotenv()

# Windows' default console/redirect encoding (cp1252) can't encode this
# script's emoji output, which crashes print() outright. UTF-8 output
# encoding is available on stdout/stderr since Python 3.7.
if sys.stdout.encoding is not None and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

async def main():
    print("🚀 Starting Database Population Script")
    
    # 1. Run the Crawler
    print("\n--- Phase 1: Crawling Websites ---")
    crawler = ChurchMusicCrawler(
        output_dir="./data/crawled",
        rate_limit_delay=1.0  # Slightly faster for manual script
    )
    
    urls = [
        "https://www.churchofjesuschrist.org/media/music?lang=eng",
        "https://www.churchofjesuschrist.org/initiative/new-hymns?lang=eng",
        "https://www.churchofjesuschrist.org/callings/music/common-questions-about-music-in-church-meetings?lang=eng",
        "https://www.churchofjesuschrist.org/study/handbooks-and-callings/ward-or-branch-callings/music?lang=eng"
    ]
    
    await crawler.crawl_sites(urls)
    
    # 2. Rebuild the Vector Store
    print("\n--- Phase 2: Building Vector Index ---")
    
    # Check for API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables.")
        return

    rag = RAGPipeline(
        vector_db_path=os.getenv("VECTOR_DB_PATH", "./data/vector_store"),
        model_name=os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    )
    
    # Initialize (loads existing or creates placeholder)
    await rag.initialize()
    
    try:
        # Ingest the crawled data
        await rag.rebuild_vector_store()
        print("\n✅ Database population complete!")
        print(f"   Generated index file at: {os.path.abspath(os.path.join(rag.vector_db_path, 'index.faiss'))}")
    except Exception as e:
        print("\n❌ PHASE 2 FAILED: Could not build vector database.")
        print(f"Error details: {e}")
        print("The chatbot will not work until this is fixed.")

if __name__ == "__main__":
    asyncio.run(main())