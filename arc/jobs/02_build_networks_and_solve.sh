#!/bin/bash
#SBATCH --job-name=pypsa-earth-build-networks
#SBATCH --partition=short
#SBATCH --clusters=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=48
#SBATCH --mem=256G
#SBATCH --time=08:00:00
#SBATCH --mail-type=BEGIN,END
#SBATCH --mail-user=carlo.palazzi@eng.ox.ac.uk

if [[ $# -lt 3 ]]; then
  echo "Usage: sbatch ../arc/jobs/02_build_networks_and_solve.sh <run-label> <result-network-target> <configfile> [configfile ...]" >&2
  echo "Example: sbatch ../arc/jobs/02_build_networks_and_solve.sh europe-week-140 results/europe-year-140/networks/elec_s_140_ec_lcopt_Co2L-3h-week01.nc configs/scenarios/config.europe-week-140.yaml" >&2
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
RESULT_NETWORK_TARGET="$2"
shift 2
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

# Fail fast if annual profiles are missing for the solve config.
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

cd "$WORKDIR"
mkdir -p logs
export PYTHONPATH="$WORKDIR${PYTHONPATH:+:$PYTHONPATH}"

LOGFILE="logs/snakemake-${SCENARIO}-$(date +%Y%m%d-%H%M%S)-build-networks.log"
echo "Snakemake log: $LOGFILE"

MEM_MB=${SLURM_MEM_PER_NODE:-256000}
CPUS=${SLURM_CPUS_PER_TASK:-48}
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-$CPUS}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-$CPUS}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-$CPUS}
export GRB_THREADS=${GRB_THREADS:-$CPUS}
LATENCY_WAIT=${ARC_SNAKE_LATENCY_WAIT:-60}

ALLOWED_RULES=(
  retrieve_cost_data
  base_network
  build_bus_regions
  build_demand_profiles
  build_powerplants
  add_electricity
  simplify_network
  cluster_network
  add_extra_components
  prepare_network
  solve_network
)

"$SNAKEMAKE" \
  "$RESULT_NETWORK_TARGET" \
  --allowed-rules "${ALLOWED_RULES[@]}" \
  "${CONFIG_ARGS[@]}" \
  -j "${CPUS}" \
  --resources mem_mb="${MEM_MB}" \
  --latency-wait "${LATENCY_WAIT}" \
  --keep-going --rerun-incomplete --printshellcmds \
  --stats "logs/snakemake-${SCENARIO}-build-networks.stats.json" 2>&1 | tee -a "$LOGFILE"
