from builder.parsers import parse_uri

def test_vless():
    n = parse_uri(
        "vless://859a537b-09cf-4bce-8da4-ecbb72950e3a@159.195.27.99:443"
        "?type=tcp&security=reality&encryption=none&flow=xtls-rprx-vision"
        "&fp=random&pbk=PUBKEY&sid=SHORT&sni=example.com#test",
        1,
    )
    assert n.scheme == "vless"
    assert n.mihomo["reality-opts"]["public-key"] == "PUBKEY"
    assert n.mihomo["flow"] == "xtls-rprx-vision"

def test_trojan():
    n = parse_uri("trojan://pass@example.com:443?sni=example.com#t", 1)
    assert n.mihomo["type"] == "trojan"
    assert n.mihomo["udp"] is True
