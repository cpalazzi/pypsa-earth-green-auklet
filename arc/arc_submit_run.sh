#!/bin/bash
# Quick script to submit a PyPSA-Earth run on ARC
# Usage: ./arc_submit_run.sh <scenario-name> [config-file]
#
# Examples:
#   ./arc_submit_run.sh europe-day-140
#   ./arc_submit_run.sh europe-week-140 configs/scenarios/config.europe-week-140.yaml

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <scenario-name> [config-file]"
    echo ""
    echo "Examples:"
    echo "  $0 europe-day-140"
    echo "  $0 europe-day-140 configs/scenarios/config.europe-day-140.yaml"
    exit 1
fi

SCENARIO="$1"
CONFIG="${2:-configs/scenarios/config.${SCENARIO}.yaml}"

# Check if we're in the right directory
if [ ! -f "Snakefile" ]; then
    echo "Error: Must run from pypsa-earth directory (where Snakefile is located)"
    exit 1
fi

if [ ! -f "${CONFIG}" ]; then
    echo "Error: Config file not found: ${CONFIG}"
    exit 1
fi

echo "Submitting PyPSA-Earth run:"
echo "  Scenario: ${SCENARIO}"
echo "  Config:   ${CONFIG}"
echo ""

JOBID=$(sbatch ../arc/jobs/arc_snakemake_gurobi.sh "${SCENARIO}" "${CONFIG}" | awk '{print $NF}')

echo "Job submitted: ${JOBID}"
echo ""
echo "Monitor with:"
echo "  squeue -j ${JOBID}"
echo "  tail -f logs/snakemake-${SCENARIO}-*-gurobi.log"
echo ""
echo "Check status:"
echo "  sacct -j ${JOBID} --format=JobID,JobName,State,Elapsed,MaxRSS"
echo ""
