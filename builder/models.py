from dataclasses import dataclass, field
from typing import Any

@dataclass
class Node:
    name: str
    scheme: str
    raw_uri: str
    mihomo: dict[str, Any]
    server: str = ""
    port: int = 0
    source: str = ""
    fingerprint: str = ""

@dataclass
class Result:
    node: Node
    udp_ok: bool = False
    latency_ms: float | None = None
    throughput_mbps: float | None = None
    score: float | None = None
    error: str | None = None
    stages: dict[str, Any] = field(default_factory=dict)
