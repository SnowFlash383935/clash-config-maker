from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .benchmark import benchmark, score_results
from .fetch import fetch_goida_urls, fetch_text, iter_uris
from .generate import write_config
from .parsers import parse_uri

DEFAULT_INDEX = "https://raw.githubusercontent.com/AvenCores/goida-vpn-configs/main/source/config/urls.json"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=int(os.getenv("TOP_N", "50")))
    ap.add_argument("--max-candidates", type=int, default=int(os.getenv("MAX_CANDIDATES", "0")))
    ap.add_argument("--mihomo", default=os.getenv("MIHOMO_BIN", "./mihomo"))
    ap.add_argument("--index-url", default=DEFAULT_INDEX)
    ap.add_argument("--benchmark-url", default=os.getenv(
        "BENCHMARK_URL",
        "https://speed.cloudflare.com/__down?bytes=1000000",
    ))
    ap.add_argument("--benchmark-bytes", type=int, default=int(os.getenv("BENCHMARK_BYTES", "1000000")))
    args = ap.parse_args()

    benchmark_url = f"https://speed.cloudflare.com/__down?bytes={args.benchmark_bytes}"

    print("Fetching source index...")
    all_urls = fetch_goida_urls(args.index_url)
    wanted = {1, 6, 22, 23, 24, 25}
    urls = [
        url
        for i, url in enumerate(all_urls, 1)
        if i in wanted
    ]
    print(f"Found {len(urls)} source URLs")

    nodes = []
    seen = set()
    parse_index = 0

    for source_no, url in enumerate(urls, 1):
        try:
            text = fetch_text(url)
        except Exception as exc:
            print(f"[source {source_no}] fetch failed: {exc}")
            continue
        for uri in iter_uris(text):
            parse_index += 1
            try:
                node = parse_uri(uri, parse_index)
            except Exception:
                node = None
            if node is None:
                continue
            key = node.fingerprint or f"{node.scheme}|{node.server}|{node.port}|{node.mihomo.get('uuid','')}|{node.mihomo.get('password','')}"
            if key in seen:
                continue
            seen.add(key)
            node.source = url
            nodes.append(node)
            if args.max_candidates and len(nodes) >= args.max_candidates:
                break
        if args.max_candidates and len(nodes) >= args.max_candidates:
            break

    print(f"Parsed unique supported nodes: {len(nodes)}")

    results = []
    for i, node in enumerate(nodes, 1):
        print(f"[{i}/{len(nodes)}] {node.scheme} {node.server}:{node.port}", flush=True)
        result = benchmark(
            node,
            mihomo_bin=args.mihomo,
            benchmark_url=benchmark_url,
        )
        results.append(result)
        if result.error:
            print(f"  FAIL {result.error}")
        else:
            print(f"  UDP=ok latency={result.latency_ms:.1f}ms speed={result.throughput_mbps:.2f}Mbps")

    score_results(results)

    valid = [r for r in results if r.score is not None]
    valid.sort(key=lambda r: r.score, reverse=True)
    selected = valid[:args.top_n]

    for rank, result in enumerate(selected, 1):
        result.node.name = f"TOP-{rank:02d}-{result.node.scheme.upper()}"

    write_config([r.node for r in selected])

    Path("dist").mkdir(exist_ok=True)
    report = []
    for r in results:
        report.append({
            "name": r.node.name,
            "scheme": r.node.scheme,
            "server": r.node.server,
            "port": r.node.port,
            "source": r.node.source,
            "udp_ok": r.udp_ok,
            "latency_ms": r.latency_ms,
            "throughput_mbps": r.throughput_mbps,
            "score": r.score,
            "error": r.error,
        })
    Path("dist/benchmark.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Selected {len(selected)} / {len(valid)} UDP-capable benchmarked nodes")
    print("Wrote dist/config.yaml and dist/benchmark.json")

if __name__ == "__main__":
    main()
