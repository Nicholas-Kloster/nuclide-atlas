"""Rule-based risk badges.

Returns a list of `RiskFinding` per entity. Rules are intentionally
small, deterministic, and traceable to a single field — no scoring
black box. The UI renders each finding as a colored badge with the rule
id on hover.

Categories:
  exposed        — internal API with no auth
  unencrypted    — http:// for production-tier deployment
  large-context  — model maxContext > 32k (worth a hover note, not a warning)
  no-rerank      — RAG with k > 10 and no rerankers (recall/precision risk)
  unbounded      — deployment with no maxTokens cap
  open-prompt    — safety policy with zero filters
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import EntityType, Graph


@dataclass(frozen=True)
class RiskFinding:
    entity_type: EntityType
    entity_id: str
    rule_id: str
    severity: str  # "info" | "warn" | "high"
    message: str


def evaluate(graph: Graph) -> list[RiskFinding]:
    out: list[RiskFinding] = []

    for ep in graph.endpoints:
        if ep.type == "internalAPI" and ep.auth_type == "none":
            out.append(RiskFinding(
                EntityType.endpoint, ep.id,
                "exposed.no_auth",
                "high",
                "internal API with no authentication",
            ))
        if ep.protocol == "http" and ep.type == "publicAPI":
            out.append(RiskFinding(
                EntityType.endpoint, ep.id,
                "unencrypted.public_http",
                "high",
                "public endpoint over plaintext HTTP",
            ))

    for d in graph.deployments:
        if d.configuration.max_tokens is None and d.environment == "prod":
            out.append(RiskFinding(
                EntityType.deployment, d.id,
                "unbounded.max_tokens",
                "warn",
                "prod deployment with no maxTokens cap",
            ))

    for m in graph.models:
        if m.architecture.max_context and m.architecture.max_context >= 100_000:
            out.append(RiskFinding(
                EntityType.model, m.id,
                "info.large_context",
                "info",
                f"large context window ({m.architecture.max_context} tokens)",
            ))

    for r in graph.rag_pipelines:
        if r.retrieval.k > 10 and not r.retrieval.rerankers:
            out.append(RiskFinding(
                EntityType.rag_pipeline, r.id,
                "no_rerank.high_k",
                "warn",
                f"k={r.retrieval.k} with no reranker — precision likely poor",
            ))

    for p in graph.safety_policies:
        if not p.pre_prompt_filters and not p.post_response_filters:
            out.append(RiskFinding(
                EntityType.safety_policy, p.id,
                "open_prompt.no_filters",
                "high",
                "safety policy with no filters at any stage",
            ))

    return out


def by_entity(findings: Iterable[RiskFinding]) -> dict[str, list[RiskFinding]]:
    out: dict[str, list[RiskFinding]] = {}
    for f in findings:
        key = f"{f.entity_type}:{f.entity_id}"
        out.setdefault(key, []).append(f)
    return out
