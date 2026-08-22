# Clash Config Builder

Python builder for a Mihomo/FlClash profile.

Current MVP:
- pulls the 25 upstream source URLs from `AvenCores/goida-vpn-configs`;
- parses common proxy URI formats into Mihomo proxy objects;
- deduplicates nodes;
- requires a real UDP probe through the proxy;
- benchmarks latency and throughput;
- ranks nodes by `0.30 * latency_score + 0.70 * throughput_score`;
- emits `dist/config.yaml` and `dist/benchmark.json`;
- keeps the benchmark engine separate from final routing/rule generation.

The benchmark deliberately does **not** include reliability, GeoIP, ASN diversity, or Russia filtering yet.

## Requirements

- Python 3.11+
- `mihomo` binary available on PATH, or `MIHOMO_BIN` pointing to it.
- Network access from the runner.

Install:

```bash
python -m pip install -r requirements.txt
```

Run:

```bash
python -m builder
```

Quick smoke run:

```bash
python -m builder --top-n 10 --max-candidates 100
```

## Configuration

Environment variables:

- `TOP_N` — default `50`
- `MAX_CANDIDATES` — optional cap after parsing/deduplication
- `MIHOMO_BIN` — path/name of Mihomo binary
- `BENCHMARK_URL` — default Cloudflare fixed-size download endpoint
- `BENCHMARK_BYTES` — default `1000000`
- `BENCHMARK_TIMEOUT` — default `12`
- `UDP_HOST` — default `1.1.1.1`
- `UDP_PORT` — default `53`
- `UDP_TIMEOUT` — default `3`

## Important design choice

The builder launches a temporary Mihomo instance per candidate and talks to its local SOCKS5 listener. This means the benchmark exercises the same protocol engine that will later be used by FlClash/Mihomo rather than implementing VLESS/VMess/Hysteria/etc. in Python.

The first implementation supports:
- VLESS
- VMess
- Trojan
- Shadowsocks
- Hysteria / Hysteria2 (common URI forms)

Unknown schemes are skipped and recorded in `benchmark.json`.

## Outputs

`dist/config.yaml`
- top-N selected nodes
- a `TOP` select group
- a `DIRECT` fallback

`dist/benchmark.json`
- parsed candidate metadata
- UDP result
- latency
- throughput
- score
- failure reason

