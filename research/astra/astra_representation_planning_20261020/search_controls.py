"""Registered feature-only paid-search controls; no learned classification scores."""
import argparse
import json
import time
from coordination import ROOT, Slot, now
from ledger import atomic_json, sha256


def run():
    import numpy as np
    from worlds import World, feature_prefix
    from policy import random_order
    manifest = json.loads((ROOT/"FROZEN_TEST_V1.json").read_text())
    for name in ("worlds.py", "policy.py"):
        assert sha256(ROOT/name) == manifest["source_hashes"][name]
    rows = []
    start = time.process_time()
    for spec in manifest["worlds"]:
        if not spec["end_to_end"]:
            continue
        world = World(spec["family"], spec["seed"], **manifest["world_options"])
        for selector in ("random", "maximin"):
            clock = time.process_time()
            paid = list(world.prefix[:8])
            if selector == "maximin":
                paid = feature_prefix(world.x, 48, spec["seed"]+57)
            else:
                while len(paid) < 48:
                    priorities = random_order(len(world.x), spec["seed"]+1001, len(paid)+1)
                    paid.append(next(i for i in priorities if i not in paid))
            assert len(set(paid)) == 48
            observations = [world.pay(i) for i in paid]
            hits = [k+1 for k, i in enumerate(paid) if world.island[i] and world.quality[i]]
            rows.append({**spec, "selector": selector, "world_hash": world.hash,
                "paid_ids": paid, "observations": observations, "query_cost": 48.,
                "first_valid_hit": hits[0] if hits else None,
                "third_valid_hit": hits[2] if len(hits) >= 3 else None,
                "island_queries": len(hits), "pool_island_n": int(world.island.sum()),
                "missing_queries": int((~world.quality[paid]).sum()),
                "search_cpu_seconds": time.process_time()-clock})
    output = {"status": "COMPLETE", "utc": now().isoformat(), "paths": rows,
              "count": len(rows), "total_cpu_seconds": time.process_time()-start,
              "manifest_sha256": sha256(ROOT/"FROZEN_TEST_V1.json"),
              "source_sha256": sha256(__file__),
              "scope": "Feature-only paid search. No GP fits, classification predictions or free-hit conditioning."}
    assert len(rows) == 352
    atomic_json(ROOT/"results/SEARCH_CONTROLS.json", output)
    print(json.dumps({k: v for k, v in output.items() if k != "paths"}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--threads", type=int, choices=[1], required=True); p.parse_args()
    with Slot():
        run()
