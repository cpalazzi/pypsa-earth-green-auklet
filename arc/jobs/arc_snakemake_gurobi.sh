#!/bin/bash
#SBATCH --job-name=pypsa-earth-gurobi
#SBATCH --partition=long
#SBATCH --clusters=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=256G
#SBATCH --time=24:00:00
#SBATCH --mail-type=BEGIN,END
#SBATCH --mail-user=carlo.palazzi@eng.ox.ac.uk

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

if [[ $# -lt 2 ]]; then
  echo "Usage: sbatch scripts/arc/jobs/arc_snakemake_gurobi.sh <run-label> <configfile> [configfile ...]" >&2
  echo "Example: sbatch scripts/arc/jobs/arc_snakemake_gurobi.sh 20251202-green config/default-single-timestep.yaml config/overrides/green-ammonia.yaml" >&2
  exit 2
fi

SCENARIO="$1"
shift

CONFIG_FILES=("$@")
CONFIG_ARGS=()
for cfg in "${CONFIG_FILES[@]}"; do
  CONFIG_ARGS+=("--configfile" "$cfg")
done

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WORKDIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
WORKDIR=${ARC_WORKDIR:-${SLURM_SUBMIT_DIR:-$DEFAULT_WORKDIR}}
cd "$WORKDIR"
mkdir -p logs
export PYTHONPATH="$WORKDIR${PYTHONPATH:+:$PYTHONPATH}"

LOGFILE="logs/snakemake-${SCENARIO}-$(date +%Y%m%d-%H%M%S)-gurobi.log"
echo "Snakemake log: $LOGFILE"

MEM_MB=${SLURM_MEM_PER_NODE:-256000}
CPUS=${SLURM_CPUS_PER_TASK:-16}
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-$CPUS}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-$CPUS}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-$CPUS}
export GRB_THREADS=${GRB_THREADS:-$CPUS}
LATENCY_WAIT=${ARC_SNAKE_LATENCY_WAIT:-60}
EXTRA_ARGS=()
if [[ "${ARC_SNAKE_DRYRUN:-0}" == "1" ]]; then
  EXTRA_ARGS+=("-n")
fi
if [[ "${ARC_SNAKE_NOLOCK:-0}" == "1" ]]; then
  EXTRA_ARGS+=("--nolock")
fi

if [[ "${ARC_SNAKE_UNLOCK:-0}" == "1" ]]; then
  "$SNAKEMAKE" --unlock
fi

run_snakemake() {
  "$SNAKEMAKE" \
    "$@" \
    "${EXTRA_ARGS[@]}" \
    -j "${CPUS}" \
    --resources mem_mb="${MEM_MB}" \
    --latency-wait "${LATENCY_WAIT}" \
    --keep-going --rerun-incomplete --printshellcmds \
    --stats "logs/snakemake-${SCENARIO}-gurobi.stats.json" 2>&1 | tee -a "$LOGFILE"
}

if [[ "${ARC_STAGE_DATA:-0}" == "1" ]]; then
  mapfile -t AVAILABLE_RULES < <("$SNAKEMAKE" --list)
  stage_targets=()
  for rule in retrieve_databundle_light download_osm_data build_cutout; do
    if printf '%s\n' "${AVAILABLE_RULES[@]}" | grep -qx "$rule"; then
      stage_targets+=("$rule")
    fi
  done
  if [[ ${#stage_targets[@]} -gt 0 ]]; then
    if [[ " ${stage_targets[*]} " == *" retrieve_databundle_light "* ]]; then
      printf 'all\n\n' | "$SNAKEMAKE" --cores "$CPUS" "${stage_targets[@]}" \
        --resources mem_mb="$MEM_MB" --keep-going --rerun-incomplete \
        --latency-wait "$LATENCY_WAIT" \
        "${CONFIG_ARGS[@]}"
    else
      "$SNAKEMAKE" --cores "$CPUS" "${stage_targets[@]}" \
        --resources mem_mb="$MEM_MB" --keep-going --rerun-incomplete \
        --latency-wait "$LATENCY_WAIT" \
        "${CONFIG_ARGS[@]}"
    fi
  fi
fi

if [[ "${ARC_PROFILES_ONLY:-0}" == "1" ]]; then
  echo "ARC_PROFILES_ONLY=1 set; building annual renewable profiles only."
  RUN_NAME="${ARC_RUN_NAME:-}"
  if [[ -z "$RUN_NAME" ]]; then
    LAST_CFG="${CONFIG_FILES[-1]}"
    if [[ -n "$LAST_CFG" && -f "$LAST_CFG" ]]; then
      RUN_NAME=$(
        "$PYPSA_ENV/bin/python" - "$LAST_CFG" <<'PY'
import sys
import yaml

cfg_path = sys.argv[1]
with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
run = cfg.get("run", {}) or {}
print(run.get("name", ""))
PY
      )
    fi
  fi
  PROFILE_TECHS_STR=${ARC_PROFILE_TECHS:-"onwind offwind-ac offwind-dc solar hydro csp"}
  read -r -a PROFILE_TECHS <<< "$PROFILE_TECHS_STR"
  PROFILE_TARGETS=()
  for tech in "${PROFILE_TECHS[@]}"; do
    if [[ -n "$RUN_NAME" ]]; then
      PROFILE_TARGETS+=("resources/${RUN_NAME}/renewable_profiles/profile_${tech}.nc")
    else
      PROFILE_TARGETS+=("resources/renewable_profiles/profile_${tech}.nc")
    fi
  done
  run_snakemake "${PROFILE_TARGETS[@]}" "${CONFIG_ARGS[@]}"
  exit 0
fi

if [[ "${ARC_STAGE_ONLY:-0}" == "1" ]]; then
  echo "ARC_STAGE_ONLY=1 set; skipping full solve."
  exit 0
fi

SNAKE_TARGET=${ARC_SNAKE_TARGET:-solve_all_networks}
SNAKE_ALLOWED_RULES=${ARC_SNAKE_ALLOWED_RULES:-}
SNAKE_FORCE_RULES=${ARC_SNAKE_FORCE_RULES:-}
SNAKE_ARGS=()

if [[ -n "$SNAKE_ALLOWED_RULES" ]]; then
  read -r -a _allowed_rules <<< "$SNAKE_ALLOWED_RULES"
  SNAKE_ARGS+=("--allowed-rules" "${_allowed_rules[@]}")
fi

if [[ -n "$SNAKE_FORCE_RULES" ]]; then
  read -r -a _force_rules <<< "$SNAKE_FORCE_RULES"
  SNAKE_ARGS+=("--forcerun" "${_force_rules[@]}")
fi

run_snakemake "$SNAKE_TARGET" "${CONFIG_ARGS[@]}" "${SNAKE_ARGS[@]}"
