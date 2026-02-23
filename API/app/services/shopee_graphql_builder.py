from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from app.constants.graphql_queries import (
    PRODUCT_OFFER_V2_SELECTION_SET,
    SHOP_OFFER_V2_SELECTION_SET,
    SHORT_LINK_SELECTION_SET,
)


def compact_json(payload: dict[str, Any], *, sort_keys: bool = False) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False, sort_keys=sort_keys)


def graphql_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("Invalid float value for GraphQL literal")
        return format(value, "g")
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(graphql_literal(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(f"{key}:{graphql_literal(val)}" for key, val in value.items()) + "}"
    raise TypeError(f"Unsupported GraphQL literal type: {type(value)!r}")


def _omit_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _args_literal(values: dict[str, Any]) -> str:
    normalized = _omit_none(values)
    if not normalized:
        return ""
    return "(" + ",".join(f"{key}:{graphql_literal(value)}" for key, value in normalized.items()) + ")"


def _compact_graphql(document: str) -> str:
    # Keep inner string contents untouched; only remove indentation/newlines we add in templates.
    return document.strip().replace("\n", " ").replace("\r", "").replace("\t", " ")


def build_generate_short_link_mutation(*, origin_url: str, sub_ids: list[str] | None) -> str:
    input_payload: dict[str, Any] = {"originUrl": origin_url}
    if sub_ids is not None:
        input_payload["subIds"] = sub_ids

    query = f"""
    mutation {{
      generateShortLink(input:{graphql_literal(input_payload)}) {{
        {SHORT_LINK_SELECTION_SET}
      }}
    }}
    """
    return _compact_graphql(query)


def build_product_offer_v2_query(filters: dict[str, Any]) -> str:
    args = _args_literal(filters)
    query = f"""
    {{
      productOfferV2{args} {{
        {PRODUCT_OFFER_V2_SELECTION_SET}
      }}
    }}
    """
    return _compact_graphql(query)


def build_shop_offer_v2_query(filters: dict[str, Any]) -> str:
    args = _args_literal(filters)
    query = f"""
    {{
      shopOfferV2{args} {{
        {SHOP_OFFER_V2_SELECTION_SET}
      }}
    }}
    """
    return _compact_graphql(query)
