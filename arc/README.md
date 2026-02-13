# ARC Cluster Scripts

This directory contains scripts for running PyPSA-Earth on the Oxford ARC (Advanced Research Computing) cluster.

## Scripts

### `arc_initial_setup.sh`
Interactive setup script for first-time ARC setup.

**What it does:**
- Cleans old pypsa-earth installations
- Clones the repository
- Sets up directory structure
- Checks for Gurobi license
- Submits environment build job

**Usage:**
```bash
ssh <user>@arc-login.arc.ox.ac.uk
cd /data/<group>/<user>
# Copy this script to ARC, then:
bash arc_initial_setup.sh
```

Submission is standardized on a single script:

```bash
sbatch ../arc/jobs/arc_snakemake_gurobi.sh <run-label> <config-file>
```

### `arc_check_run_inputs.sh`
Preflight checker for profile-reuse scenarios (for example week/month runs that point `run.name` to annual resources).

**What it does:**
- Reads `run.name` from the scenario config
- Verifies expected renewable profile files exist in `resources/<run.name>/renewable_profiles/`
- Prints an exact rebuild command if any profiles are missing

**Usage:**
```bash
cd pypsa-earth
../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-week-140.yaml
```

Optional detailed check (prints profile time sizes/ranges):
```bash
ARC_CHECK_TIME_DIMS=1 ../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-week-140.yaml
```

### `build-pypsa-earth-env`
SLURM job script to build the conda environment.

**What it does:**
- Loads Anaconda module
- Creates conda environment from `envs/environment.yaml`
- Installs Gurobi from conda-forge
- Logs installed packages

**Usage:**
```bash
sbatch arc/build-pypsa-earth-env
```

**Resource allocation:**
- Defined in `arc/build-pypsa-earth-env` (`#SBATCH` header).
- Check current values before submitting:
  ```bash
  sed -n '1,40p' arc/build-pypsa-earth-env
  ```

### `jobs/arc_snakemake_gurobi.sh`
SLURM job script to run PyPSA-Earth with Gurobi solver.

**What it does:**
- Loads conda environment
- Sets up Gurobi license
- Runs Snakemake workflow with specified config
- Logs output

**Usage:**
```bash
cd pypsa-earth
sbatch ../arc/jobs/arc_snakemake_gurobi.sh <scenario-name> <config-file> [additional-configs...]
```

**Examples:**
```bash
sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-day-140 configs/scenarios/config.europe-day-140.yaml
```

**Resource allocation:**
- Defined in `arc/jobs/arc_snakemake_gurobi.sh` (`#SBATCH` header).
- Check current values before submitting:
  ```bash
  sed -n '1,40p' arc/jobs/arc_snakemake_gurobi.sh
  ```

**Environment variables you can set:**
- `ARC_ANACONDA_MODULE`: Anaconda module to load (default: Anaconda3/2024.06-1)
- `ARC_PYPSA_ENV`: Path to conda environment
- `PYPSA_SOLVER_NAME`: Solver name (default: gurobi)
- `LINOPY_SOLVER`: Linopy solver (default: gurobi)
- `GRB_LICENSE_FILE`: Gurobi license file path
- `ARC_WORKDIR`: Working directory (default: submission directory)
- `ARC_SNAKE_LATENCY_WAIT`: File system latency wait (default: 60s)
- `ARC_SNAKE_DRYRUN`: Set to 1 for dry run
- `ARC_SNAKE_NOLOCK`: Set to 1 to disable Snakemake locks
- `ARC_SNAKE_UNLOCK`: Set to 1 to unlock before running
- `ARC_STAGE_DATA`: Set to 1 to stage data before main run
- `ARC_SNAKE_TARGET`: Snakemake target (default: solve_all_networks)
- `ARC_SNAKE_ALLOWED_RULES`: Space-separated list passed to `--allowed-rules`
- `ARC_SNAKE_FORCE_RULES`: Space-separated list passed to `--forcerun`

## Directory Structure on ARC

After setup, your ARC workspace will look like:

```
/data/<group>/<user>/
├── pypsa-earth-green-auklet/          # Repository
│   ├── pypsa-earth/                   # Main model code
│   │   ├── Snakefile
│   │   ├── configs/scenarios/
│   │   └── scripts/
│   ├── arc/                           # This directory
│   ├── notebooks/
│   └── results/                       # Results by scenario
│       └── europe-day-140/
├── envs/                              # Conda environments
│   ├── pypsa-earth-env/
│   └── logs/
└── licenses/                          # Solver licenses
    └── gurobi.lic
```

## Workflow

### ARC commands via SSH (Copilot/automation-safe)

Use non-interactive SSH with a single quoted remote command. This is the most reliable pattern for scripted execution from local terminals and AI tooling.

```bash
ssh <user>@arc-login.arc.ox.ac.uk 'cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth && <command>'
```

Examples:

```bash
# Check queue
ssh <user>@arc-login.arc.ox.ac.uk 'squeue -u <user>'

# Validate profile inputs for week reuse
ssh <user>@arc-login.arc.ox.ac.uk 'cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth && ../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-week-140.yaml'

# Submit missing onwind profile rebuild (dedicated profiles config)
ssh <user>@arc-login.arc.ox.ac.uk 'cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth && ARC_PROFILES_ONLY=1 ARC_PROFILE_TECHS="onwind" sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-year-140-profiles configs/scenarios/config.europe-year-140-profiles.yaml'
```

Tips:
- Prefer absolute paths on the remote side.
- Keep the full remote command inside single quotes.
- Use escaped double quotes inside the remote command when needed.
- If SSH auth fails with `Permission denied`, fix key/password setup first; command logic is usually not the issue.

### ARC commands via interactive SSH (password login)

If key-based non-interactive SSH is unavailable, use this sequence and enter your password when prompted:

```bash
ssh <user>@arc-login.arc.ox.ac.uk
cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth
```

Then run ARC commands directly in that shell (no nested ssh needed):

```bash
../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-week-140.yaml
```

Submit directly with `arc_snakemake_gurobi.sh` and env flags (for example `ARC_PROFILES_ONLY`, `ARC_PROFILE_TECHS`, `ARC_SNAKE_TARGET`).

### 1. Initial Setup (Once)
```bash
# On local machine, copy scripts to ARC
scp -r arc <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/

# SSH to ARC
ssh <user>@arc-login.arc.ox.ac.uk

# Run setup
cd /data/<group>/<user>
bash arc/arc_initial_setup.sh

# Wait for environment build to complete
squeue -u <user>
```

### 1b. Sync local custom data (recommended)
`data/` is gitignored and not cloned to ARC. If you have custom CSVs locally, sync them to avoid MissingInput errors:

```bash
# On local machine
rsync -av pypsa-earth/data/custom_*.csv \
    <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth/data/

rsync -av pypsa-earth/data/hydro_capacities.csv \
    pypsa-earth/data/eia_hydro_annual_generation.csv \
    <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth/data/
```

### 2. Submit Runs
```bash
cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth
sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-day-140 configs/scenarios/config.europe-day-140.yaml
```

### 2a. Safe base-profile reuse (week/variant runs)
Keep `run.name` pointing at the base profile directory (for example `europe-year-140`), vary `scenario.opts` for labeling, and ensure `enable.build_cutout: false`.

Preflight first:

```bash
cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth
../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-week-140.yaml
```

If `onwind` (or any technology) is missing, rebuild only the missing profile(s):

```bash
cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth
ARC_PROFILES_ONLY=1 ARC_PROFILE_TECHS="onwind" \
sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-year-140-profiles configs/scenarios/config.europe-year-140-profiles.yaml
```

### 2c. Build annual profiles only (all technologies)

Use dedicated config:

```bash
configs/scenarios/config.europe-year-140-profiles.yaml
```

Run from `pypsa-earth/`:

```bash
ARC_PROFILES_ONLY=1 \
sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-year-140-profiles configs/scenarios/config.europe-year-140-profiles.yaml
```

Outputs are written to:

```bash
resources/europe-year-140/renewable_profiles/profile_*.nc
```

Default 2013-data behavior:

- This workflow uses the 2013 ERA5 cutout configuration by default.
- `retrieve_databundle_light` is the mechanism used by PyPSA-Earth to fetch missing databundle inputs when `enable.retrieve_databundle: true`.
- If databundle selection becomes interactive in batch mode, stage data first to avoid stdin/EOF issues:

```bash
ARC_STAGE_DATA=1 ARC_STAGE_ONLY=1 \
sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-year-140-stage configs/scenarios/config.europe-year-140-profiles.yaml
```

Example safe run with explicit target and restricted rule set:

```bash
cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth
ARC_SNAKE_TARGET="results/europe-year-140/networks/elec_s_140_ec_lcopt_Co2L-3h-week01.nc" \
ARC_SNAKE_ALLOWED_RULES="base_network build_bus_regions build_demand_profiles add_electricity simplify_network cluster_network add_extra_components prepare_network solve_network" \
ARC_SNAKE_FORCE_RULES="base_network build_bus_regions" \
sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-week-140 configs/scenarios/config.europe-week-140.yaml
```

### 2b. Optional: stage OSM data only (faster re-runs)
```bash
cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth
ARC_STAGE_DATA=1 ARC_STAGE_ONLY=1 \
sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-year-140-stage configs/scenarios/config.europe-year-140-stage.yaml
```

To reuse staged data for a day run, copy staged resources:
```bash
cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth
rsync -a --delete resources/europe-year-140-stage/ resources/europe-day-140/
```

### 3. Monitor
```bash
# Check job queue
squeue -u <user>

# Watch log file
tail -f logs/snakemake-europe-day-140-*-gurobi.log

# Check job accounting
sacct -j <jobid> --format=JobID,JobName,State,Elapsed,MaxRSS,NodeList
```

### 4. Download Results
```bash
# On local machine
rsync -av --progress <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/pypsa-earth-green-auklet/results/europe-day-140/ results/europe-day-140/
```

## Troubleshooting

### Environment Build Fails
Check the log:
```bash
cat slurm-<jobid>.out
```

Common issues:
- Network issues: Retry the build
- Package conflicts: Check environment.yaml
- Disk quota: Clean old files

### Job Fails to Start
Check SLURM logs:
```bash
cat slurm-<jobid>.out
```

Common issues:
- Wrong partition: Check available partitions with `sinfo`
- Resource limits: Reduce memory/CPU requirements
- Module not found: Check module availability with `module avail`

### Gurobi License Error
Verify license file:
```bash
cat $GRB_LICENSE_FILE
# Should show license content
```

Set environment variable:
```bash
export GRB_LICENSE_FILE=/data/<group>/<user>/licenses/gurobi.lic
```

### Snakemake Lock Error
Unlock the workflow:
```bash
cd pypsa-earth
snakemake --unlock
# Or set ARC_SNAKE_UNLOCK=1 in job script
```

### Out of Memory
Increase memory in job script:
```bash
#SBATCH --mem=512G
```

Or run on a larger node:
```bash
#SBATCH --partition=large
```

### Files Not Found
Check latency wait setting:
```bash
export ARC_SNAKE_LATENCY_WAIT=120  # Increase to 2 minutes
```

## Cluster Resource Planning

ARC partition limits and queue policies can change. Check current limits and availability directly:

```bash
sinfo -o "%P %.5a %.10l %.6D %.6t %N"
```

For measured runtime and memory on completed jobs, use accounting data instead of fixed estimates:

```bash
sacct -j <jobid> --format=JobID,JobName,State,Elapsed,MaxRSS,NodeList
```

## Best Practices

1. **Test first**: Always run a short test (1 day) before long runs
2. **Monitor actively**: Check logs during first hour of execution
3. **Use dryrun**: Test workflow with `ARC_SNAKE_DRYRUN=1`
4. **Save checkpoints**: Enable Snakemake's `--rerun-incomplete`
5. **Backup results**: Download important results regularly
6. **Clean workspace**: Remove old results to save disk space
7. **Document changes**: Update config comments with run details

## Contact

For ARC-specific issues:
- ARC User Guide: https://arc-user-guide.rc.ox.ac.uk/
- ARC Support: support@arc.ox.ac.uk

For PyPSA-Earth issues:
- Documentation: https://pypsa-earth.readthedocs.io/
- GitHub: https://github.com/pypsa-meets-earth/pypsa-earth
