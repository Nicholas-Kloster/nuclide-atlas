"""Tiny stdlib HTTP helper shared by probes.

httpx is a hard dep of the backend, but the discovery layer pretends it
isn't there so the bootstrap CLI can run with bare `python3`. Keeping
this file small on purpose — it is not an HTTP library.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class Probed:
    url: str
    ok: bool
    status: int | None
    body: str
    json: Any | None
    elapsed_ms: float | None
    error: str | None


def get(url: str, *, timeout: float = 1.5, headers: dict[str, str] | None = None) -> Probed:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "nuclide-atlas-discovery/0.2", **(headers or {})},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(64 * 1024).decode("utf-8", errors="replace")
            elapsed = (time.perf_counter() - started) * 1000.0
            data: Any | None = None
            ct = resp.headers.get("content-type", "")
            if "json" in ct:
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    data = None
            return Probed(url, True, resp.status, body, data, round(elapsed, 1), None)
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read(64 * 1024).decode("utf-8", errors="replace")
        except Exception:
            pass
        return Probed(url, False, exc.code, body, None, None, f"HTTP {exc.code}")
    except (urllib.error.URLError, socket.timeout, ConnectionError) as exc:
        return Probed(url, False, None, "", None, None, type(exc).__name__)


def tcp_open(host: str, port: int, timeout: float = 0.4) -> bool:
    """Quick TCP-connect check before sending HTTP. Saves time on closed ports."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            return True
        except OSError:
            return False
