from __future__ import annotations

import base64
import json
import re
from urllib.parse import unquote

import requests

UA = "clash-config-builder/0.1"

def fetch_text(url: str, timeout: int = 20) -> str:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": UA})
    r.raise_for_status()
    return r.text

def fetch_urls() -> list[str]:
    return ["https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt", "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt", "https://raw.githack.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt", "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/1.txt"]
def decode_subscription(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    # Many mixed subscriptions are base64-encoded. Do not force-decode ordinary URI lists.
    if "://" in text:
        return text
    compact = re.sub(r"\s+", "", text)
    try:
        raw = base64.b64decode(compact + "=" * (-len(compact) % 4), validate=True)
        decoded = raw.decode("utf-8")
        if "://" in decoded:
            return decoded
    except Exception:
        pass
    return text

def iter_uris(text: str):
    text = decode_subscription(text)
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Some sources put several URIs in one whitespace-separated line.
        for item in re.findall(r"[A-Za-z][A-Za-z0-9+.-]*://\S+", line):
            yield item.rstrip(",;")