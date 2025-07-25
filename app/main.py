"""
Flask entry point defining all API routes.
"""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Dict, Final

from flask import Flask, jsonify, redirect, request

from app.models import UrlRepository
from app.utils import is_valid_url

# ------------------------------------------------
# Application Setup
# ------------------------------------------------

app: Final[Flask] = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("url-shortener")

# Global, singleton repository.
repo: Final[UrlRepository] = UrlRepository()


# ------------------------------------------------
# Health Check Endpoints
# ------------------------------------------------

@app.get("/")
def root() -> Dict[str, str]:
    """
    Simple health check.
    """
    return {"status": "healthy", "service": "URL Shortener API"}, HTTPStatus.OK


@app.get("/api/health")
def api_health() -> Dict[str, str]:
    """
    Another health check for automated monitoring.
    """
    return {"status": "healthy"}, HTTPStatus.OK


# ------------------------------------------------
# Core Endpoints
# ------------------------------------------------

@app.post("/api/shorten")
def shorten_url():
    """
    Accept JSON {"url": "<long_url>"} and return a shortened code & URL.
    """
    payload = request.get_json(silent=True) or {}
    long_url: str | None = payload.get("url") if isinstance(payload, dict) else None

    if not long_url:
        logger.warning("Missing URL in request.")
        return (
            jsonify({"error": "Missing 'url' in request body."}),
            HTTPStatus.BAD_REQUEST,
        )

    if not is_valid_url(long_url):
        logger.warning("Invalid URL: %s", long_url)
        return jsonify({"error": "Invalid URL."}), HTTPStatus.BAD_REQUEST

    short_code = repo.create(long_url)
    logger.info("Shortened %s -> %s", long_url, short_code)

    return (
        jsonify(
            {
                "short_code": short_code,
                "short_url": request.host_url.rstrip("/") + f"/{short_code}",
            }
        ),
        HTTPStatus.CREATED,
    )


@app.get("/<string:short_code>")
def redirect_short_code(short_code: str):
    """
    Redirect to the original URL or return 404.
    """
    if not repo.exists(short_code):
        logger.info("Short code %s not found.", short_code)
        return jsonify({"error": "Short code not found."}), HTTPStatus.NOT_FOUND

    record = repo.get(short_code)
    repo.increment_clicks(short_code)
    logger.info("Redirecting %s (click #%s)", short_code, record.clicks + 1)
    return redirect(record.original_url, code=HTTPStatus.FOUND)


@app.get("/api/stats/<string:short_code>")
def stats(short_code: str):
    """
    Return analytics for a short code.
    """
    if not repo.exists(short_code):
        logger.info("Stats request: short code %s not found.", short_code)
        return jsonify({"error": "Short code not found."}), HTTPStatus.NOT_FOUND

    record = repo.get(short_code)
    return (
        jsonify(
            {
                "url": record.original_url,
                "clicks": record.clicks,
                "created_at": record.created_at,
            }
        ),
        HTTPStatus.OK,
    )
