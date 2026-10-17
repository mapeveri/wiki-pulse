"""Tests that do not require a running ClickHouse."""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "WikiPulse API"


def test_articles_rejects_invalid_sort() -> None:
    response = client.get("/metrics/articles", params={"sort": "drop table"})
    assert response.status_code == 400


def test_articles_rejects_invalid_order() -> None:
    response = client.get("/metrics/articles", params={"order": "sideways"})
    assert response.status_code == 422
