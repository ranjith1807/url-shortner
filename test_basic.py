"""
Comprehensive test suite for the URL Shortener API.

Run with: pytest -q
"""

from __future__ import annotations

import concurrent.futures
import time
from http import HTTPStatus
from typing import List

import pytest

from app.main import app
from app.utils import SHORT_CODE_LENGTH, ALPHANUMERIC


@pytest.fixture()
def client():
    """
    Provide a Flask test client with app context.
    """
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# -------------------------
# Health Checks
# -------------------------

def test_root_health_check(client):
    resp = client.get("/")
    assert resp.status_code == HTTPStatus.OK
    data = resp.get_json()
    assert data == {"status": "healthy", "service": "URL Shortener API"}


# -------------------------
# URL Shortening
# -------------------------

def test_shorten_success(client):
    resp = client.post("/api/shorten", json={"url": "https://example.com"})
    assert resp.status_code == HTTPStatus.CREATED
    data = resp.get_json()
    assert "short_code" in data
    assert len(data["short_code"]) == SHORT_CODE_LENGTH
    assert all(ch in ALPHANUMERIC for ch in data["short_code"])
    assert data["short_url"].endswith(data["short_code"])


def test_shorten_invalid_url(client):
    resp = client.post("/api/shorten", json={"url": "notaurl"})
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.get_json()["error"] == "Invalid URL."


def test_shorten_missing_url_field(client):
    resp = client.post("/api/shorten", json={})
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.get_json()["error"].startswith("Missing")


# -------------------------
# Redirection
# -------------------------

def test_redirect_and_click_tracking(client):
    # Shorten first
    post_resp = client.post("/api/shorten", json={"url": "https://example.com/a"})
    short_code = post_resp.get_json()["short_code"]

    # Click twice
    for _ in range(2):
        redir = client.get(f"/{short_code}", follow_redirects=False)
        assert redir.status_code == HTTPStatus.FOUND
        assert redir.headers["Location"] == "https://example.com/a"

    # Stats should show 2 clicks
    stats = client.get(f"/api/stats/{short_code}")
    assert stats.status_code == HTTPStatus.OK
    data = stats.get_json()
    assert data["clicks"] == 2
    assert data["url"] == "https://example.com/a"
    assert data["created_at"]  # timestamp present


def test_redirect_nonexistent(client):
    resp = client.get("/abcdef", follow_redirects=False)
    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert resp.get_json()["error"].startswith("Short code")


# -------------------------
# Concurrency
# -------------------------

def test_concurrent_shortening(client):
    """
    Fire 50 concurrent shorten requests and assert unique codes.
    """

    urls: List[str] = [f"https://example.com/{i}" for i in range(50)]

    def shorten(u):
        r = client.post("/api/shorten", json={"url": u})
        assert r.status_code == HTTPStatus.CREATED
        return r.get_json()["short_code"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        codes = list(pool.map(shorten, urls))

    # All codes should be unique
    assert len(set(codes)) == len(urls)


def test_concurrent_clicks(client):
    """
    Ensure click count increments correctly under parallel access.
    """
    post_resp = client.post("/api/shorten", json={"url": "https://parallel.com"})
    short_code = post_resp.get_json()["short_code"]

    def click():
        r = client.get(f"/{short_code}", follow_redirects=False)
        assert r.status_code == HTTPStatus.FOUND

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        list(pool.map(lambda _: click(), range(100)))

    stats = client.get(f"/api/stats/{short_code}").get_json()
    assert stats["clicks"] == 100
