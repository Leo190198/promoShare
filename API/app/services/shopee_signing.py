from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class ShopeeSignature:
    timestamp: int
    signature: str
    authorization_header: str


def build_shopee_signature(
    *,
    app_id: str,
    app_secret: str,
    payload_json: str,
    timestamp: int | None = None,
) -> ShopeeSignature:
    ts = int(time.time()) if timestamp is None else int(timestamp)
    signature_factor = f"{app_id}{ts}{payload_json}{app_secret}"
    signature = hashlib.sha256(signature_factor.encode("utf-8")).hexdigest()
    header = f"SHA256 Credential={app_id}, Timestamp={ts}, Signature={signature}"
    return ShopeeSignature(timestamp=ts, signature=signature, authorization_header=header)

