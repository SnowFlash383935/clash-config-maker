from __future__ import annotations

from pathlib import Path
import yaml

def build_config(nodes):
    proxies = []
    names = []
    for node in nodes:
        p = dict(node.mihomo)
        p["name"] = node.name
        proxies.append(p)
        names.append(node.name)

    return {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "info",
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "TOP",
                "type": "select",
                "proxies": names + ["DIRECT"],
            },
        ],
        "rules": [
            "MATCH,TOP",
        ],
    }

def write_config(nodes, path="dist/config.yaml"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        yaml.safe_dump(build_config(nodes), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
