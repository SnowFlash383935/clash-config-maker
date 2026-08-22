from __future__ import annotations

import socket
import time

import requests
import socks

from .mihomo import MihomoInstance
from .models import Node, Result

def _socks_session(port: int):
    s = requests.Session()
    s.proxies.update({
        "http": f"socks5h://127.0.0.1:{port}",
        "https": f"socks5h://127.0.0.1:{port}",
    })
    return s

def udp_probe(port: int, host: str, udp_port: int, timeout: float) -> bool:
    # SOCKS5 UDP ASSOCIATE. We send a minimal DNS query to 1.1.1.1:53.
    # A valid DNS response proves that UDP relay works through the proxy.
    s = socks.socksocket(socket.AF_INET, socket.SOCK_DGRAM)
    s.set_proxy(socks.SOCKS5, "127.0.0.1", port, rdns=True)
    s.settimeout(timeout)
    tid = int(time.time() * 1000) & 0xFFFF
    query = (
        tid.to_bytes(2, "big") +
        b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00" +
        b"\x03www\x07example\x03com\x00" +
        b"\x00\x01\x00\x01"
    )
    try:
        s.sendto(query, (host, udp_port))
        data, _ = s.recvfrom(4096)
        return len(data) >= 12 and data[:2] == tid.to_bytes(2, "big")
    finally:
        s.close()

def latency_probe(session, url: str, timeout: float) -> float:
    t0 = time.perf_counter()
    r = session.get(url, timeout=timeout, stream=True)
    r.close()
    return (time.perf_counter() - t0) * 1000

def throughput_probe(session, url: str, timeout: float) -> float:
    t0 = time.perf_counter()
    total = 0
    with session.get(url, timeout=timeout, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=64 * 1024):
            if chunk:
                total += len(chunk)
    elapsed = max(time.perf_counter() - t0, 1e-6)
    return (total * 8) / elapsed / 1_000_000

def benchmark(node: Node, *,
              mihomo_bin="mihomo",
              startup_timeout=8,
              benchmark_url="https://speed.cloudflare.com/__down?bytes=1000000",
              timeout=12,
              udp_host="1.1.1.1",
              udp_port=53,
              udp_timeout=3) -> Result:
    result = Result(node)
    try:
        with MihomoInstance(mihomo_bin, startup_timeout) as instance:
            instance.start(node.mihomo)

            if not udp_probe(instance.port, udp_host, udp_port, udp_timeout):
                result.error = "udp_probe_failed"
                return result
            result.udp_ok = True

            session = _socks_session(instance.port)
            result.latency_ms = latency_probe(session, benchmark_url, timeout)
            result.throughput_mbps = throughput_probe(session, benchmark_url, timeout)
            return result
    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
        return result

def score_results(results: list[Result], latency_weight=0.30, throughput_weight=0.70):
    valid = [r for r in results if r.udp_ok and r.latency_ms and r.throughput_mbps]
    if not valid:
        return
    latitudes = [r.latency_ms for r in valid]
    speeds = [r.throughput_mbps for r in valid]
    lo_lat, hi_lat = min(latitudes), max(latitudes)
    lo_spd, hi_spd = min(speeds), max(speeds)

    def norm(v, lo, hi):
        return 1.0 if hi == lo else (v - lo) / (hi - lo)

    for r in valid:
        lat_score = 1.0 - norm(r.latency_ms, lo_lat, hi_lat)
        speed_score = norm(r.throughput_mbps, lo_spd, hi_spd)
        r.score = latency_weight * lat_score + throughput_weight * speed_score
