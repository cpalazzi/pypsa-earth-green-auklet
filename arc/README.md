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

Submission now uses a three-step sector workflow:

```bash
sbatch ../arc/jobs/01_build_profiles.sh <run-label> <config-file>
sbatch ../arc/jobs/02_build_sector_data.sh <run-label> <config-file>
sbatch ../arc/jobs/03_build_networks_and_solve_sector.sh <run-label> <config-file>
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

### `jobs/01_build_profiles.sh`
Step 1 submission script.

**What it does:**
- Builds renewable profiles (Atlite-heavy stage) for the given config
- Uses standard PyPSA-Earth/Snakemake dependency resolution and data retrieval behavior

**Usage:**
```bash
cd pypsa-earth
sbatch ../arc/jobs/01_build_profiles.sh <run-label> <config-file> [additional-configs...]
```

### `jobs/02_build_sector_data.sh`
Sector step 2 submission script (precompute sector data + pre-networks).

**What it does:**
- Builds sector-coupled preprocessing outputs up to `override_res_all_nets`
- Uses the same CPU/thread settings as steps 01/02/03
- Performs the same sector input preflight checks as step 03

**Usage:**
```bash
cd pypsa-earth
sbatch ../arc/jobs/02_build_sector_data.sh <run-label> <config-file> [additional-configs...]
```

**Environment variables you can set (advanced):**
- `ARC_ANACONDA_MODULE`: Anaconda module to load (default: Anaconda3/2024.06-1)
- `ARC_PYPSA_ENV`: Path to conda environment
- `PYPSA_SOLVER_NAME`: Solver name (default: gurobi)
- `LINOPY_SOLVER`: Linopy solver (default: gurobi)
- `GRB_LICENSE_FILE`: Gurobi license file path
- `ARC_WORKDIR`: Working directory (default: submission directory)
- `ARC_SNAKE_LATENCY_WAIT`: File system latency wait (default: 60s)

### `jobs/03_build_networks_and_solve_sector.sh`
Sector-coupled solve submission script.

**What it does:**
- Runs `solve_sector_networks` for a sector-coupled scenario config
- Supports hydrogen coupling and export wildcard handling from config

**Usage:**
```bash
cd pypsa-earth
sbatch ../arc/jobs/03_build_networks_and_solve_sector.sh <run-label> <config-file> [additional-configs...]
```

Example:
```bash
cd pypsa-earth
sbatch ../arc/jobs/02_build_sector_data.sh \
  europe-year-140-co2-zero-h2-sector-prep \
  configs/scenarios/config.europe-year-140-co2-zero-h2-sector.yaml

sbatch ../arc/jobs/03_build_networks_and_solve_sector.sh \
  europe-year-140-co2-zero-h2-sector \
  configs/scenarios/config.europe-year-140-co2-zero-h2-sector.yaml
```

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

# Submit Step 1 build-profiles run
ssh <user>@arc-login.arc.ox.ac.uk 'cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth && sbatch ../arc/jobs/01_build_profiles.sh europe-year-140-profiles configs/scenarios/config.europe-year-140-profiles.yaml'
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

Submit directly with `01_build_profiles.sh` for Step 1, `02_build_sector_data.sh` for Step 2, and `03_build_networks_and_solve_sector.sh` for Step 3.

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

# Sector-coupled full pre-sync (recommended for `03_build_networks_and_solve_sector.sh`)
# Rationale: ARC clone does not include local `data/` and `cutouts/` content,
# and electricity-only runs may not reveal these missing sector inputs.
rsync -av pypsa-earth/data/demand/ \
  <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth/data/demand/

rsync -av pypsa-earth/data/emobility/ \
  <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth/data/emobility/

rsync -av pypsa-earth/data/heat_load_profile_BDEW.csv \
  <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth/data/

rsync -av pypsa-earth/data/unsd_transactions.csv \
  <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth/data/

rsync -av pypsa-earth/cutouts/cutout-2013-era5.nc \
  <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth/cutouts/
```

### 2. Recommended three-step sector workflow

Run all commands from:

```bash
cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth
```

#### Step 1: Build renewable profiles (Atlite-heavy stage)

Submit build-profiles job:

```bash
sbatch ../arc/jobs/01_build_profiles.sh \
  europe-year-140-profiles \
  configs/scenarios/config.europe-year-140-profiles.yaml
```

Verify expected profile outputs after Step 1:

```bash
../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-week-140.yaml
ls -lh resources/europe-year-140/renewable_profiles/profile_*.nc
```

#### Step 2: Build sector preprocessing data (reuses profiles from Step 1)

```bash
sbatch ../arc/jobs/02_build_sector_data.sh \
  europe-year-140-co2-zero-h2-sector-prep \
  configs/scenarios/config.europe-year-140-co2-zero-h2-sector.yaml
```

#### Step 3: Build + solve sector network

```bash
sbatch ../arc/jobs/03_build_networks_and_solve_sector.sh \
  europe-year-140-co2-zero-h2-sector \
  configs/scenarios/config.europe-year-140-co2-zero-h2-sector.yaml
```

Conditional dependency-chained submission examples are documented only in `DEVELOPMENT_NOTES.md`.

### 3. Monitor
```bash
# Check job queue
squeue -u <user>

# Watch log file
tail -f logs/snakemake-*-build-profiles.log
tail -f logs/snakemake-*-build-networks.log

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
3. **Use dryrun**: Test workflow with `snakemake -n <target> --configfile <config>`
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
