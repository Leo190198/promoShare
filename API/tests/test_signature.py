from __future__ import annotations

import hashlib

from app.services.shopee_graphql_builder import compact_json, graphql_literal
from app.services.shopee_signing import build_shopee_signature


def test_shopee_signature_header_format_and_value() -> None:
    payload_json = '{"query":"{__typename}"}'
    timestamp = 1577836800

    signature = build_shopee_signature(
        app_id="123456",
        app_secret="demo",
        payload_json=payload_json,
        timestamp=timestamp,
    )

    expected_hash = hashlib.sha256(f"123456{timestamp}{payload_json}demo".encode("utf-8")).hexdigest()
    expected_header = f"SHA256 Credential=123456, Timestamp={timestamp}, Signature={expected_hash}"

    assert signature.signature == expected_hash
    assert signature.authorization_header == expected_header


def test_shopee_signature_changes_when_payload_changes() -> None:
    sig_a = build_shopee_signature(
        app_id="123456",
        app_secret="demo",
        payload_json='{"query":"{a}"}',
        timestamp=1,
    )
    sig_b = build_shopee_signature(
        app_id="123456",
        app_secret="demo",
        payload_json='{"query":"{b}"}',
        timestamp=1,
    )
    assert sig_a.signature != sig_b.signature


def test_compact_json_and_graphql_literal_string_escaping() -> None:
    payload = {"query": '{productOfferV2(keyword:"iphone 11"){nodes{productName}}}'}
    payload_json = compact_json(payload)
    assert payload_json == '{"query":"{productOfferV2(keyword:\\"iphone 11\\"){nodes{productName}}}"}'

    literal = graphql_literal('he said "oi"')
    assert literal == '"he said \\"oi\\""'
    assert graphql_literal(True) == "true"
    assert graphql_literal([1, "x"]) == '[1,"x"]'

