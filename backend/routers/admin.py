"""Admin-protected endpoints: crawl trigger and memory diagnostics.

Both require ADMIN_KEY to be set and match the caller-supplied key, compared
with secrets.compare_digest to avoid a timing side-channel on the comparison.
"""
import secrets
from datetime import datetime, timezone
from typing import Optional

import firebase_admin
from fastapi import APIRouter, Depends, HTTPException

from config import settings
from dependencies import get_rag_pipeline, get_rag_pipeline_optional
from rag_pipeline import RAGPipeline

router = APIRouter(tags=["admin"])


def _require_admin_key(admin_key: Optional[str]) -> None:
    expected = settings.admin_key
    if not expected or not admin_key or not secrets.compare_digest(admin_key, expected):
        raise HTTPException(status_code=403, detail="Unauthorized")


@router.get("/debug/memory")
async def debug_memory(
    admin_key: Optional[str] = None,
    rag_pipeline: Optional[RAGPipeline] = Depends(get_rag_pipeline_optional),
):
    """Diagnostic for conversation memory status"""
    _require_admin_key(admin_key)
    return {
        "firebase_apps": [app.name for app in firebase_admin._apps] if firebase_admin._apps else [],
        "has_rag_pipeline": rag_pipeline is not None,
        "has_memory": rag_pipeline.memory is not None if rag_pipeline else False,
        "is_using_firestore": (
            getattr(rag_pipeline.memory, "db", None) is not None
        ) if (rag_pipeline and rag_pipeline.memory) else False,
    }


@router.post("/crawl/trigger")
async def trigger_crawl(
    admin_key: str,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
):
    """
    Trigger web crawler to update document corpus.
    Protected endpoint - requires admin key.
    """
    _require_admin_key(admin_key)

    try:
        from crawler import ChurchMusicCrawler

        crawler = ChurchMusicCrawler(
            output_dir="./data/crawled",
            rate_limit_delay=2.0,
        )

        urls = [
            # Hymns and Music Library
            "https://www.churchofjesuschrist.org/media/music?lang=eng",
            "https://www.churchofjesuschrist.org/music/library/hymns?lang=eng",
            "https://www.churchofjesuschrist.org/initiative/new-hymns?lang=eng",
            "https://www.churchofjesuschrist.org/media/music/archived-content?lang=eng",

            # Music Guidelines and Handbooks
            "https://www.churchofjesuschrist.org/callings/music/common-questions-about-music-in-church-meetings?lang=eng",
            "https://www.churchofjesuschrist.org/study/handbooks-and-callings/ward-or-branch-callings/music?lang=eng",
            "https://www.churchofjesuschrist.org/study/manual/general-handbook/19-music?lang=eng",
            "https://www.churchofjesuschrist.org/study/manual/general-handbook/38-church-policies-and-guidelines?lang=eng",

            # Tabernacle Choir (Mack Wilberg and other conductors)
            "https://www.churchofjesuschrist.org/media/music/tabernacle-choir?lang=eng",
            "https://www.thetabernaclechoir.org/about.html",
            "https://www.thetabernaclechoir.org/about/conductors.html",
            "https://www.churchofjesuschrist.org/study/ensign/topics/tabernacle-choir-at-temple-square?lang=eng",
            "https://www.churchofjesuschrist.org/study/friend/topics/tabernacle-choir?lang=eng",

            # Music Theory and Education
            "https://www.churchofjesuschrist.org/study/music?lang=eng",
            "https://www.churchofjesuschrist.org/study/manual/conducting-course?lang=eng",
            "https://www.churchofjesuschrist.org/music/resources?lang=eng",

            # Children's Songbook
            "https://www.churchofjesuschrist.org/music/text/childrens-songbook?lang=eng",
            "https://www.churchofjesuschrist.org/children/resources/music?lang=eng",

            # Articles and Ensign Topics
            "https://www.churchofjesuschrist.org/study/ensign/topics/music?lang=eng",
            "https://www.churchofjesuschrist.org/study/ensign/topics/hymns?lang=eng",
            "https://www.churchofjesuschrist.org/study/ensign/topics/choirs?lang=eng",
            "https://www.churchofjesuschrist.org/study/liahona/topics/music?lang=eng",

            # Music Callings and Service
            "https://www.churchofjesuschrist.org/callings/music?lang=eng",
            "https://www.churchofjesuschrist.org/study/manual/music-callings?lang=eng",

            # Composer and Arranger Resources
            "https://www.churchofjesuschrist.org/study/ensign/topics/composers?lang=eng",
            "https://www.churchofjesuschrist.org/music/library/composers?lang=eng",
        ]

        results = await crawler.crawl_sites(urls)

        # Rebuild vector store with new data
        await rag_pipeline.rebuild_vector_store()

        return {
            "status": "success",
            "documents_crawled": results["total_documents"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crawl failed: {str(e)}")
