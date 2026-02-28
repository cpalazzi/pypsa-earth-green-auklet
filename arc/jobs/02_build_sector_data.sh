#!/bin/bash
#SBATCH --job-name=pypsa-earth-build-sector-data
#SBATCH --partition=short
#SBATCH --clusters=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=48
#SBATCH --mem=256G
#SBATCH --time=08:00:00
#SBATCH --mail-type=BEGIN,END
#SBATCH --mail-user=carlo.palazzi@eng.ox.ac.uk

if [[ $# -lt 2 ]]; then
  echo "Usage: sbatch ../arc/jobs/02_build_sector_data.sh <run-label> <configfile> [configfile ...]" >&2
  echo "Example: sbatch ../arc/jobs/02_build_sector_data.sh europe-year-140-co2-zero-h2-sector configs/scenarios/config.europe-year-140-co2-zero-h2-sector.yaml" >&2
  exit 2
fi

if [ -f /etc/profile ]; then
  source /etc/profile
fi
if [ -f /etc/profile.d/modules.sh ]; then
  source /etc/profile.d/modules.sh
fi
if [ -f /etc/profile.d/lmod.sh ]; then
  source /etc/profile.d/lmod.sh
fi
if ! command -v module >/dev/null 2>&1; then
  source /usr/share/lmod/lmod/init/bash
fi

set -euo pipefail

SCENARIO="$1"
shift 1
CONFIG_FILES=("$@")
CONFIG_ARGS=()
for cfg in "${CONFIG_FILES[@]}"; do
  CONFIG_ARGS+=("--configfile" "$cfg")
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WORKDIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
WORKDIR=${ARC_WORKDIR:-${SLURM_SUBMIT_DIR:-$DEFAULT_WORKDIR}}

if [[ ! -f "$WORKDIR/Snakefile" && -f "$DEFAULT_WORKDIR/Snakefile" ]]; then
  echo "WARN: No Snakefile in WORKDIR '$WORKDIR'; falling back to '$DEFAULT_WORKDIR'" >&2
  WORKDIR="$DEFAULT_WORKDIR"
fi

CHECK_SCRIPT_CANDIDATES=(
  "$WORKDIR/../arc/arc_check_run_inputs.sh"
  "$SLURM_SUBMIT_DIR/../arc/arc_check_run_inputs.sh"
  "$SCRIPT_DIR/../arc_check_run_inputs.sh"
)

CHECK_SCRIPT=""
for candidate in "${CHECK_SCRIPT_CANDIDATES[@]}"; do
  if [[ -n "${candidate}" && -x "${candidate}" ]]; then
    CHECK_SCRIPT="$candidate"
    break
  fi
done

if [[ -z "$CHECK_SCRIPT" ]]; then
  echo "Required profile preflight checker not found/executable." >&2
  echo "Checked:" >&2
  for candidate in "${CHECK_SCRIPT_CANDIDATES[@]}"; do
    echo "  $candidate" >&2
  done
  exit 2
fi

# Fail fast if annual profiles are missing for this sector config.
"$CHECK_SCRIPT" "${CONFIG_FILES[0]}"

ANACONDA_MODULE=${ARC_ANACONDA_MODULE:-"Anaconda3/2024.06-1"}
module load "$ANACONDA_MODULE"

PYPSA_ENV=${ARC_PYPSA_ENV:-"/data/engs-df-green-ammonia/engs2523/envs/pypsa-earth-env"}

export PATH="$PYPSA_ENV/bin:$PATH"
SNAKEMAKE="$PYPSA_ENV/bin/snakemake"

export PYPSA_SOLVER_NAME=${PYPSA_SOLVER_NAME:-gurobi}
export LINOPY_SOLVER=${LINOPY_SOLVER:-gurobi}
export GRB_LICENSE_FILE=${GRB_LICENSE_FILE:-"/data/engs-df-green-ammonia/engs2523/licenses/gurobi.lic"}
export PROJ_LIB=${PROJ_LIB:-"$PYPSA_ENV/share/proj"}
export PROJ_DATA=${PROJ_DATA:-"$PYPSA_ENV/share/proj"}
RERUN_TRIGGERS=${ARC_SNAKE_RERUN_TRIGGERS:-mtime}

DRYRUN_LOG=$(mktemp)
if ! "$SNAKEMAKE" \
  -n \
  override_res_all_nets \
  --rerun-triggers "${RERUN_TRIGGERS}" \
  "${CONFIG_ARGS[@]}" >"$DRYRUN_LOG" 2>&1; then
  echo "ERROR: Dry-run for step 2 failed. See output below:" >&2
  cat "$DRYRUN_LOG" >&2
  rm -f "$DRYRUN_LOG"
  exit 2
fi

if grep -Eq '^rule build_renewable_profiles:' "$DRYRUN_LOG"; then
  echo "WARN: Step 2 dry-run includes build_renewable_profiles; continuing because prerequisite files were validated." >&2
  echo "WARN: Using --rerun-triggers ${RERUN_TRIGGERS} to avoid metadata-only reruns where possible." >&2
fi
rm -f "$DRYRUN_LOG"

cd "$WORKDIR"
mkdir -p logs
export PYTHONPATH="$WORKDIR${PYTHONPATH:+:$PYTHONPATH}"

REQUIRED_FILES=(
  "cutouts/cutout-2013-era5.nc"
  "data/demand/unsd/paths/Energy_Statistics_Database.xlsx"
  "data/demand/fuel_shares.csv"
  "data/demand/growth_factors_cagr.csv"
  "data/demand/district_heating.csv"
  "data/demand/efficiency_gains_cagr.csv"
  "data/emobility/KFZ__count"
  "data/emobility/Pkw__count"
  "data/heat_load_profile_BDEW.csv"
  "data/unsd_transactions.csv"
  "data/hydrogen_salt_cavern_potentials.csv"
  "data/temp_hard_coded/biomass_transport_costs.csv"
)

MISSING=()
for f in "${REQUIRED_FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    MISSING+=("$f")
  fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "ERROR: Missing required sector-demand input files:" >&2
  for f in "${MISSING[@]}"; do
    echo "  - $f" >&2
  done
  echo "Sync these from local before submitting this job." >&2
  echo "Recommended one-time pre-sync commands are documented in arc/README.md (section: Sync local custom data)." >&2
  exit 2
fi

LOGFILE="logs/snakemake-${SCENARIO}-$(date +%Y%m%d-%H%M%S)-build-sector-data.log"
echo "Snakemake log: $LOGFILE"

MEM_MB=${SLURM_MEM_PER_NODE:-256000}
CPUS=${SLURM_CPUS_PER_TASK:-48}
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-$CPUS}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-$CPUS}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-$CPUS}
export GRB_THREADS=${GRB_THREADS:-$CPUS}
LATENCY_WAIT=${ARC_SNAKE_LATENCY_WAIT:-60}

"$SNAKEMAKE" \
  override_res_all_nets \
  --rerun-triggers "${RERUN_TRIGGERS}" \
  "${CONFIG_ARGS[@]}" \
  -j "${CPUS}" \
  --resources mem_mb="${MEM_MB}" \
  --latency-wait "${LATENCY_WAIT}" \
  --keep-going --rerun-incomplete --printshellcmds \
  --stats "logs/snakemake-${SCENARIO}-build-sector-data.stats.json" 2>&1 | tee -a "$LOGFILE"
