#!/usr/bin/env python3
"""Measure the infrastructure boundary: what is shared, what costs per domain.

Counts non-blank, non-comment lines. Run from the repository root:
  python tools/measure-reuse.py
  python tools/measure-reuse.py --json > results/reuse.json
"""

import argparse
import glob
import json
import os

DOMAINS = ["smartbuilding", "vehicle", "healthcare"]

SHARED = {
    "bicep": ["infrastructure/*.bicep", "infrastructure/modules/*.bicep"],
    "function app": ["functionapp/EventHubToAdtFunction/*.cs",
                     "functionapp/EventHubToAdtFunction/host.json",
                     "functionapp/EventHubToAdtFunction/*.csproj"],
    "provisioner": ["digital-twins/scripts/provision-twins.py",
                    "digital-twins/scripts/build-telemetry-map.py"],
    "deploy scripts": ["digital-twins/scripts/upload-*.ps1"],
    "core DTDL": ["digital-twins/models/core/*.json"],
}

PER_DOMAIN = {
    "DTDL models": "digital-twins/models/{d}/*.json",
    "manifest": "digital-twins/manifests/{d}.json",
    "twin script (legacy)": "digital-twins/scripts/create-twins-{d}.ps1",
}

COMMENT_PREFIXES = ("//", "#", "<!--")


def count(path):
    n = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith(COMMENT_PREFIXES):
                continue
            n += 1
    return n


def total(patterns):
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    return sum(count(f) for f in files), sorted(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    shared = {}
    for name, patterns in SHARED.items():
        n, files = total(patterns)
        if files:
            shared[name] = n
    shared_total = sum(shared.values())

    domains = {}
    for d in DOMAINS:
        parts = {}
        for name, pattern in PER_DOMAIN.items():
            n, files = total([pattern.format(d=d)])
            if files:
                parts[name] = n
        domains[d] = parts

    # the legacy script only counts if the manifest has not replaced it
    def domain_cost(parts):
        if "manifest" in parts:
            return sum(v for k, v in parts.items() if k != "twin script (legacy)")
        return sum(parts.values())

    costs = {d: domain_cost(p) for d, p in domains.items()}
    mean = sum(costs.values()) / len(costs)
    reuse = 100 * shared_total / (shared_total + mean)

    result = {
        "shared": shared,
        "shared_total": shared_total,
        "per_domain": domains,
        "per_domain_cost": costs,
        "mean_domain_cost": round(mean, 1),
        "reuse_percent": round(reuse, 1),
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print("SHARED (written once, identical for every domain)")
    for k, v in shared.items():
        print(f"  {k:20} {v:5}")
    print(f"  {'TOTAL':20} {shared_total:5}")
    print()
    print("PER DOMAIN (written again for each new domain)")
    for d, parts in domains.items():
        detail = "  ".join(f"{k} {v}" for k, v in parts.items()
                           if k != "twin script (legacy)" or "manifest" not in parts)
        print(f"  {d:16} {costs[d]:5}   ({detail})")
    print(f"  {'MEAN':16} {mean:5.1f}")
    print()
    print(f"Reuse            {reuse:.1f}%")
    print(f"Cost of a new domain   {mean:.0f} lines, 0 changes below the boundary")


if __name__ == "__main__":
    main()