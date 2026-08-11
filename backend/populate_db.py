"""
populate_db.py — Offline script to crawl LDS music websites and build
the FAISS vector index used by the RAG pipeline at runtime.

Run from the backend/ directory:
    python populate_db.py
"""
import asyncio
import os
import sys

import structlog
from dotenv import load_dotenv

from crawler import ChurchMusicCrawler
from logging_config import setup_logging
from rag_pipeline import RAGPipeline

# Ensure UTF-8 output encoding on Windows (default cp1252 can't encode emojis)
if sys.stdout.encoding is not None and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()
setup_logging()

logger = structlog.get_logger(__name__)


async def main():
    logger.info("starting_database_population")

    # Phase 1: Crawl
    logger.info("phase_1_crawling_websites")
    crawler = ChurchMusicCrawler(
        output_dir="./data/crawled",
        rate_limit_delay=1.0
    )

    urls = [
        "https://www.churchofjesuschrist.org/media/music?lang=eng",
        "https://www.churchofjesuschrist.org/initiative/new-hymns?lang=eng",
        "https://www.churchofjesuschrist.org/callings/music/common-questions-about-music-in-church-meetings?lang=eng",
        "https://www.churchofjesuschrist.org/study/handbooks-and-callings/ward-or-branch-callings/music?lang=eng"
    ]

    await crawler.crawl_sites(urls)

    # Phase 2: Build vector index
    logger.info("phase_2_building_vector_index")

    if not os.getenv("OPENAI_API_KEY"):
        logger.error("error_openai_api_key_not_found")
        return

    rag = RAGPipeline(
        vector_db_path=os.getenv("VECTOR_DB_PATH", "./data/vector_store"),
        model_name=os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    )

    await rag.initialize()

    try:
        await rag.rebuild_vector_store()
        logger.info(
            "database_population_complete",
            collection=rag.collection_name
        )
    except Exception as e:
        logger.error("phase_2_failed", error=str(e), exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())