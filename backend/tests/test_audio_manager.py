"""Unit tests for AudioCacheManager.get_local_path (local-disk hymn cache)."""
import pytest

from audio_manager import AudioCacheManager


class FakeResponse:
    def __init__(self, status_code: int, chunks=(b"audio-bytes",)):
        self.status_code = status_code
        self._chunks = chunks

    def iter_content(self, chunk_size):
        yield from self._chunks


@pytest.fixture
def cache(tmp_path):
    return AudioCacheManager(cache_dir=str(tmp_path))


def test_returns_existing_file_without_downloading(cache, tmp_path, monkeypatch):
    cached_file = tmp_path / "hymn_2.mp3"
    cached_file.write_bytes(b"already cached")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("should not re-download an already-cached file")

    monkeypatch.setattr("audio_manager.requests.get", fail_if_called)

    result = cache.get_local_path(2, "https://example.com/hymn2.mp3")

    assert result == str(cached_file)


def test_downloads_and_caches_on_first_request(cache, tmp_path, monkeypatch):
    monkeypatch.setattr("audio_manager.requests.get", lambda *a, **kw: FakeResponse(200))

    result = cache.get_local_path(2, "https://example.com/hymn2.mp3")

    assert result == str(tmp_path / "hymn_2.mp3")
    assert (tmp_path / "hymn_2.mp3").read_bytes() == b"audio-bytes"
    # Atomic rename should leave no leftover temp file behind.
    assert not (tmp_path / "hymn_2.mp3.tmp").exists()


def test_returns_none_when_source_returns_non_200(cache, tmp_path, monkeypatch):
    monkeypatch.setattr("audio_manager.requests.get", lambda *a, **kw: FakeResponse(404))

    result = cache.get_local_path(2, "https://example.com/missing.mp3")

    assert result is None
    assert not (tmp_path / "hymn_2.mp3").exists()
    assert not (tmp_path / "hymn_2.mp3.tmp").exists()


def test_returns_none_when_download_raises(cache, tmp_path, monkeypatch):
    def raise_error(*args, **kwargs):
        raise ConnectionError("network down")

    monkeypatch.setattr("audio_manager.requests.get", raise_error)

    result = cache.get_local_path(2, "https://example.com/hymn2.mp3")

    assert result is None
    assert not (tmp_path / "hymn_2.mp3.tmp").exists()
