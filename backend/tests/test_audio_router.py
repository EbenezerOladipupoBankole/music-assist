"""Tests for /audio/hymn/{number} - local cache miss, proxy fallback, error cases."""


class _FakeSourceResponse:
    """Stand-in for requests.Response used as a context manager."""

    def __init__(self, status_code=200, content=b"fake-audio-bytes"):
        self.status_code = status_code
        self._content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=1024):
        yield self._content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _HymnPlayerWithUrl:
    def get_hymns(self, query):
        return [{"title": "Test Hymn", "number": 5, "url": "https://example.com/audio.mp3"}]


def test_audio_hymn_without_source_url_returns_404(client):
    response = client.get("/audio/hymn/1")

    assert response.status_code == 404


def test_audio_hymn_not_found_returns_404(client):
    response = client.get("/audio/hymn/99999")

    assert response.status_code == 404


def test_audio_hymn_proxies_from_source_when_cache_misses(client, monkeypatch):
    import routers.audio as audio_module
    from dependencies import get_hymn_player
    from main import app

    monkeypatch.setattr(audio_module.requests, "get", lambda *a, **k: _FakeSourceResponse())
    app.dependency_overrides[get_hymn_player] = lambda: _HymnPlayerWithUrl()
    try:
        response = client.get("/audio/hymn/5")
    finally:
        app.dependency_overrides.pop(get_hymn_player, None)

    assert response.status_code == 200
    assert response.content == b"fake-audio-bytes"


def test_audio_hymn_proxy_failure_ends_stream_without_500(client, monkeypatch):
    import routers.audio as audio_module
    from dependencies import get_hymn_player
    from main import app

    def _raise(*args, **kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(audio_module.requests, "get", _raise)
    app.dependency_overrides[get_hymn_player] = lambda: _HymnPlayerWithUrl()
    try:
        response = client.get("/audio/hymn/5")
    finally:
        app.dependency_overrides.pop(get_hymn_player, None)

    # Headers are already committed to a streaming 200 by the time the fetch
    # fails, so the stream just ends empty rather than surfacing a 500.
    assert response.status_code == 200
    assert response.content == b""
