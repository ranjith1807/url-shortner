"""
Thread-safe in-memory storage and domain logic for URL mappings.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

from app.utils import generate_short_code


@dataclass(slots=True, frozen=True)
class UrlRecord:
    """
    Immutable record representing a shortened URL.
    """
    original_url: str
    created_at: float
    clicks: int = 0


class UrlRepository:
    """
    An in-memory, concurrency-safe repository that stores mappings of
    short codes to UrlRecord objects.
    """

    def __init__(self) -> None:
        self._records: Dict[str, UrlRecord] = {}
        self._lock: threading.RLock = threading.RLock()

    # ---------------------------------
    # CRUD-like operations
    # ---------------------------------

    def create(self, original_url: str) -> str:
        """
        Generate a unique short code and store the mapping.

        Parameters
        ----------
        original_url : str
            The long URL to shorten.

        Returns
        -------
        str
            The newly created short code.
        """
        with self._lock:
            short_code = generate_short_code()
            # Ensure uniqueness (statistically rare collision, but we guard anyway).
            while short_code in self._records:
                short_code = generate_short_code()

            self._records[short_code] = UrlRecord(
                original_url=original_url,
                created_at=time.time(),
                clicks=0,
            )
            return short_code

    def increment_clicks(self, short_code: str) -> None:
        """
        Atomically increment click count for a short code.

        Raises
        ------
        KeyError
            If the short code does not exist.
        """
        with self._lock:
            record = self._records[short_code]
            # Because UrlRecord is frozen, create a new one with updated clicks
            self._records[short_code] = UrlRecord(
                original_url=record.original_url,
                created_at=record.created_at,
                clicks=record.clicks + 1,
            )

    def get(self, short_code: str) -> UrlRecord:
        """
        Retrieve a UrlRecord.

        Raises
        ------
        KeyError
            If the short code does not exist.
        """
        with self._lock:
            return self._records[short_code]

    def exists(self, short_code: str) -> bool:
        """
        Check whether a short code exists.
        """
        with self._lock:
            return short_code in self._records
