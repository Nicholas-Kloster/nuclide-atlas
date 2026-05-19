"""Probe `localhost` (and any extra hosts the caller passes) for the
service catalog. This is the workhorse: the single move that lights up
a graph for a developer who runs Ollama or vLLM on their laptop."""

from __future__ import annotations

from typing import Iterable

from .fingerprint import classify, probe_host_ports
from ..types import FoundEndpoint, FoundObservability, FoundVectorStore


def run(
    hosts: Iterable[str] = ("127.0.0.1",),
) -> tuple[list[FoundEndpoint], list[FoundVectorStore], list[FoundObservability]]:
    endpoints: list[FoundEndpoint] = []
    vectors: list[FoundVectorStore] = []
    observ: list[FoundObservability] = []
    for host in hosts:
        for probed in probe_host_ports(host):
            e, v, o = classify(probed)
            if e:
                e.source = f"local:{host}"
                endpoints.append(e)
            if v:
                v.source = f"local:{host}"
                vectors.append(v)
            if o:
                o.source = f"local:{host}"
                observ.append(o)
    return endpoints, vectors, observ
