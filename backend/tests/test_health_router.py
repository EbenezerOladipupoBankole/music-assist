"""Tests for the liveness/readiness/stats endpoints."""


def test_root_is_always_healthy(client_no_rag):
    response = client_no_rag.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_health_reflects_rag_pipeline_status_when_healthy(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_health_is_unhealthy_when_rag_pipeline_unavailable(client_no_rag):
    response = client_no_rag.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "unhealthy"


def test_stats_returns_503_without_rag_pipeline(client_no_rag):
    response = client_no_rag.get("/stats")

    assert response.status_code == 503


def test_stats_returns_pipeline_statistics(client):
    response = client.get("/stats")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
