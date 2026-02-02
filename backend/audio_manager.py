import os
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AudioCacheManager:
    """
    Manages caching of hymn audio files on LOCAL DISK.
    Saves space and bypasses official CDN restrictions.
    """
    def __init__(self, cache_dir: str = "./data/audio_cache"):
        self.cache_dir = cache_dir
        # Create directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"✅ Local Audio Cache initialized at: {os.path.abspath(self.cache_dir)}")

    def get_local_path(self, hymn_number: int, source_url: str) -> str:
        """
        Returns the local path to a cached hymn.
        Downloads it if it doesn't exist.
        """
        file_name = f"hymn_{hymn_number}.mp3"
        local_path = os.path.join(self.cache_dir, file_name)

        # 1. Check if we already have it
        if os.path.exists(local_path):
            return local_path

        # 2. Download it if we don't
        try:
            logger.info(f"📥 Downloading hymn {hymn_number} to local cache...")
            temp_path = f"{local_path}.tmp"
            response = requests.get(source_url, timeout=15, stream=True)
            if response.status_code == 200:
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                # Atomic rename
                os.replace(temp_path, local_path)
                logger.info(f"✅ Cached hymn {hymn_number} locally")
                return local_path
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            logger.error(f"❌ Failed to cache hymn {hymn_number}: {e}")
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        
        return None # Indicate failure so we can fallback to direct stream
