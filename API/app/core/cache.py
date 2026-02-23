from __future__ import annotations

import copy
import json
import threading
from typing import Any

from cachetools import TTLCache

from app.core.config import get_settings


def _normalized_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


class _TTLStore:
    def __init__(self, maxsize: int, ttl_seconds: int) -> None:
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=maxsize, ttl=ttl_seconds)
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._cache:
                return None
            return copy.deepcopy(self._cache[key])

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = copy.deepcopy(value)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class CacheManager:
    def __init__(self) -> None:
        settings = get_settings()
        self.enabled = settings.cache_enabled
        self.product_offers = _TTLStore(
            maxsize=settings.cache_maxsize,
            ttl_seconds=settings.cache_product_offers_ttl_seconds,
        )
        self.shop_offers = _TTLStore(
            maxsize=settings.cache_maxsize,
            ttl_seconds=settings.cache_shop_offers_ttl_seconds,
        )

    def build_key(self, operation: str, request_payload: dict[str, Any], selection_set_version: str) -> str:
        normalized = _normalized_json(request_payload)
        return f"{operation}:{selection_set_version}:{normalized}"

    def get(self, cache_name: str, key: str) -> Any | None:
        if not self.enabled:
            return None
        store = getattr(self, cache_name)
        return store.get(key)

    def set(self, cache_name: str, key: str, value: Any) -> None:
        if not self.enabled:
            return
        store = getattr(self, cache_name)
        store.set(key, value)

    def clear_all(self) -> None:
        self.product_offers.clear()
        self.shop_offers.clear()


_cache_manager: CacheManager | None = None
_cache_lock = threading.Lock()


def get_cache_manager() -> CacheManager:
    global _cache_manager
    if _cache_manager is None:
        with _cache_lock:
            if _cache_manager is None:
                _cache_manager = CacheManager()
    return _cache_manager


def reset_cache_manager() -> None:
    global _cache_manager
    with _cache_lock:
        _cache_manager = None

