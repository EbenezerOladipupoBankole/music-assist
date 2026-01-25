import os
import requests
import firebase_admin
from firebase_admin import storage
import logging

logger = logging.getLogger(__name__)

class AudioCacheManager:
    """
    Manages caching of hymn audio files in Firebase Storage 
    to bypass LDS CDN restrictions (CORS/expirey).
    """
    def __init__(self, bucket_name=None):
        self.bucket_name = bucket_name or f"{os.getenv('FIREBASE_PROJECT_ID', 'music-assists')}.firebasestorage.app"
        try:
            self.bucket = storage.bucket(self.bucket_name)
            logger.info(f"✅ AudioCacheManager initialized with bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize storage bucket: {e}")
            self.bucket = None

    def get_audio_url(self, hymn_number, source_url):
        """
        Returns a permanent URL for the hymn. 
        If not in cache, downloads from source and uploads to Firebase.
        """
        if not self.bucket:
            return source_url # Fallback if storage is failing

        file_path = f"audio/hymn_{hymn_number}.mp3"
        blob = self.bucket.blob(file_path)

        # 1. Check if already exists in cache
        if blob.exists():
            # Return public URL (make public if not already)
            blob.make_public()
            return blob.public_url

        # 2. If not, download and cache
        try:
            logger.info(f"📥 Downloading hymn {hymn_number} for caching...")
            response = requests.get(source_url, timeout=10)
            if response.status_code == 200:
                blob.upload_from_string(response.content, content_type='audio/mpeg')
                blob.make_public()
                logger.info(f"✅ Cached hymn {hymn_number} to Firebase Storage")
                return blob.public_url
        except Exception as e:
            logger.error(f"❌ Cache upload failed for hymn {hymn_number}: {e}")
        
        return source_url # Final fallback
