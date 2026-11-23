#!/bin/bash
# Preflight check for profile reuse runs (e.g. week/month using annual profiles).
#
# Usage:
#   cd pypsa-earth
#   ../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-week-140.yaml
#
# It checks the profiles that add_electricity reads: one for each of the config's
# electricity.renewable_carriers that has a section under `renewable`, with the config merged over
# config.default.yaml and config.yaml as Snakemake merges them.
#
# Optional env vars:
#   ARC_PROFILE_TECHS="onwind offwind-ac offwind-dc solar hydro"  # check these profiles instead
#   ARC_CHECK_TIME_DIMS=1

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <config-file>" >&2
  exit 2
fi

CONFIG_FILE="$1"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "ERROR: Config file not found: $CONFIG_FILE" >&2
  exit 2
fi

if [[ ! -f "Snakefile" ]]; then
  echo "ERROR: Run this from the pypsa-earth directory (where Snakefile is)." >&2
  exit 2
fi

PYTHON_BIN="${ARC_PYTHON_BIN:-python}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "ERROR: python/python3 not found in PATH." >&2
    exit 2
  fi
fi

CONFIG_VALUES=$(
  "$PYTHON_BIN" - "$CONFIG_FILE" <<'PY'
import sys
from pathlib import Path

try:
    import yaml
except Exception as exc:
    print(f"__YAML_IMPORT_ERROR__:{exc}")
    raise SystemExit(0)


def merge(base, new):
    for key, value in new.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merge(base[key], value)
        else:
            base[key] = value
    return base


cfg = {}
for path in ["config.default.yaml", "config.yaml", sys.argv[1]]:
    if Path(path).is_file():
        with open(path, encoding="utf-8") as f:
            merge(cfg, yaml.safe_load(f) or {})

carriers = (cfg.get("electricity") or {}).get("renewable_carriers") or []
renewable = cfg.get("renewable") or {}
print((cfg.get("run") or {}).get("name", ""))
print(" ".join(c for c in carriers if c in renewable))
PY
)

if [[ "$CONFIG_VALUES" == __YAML_IMPORT_ERROR__:* ]]; then
  echo "ERROR: Could not import PyYAML with $PYTHON_BIN." >&2
  echo "Install PyYAML or run from the project environment." >&2
  exit 2
fi

RUN_NAME=""
CONFIG_TECHS=""
{ read -r RUN_NAME; read -r CONFIG_TECHS; } <<< "$CONFIG_VALUES" || true

if [[ -z "$RUN_NAME" ]]; then
  echo "ERROR: run.name is not set in $CONFIG_FILE" >&2
  exit 2
fi

PROFILE_TECHS_STR="$CONFIG_TECHS"
PROFILE_SOURCE="electricity.renewable_carriers"
if [[ -n "${ARC_PROFILE_TECHS:-}" ]]; then
  PROFILE_TECHS_STR="$ARC_PROFILE_TECHS"
  PROFILE_SOURCE="ARC_PROFILE_TECHS"
fi
if [[ -z "$PROFILE_TECHS_STR" ]]; then
  echo "No renewable carriers need profiles (electricity.renewable_carriers); nothing to check."
  exit 0
fi
read -r -a PROFILE_TECHS <<< "$PROFILE_TECHS_STR"

PROFILE_DIR="resources/${RUN_NAME}/renewable_profiles"
PROFILE_CONFIG_CANDIDATE="configs/scenarios/config.${RUN_NAME}-profiles.yaml"
STAGE_CONFIG_CANDIDATE="configs/scenarios/config.${RUN_NAME}-stage.yaml"
if [[ -f "$PROFILE_CONFIG_CANDIDATE" ]]; then
  DEFAULT_PROFILE_BUILD_CONFIG="$PROFILE_CONFIG_CANDIDATE"
elif [[ -f "$STAGE_CONFIG_CANDIDATE" ]]; then
  DEFAULT_PROFILE_BUILD_CONFIG="$STAGE_CONFIG_CANDIDATE"
else
  DEFAULT_PROFILE_BUILD_CONFIG="$CONFIG_FILE"
fi

echo "Preflight profile check"
echo "  Config:   $CONFIG_FILE"
echo "  run.name: $RUN_NAME"
echo "  Profile dir: $PROFILE_DIR"
echo "  Profiles:    ${PROFILE_TECHS[*]} (from $PROFILE_SOURCE)"
echo

if [[ ! -d "$PROFILE_DIR" ]]; then
  echo "ERROR: Profile directory does not exist: $PROFILE_DIR" >&2
  echo "Build profiles first, for example:" >&2
  PROFILE_BUILD_CONFIG=${ARC_PROFILE_BUILD_CONFIG:-$DEFAULT_PROFILE_BUILD_CONFIG}
  echo "  ARC_PROFILES_ONLY=1 sbatch ../arc/jobs/arc_snakemake_gurobi.sh ${RUN_NAME}-profiles $PROFILE_BUILD_CONFIG" >&2
  exit 1
fi

missing=()
present=()
for tech in "${PROFILE_TECHS[@]}"; do
  f="$PROFILE_DIR/profile_${tech}.nc"
  if [[ -f "$f" ]]; then
    present+=("$tech")
  else
    missing+=("$tech")
  fi
done

echo "Present profiles: ${present[*]:-(none)}"
if [[ ${#missing[@]} -gt 0 ]]; then
  PROFILE_BUILD_CONFIG=${ARC_PROFILE_BUILD_CONFIG:-$DEFAULT_PROFILE_BUILD_CONFIG}
  echo "Missing profiles: ${missing[*]}"
  echo
  if [[ "$CONFIG_FILE" == *week* || "$CONFIG_FILE" == *day* || "$CONFIG_FILE" == *month* ]]; then
    echo "Note: this config appears to be a short-horizon run."
    echo "If you intend to regenerate shared annual profiles, set ARC_PROFILE_BUILD_CONFIG to an annual staging config."
    echo
  fi
  echo "Rebuild missing profiles with:"
  echo "  ARC_PROFILE_BUILD_CONFIG=${PROFILE_BUILD_CONFIG} ARC_PROFILES_ONLY=1 ARC_PROFILE_TECHS=\"${missing[*]}\" sbatch ../arc/jobs/arc_snakemake_gurobi.sh ${RUN_NAME}-profiles-missing ${PROFILE_BUILD_CONFIG}"
  exit 1
fi

echo "Missing profiles: (none)"

if [[ "${ARC_CHECK_TIME_DIMS:-0}" == "1" ]]; then
  echo
  echo "Inspecting time dimensions (best effort)..."
  "$PYTHON_BIN" - "$PROFILE_DIR" "${PROFILE_TECHS[@]}" <<'PY'
import sys
from pathlib import Path

profile_dir = Path(sys.argv[1])
techs = sys.argv[2:]

try:
    import xarray as xr
except Exception:
    print("  xarray not available; skipping time-dimension checks")
    raise SystemExit(0)

for tech in techs:
    path = profile_dir / f"profile_{tech}.nc"
    if not path.exists():
      continue
    try:
      ds = xr.open_dataset(path)
      t = ds.get("time")
      if t is not None and t.size > 0:
        print(f"  {tech}: time={t.size}, start={str(t.values[0])}, end={str(t.values[-1])}")
      else:
        print(f"  {tech}: no time coordinate found")
      ds.close()
    except Exception as exc:
      print(f"  {tech}: could not inspect ({exc})")
PY
fi

echo
echo "OK: required profile files are in place."
