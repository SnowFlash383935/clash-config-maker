from __future__ import annotations

import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import yaml

class MihomoInstance:
    def __init__(self, binary="mihomo", startup_timeout=8):
        self.binary = binary
        self.startup_timeout = startup_timeout
        self.tmp = None
        self.proc = None
        self.port = None

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="clash-builder-")
        self.port = self._free_port()
        return self

    def start(self, proxy: dict):
        config = {
            "mixed-port": self.port,
            "allow-lan": False,
            "mode": "rule",
            "log-level": "error",
            "proxies": [proxy],
            "proxy-groups": [{
                "name": "PROXY",
                "type": "select",
                "proxies": [proxy["name"]],
            }],
            "rules": ["MATCH,PROXY"],
        }
        path = Path(self.tmp.name) / "config.yaml"
        path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
        self.proc = subprocess.Popen(
            [self.binary, "-d", self.tmp.name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("mihomo exited during startup")
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                    return
            except OSError:
                time.sleep(0.1)
        raise TimeoutError("mihomo did not open mixed-port")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def __exit__(self, exc_type, exc, tb):
        self.stop()
        if self.tmp:
            self.tmp.cleanup()

    @staticmethod
    def _free_port():
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        p = s.getsockname()[1]
        s.close()
        return p
