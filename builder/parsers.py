from __future__ import annotations

import base64
import json
import re
from urllib.parse import parse_qs, unquote, urlsplit

from .models import Node

SUPPORTED = {
    "vless", "vmess", "trojan", "ss", "shadowsocks", "hysteria", "hysteria2"
}

def _one(q, key, default=None):
    value = q.get(key)
    if not value:
        return default
    return value[0]

def _bool(v, default=False):
    if v is None:
        return default
    return str(v).lower() in {"1", "true", "yes", "on"}

def _host_port(netloc: str):
    if "@" in netloc:
        netloc = netloc.rsplit("@", 1)[1]
    if netloc.startswith("["):
        host, _, port = netloc.rpartition("]:")
        return host.lstrip("["), int(port or 0)
    host, sep, port = netloc.rpartition(":")
    return (host, int(port)) if sep and port.isdigit() else (netloc, 0)

def parse_vless(uri: str, idx: int) -> Node:
    p = urlsplit(uri)
    q = parse_qs(p.query)
    host, port = _host_port(p.netloc)
    obj = {
        "name": unquote(p.fragment) or f"VLESS-{idx}",
        "type": "vless",
        "server": host,
        "port": port,
        "uuid": unquote(p.username or ""),
        "udp": True,
    }
    network = _one(q, "type", "tcp")
    obj["network"] = network
    security = _one(q, "security")
    if security in {"tls", "reality"}:
        obj["tls"] = True
    sni = _one(q, "sni") or _one(q, "servername")
    if sni:
        obj["servername"] = unquote(sni)
    fp = _one(q, "fp")
    if fp:
        obj["client-fingerprint"] = fp
    flow = _one(q, "flow")
    if flow:
        obj["flow"] = flow
    if security == "reality":
        pbk = _one(q, "pbk") or _one(q, "public-key")
        sid = _one(q, "sid") or _one(q, "short-id")
        obj["reality-opts"] = {}
        if pbk:
            obj["reality-opts"]["public-key"] = pbk
        if sid:
            obj["reality-opts"]["short-id"] = sid
    if network == "ws":
        obj["ws-opts"] = {}
        path = _one(q, "path")
        host_header = _one(q, "host")
        if path:
            obj["ws-opts"]["path"] = unquote(path)
        if host_header:
            obj["ws-opts"]["headers"] = {"Host": unquote(host_header)}
    if network == "grpc":
        service = _one(q, "serviceName") or _one(q, "service-name")
        if service:
            obj["grpc-opts"] = {"grpc-service-name": unquote(service)}
    return Node(obj["name"], "vless", uri, obj, host, port)

def parse_vmess(uri: str, idx: int) -> Node:
    payload = uri.split("://", 1)[1].split("#", 1)[0]
    raw = base64.b64decode(payload + "=" * (-len(payload) % 4)).decode("utf-8")
    data = json.loads(raw)
    obj = {
        "name": unquote(urlsplit(uri).fragment) or data.get("ps") or f"VMess-{idx}",
        "type": "vmess",
        "server": data["add"],
        "port": int(data.get("port", 443)),
        "uuid": data["id"],
        "alterId": int(data.get("aid", 0)),
        "cipher": data.get("scy", "auto"),
        "udp": True,
    }
    net = data.get("net", "tcp")
    obj["network"] = net
    if str(data.get("tls", "")).lower() in {"tls", "true"}:
        obj["tls"] = True
    if data.get("sni"):
        obj["servername"] = data["sni"]
    if net == "ws":
        obj["ws-opts"] = {"path": data.get("path", "")}
        host = data.get("host")
        if host:
            obj["ws-opts"]["headers"] = {"Host": host}
    return Node(obj["name"], "vmess", uri, obj, obj["server"], obj["port"])

def parse_trojan(uri: str, idx: int) -> Node:
    p = urlsplit(uri)
    q = parse_qs(p.query)
    host, port = _host_port(p.netloc)
    obj = {
        "name": unquote(p.fragment) or f"Trojan-{idx}",
        "type": "trojan",
        "server": host,
        "port": port,
        "password": unquote(p.username or ""),
        "udp": True,
    }
    sni = _one(q, "sni") or _one(q, "peer")
    if sni:
        obj["sni"] = unquote(sni)
    if _one(q, "allowInsecure") is not None:
        obj["skip-cert-verify"] = _bool(_one(q, "allowInsecure"))
    return Node(obj["name"], "trojan", uri, obj, host, port)

def parse_ss(uri: str, idx: int) -> Node:
    p = urlsplit(uri)
    payload = p.netloc
    if "@" not in payload:
        raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode()
        payload = raw
    userinfo, hostport = payload.rsplit("@", 1)
    method, password = userinfo.split(":", 1)
    host, port = _host_port(hostport)
    obj = {
        "name": unquote(p.fragment) or f"SS-{idx}",
        "type": "ss",
        "server": host,
        "port": port,
        "cipher": method,
        "password": unquote(password),
        "udp": True,
    }
    return Node(obj["name"], "ss", uri, obj, host, port)

def parse_hysteria(uri: str, idx: int) -> Node:
    p = urlsplit(uri)
    q = parse_qs(p.query)
    host, port = _host_port(p.netloc)
    scheme = p.scheme.lower()
    obj = {
        "name": unquote(p.fragment) or f"{scheme.upper()}-{idx}",
        "type": "hysteria2" if scheme == "hysteria2" else "hysteria",
        "server": host,
        "port": port,
        "udp": True,
    }
    if p.username:
        obj["password"] = unquote(p.username)
    if _one(q, "auth"):
        obj["password"] = unquote(_one(q, "auth"))
    if _one(q, "sni"):
        obj["sni"] = unquote(_one(q, "sni"))
    if _one(q, "insecure") is not None:
        obj["skip-cert-verify"] = _bool(_one(q, "insecure"))
    if _one(q, "obfs"):
        obj["obfs"] = _one(q, "obfs")
    if _one(q, "obfs-password"):
        obj["obfs-password"] = _one(q, "obfs-password")
    return Node(obj["name"], obj["type"], uri, obj, host, port)

PARSERS = {
    "vless": parse_vless,
    "vmess": parse_vmess,
    "trojan": parse_trojan,
    "ss": parse_ss,
    "shadowsocks": parse_ss,
    "hysteria": parse_hysteria,
    "hysteria2": parse_hysteria,
}

def parse_uri(uri: str, idx: int) -> Node | None:
    scheme = uri.split("://", 1)[0].lower()
    parser = PARSERS.get(scheme)
    if not parser:
        return None
    return parser(uri, idx)
