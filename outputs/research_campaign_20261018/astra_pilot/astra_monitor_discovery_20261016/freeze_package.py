"""Create the prospective manifest ONCE. Hashing only; no numerical imports."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
from discovery import Config

HERE = Path(__file__).resolve().parent


def main():
    target = HERE/"FROZEN_MANIFEST.json"
    if target.exists():
        raise SystemExit("Freeze exists; preserve it. Any change needs a prospective versioned amendment.")
    code = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob("*.py"))}
    docs = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob("*.md"))}
    manifest = {
        "package": "astra_monitor_discovery_20261016",
        "status": "FROZEN_BEFORE_ANY_SYNTHETIC_FIT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "code_hashes": code,
        "code_digest": hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest(),
        "document_hashes": docs,
        "provenance_hashes": {name: hashlib.sha256((HERE/name).read_bytes()).hexdigest()
                              for name in ("SOURCE_SNAPSHOT.json", "METHOD_CHOICE_RECORD.json", "requirements.txt")},
        "experiment": {"target": "uniform feature distribution on [0,1]^4; separate fixed evaluator cloud",
                       "pool_size": 512, "eval_size": 2048, "seeds": [61016, 61017],
                       "worlds": ["island", "null_bad_scale", "island_bad_monitor"],
                       "core_arms": ["surprise", "straddle_global", "straddle", "margin", "random"],
                       "aux_arms": ["primary_variance", "multi_variance"],
                       "startup": 8, "budget": 24, "readouts": "every B from 8 through 24",
                       "core_trajectories": 30, "aux_trajectories": 4,
                       "aux_world": "island", "matched_startup_seed_offset": 100,
                       "matched_global_order_seed_offset": 200},
        "selector": Config().__dict__,
        "model": {"kernel": "isotropic Matern 3/2", "length": .28, "amplitude_sd": .8,
                  "noise_sd": .08, "mean_primary": -.4, "mean_aux": 0., "aux_length": .45,
                  "jitter_variance": 1e-10,
                  "optimizer": None, "hyperparameter_uncertainty": "not integrated",
                  "decision": "posterior latent mean > 0", "margin": "abs(P(f>0)-0.5)",
                  "null_bad_scale": "all supplied predictive SDs multiplied by 0.15, same GP in all arms"},
        "oracle": {"cost": "one selected simulation; scalar primary + canonical synthetic label + auxiliary",
                   "hidden": "island/boundary memberships, latent truth, all unpaid outcomes, evaluator cloud",
                   "invalid_channel": "cost retained; no primary regression row or discovery trigger; label retained"},
        "targets": {"discovery": "global error <=0.10 AND island recall >=0.75 AND island-boundary error <=0.20",
                    "paired_regression": "primary RMSE <=0.30 AND auxiliary RMSE <=0.30",
                    "confirmation": "two consecutive budget readouts; count second readout",
                    "censoring": "unreached at B24 is right-censored, not an assumed B25 hit",
                    "first_discovery": "first paid valid member of evaluator-defined island, startup included"},
        "caps": {"controlled_fit_requests": 578, "reference_fits": 4,
                 "component_solves": 650, "wall_seconds": 1200, "threads": 1},
        "numerics": {"independent_dense_reference_absolute_tolerance": 1e-9,
                     "negative_variance_reject_below": -1e-7, "tie_rule": "smallest pool index",
                     "near_ties": "no numerical refinement ladder; report deterministic ties"},
        "expected_directions": {"island": "local response may help AFTER a valid surprise; no guaranteed initial hit benefit",
                                "null_bad_scale": "calibration guard should curb spurious local episodes; early errors may remain",
                                "island_bad_monitor": "flagged invalid channels cannot trigger; they still consume queries",
                                "auxiliary": "variance sharing may help auxiliary RMSE at a cost to primary accuracy; no numeric effect prediction"},
        "uncertainty": "all paired seed outcomes and seed range; two seeds cannot support reliable superiority inference",
        "stops": ["no allocation", "expired/revoked allocation", "20-minute cumulative wall budget", "fit/component cap",
                  "reference error", "nonfinite posterior", "failed fit", "unresolved interrupted attempt", "code hash mismatch"],
        "claim_scope": "synthetic feasibility only; no SPH, G3, short-K, C3/C4, Stage A or physical-simulator claim"
    }
    target.write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(manifest["code_digest"])


if __name__ == "__main__":
    main()
