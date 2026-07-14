"""
Tests for the admin-protected endpoints (/debug/memory, /crawl/trigger).

`settings` is a single shared instance (backend/config.py), so monkeypatching
its `admin_key` attribute here also affects what routers/admin.py sees.
"""
from config import settings


def test_debug_memory_rejects_missing_key(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_key", "correct-key")

    response = client.get("/debug/memory")

    assert response.status_code == 403


def test_debug_memory_rejects_wrong_key(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_key", "correct-key")

    response = client.get("/debug/memory", params={"admin_key": "wrong-key"})

    assert response.status_code == 403


def test_debug_memory_accepts_correct_key(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_key", "correct-key")

    response = client.get("/debug/memory", params={"admin_key": "correct-key"})

    assert response.status_code == 200
    assert response.json()["has_rag_pipeline"] is True


def test_debug_memory_rejects_everything_when_admin_key_unconfigured(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_key", None)

    response = client.get("/debug/memory", params={"admin_key": "anything"})

    assert response.status_code == 403


def test_crawl_trigger_rejects_wrong_key(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_key", "correct-key")

    response = client.post("/crawl/trigger", params={"admin_key": "wrong-key"})

    assert response.status_code == 403


def test_crawl_trigger_requires_admin_key_query_param(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_key", "correct-key")

    response = client.post("/crawl/trigger")

    assert response.status_code == 422  # missing required query param
