from __future__ import annotations

from app.core.cache import get_cache_manager


def test_cache_key_deterministic_and_returns_deep_copy() -> None:
    cache = get_cache_manager()

    request_a = {"limit": 10, "keyword": "abc"}
    request_b = {"keyword": "abc", "limit": 10}
    key_a = cache.build_key("productOfferV2", request_a, "v1")
    key_b = cache.build_key("productOfferV2", request_b, "v1")
    assert key_a == key_b

    cache.set("product_offers", key_a, {"nodes": [{"itemId": 1}], "pageInfo": {"limit": 10}})
    cached_1 = cache.get("product_offers", key_a)
    assert cached_1 is not None
    cached_1["nodes"].append({"itemId": 2})

    cached_2 = cache.get("product_offers", key_a)
    assert cached_2 == {"nodes": [{"itemId": 1}], "pageInfo": {"limit": 10}}

