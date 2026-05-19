"""Stubbed metrics adapter.

Returns values that are random-looking but deterministic per entity, so
the UI renders consistent numbers across reloads instead of flickering.

TODO(prod): swap `_snapshot` for a real backend. Two natural integration
points:

  * Prometheus: query histogram_quantile() on
    `llm_request_duration_seconds_bucket{deployment_id="…"}`
  * vLLM/TGI native /metrics endpoints: scrape and aggregate per
    deployment id (most frameworks emit Prometheus text format already).

The shape of `MetricsSnapshot` is the contract: keep it stable when
plugging in real data.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from .models import EntityType, MetricsSnapshot, TimeRange


def _seeded_floats(entity_type: EntityType, entity_id: str) -> tuple[float, ...]:
    """Deterministic pseudo-random floats keyed by (type, id)."""
    seed = hashlib.sha256(f"{entity_type}:{entity_id}".encode()).digest()
    # Slice the digest into 8-byte chunks → 0..1 floats.
    return tuple(int.from_bytes(seed[i : i + 4], "big") / 2**32 for i in range(0, 24, 4))


def snapshot(
    entity_type: EntityType, entity_id: str, time_range: TimeRange = TimeRange.last_1h
) -> MetricsSnapshot:
    a, b, c, d, e, f = _seeded_floats(entity_type, entity_id)

    # Latency: skewed toward sub-second, p95 always > p50.
    p50 = 40 + a * 220  # 40–260 ms
    p95 = p50 + 60 + b * 540  # +60..+600 ms

    tps = None
    gpu = None
    if entity_type in (EntityType.deployment, EntityType.endpoint, EntityType.model):
        tps = 8 + c * 92  # 8..100 tok/s
    if entity_type == EntityType.deployment:
        gpu = 0.20 + d * 0.75  # 20..95%

    error_rate = (e ** 3) * 0.05  # heavy-tailed toward 0, cap ~5%

    return MetricsSnapshot(
        entityType=entity_type,
        entityId=entity_id,
        latencyP50=round(p50, 2),
        latencyP95=round(p95, 2),
        tokensPerSecond=round(tps, 2) if tps is not None else None,
        errorRate=round(error_rate, 5),
        gpuUtilization=round(gpu, 3) if gpu is not None else None,
        timeRange=time_range,
        sampledAt=datetime.now(timezone.utc),
    )
