#!/bin/bash
# Submit the 1-hour-resolution check of co2-zero-nh3-td30 (Appendix F of the green-caribou paper).
# Prepared 8 Oct 2026; not yet run.
#
# Run on the ARC login node from pypsa-earth/:
#   bash ../arc/submit_td30_1h.sh                  # only if no other auklet scenario is queued
#   bash ../arc/submit_td30_1h.sh <jobid> [arc|htc] # chain after that job (same cluster)
#
# Resources follow the March 1 h run (job 7271257: 13 h 06 min, 232 GB peak on 16 CPUs). The TD30
# network is slightly larger, so this asks for 320 GB and 36 h on medium. It shares run.name
# "europe-year-140" with the 3 h scenarios, and job 02 deletes the shared intermediates, so it must
# never run alongside them.
set -euo pipefail
LABEL=co2-zero-nh3-td30-1h
CONFIG=configs/scenarios/config.europe-year-140-co2-zero-nh3-td30-1h.yaml
[[ -f Snakefile && -f "$CONFIG" ]] || { echo "Run from the pypsa-earth directory." >&2; exit 2; }

DEP=()
if [[ $# -ge 1 ]]; then
  DEP=(--dependency="afterany:$1" --clusters="${2:-arc}")
else
  busy=$(squeue -M all -u "$USER" -h -n pypsa-earth-solve-power | wc -l)
  if [[ "$busy" -gt 0 ]]; then
    echo "Other pypsa-earth-solve-power jobs are queued or running; pass one of their ids to chain after it." >&2
    squeue -M all -u "$USER" -n pypsa-earth-solve-power -o "%.10i %.9P %.8T %.10M %R" >&2
    exit 3
  fi
fi

sbatch --partition=medium --mem=320G --time=1-12:00:00 "${DEP[@]}" \
  ../arc/jobs/02_build_networks_and_solve_power.sh "$LABEL" "$CONFIG"
