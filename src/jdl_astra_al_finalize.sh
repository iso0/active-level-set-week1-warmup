#!/usr/bin/env bash
# Dependency-gated final evaluation of ASTRA_AL (owner execution request of 2026-10-15).
# Gate: the pool runner has logged POOL_END (no live workers, every enabled study finished) AND all 30 ASTRA_AL units exist.
# Capacity: waits until at most 2 numeric leaf processes run elsewhere (Astra may hold her reserved slot), then runs the
# frozen evaluator once on one BLAS thread.  It never commits, never edits a plan, never touches another process.
# Log: outputs/joint_depth_label_development/astra_al/logs/finalize.log      Restartable: running it twice is harmless
# (it exits at once if FINAL_EVALUATION.done exists).
set -u
ROOT="C:/Users/ozgur/Documents/thesis/.claude/worktrees/joint-depth-label-dev"
OUT="$ROOT/outputs/joint_depth_label_development"
LOG="$OUT/astra_al/logs/finalize.log"
DONE="$OUT/astra_al/results/FINAL_EVALUATION.done"
mkdir -p "$OUT/astra_al/logs"
log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$LOG"; }
[ -f "$DONE" ] && { log "already done; exiting"; exit 0; }
log "finalizer started (pid $$); waiting for POOL_END and 30/30 units"
while true; do
  n=$(ls "$OUT/_cache/astra_al/" 2>/dev/null | grep -c '^NEW__.*\.json\.gz$')
  if grep -q '"event":"POOL_END"' <(tail -n 5 "$OUT/pool/pool_log.jsonl") && [ "$n" -ge 30 ]; then break; fi
  sleep 300
done
log "gate open: POOL_END logged and $n units present; checking capacity"
while true; do
  busy=$(powershell -NoProfile -Command "@(Get-Process python,pythonw,julia,Rscript -ErrorAction SilentlyContinue).Count" | tr -d '\r')
  [ "${busy:-9}" -le 2 ] && break
  log "capacity busy ($busy numeric processes); waiting"; sleep 300
done
cd "$ROOT" || exit 1
log "running: python -m src.jdl_astra_al_eval --threads 1"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONIOENCODING=utf-8 python -m src.jdl_astra_al_eval --threads 1 \
  > "$OUT/astra_al/logs/evaluate_final.log" 2> "$OUT/astra_al/logs/evaluate_final.err.log"
rc=$?
log "evaluator exit code $rc"
[ "$rc" -eq 0 ] && date -u +%Y-%m-%dT%H:%M:%SZ > "$DONE"
exit "$rc"
