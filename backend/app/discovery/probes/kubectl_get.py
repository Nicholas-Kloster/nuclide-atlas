"""Optional Kubernetes probe.

Skipped silently if kubectl is not on PATH or no context is configured.
We never pass `--all-namespaces` by default: the caller passes the
namespace they want. Defaults to the current context's namespace.

Output is intentionally shallow: one Deployment → one FoundContainer.
Atlas does not try to reverse-engineer a Service mesh; that's a
different tool.
"""

from __future__ import annotations

import json
import shutil
import subprocess

from .docker_ps import IMAGE_HINTS, SKIP_IMAGE
from ..types import FoundContainer


def run(namespace: str | None = None) -> list[FoundContainer]:
    if not shutil.which("kubectl"):
        return []
    args = ["kubectl", "get", "deploy", "-o", "json"]
    if namespace:
        args += ["-n", namespace]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=5)
    except FileNotFoundError:
        return []
    if proc.returncode != 0:
        return []
    try:
        listing = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []

    out: list[FoundContainer] = []
    for item in listing.get("items", []):
        spec_containers = (
            item.get("spec", {})
            .get("template", {})
            .get("spec", {})
            .get("containers", [])
        )
        for c in spec_containers:
            image = c.get("image", "")
            img_low = image.lower()
            if any(s in img_low for s in SKIP_IMAGE):
                continue
            hint = None
            for h, needle in IMAGE_HINTS.items():
                if needle in img_low:
                    hint = h
                    break
            if hint is None:
                continue
            ports = [
                p.get("containerPort")
                for p in c.get("ports", [])
                if isinstance(p.get("containerPort"), int)
            ]
            out.append(
                FoundContainer(
                    name=item.get("metadata", {}).get("name", ""),
                    image=image,
                    ports=ports,
                    framework=hint,
                    source=f"k8s:{item.get('metadata', {}).get('namespace', namespace or 'default')}",
                )
            )
    return out
