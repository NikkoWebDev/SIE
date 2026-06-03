"""
VYNTRA AI Cache — TTL-based cache for repeated AI queries.

Reduces API cost and latency by caching deterministic tool results.
"""

import json
import logging
import threading
import time
from typing import Any

logger = logging.getLogger("siee.cache")


class TTLCache:
    """Simple thread-safe TTL cache with max size."""

    def __init__(self, maxsize: int = 256, ttl: int = 60):
        self._maxsize = maxsize
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def _make_key(self, tool_name: str, user_id: str, args: dict) -> str:
        return f"{tool_name}:{user_id}:{json.dumps(args, sort_keys=True)}"

    def get(self, tool_name: str, user_id: str, args: dict) -> Any | None:
        key = self._make_key(tool_name, user_id, args)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ts, value = entry
            if time.time() - ts > self._ttl:
                del self._store[key]
                return None
            return value

    def set(self, tool_name: str, user_id: str, args: dict, value: Any) -> None:
        key = self._make_key(tool_name, user_id, args)
        with self._lock:
            if len(self._store) >= self._maxsize:
                oldest = min(self._store.keys(), key=lambda k: self._store[k][0])
                del self._store[oldest]
            self._store[key] = (time.time(), value)

    def invalidate(self, tool_name: str | None = None, user_id: str | None = None) -> None:
        with self._lock:
            if tool_name is None and user_id is None:
                self._store.clear()
                return
            to_remove = []
            for key in self._store:
                parts = key.split(":")
                if tool_name and parts[0] != tool_name:
                    continue
                if user_id and parts[1] != user_id:
                    continue
                to_remove.append(key)
            for key in to_remove:
                del self._store[key]

    @property
    def size(self) -> int:
        return len(self._store)


tool_cache = TTLCache(maxsize=256, ttl=60)

# Tools whose results don't vary per-user and can be cached globally
CACHEABLE_TOOLS = {"get_risk_students", "get_admin_stats", "get_subject_info", "get_teacher_grade_count"}
