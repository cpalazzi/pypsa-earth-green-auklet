# ARC Cluster Scripts

This directory contains scripts for running PyPSA-Earth on the Oxford ARC (Advanced Research Computing) cluster.

## Scripts

### `arc_initial_setup.sh`
Interactive setup script for first-time ARC setup.

### `arc_check_run_inputs.sh`
Preflight checker for profile-reuse scenarios.

What it does:
- Reads the scenario config
- Verifies expected renewable profile files in `resources/<run.name>/renewable_profiles/`
- Prints an exact rebuild command if required profiles are missing

Usage:
```bash
cd pypsa-earth
../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-year-140-co2-zero-h2-power.yaml
```

### `build-pypsa-earth-env`
SLURM job script to build the conda environment.

### `jobs/01_build_profiles.sh`
Step 1 submission script.

What it does:
- Builds renewable profiles (Atlite-heavy stage) for the given config
- Uses standard PyPSA-Earth/Snakemake dependency resolution

Usage:
```bash
cd pypsa-earth
sbatch ../arc/jobs/01_build_profiles.sh <run-label> <config-file> [additional-configs...]
```

### `jobs/02_build_networks_and_solve_power.sh`
Step 2 submission script (power workflow).

What it does:
- Runs `solve_all_networks` for non-sector scenarios
- Includes profile preflight checks using `arc_check_run_inputs.sh`
- Supports the H2-power scenario (`Store: [H2]` and `Link: [CCGT H2]`)

Usage:
```bash
cd pypsa-earth
sbatch ../arc/jobs/02_build_networks_and_solve_power.sh <run-label> <config-file> [additional-configs...]
```

Example:
```bash
cd pypsa-earth
sbatch ../arc/jobs/01_build_profiles.sh \
  europe-year-140-profiles \
  configs/scenarios/config.europe-year-140-profiles.yaml

sbatch ../arc/jobs/02_build_networks_and_solve_power.sh \
  europe-year-140-co2-zero-h2-power \
  configs/scenarios/config.europe-year-140-co2-zero-h2-power.yaml
```

## Directory Structure on ARC

```
/data/<group>/<user>/
├── pypsa-earth-green-auklet/
│   ├── pypsa-earth/
│   │   ├── Snakefile
│   │   ├── configs/scenarios/
│   │   └── scripts/
│   ├── arc/
│   ├── notebooks/
│   └── results/
├── envs/
└── licenses/
```

## Workflow

### ARC commands via SSH (automation-safe)

Use non-interactive SSH with one quoted remote command:

```bash
ssh <user>@arc-login.arc.ox.ac.uk 'cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth && <command>'
```

Examples:

```bash
# Check queue
ssh <user>@arc-login.arc.ox.ac.uk 'squeue -u <user>'

# Validate profile inputs
ssh <user>@arc-login.arc.ox.ac.uk 'cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth && ../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-year-140-co2-zero-h2-power.yaml'

# Submit profile build
ssh <user>@arc-login.arc.ox.ac.uk 'cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth && sbatch ../arc/jobs/01_build_profiles.sh europe-year-140-profiles configs/scenarios/config.europe-year-140-profiles.yaml'

# Submit power solve
ssh <user>@arc-login.arc.ox.ac.uk 'cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth && sbatch ../arc/jobs/02_build_networks_and_solve_power.sh europe-year-140-co2-zero-h2-power configs/scenarios/config.europe-year-140-co2-zero-h2-power.yaml'
```

### Interactive SSH

```bash
ssh <user>@arc-login.arc.ox.ac.uk
cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth
```

Then run:

```bash
sbatch ../arc/jobs/01_build_profiles.sh europe-year-140-profiles configs/scenarios/config.europe-year-140-profiles.yaml
sbatch ../arc/jobs/02_build_networks_and_solve_power.sh europe-year-140-co2-zero-h2-power configs/scenarios/config.europe-year-140-co2-zero-h2-power.yaml
```

## Monitor

```bash
squeue -u <user>
tail -f logs/snakemake-*-build-profiles.log
tail -f logs/snakemake-*-solve-power.log
sacct -j <jobid> --format=JobID,JobName,State,Elapsed,MaxRSS,NodeList
```

## Download Results

```bash
rsync -av --progress <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/pypsa-earth-green-auklet/results/europe-year-140/ results/europe-year-140/
```

## Troubleshooting

### Snakemake lock

```bash
cd pypsa-earth
snakemake --unlock
```

### Gurobi license

```bash
echo "$GRB_LICENSE_FILE"
```

### Out of memory
Increase SLURM memory in the job script (`#SBATCH --mem=...`).
