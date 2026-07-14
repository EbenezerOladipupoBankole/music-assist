"""Hymn audio retrieval - local cache first, direct-source proxy as fallback."""
import asyncio
import logging
import os

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from audio_manager import AudioCacheManager
from dependencies import get_audio_cache, get_hymn_player
from hymn_player import HymnPlayer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["audio"])


@router.get("/audio/hymn/{number}")
async def get_hymn_audio(
    number: int,
    hymn_player: HymnPlayer = Depends(get_hymn_player),
    audio_cache: AudioCacheManager = Depends(get_audio_cache),
):
    """
    Retrieves hymn audio from LOCAL CACHE.
    Downloads once, serves many times. Faster and reliable.
    """
    if not (hymn_player and audio_cache):
        raise HTTPException(status_code=503, detail="Audio system not ready")

    hymns = hymn_player.get_hymns(str(number))
    if not hymns:
        raise HTTPException(status_code=404, detail="Hymn not found")

    h = hymns[0]
    source_url = h["url"]

    if source_url is None:
        # This hymn has no known audio source (Church platform migration) - nothing to
        # cache or proxy, so fail fast with a clear error instead of attempting a
        # request against a None URL.
        raise HTTPException(
            status_code=404,
            detail="Audio for this hymn is not currently available. Use the Gospel Library app or ChurchofJesusChrist.org/music.",
        )

    # 1. Try to get from local disk
    try:
        local_path = await asyncio.to_thread(audio_cache.get_local_path, h["number"], source_url)
        if local_path and os.path.exists(local_path):
            logger.info(f"🔊 Serving Hymn {number} from Local Disk")
            return FileResponse(local_path, media_type="audio/mpeg")
    except Exception as e:
        logger.warning(f"Local cache failed for hymn {number}: {e}")

    # 2. Extreme fallback: proxy direct from source if disk fails.
    # Note: once StreamingResponse starts, headers are already sent, so a failure
    # inside iterfile() can only be logged and end the stream early - it can't be
    # turned into an HTTPException at that point.
    def iterfile():
        try:
            with requests.get(source_url, stream=True, timeout=15) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    yield chunk
        except Exception as e:
            logger.error(f"Audio proxy stream failed for hymn {number}: {e}")

    logger.info(f"🔄 Proxying Hymn {number} from official source (Disk Fallback)")
    return StreamingResponse(iterfile(), media_type="audio/mpeg")
