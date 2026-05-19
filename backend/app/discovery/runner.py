"""Orchestrate all probes and produce one DiscoveryResult.

Each probe is fenced: a failure in `docker_ps` does not stop
`local_ports`. The runner is deliberately synchronous and stdlib-only;
parallelism happens inside each probe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .merger import _AssembledGraph, merge, to_yaml
from .probes import (
    docker_ps,
    env_vars,
    kubectl_get,
    local_ports,
)
from .types import (
    FoundContainer,
    FoundEndpoint,
    FoundObservability,
    FoundVectorStore,
)


@dataclass
class DiscoveryResult:
    endpoints: list[FoundEndpoint] = field(default_factory=list)
    vectors: list[FoundVectorStore] = field(default_factory=list)
    observability: list[FoundObservability] = field(default_factory=list)
    containers: list[FoundContainer] = field(default_factory=list)
    sources_run: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.endpoints or self.vectors or self.observability or self.containers)

    def counts(self) -> dict[str, int]:
        return {
            "endpoints": len(self.endpoints),
            "vector_stores": len(self.vectors),
            "observability": len(self.observability),
            "containers": len(self.containers),
        }

    def print_summary(self, indent: str = "") -> None:
        for ep in self.endpoints:
            line = f"{ep.framework or '?':14s} {ep.url}"
            if ep.raw_models:
                line += f"  models: {', '.join(ep.raw_models[:3])}"
                if len(ep.raw_models) > 3:
                    line += f" (+{len(ep.raw_models) - 3} more)"
            print(indent + line)
        for vs in self.vectors:
            cols = f" collections: {', '.join(vs.collections)}" if vs.collections else ""
            print(f"{indent}{vs.db_type:14s} {vs.url}{cols}")
        for obs in self.observability:
            print(f"{indent}{obs.kind:14s} {obs.url}")
        for c in self.containers:
            if not any(ep.source.endswith(c.name) for ep in self.endpoints):
                print(f"{indent}container      {c.name:24s} ({c.image})")

    def merge_to_graph(self) -> _AssembledGraph:
        return merge(
            endpoints=self.endpoints,
            vectors=self.vectors,
            observability=self.observability,
            containers=self.containers,
        )

    def write_yaml(self, path: Path, *, header: str | None = None) -> None:
        g = self.merge_to_graph()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(to_yaml(g, header=header) + "\n")

    def node_summary(self) -> str:
        g = self.merge_to_graph()
        return (
            f"{len(g.models)} models, "
            f"{len(g.deployments)} deployments, "
            f"{len(g.endpoints)} endpoints, "
            f"{len(g.vector_indexes)} vector indexes, "
            f"{len(g.tools)} tools"
        )


def run_discovery(
    *,
    include_env: bool = True,
    include_local: bool = True,
    include_docker: bool = True,
    include_k8s: bool = False,
    local_hosts: tuple[str, ...] = ("127.0.0.1",),
    k8s_namespace: str | None = None,
) -> DiscoveryResult:
    result = DiscoveryResult()

    if include_env:
        try:
            e, v, o = env_vars.run()
            result.endpoints.extend(e)
            result.vectors.extend(v)
            result.observability.extend(o)
            result.sources_run.append("env")
        except Exception:
            pass

    if include_local:
        try:
            e, v, o = local_ports.run(local_hosts)
            result.endpoints.extend(e)
            result.vectors.extend(v)
            result.observability.extend(o)
            result.sources_run.append("local_ports")
        except Exception:
            pass

    if include_docker:
        try:
            c, e, v, o = docker_ps.run()
            result.containers.extend(c)
            result.endpoints.extend(e)
            result.vectors.extend(v)
            result.observability.extend(o)
            result.sources_run.append("docker")
        except Exception:
            pass

    if include_k8s:
        try:
            result.containers.extend(kubectl_get.run(k8s_namespace))
            result.sources_run.append("k8s")
        except Exception:
            pass

    return result
